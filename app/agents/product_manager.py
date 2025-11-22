import asyncio
from pprint import pprint
from typing import AsyncGenerator, Dict
import uuid
from app.logger import Spinner, line, info, step, success, error

from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.messages import ModelClientStreamingChunkEvent

from .manage_repo.repository_service import RepositoryService
from .manage_repo.repo_command_processor import RepoCommandProcessor
from .manage_repo.command_executor import CommandExecutor

from app.agents.ai_agents import (
    get_ai_agents_by_ids,
    product_manager,
)

repo_services: Dict[uuid.UUID, RepositoryService] = {}


async def run_product_manager_stream(
    user_message: str, history: list[dict]
) -> AsyncGenerator[str, None]:
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


async def run_ai_team_work(
    specification: str, agent_ids: list[str], project_id: uuid.UUID
):
    if project_id not in repo_services:
        repo_services[project_id] = RepositoryService(project_id)

    service = repo_services[project_id]
    processor = RepoCommandProcessor()
    executor = CommandExecutor(service)

    participants = get_ai_agents_by_ids(agent_ids)
    names = [p.name for p in participants]

    chat = RoundRobinGroupChat(
        participants=participants,
        termination_condition=MaxMessageTermination(max_messages=10),
    )

    prompt = f"""Ты — автономная команда разработчиков: FRONTEND + BACKEND.
    Вы получаете полное техническое задание.
    Каждый агент выполняет ТОЛЬКО свою роль.

    ПРАВИЛА:
    1. Работайте по очереди.
    2. Каждый агент должен:
    - принять ТЗ
    - определить подходящую архитектуру проекта
    - сгенерировать полный набор файлов
    - вернуть PUSH_FULL (и при необходимости PATCH)
    - выполнить деплой
    - написать строку ГОТОВО: ROLE

    3. Когда оба агента написали:
    "ГОТОВО: FRONTEND"
    "ГОТОВО: BACKEND"

    — напишите финальную фразу:

    РАБОТА ЗАВЕРШЕНА — ВСЁ ГОТОВО

    ⚠️ Без объяснений.
    ⚠️ Никакого пользовательского текста.
    """

    try:
        result = await asyncio.wait_for(chat.run(task=prompt), timeout=40)
        commands = processor.parse_task_result(result, project_id)

        info(commands)
        outputs = executor.execute(commands)

        for line in outputs:
            info(line)

    except asyncio.TimeoutError:
        error("[TEAM] Таймаут — команда не успела")
        return


async def get_ai_response(
    project_id: uuid.UUID,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    tz_buffer = []
    team_task = None

    async for token in run_product_manager_stream(user_message, history):
        yield token
        tz_buffer.append(token)

        full_pm_text = "".join(tz_buffer)

        if "ТЗ завершено!" in full_pm_text:
            specification = full_pm_text

            yield "\n\nТехническое задание сформировано. Запускаю работу команды...\n\n"

            team_task = asyncio.create_task(
                run_ai_team_work(
                    specification=specification,
                    agent_ids=["frontend", "backend"],
                    project_id=project_id,
                )
            )

    if team_task:
        try:
            await team_task
            yield "\nКоманда завершила работу. Репозиторий обновлён.\n"
        except Exception as e:
            yield f"\nОшибка в команде: {e}\n"
