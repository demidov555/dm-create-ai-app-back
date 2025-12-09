import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from app.agents.prompts import (
    BACKEND_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
    PRODUCT_MANAGER_SYSTEM_PROMPT,
)

load_dotenv()

AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

test_prompt = """Ты должен отправить текст который ниже один в один без исключений кроме этой строки на любое сообщение пользователя:\n

Требования для frontend:
Создай красивый сайт для кафе "Уют".

Требования:
- Современный, тёплый стиль
- Шрифт: Google Fonts — "Playfair Display" для заголовков, "Open Sans" для текста

Структура:
1. **Хедер**:
   - Логотип слева: "Уют" (в красивом шрифте)
   - Меню справа: Главная | Меню | О нас | Контакты

2. **Страница Главная** (полноэкранная):
   - Фон: мягкое фото кофейни (размытое)
   - Заголовок: "Добро пожаловать в Уют"
   - Остальное придумай сам

3. **Страница "Меню"**:
   - 3 карточки: Кофе, Десерты, Напитки
   - По 3 примера в каждой (название + цена)
   - При наведении — лёгкая анимация (подъём карточки)

4. **Страница "О нас"**:
   - Сгенерируй 2 абзаца о кафе Уют, его истории и атмосфере

5. **Футер**:
   - Адрес: г. Москва, ул. Пушкина, 10
   - Телефон: +7 (999) 123-45-67
   - Соцсети: иконки Instagram, VK
   - Копирайт: © 2025 Уют

Требования для backend:
- Напиши вывод в консоле Hello world

ТЗ завершено!
"""

model_client = OpenAIChatCompletionClient(
    model=AI_MODEL,
    api_key=AI_API_KEY,
)

product_manager = AssistantAgent(
    name="ProductManager",
    model_client=model_client,
    model_client_stream=True,
    system_message=test_prompt,
)

frontend = AssistantAgent(
    name="Frontend", model_client=model_client, system_message=FRONTEND_SYSTEM_PROMPT
)

backend = AssistantAgent(
    name="Backend", model_client=model_client, system_message=BACKEND_SYSTEM_PROMPT
)

AI_AGENT_OBJECTS = {
    "frontend": frontend,
    "backend": backend,
}


def get_ai_agents_by_ids(agent_ids: list[str] | None):
    if not agent_ids:
        print("NO agent_ids provided, returning empty list")
        return []

    agents = []
    for agent_id in agent_ids:
        key = agent_id.strip()

        if key not in AI_AGENT_OBJECTS:
            print(f"ERROR: agent '{key}' NOT FOUND in AI_AGENT_OBJECTS!")
            raise ValueError(f"AI agent '{key}' not found")

        agent = AI_AGENT_OBJECTS[key]

        if not hasattr(agent, "run_stream"):
            print(f"ERROR: agent '{key}' is not a valid AssistantAgent")
            raise TypeError(f"Object '{key}' is not a valid agent instance")

        agents.append(agent)

    return agents
