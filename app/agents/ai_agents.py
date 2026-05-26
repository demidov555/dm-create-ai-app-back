import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.prompts import (
    BACKEND_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
    PRODUCT_MANAGER_ROUTER_PROMPT,
)
from app.logger.console_logger import error


AgentAction = Literal[
    "ask_clarification",
    "run_agents",
    "revise_agents",
    "answer_user",
]


@dataclass
class AgentMessage:
    source: str
    content: str


@dataclass
class AgentTaskResult:
    messages: list[AgentMessage]


@dataclass
class ProductManagerParsedResult:
    action: AgentAction
    is_ready: bool
    clarification_question: str | None
    technical_specification: str | None
    revision_request: str | None
    answer: str | None
    required_agents: list[str]


@dataclass
class ProjectSession:
    pm_context_messages: list[BaseMessage] = field(default_factory=list)
    last_technical_specification: str | None = None
    last_agent_results: list[AgentMessage] = field(default_factory=list)
    status: str = "collecting_spec"


class AgentState(TypedDict):
    messages: list[BaseMessage]


class LangGraphAssistantAgent:
    def __init__(
        self,
        name: str,
        model: ChatOpenAI,
        system_message: str,
        stream_output: bool = False,
    ):
        self.name = name
        self.model = model
        self.system_message = system_message
        self.stream_output = stream_output
        self.app = self._build_graph()

    def _build_graph(self):
        async def call_model(state: AgentState) -> AgentState:
            messages = state["messages"]
            response = await self.model.ainvoke(messages)
            return {"messages": [*messages, response]}

        graph = StateGraph(AgentState)
        graph.add_node("call_model", call_model)
        graph.set_entry_point("call_model")
        graph.add_edge("call_model", END)

        return graph.compile()

    async def run(
        self,
        task: str,
        context_messages: list[BaseMessage] | None = None,
    ) -> AgentTaskResult:
        context_messages = context_messages or []

        initial_messages: list[BaseMessage] = [
            SystemMessage(content=self.system_message),
            *context_messages,
            HumanMessage(content=task),
        ]

        result = await self.app.ainvoke({"messages": initial_messages})
        response = result["messages"][-1]

        content = response.content if isinstance(
            response, AIMessage) else str(response)

        return AgentTaskResult(
            messages=[
                AgentMessage(
                    source=self.name,
                    content=str(content),
                )
            ]
        )

    async def run_stream(
        self,
        task: str,
        context_messages: list[BaseMessage] | None = None,
    ) -> AsyncGenerator[AgentMessage, None]:
        context_messages = context_messages or []

        input_messages: list[BaseMessage] = [
            SystemMessage(content=self.system_message),
            *context_messages,
            HumanMessage(content=task),
        ]

        async for chunk in self.model.astream(input_messages):
            content = getattr(chunk, "content", "")
            if content:
                yield AgentMessage(source=self.name, content=str(content))


load_dotenv()

AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

if not AI_MODEL or not AI_API_KEY:
    raise EnvironmentError("Установите AI_MODEL и AI_API_KEY в .env")


def create_model_client() -> ChatOpenAI:
    model_kwargs: dict[str, Any] = {
        "model": AI_MODEL,
        "api_key": AI_API_KEY,
    }

    if AI_MODEL.startswith("o3") or AI_MODEL.startswith("o4"):
        model_kwargs["reasoning_effort"] = "medium"
    else:
        model_kwargs["temperature"] = 0

    return ChatOpenAI(**model_kwargs)


model_client = create_model_client()

product_manager = LangGraphAssistantAgent(
    name="ProductManager",
    model=model_client,
    system_message=PRODUCT_MANAGER_ROUTER_PROMPT,
    stream_output=False,
)

frontend = LangGraphAssistantAgent(
    name="Frontend",
    model=model_client,
    system_message=FRONTEND_SYSTEM_PROMPT,
)

backend = LangGraphAssistantAgent(
    name="Backend",
    model=model_client,
    system_message=BACKEND_SYSTEM_PROMPT,
)


AI_AGENT_OBJECTS: dict[str, LangGraphAssistantAgent] = {
    "frontend": frontend,
    "backend": backend,
}


project_sessions: dict[str, ProjectSession] = {}


def get_or_create_session(session_id: str) -> ProjectSession:
    if session_id not in project_sessions:
        project_sessions[session_id] = ProjectSession()

    return project_sessions[session_id]


def reset_project_session(session_id: str) -> None:
    if session_id in project_sessions:
        del project_sessions[session_id]


def get_ai_agents_by_ids(agent_ids: list[str]) -> list[LangGraphAssistantAgent]:
    agents: list[LangGraphAssistantAgent] = []

    for agent_id in agent_ids:
        key = agent_id.strip().lower()

        if key not in AI_AGENT_OBJECTS:
            error(f"ERROR: agent '{key}' NOT FOUND in AI_AGENT_OBJECTS!")
            raise ValueError(f"AI agent '{key}' not found")

        agent = AI_AGENT_OBJECTS[key]

        if not isinstance(agent, LangGraphAssistantAgent):
            error(
                f"ERROR: agent '{key}' is not a valid LangGraphAssistantAgent")
            raise TypeError(f"Object '{key}' is not a valid agent instance")

        agents.append(agent)

    return agents


def clean_json_response(content: str) -> str:
    content = content.strip()

    if content.startswith("```json"):
        content = content.removeprefix("```json").strip()

    if content.startswith("```"):
        content = content.removeprefix("```").strip()

    if content.endswith("```"):
        content = content.removesuffix("```").strip()

    return content


def parse_product_manager_response(content: str) -> ProductManagerParsedResult:
    cleaned_content = clean_json_response(content)

    try:
        data = json.loads(cleaned_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"ProductManager вернул невалидный JSON: {content}") from exc

    action = data.get("action")

    allowed_actions = {
        "ask_clarification",
        "run_agents",
        "revise_agents",
        "answer_user",
    }

    if action not in allowed_actions:
        raise ValueError(f"ProductManager вернул неизвестный action: {action}")

    return ProductManagerParsedResult(
        action=action,
        is_ready=bool(data.get("is_ready")),
        clarification_question=data.get("clarification_question"),
        technical_specification=data.get("technical_specification"),
        revision_request=data.get("revision_request"),
        answer=data.get("answer"),
        required_agents=data.get("required_agents") or [],
    )


def serialize_agent_results(messages: list[AgentMessage]) -> str:
    if not messages:
        return "Предыдущих результатов агентов нет."

    parts: list[str] = []

    for message in messages:
        parts.append(
            f"AGENT: {message.source}\n"
            f"RESULT:\n{message.content}"
        )

    return "\n\n---\n\n".join(parts)


async def run_selected_agents(
    technical_specification: str,
    agent_ids: list[str],
    extra_context_messages: list[BaseMessage] | None = None,
) -> list[AgentMessage]:
    agents = get_ai_agents_by_ids(agent_ids)
    final_messages: list[AgentMessage] = []

    for agent in agents:
        result = await agent.run(
            task=technical_specification,
            context_messages=extra_context_messages or [],
        )

        final_messages.extend(result.messages)

    return final_messages


async def handle_user_message(
    session_id: str,
    user_message: str,
) -> AgentTaskResult:
    """
    Главная функция.

    Пользователь всегда пишет только сюда.
    ProductManager решает:
    - задать уточняющий вопрос
    - запустить агентов по новому ТЗ
    - отправить правку агентам
    - ответить пользователю без агентов
    """

    session = get_or_create_session(session_id)

    project_state_message = SystemMessage(
        content=(
            "Текущее состояние проекта:\n"
            f"status: {session.status}\n\n"
            f"last_technical_specification:\n"
            f"{session.last_technical_specification or 'Пока нет финального ТЗ.'}\n\n"
            f"last_agent_results:\n"
            f"{serialize_agent_results(session.last_agent_results)}"
        )
    )

    pm_result = await product_manager.run(
        task=user_message,
        context_messages=[
            project_state_message,
            *session.pm_context_messages,
        ],
    )

    pm_answer = pm_result.messages[-1].content

    session.pm_context_messages.append(HumanMessage(content=user_message))
    session.pm_context_messages.append(AIMessage(content=pm_answer))

    parsed = parse_product_manager_response(pm_answer)

    if parsed.action == "ask_clarification":
        session.status = "collecting_spec"

        return AgentTaskResult(
            messages=[
                AgentMessage(
                    source="ProductManager",
                    content=parsed.clarification_question or "Уточните задачу подробнее.",
                )
            ]
        )

    if parsed.action == "answer_user":
        return AgentTaskResult(
            messages=[
                AgentMessage(
                    source="ProductManager",
                    content=parsed.answer or "Хорошо.",
                )
            ]
        )

    if parsed.action == "run_agents":
        if not parsed.technical_specification:
            raise ValueError(
                "ProductManager выбрал run_agents, но не вернул technical_specification")

        if not parsed.required_agents:
            raise ValueError(
                "ProductManager выбрал run_agents, но не указал required_agents")

        session.status = "agents_running"
        session.last_technical_specification = parsed.technical_specification

        agent_context = [
            SystemMessage(
                content=(
                    "Ниже находится финальное ТЗ от Product Manager. "
                    "Выполняй только свою часть задачи согласно своей роли."
                )
            )
        ]

        agent_messages = await run_selected_agents(
            technical_specification=parsed.technical_specification,
            agent_ids=parsed.required_agents,
            extra_context_messages=agent_context,
        )

        session.last_agent_results = agent_messages
        session.status = "completed"

        return AgentTaskResult(messages=agent_messages)

    if parsed.action == "revise_agents":
        if not parsed.technical_specification:
            raise ValueError(
                "ProductManager выбрал revise_agents, но не вернул technical_specification")

        if not parsed.revision_request:
            raise ValueError(
                "ProductManager выбрал revise_agents, но не вернул revision_request")

        if not parsed.required_agents:
            raise ValueError(
                "ProductManager выбрал revise_agents, но не указал required_agents")

        previous_spec = session.last_technical_specification or "Предыдущее ТЗ отсутствует."
        previous_results = serialize_agent_results(session.last_agent_results)

        session.status = "revision_running"
        session.last_technical_specification = parsed.technical_specification

        revision_context = [
            SystemMessage(
                content=(
                    "Это правка уже выполненного проекта.\n\n"
                    "Пользователь общается только с Product Manager. "
                    "Ты получаешь от Product Manager обновленное ТЗ и конкретную правку.\n\n"
                    f"ПРЕДЫДУЩЕЕ ТЗ:\n{previous_spec}\n\n"
                    f"ПРЕДЫДУЩИЕ РЕЗУЛЬТАТЫ АГЕНТОВ:\n{previous_results}\n\n"
                    f"ЗАПРОС НА ПРАВКУ:\n{parsed.revision_request}\n\n"
                    "Выполни только свою часть правки. "
                    "Не переписывай все с нуля, если это не требуется."
                )
            )
        ]

        agent_messages = await run_selected_agents(
            technical_specification=parsed.technical_specification,
            agent_ids=parsed.required_agents,
            extra_context_messages=revision_context,
        )

        session.last_agent_results = agent_messages
        session.status = "completed"

        return AgentTaskResult(messages=agent_messages)

    raise ValueError(f"Необработанный action: {parsed.action}")


async def run_agents_directly(
    technical_specification: str,
    agent_ids: list[str],
) -> AgentTaskResult:
    """
    Ручной запуск агентов, если ТЗ уже готово.
    ProductManager здесь не используется.
    """

    messages = await run_selected_agents(
        technical_specification=technical_specification,
        agent_ids=agent_ids,
    )

    return AgentTaskResult(messages=messages)
