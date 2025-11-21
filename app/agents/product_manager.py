import os
import re
import json
from typing import AsyncGenerator, List, Dict
from pprint import pprint
import uuid

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import ModelClientStreamingChunkEvent

from .repo_manager import RepoManager

# -------------------------------------------------
# 1. Конфигурация
# -------------------------------------------------
AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

model_client = OpenAIChatCompletionClient(
    model=AI_MODEL,
    api_key=AI_API_KEY,
)


# -------------------------------------------------
# 2. Агенты
# -------------------------------------------------
product_manager = AssistantAgent(
    name="ProductManager",
    model_client=model_client,
    model_client_stream=True,
    system_message=(
        # "Ты — Product Manager.\n"
        # "Отвечай текстом когда надо дать просто информацию и в markdown формате когда надо структурировать сообщение"
        # "Если пользователь отправляет готовый промпт и все понятно по ТЗ — приступай к работе. Если нет, уточняй.\n"
        # "1. Собери полное ТЗ. Задавай вопросы, пока всё не ясно.\n"
        # "2. Когда осознал — скажи: 'ТЗ завершено'.\n"
        "Ты ии агент для тестирования чата\n"
        "Присылай контент который попросит пользователь.\n"
        "Отвечай в формате текса и markdown.\n"
        "Подставляй смайлики в заголовки и списки. В параграфы не нужно\n"
    ),
)

frontend = AssistantAgent(
    name="Frontend",
    model_client=model_client,
    model_client_stream=True,
    system_message=(
        "Ты — Frontend. Пиши React/Vite/JS.\n"
        "Ответ: JSON-массив файлов.\n"
        "```json\n"
        '[{"path": "src/App.jsx", "content": "..."}]\n'
        "```"
    ),
)

backend = AssistantAgent(
    name="Backend",
    model_client=model_client,
    model_client_stream=True,
    system_message=(
        "Ты — Backend. Пиши FastAPI.\n"
        "Ответ: JSON-массив файлов.\n"
        "```json\n"
        '[{"path": "main.py", "content": "..."}]\n'
        "```"
    ),
)

# -------------------------------------------------
# 3. Хранилище
# -------------------------------------------------
repo_managers: Dict[str, RepoManager] = {}


# -------------------------------------------------
# 4. Парсинг команд
# -------------------------------------------------
def _parse_pm_commands(message: str, manager: RepoManager) -> str:
    out = []

    # CREATE_REPO
    if m := re.search(r"CREATE_REPO:\s*([^\s\n]+)", message, re.IGNORECASE):
        name = m.group(1).strip()
        out.append(manager.create_repo(name))

    # PUSH_FULL / PUSH_PATCH
    if m := re.search(
        r"(PUSH_FULL|PUSH_PATCH):\s*```json\s*([\s\S]*?)\s*```", message, re.IGNORECASE
    ):
        cmd, json_str = m.groups()
        try:
            files = json.loads(json_str)
            if not isinstance(files, list):
                files = [files]
            if cmd.upper() == "PUSH_FULL":
                out.append(manager.push_full(files))
            else:
                out.append(manager.push_patch(files))
        except json.JSONDecodeError as e:
            out.append(f"JSON error: {e}")

    # DEPLOY
    if re.search(r"DEPLOY_PAGES", message, re.IGNORECASE):
        out.append(manager.enable_pages())
    if re.search(r"DEPLOY_RENDER", message, re.IGNORECASE):
        out.append(manager.add_render_yaml())

    return "\n".join(filter(None, out))


# -------------------------------------------------
# 5. Проверка ТЗ
# -------------------------------------------------
def is_spec_complete(text: str) -> bool:
    return "тз завершено" in text.lower()


# -------------------------------------------------
# 6. Ответ ProductManager (основной стрим)
# -------------------------------------------------
async def get_product_manager_stream(
    project_id: uuid.UUID, user_message: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """
    Стриминг только токенов.
    Сохраняем все пробелы и переносы.
    """
    ctx = "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('message', '')}"
        for msg in history[-10:]
        if msg.get("message")
    )

    # task = (
    #     f"История:\n{ctx}\n\n"
    #     f"Пользователь: {user_message}\n\n"
    #     "Ты — Product Manager. Собери ТЗ. Когда готов — скажи 'ТЗ завершено'."
    # )
    task = (
        f"История:\n{ctx}\n\n"
        f"Пользователь прислал сообщение: {user_message}\n\n"
        "Ответь как будто ты человек."
    )

    async for msg in product_manager.run_stream(task=task):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            content = getattr(msg, "content", "")
            # ❗ Не используем .strip() — чтобы не терять пробелы и переносы
            if content:
                yield content


# -------------------------------------------------
# 7. Командная работа после завершения ТЗ
# -------------------------------------------------
async def run_team_work_stream(
    project_id: uuid.UUID, specification: str
) -> AsyncGenerator[str, None]:
    chat = RoundRobinGroupChat(
        participants=[product_manager, frontend, backend],
        termination_condition=MaxMessageTermination(max_messages=10),
    )

    prompt = f"ТЗ:\n{specification}\n\nСгенерируй код."

    async for msg in chat.run_stream(task=prompt):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            content = getattr(msg, "content", "")
            if content:
                yield content


# -------------------------------------------------
# 8. Основная функция: объединение стримов
# -------------------------------------------------
async def get_ai_response(
    project_id: uuid.UUID, user_message: str, history: list[dict]
) -> AsyncGenerator[str, None]:
    """
    Генератор, который объединяет стримы AI.
    Пока отдаёт только стрим ProductManager-а.
    """
    async for token in get_product_manager_stream(
        project_id, user_message, history
    ):
        yield token

    # Позже можно добавить логику, когда ТЗ завершено:
    # full = "".join([t async for t in get_product_manager_stream(...)])
    # if "тз завершено" in full.lower():
    #     async for token in run_team_work_stream(project_id, full):
    #         yield token
