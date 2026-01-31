import asyncio
from app.agents.ai_agents import (
    get_ai_agents_by_ids,
    product_manager,
    contract_agent,
)
from app.agents.manage_repo.github_deploy_service import GitHubDeployService
from .manage_repo.repo_command_processor import RepoCommandProcessor
from .manage_repo.repository_service import RepositoryService
from typing import AsyncGenerator, Dict
import uuid

from app.agents.context.build_agent_context import build_agent_context
from app.agents.context.project_context_service import ProjectContextService
from app.agents.prompts import generate_agent_prompt

from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_agentchat.base import TaskResult

from app.logger.console_logger import info, error
from app.status.enums import AgentTask, ProjectStage
import app.status.status_helpers as status


repo_services: Dict[uuid.UUID, RepositoryService] = {}


# =====================
# Helpers: PM + Contract
# =====================

def _tz_done(text: str) -> bool:
    # В PM prompt финальная строка: "ТЗ завершено"
    return "ТЗ завершено" in text


def _build_pm_task(user_message: str, history: list[dict]) -> str:
    ctx = "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('message', '')}"
        for msg in history[-10:]
        if msg.get("message")
    )
    return (
        f"Контекст:\n{ctx}\n\n"
        f"Пользователь прислал сообщение: {user_message}\n\n"
        "Продолжи диалог или если нет контекста, собери полное техническое задание. "
        "Отвечай как будто ты человек."
    )


def _build_contract_task(project_id: uuid.UUID, specification: str) -> str:
    return (
        f"project_id: {project_id}\n\n"
        "Требуется сделать из технического задания контракт.\n"
        "ТЕХНИЧЕСКОЕ ЗАДАНИЕ:\n"
        f"{specification}\n"
        "На выходе требуется один объект в формате json без markdown. Соблюдай обший формат"
    )


# =====================
# PM Stream
# =====================

async def run_product_manager_stream(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    await status.set_stage(project_id, ProjectStage.PM_TZ, 0)

    task = _build_pm_task(user_message, history)

    async for msg in product_manager.run_stream(task=task):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            content = getattr(msg, "content", "")
            if content:
                yield content


# =====================
# Contract build (one-shot)
# =====================

async def build_contract(project_id, specification) -> str:
    result = await contract_agent.run(task=_build_contract_task(project_id, specification))

    if isinstance(result, TaskResult) and result.messages:
        return (result.messages[-1].source or "").strip()
    return (result if isinstance(result, str) else str(result)).strip()


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if "```" in t:
            t = t.rsplit("```", 1)[0]
    return t.strip()


# =====================
# Repo services
# =====================

def _get_repo_service(project_id: uuid.UUID) -> RepositoryService:
    if project_id not in repo_services:
        repo_services[project_id] = RepositoryService(project_id)
    return repo_services[project_id]


# =====================
# Agent context rebuild
# =====================

async def _rebuild_agent_context(agent, project_id: uuid.UUID, task: str):
    """
    Полностью пересобирает контекст агента
    """
    new_ctx = await build_agent_context(
        agent_name=agent.name,
        project_id=project_id,
        task=task,
    )

    await agent.model_context.clear()

    for msg in await new_ctx.get_messages():
        await agent.model_context.add_message(msg)


# =====================
# Agents execution (sequential, no chat)
# =====================

async def run_ai_agents(
    specification: str,
    agent_ids: list[str],
    project_id: uuid.UUID,
):
    repo_service = _get_repo_service(project_id)
    context_service = ProjectContextService(project_id)
    participants = get_ai_agents_by_ids(agent_ids)
    deploy_service = GitHubDeployService(
        repo_service.manager.token,
        repo_service.manager.user.name,
        repo_service.manager.repo_name
    )

    await status.set_stage(project_id, ProjectStage.ANALYSIS, 100)
    await status.set_stage(project_id, ProjectStage.CODING, 0)

    processor = RepoCommandProcessor()
    repo_update_started = False

    for idx, agent in enumerate(participants):
        prompt = generate_agent_prompt(
            specification=specification,
            role=agent.name,
        )
        await status.agent_working(project_id, agent.name, AgentTask.ANALYZING_SPEC)
        await _rebuild_agent_context(agent, project_id, task=prompt)
        await status.agent_live(project_id, agent.name, AgentTask.GENERATING_CODE)

        result = await agent.run(task=prompt)
        task_result = result if isinstance(result, TaskResult) else result

        await status.set_stage(project_id, ProjectStage.CODING, None)

        info(f"[TEAM] response {agent.name} agent: {task_result}")

        commands = processor.parse_task_result(task_result)

        info(f"[TEAM] {agent.name}: {commands}")

        if not repo_update_started:
            repo_update_started = True
            await status.set_stage(project_id, ProjectStage.REPO_UPDATE, 0)

        context_service.apply_operations(commands)
        sha_commit = repo_service.push(commands) or ''

        res = await asyncio.to_thread(
            deploy_service.wait_build_and_get_error_text,
            head_sha=sha_commit,
            include_raw_logs=False,
        )

        if res.ok:
            error(f"[HANDLE_BUILD]OK: {res.run_url}")
        else:
            error("[HANDLE_BUILD] FAILED: {res.conclusion}, {res.run_url}")
            error(res.error_text)

        await status.agent_completed(project_id, agent.name)
        await status.set_stage(project_id, ProjectStage.CODING, int(((idx + 1) / len(participants)) * 100))

    await status.set_stage(project_id, ProjectStage.REPO_UPDATE, 100)


async def get_ai_response(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    tz_buffer: list[str] = []
    specification: str | None = None

    try:
        async for token in run_product_manager_stream(project_id, user_message, history):
            yield token

            tz_buffer.append(token)
            full_pm_text = "".join(tz_buffer)

            if _tz_done(full_pm_text):
                specification = full_pm_text
                await status.set_stage(project_id, ProjectStage.PM_TZ, 100)
                break

    except Exception as pm_error:
        await status.set_error(project_id)
        info(f"[PM ERROR] {type(pm_error).__name__}: {pm_error}")
        yield f"\n❌ Ошибка в модуле Product Manager.\nПричина: {pm_error}\n"
        return

    # PM ещё не закончил — просто возвращаемся (диалог продолжится)
    if specification is None:
        await status.set_stage(project_id, ProjectStage.PM_TZ, 0)
        return

    # 2) Contract build
    info(f"[TEAM] start working {specification}")
    yield "\n\n📐 Отдаю техническое задание команде...\n\n"

    try:
        contract_text = await build_contract(project_id, specification)
    except Exception as contract_error:
        error(
            f"[CONTRACT ERROR] {type(contract_error).__name__}: {contract_error}")
        await status.set_error(project_id)
        yield f"\n❌ Ошибка при формировании контракта.\nПричина: {contract_error}\n"
        return

    info(f"[CONTRACT AGENT] {_strip_json_fences(contract_text)}")

    try:
        await run_ai_agents(
            specification=_strip_json_fences(contract_text),
            agent_ids=["interface", "frontend", "backend"],
            project_id=project_id,
        )
    except Exception as team_error:
        error(f"[TEAM ERROR] {type(team_error).__name__}: {team_error}")
        await status.set_error(project_id)
        yield (
            f"\n❌ В процессе выполнения командной работы произошла ошибка.\n"
            f"Причина: {team_error}\n"
            f"Команда остановлена.\n"
        )
        return

    await status.set_completed(project_id)

    info_obj = _get_repo_service(project_id).info()

    info(f"\n🎉 Команда завершила работу. Репозиторий обновлён.\n\n")

    yield (
        f"\n🎉 Команда завершила работу. Репозиторий обновлён.\n\n"
        f"[Ссылка на проект]({info_obj['pages_link']})"
    )
