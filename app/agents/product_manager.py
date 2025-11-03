import os
from typing import List, Dict
from pprint import pprint
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient


GROQ_MODEL = os.getenv("GROQ_AI_MODEL", "llama-3.1-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_MODEL_INFO = ModelInfo(
    vision=False,
    function_calling=False,
    json_output=True,
    family=GROQ_MODEL,
    structured_output=True,
)

model_client = OpenAIChatCompletionClient(
    model=GROQ_MODEL,
    model_info=GROQ_MODEL_INFO,
    api_key=GROQ_API_KEY,
    base_url=GROQ_BASE_URL,
)

product_manager = AssistantAgent(
    name="ProductManager",
    model_client=model_client,
    system_message=(
        "Ты — Product Manager. "
        "1. Собери полное техническое задание (ТЗ) от пользователя. "
        "Если чего-то не хватает — задай уточняющие вопросы. "
        "Задавай вопросы пока не убедишься что каждому члену команды будет все понятно. "
        "2. Когда ТЗ готово, скажи: 'ТЗ завершено'. "
        "3. После этого САМ реши, кому делегировать задачи (Frontend, Backend, Designer). Или как распределить работу между ними. "
        "Не спрашивай подтверждения у пользователя — ты принимаешь решение сам."
    ),
)

frontend = AssistantAgent(
    name="Frontend",
    model_client=model_client,
    system_message="Ты — Frontend-разработчик. Реализуй UI/JS/React часть проекта по ТЗ ProductManager.",
)

backend = AssistantAgent(
    name="Backend",
    model_client=model_client,
    system_message="Ты — Backend-разработчик. Реализуй API, базы данных и бизнес-логику по ТЗ.",
)

designer = AssistantAgent(
    name="Designer",
    model_client=model_client,
    system_message="Ты — UI/UX дизайнер. Предлагай визуальные решения и макеты интерфейсов по ТЗ.",
)


async def get_product_manager_response(project_id: str, user_id: int, user_message: str, history: List[Dict]) -> str:
    context = "\n".join(
        f"{m.get('role','Unknown')}: {m.get('message','')}" for m in history[-10:]
    )

    task_prompt = (
        f"Проект ID: {project_id} (Пользователь {user_id})\n"
        f"История:\n{context}\n\n"
        f"Новое сообщение пользователя: {user_message}\n\n"
        "ProductManager, оцени введённые данные. Если ТЗ неполное — уточни, что нужно. "
        "Если всё понятно, скажи 'ТЗ завершено' и объясни, что планируешь делать дальше."
    )

    response = await product_manager.run(task=task_prompt)
    response_text = response.result if hasattr(
        response, "result") else str(response)

    return response_text


def is_spec_complete(message: str) -> bool:
    keywords = ["тз завершено", "готов передать команде",
                "начинаю работу команды"]
    message_lower = message.lower()

    return any(k in message_lower for k in keywords)


async def run_team_work(project_id: str, specification: str) -> str:
    task_prompt = (
        f"Проект ID: {project_id}\n\n"
        f"Техническое задание от ProductManager:\n{specification}\n\n"
        "Теперь ProductManager распределяет задачи между Frontend, Backend и Designer, "
        "координирует их работу и возвращает финальный результат пользователю."
    )

    team_chat = RoundRobinGroupChat(
        participants=[product_manager, frontend, backend, designer],
        termination_condition=MaxMessageTermination(max_messages=6),
    )

    messages = []
    stream = team_chat.run_stream(task=task_prompt)

    async for msg in stream:
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            messages.append(content.strip())

    return messages[-1] if messages else ""


async def get_ai_response(project_id: str, user_id: int, user_message: str, history: List[Dict]) -> str:
    pm_response = await get_product_manager_response(project_id, user_id, user_message, history)

    if not pm_response:
        return "⚠️ Нет ответа от ProductManager. Проверьте ключ или настройки модели."

    if is_spec_complete(pm_response):
        team_result = await run_team_work(project_id, pm_response)
        return team_result or pm_response

    return pm_response
