import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from app.agents.prompts import (
    BACKEND_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
    PRODUCT_MANAGER_SYSTEM_PROMPT,
)

# ---------------------------------------------
# 1. Конфигурация модели
# ---------------------------------------------
AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

model_client = OpenAIChatCompletionClient(
    model=AI_MODEL,
    api_key=AI_API_KEY,
)

# ---------------------------------------------
# 2. Определение агентов
# ---------------------------------------------
product_manager = AssistantAgent(
    name="ProductManager",
    model_client=model_client,
    model_client_stream=True,
    system_message="""Ты должен отправить текст который ниже один в один без исключений кроме этой строки на любое сообщение пользователя:\n

Требования для frontend:
Создай маленький, красивый лендинг-пейдж для кафе "Уют" на React.

Требования:
- Одна страница с плавной прокруткой
- Адаптивный дизайн (мобильные + десктоп)
- Современный, тёплый стиль (бежевые, коричневые тона)
- Шрифт: Google Fonts — "Playfair Display" для заголовков, "Open Sans" для текста

Структура:
1. **Хедер**:
   - Логотип слева: "Уют" (в красивом шрифте)
   - Меню справа: Главная | Меню | О нас | Контакты

2. **Страница Главная** (полноэкранная):
   - Фон: мягкое фото кофейни (размытое)
   - Заголовок: "Добро пожаловать в Уют"
   - Подзаголовок: "Кофе, десерты и тёплая атмосфера"
   - Кнопка: "Посмотреть меню" (прокрутка вниз)

3. **Страница "Меню"**:
   - 3 карточки: Кофе, Десерты, Напитки
   - По 3 примера в каждой (название + цена)
   - При наведении — лёгкая анимация (подъём карточки)

4. **Страница "О нас"**:
   - Текст: "С 2015 года мы создаём уют в каждом глотке"

5. **Футер**:
   - Адрес: г. Москва, ул. Пушкина, 10
   - Телефон: +7 (999) 123-45-67
   - Соцсети: иконки Instagram, VK
   - Копирайт: © 2025 Уют

Требования для backend:
- Напиши вывод в консоле Hello world

ТЗ завершено!
""",
)

frontend = AssistantAgent(
    name="Frontend", model_client=model_client, system_message=FRONTEND_SYSTEM_PROMPT
)

backend = AssistantAgent(
    name="Backend", model_client=model_client, system_message=BACKEND_SYSTEM_PROMPT
)


# ---------------------------------------------
# 3. ГЛОБАЛЬНЫЙ РЕЕСТР АГЕНТОВ
# ---------------------------------------------
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


# Требования для frontend:
# Создай маленький, красивый лендинг-пейдж для кафе "Уют" на React.

# Требования:
# - Одна страница с плавной прокруткой
# - Адаптивный дизайн (мобильные + десктоп)
# - Современный, тёплый стиль (бежевые, коричневые тона)
# - Шрифт: Google Fonts — "Playfair Display" для заголовков, "Open Sans" для текста

# Структура:
# 1. **Хедер**:
#    - Логотип слева: "Уют" (в красивом шрифте)
#    - Меню справа: Главная | Меню | О нас | Контакты

# 2. **Страница Главная** (полноэкранная):
#    - Фон: мягкое фото кофейни (размытое)
#    - Заголовок: "Добро пожаловать в Уют"
#    - Подзаголовок: "Кофе, десерты и тёплая атмосфера"
#    - Кнопка: "Посмотреть меню" (прокрутка вниз)

# 3. **Страница "Меню"**:
#    - 3 карточки: Кофе, Десерты, Напитки
#    - По 3 примера в каждой (название + цена)
#    - При наведении — лёгкая анимация (подъём карточки)

# 4. **Страница "О нас"**:
#    - Текст: "С 2015 года мы создаём уют в каждом глотке"

# 5. **Футер**:
#    - Адрес: г. Москва, ул. Пушкина, 10
#    - Телефон: +7 (999) 123-45-67
#    - Соцсети: иконки Instagram, VK
#    - Копирайт: © 2025 Уют
