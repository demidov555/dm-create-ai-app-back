from typing import AsyncGenerator, Dict
import uuid

from app.agents.ai_agents import (
    get_ai_agents_by_ids,
    product_manager,
    parse_product_manager_response,
    LangGraphAssistantAgent,
    AgentTaskResult,
)
from app.agents.manage_repo.github_deploy_service import GitHubDeployService, WorkflowResult
from .manage_repo.repo_command_processor import RepoCommandProcessor
from .manage_repo.repository_service import RepositoryService

from app.agents.context.build_agent_context import build_agent_context
from app.agents.context.project_context_service import ProjectContextService
from app.agents.prompts import build_fix_prompt, generate_agent_prompt

from app.logger.console_logger import info, error
from app.status.enums import AgentTask, ProjectStage
import app.status.status_helpers as status


BUILD_CHECK_AGENTS: set[str] = {"Frontend"}


class BuildFailed(Exception):
    pass


max_fix_rounds = 5
repo_services: Dict[uuid.UUID, RepositoryService] = {}


def _build_pm_task(user_message: str, history: list[dict]) -> str:
    ctx = "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('message', '')}"
        for msg in history[-10:]
        if msg.get("message")
    )

    return (
        f"Контекст последних сообщений:\n{ctx}\n\n"
        f"Новое сообщение пользователя:\n{user_message}\n\n"
        "Продолжи диалог как Product Manager. "
        "Если данных недостаточно — задай уточняющий вопрос. "
        "Если ТЗ готово — верни JSON для запуска агентов. "
        "Если пользователь просит правку после работы агентов — верни revise_agents."
    )


async def run_product_manager_router(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
):
    await status.set_stage(project_id, ProjectStage.PM_TZ, 0)

    task = _build_pm_task(user_message, history)
    result = await product_manager.run(task=task)

    if not result.messages:
        raise ValueError("ProductManager не вернул ответ")

    raw_pm_text = result.messages[-1].content
    return parse_product_manager_response(raw_pm_text)


def _get_repo_service(project_id: uuid.UUID) -> RepositoryService:
    if project_id not in repo_services:
        repo_services[project_id] = RepositoryService(project_id)

    return repo_services[project_id]


async def _rebuild_agent_context(
    agent: LangGraphAssistantAgent,
    project_id: uuid.UUID,
    task: str,
):
    return await build_agent_context(
        agent_name=agent.name,
        project_id=project_id,
        task=task,
    )


async def _wait_and_get_build(
    deploy_service: GitHubDeployService,
    project_id: uuid.UUID,
    agent_name: str,
    head_sha: str,
) -> WorkflowResult:
    info(f"[_wait_and_get_build]: {agent_name}")

    build = await deploy_service.submit_build(
        project_id=str(project_id),
        agent_name=agent_name,
        head_sha=head_sha,
    )

    return await build


async def _run_agent_and_get_result(
    project_id: uuid.UUID,
    agent: LangGraphAssistantAgent,
    task: str,
):
    ctx_messages = await _rebuild_agent_context(
        agent,
        project_id,
        task=task,
    )

    await status.agent_live(
        project_id,
        agent.name,
        AgentTask.GENERATING_CODE,
    )

    result = await agent.run(
        task=task,
        context_messages=ctx_messages,
    )

    await status.set_stage(project_id, ProjectStage.CODING, None)

    return result if isinstance(result, AgentTaskResult) else result


async def _check_build_on_success(
    agent: LangGraphAssistantAgent,
    specification: str,
    project_id: uuid.UUID,
    repo_service: RepositoryService,
    context_service: ProjectContextService,
    processor: RepoCommandProcessor,
    deploy_service: GitHubDeployService,
    commands: list,
) -> str:
    def push_or_raise(cmds: list) -> str:
        context_service.apply_operations(cmds)
        sha = repo_service.push(cmds)

        if not sha:
            raise BuildFailed("push failed (no sha)")

        return sha

    sha = push_or_raise(commands)
    info(f"[BUILD] sha: {sha}")

    build = await _wait_and_get_build(
        deploy_service,
        project_id=project_id,
        agent_name=agent.name,
        head_sha=sha,
    )

    if build.ok:
        return sha

    error(f"[BUILD] is ok: {build.ok}")

    for round_idx in range(1, max_fix_rounds + 1):
        fix_task = build_fix_prompt(
            specification,
            agent.name,
            build,
        )

        fix_agent_result = await _run_agent_and_get_result(
            project_id,
            agent,
            fix_task,
        )

        fix_commands = processor.parse_task_result(fix_agent_result)
        sha = push_or_raise(fix_commands)

        info(f"[BUILD] retry fix build sha: {sha}")

        build = await _wait_and_get_build(
            deploy_service,
            project_id=project_id,
            agent_name=agent.name,
            head_sha=sha,
        )

        if build.ok:
            return sha

    raise BuildFailed(
        f"Build still failing after {max_fix_rounds} fix rounds. "
        f"Last run: {build.run_url}, conclusion={build.conclusion}"
    )


async def run_ai_agents(
    specification: str,
    agent_ids: list[str],
    project_id: uuid.UUID,
):
    repo_service = _get_repo_service(project_id)
    context_service = ProjectContextService(project_id)

    deploy_service = GitHubDeployService(
        repo_service.manager.token,
        repo_service.manager.user.login,
        repo_service.manager.repo_name or "",
    )

    participants = get_ai_agents_by_ids(agent_ids)

    await status.set_stage(project_id, ProjectStage.ANALYSIS, 100)
    await status.set_stage(project_id, ProjectStage.CODING, 0)

    processor = RepoCommandProcessor()
    repo_update_started = False

    for idx, agent in enumerate(participants):
        prompt = generate_agent_prompt(
            specification=specification,
            role=agent.name,
        )

        await status.agent_working(
            project_id,
            agent.name,
            AgentTask.ANALYZING_SPEC,
        )

        agent_result = await _run_agent_and_get_result(
            project_id,
            agent,
            prompt,
        )

        info(f"[AI_AGENT][{agent.name}] AI response: {agent_result}")

        commands = processor.parse_task_result(agent_result)
        info(f"[AI_AGENT][{agent.name}] parse a task for git: {commands}")

        if not repo_update_started:
            repo_update_started = True
            await status.set_stage(project_id, ProjectStage.REPO_UPDATE, 0)

        if agent.name in BUILD_CHECK_AGENTS:
            await _check_build_on_success(
                agent=agent,
                specification=specification,
                project_id=project_id,
                repo_service=repo_service,
                context_service=context_service,
                processor=processor,
                deploy_service=deploy_service,
                commands=commands,
            )
        else:
            context_service.apply_operations(commands)
            repo_service.push(commands)

        await status.agent_completed(project_id, agent.name)

        await status.set_stage(
            project_id,
            ProjectStage.CODING,
            int(((idx + 1) / len(participants)) * 100),
        )

    await status.set_stage(project_id, ProjectStage.REPO_UPDATE, 100)


async def get_ai_response(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    try:
        pm_result = await run_product_manager_router(
            project_id=project_id,
            user_message=user_message,
            history=history,
        )

    except Exception as pm_error:
        await status.set_error(project_id)
        info(f"[PM ERROR] {type(pm_error).__name__}: {pm_error}")

        yield (
            "\n❌ Ошибка в модуле Product Manager.\n"
            f"Причина: {pm_error}\n"
        )
        return

    if pm_result.action == "ask_clarification":
        await status.set_stage(project_id, ProjectStage.PM_TZ, 0)

        yield (
            pm_result.clarification_question
            or "Уточните задачу подробнее."
        )
        return

    if pm_result.action == "answer_user":
        yield pm_result.answer or "Хорошо."
        return

    if pm_result.action not in {"run_agents", "revise_agents"}:
        await status.set_error(project_id)
        yield "Не удалось определить дальнейшее действие."
        return

    specification = pm_result.technical_specification

    if not specification:
        await status.set_error(project_id)
        yield "Product Manager не вернул техническое задание."
        return

    await status.set_stage(project_id, ProjectStage.PM_TZ, 100)

    if pm_result.action == "run_agents":
        yield "\n\n📐 Техническое задание собрано. Отдаю задачу команде...\n\n"
    else:
        yield "\n\n🔧 Правка принята. Передаю изменения нужным агентам...\n\n"

    info(f"[TEAM] task: {specification}")

    agent_ids = pm_result.required_agents or ["frontend"]

    try:
        await run_ai_agents(
            specification=specification,
            agent_ids=agent_ids,
            project_id=project_id,
        )

    except Exception as team_error:
        error(f"[TEAM ERROR] {type(team_error).__name__}: {team_error}")
        await status.set_error(project_id)

        yield (
            "\n❌ В процессе выполнения командной работы произошла ошибка.\n"
            f"Причина: {team_error}\n"
            "Команда остановлена.\n"
        )
        return

    await status.set_completed(project_id)

    info_obj = _get_repo_service(project_id).info()

    info("\n🎉 Команда завершила работу. Репозиторий обновлён.\n\n")

    yield (
        "\n🎉 Команда завершила работу. Репозиторий обновлён.\n\n"
        f"[Ссылка на проект]({info_obj['pages_link']})"
    )
