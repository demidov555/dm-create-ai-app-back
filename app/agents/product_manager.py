from typing import AsyncGenerator, Dict
import uuid
from app.agents.chat_conditions.crcular_loop_termination import CircularLoopTermination
from app.agents.context.build_agent_context import build_agent_context
from app.agents.context.project_context_service import ProjectContextService
from app.agents.mock_task_result import create_mock_task_result
from app.agents.prompts import generate_team_prompt
from app.agents.chat_conditions.team_done_termination import TeamDoneTermination

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from autogen_agentchat.base import TaskResult

from app.logger.console_logger import info, success, error
from app.status.enums import AgentStatus, AgentTask, ProjectStage, ProjectStatus
from app.status.status_service import StatusService

from .manage_repo.repository_service import RepositoryService
from .manage_repo.repo_command_processor import RepoCommandProcessor

from app.agents.ai_agents import (
    get_ai_agents_by_ids,
    product_manager,
)

from app.agents.mock_task_result import mock


repo_services: Dict[uuid.UUID, RepositoryService] = {}


async def run_product_manager_stream(
    project_id: uuid.UUID, user_message: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    await StatusService.set_project_status(project_id, ProjectStatus.IN_PROGRESS)
    ctx = "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('message', '')}"
        for msg in history[-10:]
        if msg.get("message")
    )

    task = (
        f"Контекст:\n{ctx}\n\n"
        f"Пользователь прислал сообщение: {user_message}\n\n"
        "Продолжи диалог или если нет контекста, собери полное техническое задание. "
        "Отвечай как будто ты человек."
    )

    async for msg in product_manager.run_stream(task=task):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            content = getattr(msg, "content", "")
            if content:
                yield content


async def run_ai_team_work_stream(
    specification: str, agent_ids: list[str], project_id: uuid.UUID
):
    if project_id not in repo_services:
        repo_services[project_id] = RepositoryService(project_id)

    repo_service = repo_services[project_id]
    context_service = ProjectContextService(project_id)
    participants = get_ai_agents_by_ids(agent_ids)
    participant_names = [p.name for p in participants]
    prompt = generate_team_prompt(specification, participant_names)

    for agent in participants:
        await StatusService.set_agent_status(
            project_id,
            agent_id=agent.name,
            status=AgentStatus.WORKING,
            current_task=AgentTask.ANALYZING_SPEC,
        )
        await _rebuild_agent_context(agent, project_id, task=prompt)

    # await StatusService.set_project_status(project_id, ProjectStatus.IN_PROGRESS)
    chat = RoundRobinGroupChat(
        participants=participants,
        termination_condition=(
            TeamDoneTermination(expected_roles=participant_names)
            | MaxMessageTermination(50)
            | CircularLoopTermination(lookback=6, similarity_threshold=0.97)
        ),
    )

    task_result: TaskResult | None = None

     # ANALYSIS DONE
    await StatusService.set_project_status(
        project_id,
        ProjectStatus.IN_PROGRESS,
        stage=ProjectStage.ANALYSIS,
        stage_progress=100
    )
    # CODING START
    await StatusService.set_project_status(
        project_id,
        ProjectStatus.IN_PROGRESS,
        stage=ProjectStage.CODING,
        stage_progress=0
    )

    info("[TEAM] Запускаю командную работу (stream)...")
    async for event in chat.run_stream(task=prompt):
        if hasattr(event, "content"):
            text = (event.content or "").strip()
            src_obj = getattr(event, "source", None)
            src = getattr(src_obj, "name", src_obj) or "system"

            if src == "user":
                continue

            if text:
                info(f"[TEAM][MSG] {src}:\n{text}")
                await StatusService.push_agent_live_status(
                    project_id,
                    agent_id=src,
                    status=AgentStatus.WORKING,
                    current_task=AgentTask.GENERATING_CODE,
                )
                # CODING LIVE PROGRESS (если нет процентов, можно не указывать)
                await StatusService.set_project_status(
                    project_id,
                    ProjectStatus.IN_PROGRESS,
                    stage=ProjectStage.CODING,
                    stage_progress=None
                )


        elif isinstance(event, TaskResult):
            task_result = event
            # CODING DONE
            await StatusService.set_project_status(
                project_id,
                ProjectStatus.IN_PROGRESS,
                stage=ProjectStage.CODING,
                stage_progress=100
            )

            info("[TEAM] Получен TaskResult")

    for agent in participants:
        await StatusService.set_agent_status(
            project_id,
            agent_id=agent.name,
            status=AgentStatus.COMPLETED,
            current_task=AgentTask.FINALIZING,
            progress=100,
        )

    try:
        processor = RepoCommandProcessor()
        commands = processor.parse_task_result(task_result)
        # REPO UPDATE START
        await StatusService.set_project_status(
            project_id,
            ProjectStatus.IN_PROGRESS,
            stage=ProjectStage.REPO_UPDATE,
            stage_progress=0
        )

        context_service.apply_operations(commands)
        # repo_service.push(commands)
        # REPO UPDATE DONE
        await StatusService.set_project_status(
            project_id,
            ProjectStatus.IN_PROGRESS,
            stage=ProjectStage.REPO_UPDATE,
            stage_progress=100
        )


    except Exception as e:
        error(f"[TEAM] Ошибка при применении команд: {type(e).__name__}: {e}")
        await StatusService.set_project_status(project_id, ProjectStatus.ERROR)
        raise e

    await StatusService.set_project_status(project_id, ProjectStatus.COMPLETED)


async def _rebuild_agent_context(agent, project_id, task: str):
    """
    Полностью пересобирает контекст агента:
    """

    # строим новый временный контекст
    new_ctx = await build_agent_context(
        agent_name=agent.name,
        project_id=project_id,
        task=task,
    )

    # очищаем старый контекст агента
    await agent.model_context.clear()

    # переносим новые сообщения
    for msg in await new_ctx.get_messages():
        await agent.model_context.add_message(msg)


async def get_ai_response(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    tz_buffer = []
    specification = None

    try:
        async for token in run_product_manager_stream(
            project_id, user_message, history
        ):
            yield token

            tz_buffer.append(token)
            full_pm_text = "".join(tz_buffer)

            # PM сформировал ТЗ → выходим из цикла
            if "ТЗ завершено!" in full_pm_text:
                specification = full_pm_text

                # PM DONE
                await StatusService.set_project_status(
                    project_id,
                    ProjectStatus.IN_PROGRESS,
                    stage=ProjectStage.PM_TZ,
                    stage_progress=100
                )

                break

    except Exception as pm_error:
        await StatusService.set_project_status(project_id, ProjectStatus.ERROR)
        info(f"[PM ERROR] {type(pm_error).__name__}: {pm_error}")
        yield (f"\n❌ Ошибка в модуле Product Manager.\n" f"Причина: {pm_error}\n")
        return

    if specification is None:
        # yield (
        #     "\n⚠️ Product Manager не смог сформировать техническое задание.\n"
        #     "Попробуйте переформулировать запрос.\n"
        # )
        # await StatusService.set_project_status(project_id, ProjectStatus.IN_PROGRESS)
        # PM START
        await StatusService.set_project_status(
            project_id,
            ProjectStatus.IN_PROGRESS,
            stage=ProjectStage.PM_TZ,
            stage_progress=0
        )
        return

    yield "\n\nТехническое задание сформировано. Запускаю работу команды...\n\n"

    try:
        await run_ai_team_work_stream(
            specification=specification,
            agent_ids=["frontend", "backend"],
            project_id=project_id,
        )

    except Exception as team_error:
        error(f"[TEAM ERROR] {type(team_error).__name__}: {team_error}")
        await StatusService.set_project_status(project_id, ProjectStatus.ERROR)
        yield (
            f"\n❌ В процессе выполнения командной работы произошла ошибка.\n"
            f"Причина: {team_error}\n"
            f"Команда остановлена.\n"
        )
        return

    info = repo_services[project_id].info()
    yield f"\nКоманда завершила работу. Репозиторий обновлён.\n\n[Ссылка на проект]({info['pages_link']})"
