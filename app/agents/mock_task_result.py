from typing import Any, Dict, List
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from autogen_core.models import RequestUsage

ai_command = {
    "__class__": "TaskResult",
    "messages": [
        {
            "__class__": "TextMessage",
            "source": "user",
            "models_usage": "null",
            "metadata": {},
            "content": 'ТЫ — автономная команда из 2 независимых специалистов.\n\nТЕХНИЧЕСКОЕ ЗАДАНИЕ:\nТребования для frontend:\nСоздай маленький, красивый лендинг-пейдж для кафе "Уют" на React.\n\nТребования:\n- Одна страница с плавной прокруткой\n- Адаптивный дизайн (мобильные + десктоп)\n- Современный, тёплый стиль (бежевые, коричневые тона)\n- Шрифт: Google Fonts — "Playfair Display" для заголовков, "Open Sans" для текста\n\nСтруктура:\n1. **Хедер**:\n   - Логотип слева: "Уют" (в красивом шрифте)\n   - Меню справа: Главная | Меню | О нас | Контакты\n\n2. **Страница Главная** (полноэкранная):\n   - Фон: мягкое фото кофейни (размытое)\n   - Заголовок: "Добро пожаловать в Уют"\n   - Подзаголовок: "Кофе, десерты и тёплая атмосфера"\n   - Кнопка: "Посмотреть меню" (прокрутка вниз)\n\n3. **Страница "Меню"**:\n   - 3 карточки: Кофе, Десерты, Напитки\n   - По 3 примера в каждой (название + цена)\n   - При наведении — лёгкая анимация (подъём карточки)\n\n4. **Страница "О нас"**:\n   - Текст: "С 2015 года мы создаём уют в каждом глотке"\n\n5. **Футер**:\n   - Адрес: г. Москва, ул. Пушкина, 10\n   - Телефон: +7 (999) 123-45-67\n   - Соцсети: иконки Instagram, VK\n   - Копирайт: © 2025 Уют\n\nТребования для backend:\n- Напиши вывод в консоле Hello world\n\nТЗ завершено!\n\nТЫ — ТОЛЬКО ОДИН ИЗ НИХ. Твоя роль указана в имени.\n\nРОЛИ В КОМАНДЕ (пиши ГОТОВО ровно так же):\n• Frontend\n• Backend\n\nТЫ ДОЛЖЕН СДЕЛАТЬ ТОЛЬКО ДВЕ ВЕЩИ:\n1. Вывести JSON-массив со СВОИМИ файлами (один раз)\n2. После этого — ровно одну строку: ГОТОВО: ТвояРоль\n\nПРИМЕРЫ ПРАВИЛЬНЫХ СТРОК:\nГОТОВО: Frontend\nГОТОВО: Backend\n\nСТРОГО ЗАПРЕЩЕНО:\n- Писать за других участников\n- Повторять свои файлы\n- Выводить любые токены вроде <|TEAM_COMPLETE|>, <end>, DONE и т.п.\n- Писать что-либо после строки ГОТОВО: ...\n\nСИСТЕМА САМА ЗАВЕРШИТ РАБОТУ, КОГДА УВИДИТ ВСЕ СТРОКИ ГОТОВО.\nТЕБЕ НЕ НУЖНО НИЧЕГО ДЕЛАТЬ ДЛЯ ЭТОГО.\n\nНачинай прямо сейчас.',
            "type": "TextMessage",
        },
        {
            "__class__": "TextMessage",
            "source": "Frontend",
            "models_usage": {
                "__class__": "RequestUsage",
                "prompt_tokens": 969,
                "completion_tokens": 1727,
            },
            "metadata": {},
            "content": '```json\n[\n    {"path": "frontend/package.json", "content": "{ \\"name\\": \\"cafe-uet\\", \\"version\\": \\"1.0.0\\", \\"private\\": true, \\"dependencies\\": { \\"react\\": \\"^18.0.0\\", \\"react-dom\\": \\"^18.0.0\\", \\"react-scripts\\": \\"^5.0.0\\" }, \\"scripts\\": { \\"start\\": \\"react-scripts start\\", \\"build\\": \\"react-scripts build\\", \\"test\\": \\"react-scripts test\\", \\"eject\\": \\"react-scripts eject\\" }, \\"eslintConfig\\": { \\"extends\\": [ \\"react-app\\", \\"react-app/jest\\" ] }, \\"browserslist\\": { \\"production\\": [\\">0.2%\\", \\"not dead\\", \\"not op_mini all\\"], \\"development\\": [\\"last 1 chrome version\\", \\"last 1 firefox version\\", \\"last 1 safari version\\"] } }"},\n    {"path": "frontend/public/index.html", "content": "<!DOCTYPE html><html lang=\\"en\\"><head><meta charset=\\"UTF-8\\"><meta name=\\"viewport\\" content=\\"width=device-width, initial-scale=1.0\\"><link href=\\"https://fonts.googleapis.com/css2?family=Open+Sans&family=Playfair+Display&display=swap\\" rel=\\"stylesheet\\"><title>Кафе Уют</title></head><body><div id=\\"root\\"></div></body></html>"},\n    {"path": "frontend/src/index.js", "content": "import React from \'react\'; import ReactDOM from \'react-dom\'; import App from \'./App\'; import \'./index.css\'; ReactDOM.render(<React.StrictMode><App /></React.StrictMode>, document.getElementById(\'root\'));"},\n    {"path": "frontend/src/App.js", "content": "import React from \'react\'; import Header from \'./components/Header\'; import Home from \'./components/Home\'; import Menu from \'./components/Menu\'; import About from \'./components/About\'; import Footer from \'./components/Footer\'; import { BrowserRouter as Router, Route, Switch } from \'react-router-dom\'; import \'./App.css\'; function App() { return ( <Router> <Header /> <Switch> <Route path=\\"/\\" exact component={Home} /> <Route path=\\"/menu\\" component={Menu} /> <Route path=\\"/about\\" component={About} /> </Switch> <Footer /> </Router> ); } export default App;"},\n    {"path": "frontend/src/components/Header.js", "content": "import React from \'react\'; import { Link } from \'react-router-dom\'; import \'./Header.css\'; function Header() { return ( <header className=\\"header\\"> <div className=\\"logo\\">Уют</div> <nav className=\\"nav\\"> <Link to=\\"/\\">Главная</Link> <Link to=\\"/menu\\">Меню</Link> <Link to=\\"/about\\">О нас</Link> </nav> </header> ); } export default Header;"},\n    {"path": "frontend/src/components/Home.js", "content": "import React from \'react\'; import \'./Home.css\'; function Home() { return ( <div className=\\"home\\"> <div className=\\"background\\"> <h1>Добро пожаловать в Уют</h1> <h2>Кофе, десерты и тёплая атмосфера</h2> <a href=\\"#menu\\" className=\\"menu-button\\">Посмотреть меню</a> </div> </div> ); } export default Home;"},\n    {"path": "frontend/src/components/Menu.js", "content": "import React from \'react\'; import \'./Menu.css\'; function Menu() { return ( <div className=\\"menu\\"> <h2>Меню</h2> <div className=\\"card\\"> <h3>Кофе</h3> <p>Эспрессо - 150 Р</p> <p>Латте - 200 Р</p> <p>Капучино - 250 Р</p> </div> <div className=\\"card\\"> <h3>Десерты</h3> <p>Тирамису - 300 Р</p> <p>Чизкейк - 350 Р</p> <p>Медовик - 300 Р</p> </div> <div className=\\"card\\"> <h3>Напитки</h3> <p>Чай - 100 Р</p> <p>Сок - 150 Р</p> <p>Минеральная вода - 80 Р</p> </div> </div> ); } export default Menu;"},\n    {"path": "frontend/src/components/About.js", "content": "import React from \'react\'; import \'./About.css\'; function About() { return ( <div className=\\"about\\"> <h2>О нас</h2> <p>С 2015 года мы создаём уют в каждом глотке</p> </div> ); } export default About;"},\n    {"path": "frontend/src/components/Footer.js", "content": "import React from \'react\'; import \'./Footer.css\'; function Footer() { return ( <footer className=\\"footer\\"> <p>г. Москва, ул. Пушкина, 10</p> <p>Телефон: +7 (999) 123-45-67</p> <p>Соцсети: <a href=\\"#\\">Instagram</a> | <a href=\\"#\\">VK</a></p> <p>© 2025 Уют</p> </footer> ); } export default Footer;"},\n    {"path": "frontend/src/index.css", "content": "body { font-family: \'Open Sans\', sans-serif; margin: 0; padding: 0; } .header, .footer { text-align: center; padding: 20px; background: #f9f9f9; } .header .logo { font-family: \'Playfair Display\', serif; font-size: 2rem; color: #4b3a29; } .nav { margin-top: 10px; } .nav a { margin: 0 10px; text-decoration: none; color: #4b3a29; } .home { height: 100vh; display: flex; justify-content: center; align-items: center; flex-direction: column; background: url(\'path/to/your/image.jpg\') no-repeat center center fixed; background-size: cover; } .home h1, .home h2 { color: #fff; } .menu-button { border: none; background: #c49a6a; color: #fff; padding: 10px 20px; cursor: pointer; } .menu, .about { padding: 20px; } .card { border: 1px solid #ddd; padding: 10px; margin: 10px; transition: transform 0.2s; } .card:hover { transform: translateY(-5px); }"},\n    {"path": "frontend/src/components/Header.css", "content": ".header { display: flex; justify-content: space-between; align-items: center; padding: 20px; background: #e8d8b6; }"},\n    {"path": "frontend/src/components/Home.css", "content": ".background { text-align: center; }"},\n    {"path": "frontend/src/components/Menu.css", "content": ".menu { display: flex; flex-direction: column; align-items: center; } .card { width: 200px; padding: 20px; background: #f7f7f7; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }"},\n    {"path": "frontend/src/components/About.css", "content": ".about { text-align: center; }"},\n    {"path": "frontend/src/components/Footer.css", "content": ".footer { background: #e8d8b6; padding: 20px; }"}\n]\n```\nГОТОВО: Frontend',
            "type": "TextMessage",
        },
        {
            "__class__": "TextMessage",
            "source": "Backend",
            "models_usage": {
                "__class__": "RequestUsage",
                "prompt_tokens": 2683,
                "completion_tokens": 123,
            },
            "metadata": {},
            "content": '```json\n[\n  {"path": "backend/main.py", "content": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n\\n@app.get(\\"/\\")\\ndef read_root():\\n    return {\\"Hello\\": \\"World\\"}"},\n  {"path": "backend/requirements.txt", "content": "fastapi\\nuvicorn"},\n  {"path": "backend/README.md", "content": "# Backend\\n\\nЗапустите сервер командой:\\n\\n```bash\\nuvicorn main:app --reload\\n```"}\n]\n```\nГОТОВО: Backend',
            "type": "TextMessage",
        },
    ],
    "stop_reason": "<|TEAM_COMPLETE|>",
}


def create_mock_task_result(
    messages_data: List[Dict[str, Any]], stop_reason: str = "<|TEAM_COMPLETE|>"
) -> TaskResult:
    """
    Создаёт настоящий TaskResult из муляжа.
    Работает с Pydantic v2 — никаких ошибок валидации.
    """
    messages = []

    for msg_data in messages_data:
        # Исправляем models_usage — "null" → None
        models_usage_raw = msg_data.get("models_usage")
        if models_usage_raw == "null" or models_usage_raw == "string_null_placeholder":
            models_usage = None
        elif isinstance(models_usage_raw, dict) and "__class__" in models_usage_raw:
            # Если там вложенный RequestUsage — создаём настоящий объект
            usage_data = models_usage_raw.copy()
            usage_data.pop("__class__", None)
            models_usage = RequestUsage(**usage_data)
        else:
            models_usage = models_usage_raw  # уже нормальный dict или None

        # Создаём настоящий TextMessage
        msg = TextMessage(
            source=msg_data["source"],
            content=msg_data["content"],
            models_usage=models_usage,
            metadata=msg_data.get("metadata", {}),
        )
        messages.append(msg)

    return TaskResult(messages=messages, stop_reason=stop_reason)


mock = create_mock_task_result(ai_command["messages"], ai_command["stop_reason"])
