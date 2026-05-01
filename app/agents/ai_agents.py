import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agents.prompts import (
    BACKEND_SYSTEM_PROMPT,
    CONTRACT_AGENT_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
    PRODUCT_MANAGER_SYSTEM_PROMPT,
    INTERFACE_SYSTEM_PROMPT,
)
from app.logger.console_logger import error


@dataclass
class AgentMessage:
    source: str
    content: str


@dataclass
class AgentTaskResult:
    messages: list[AgentMessage]


class LangGraphAssistantAgent:
    def __init__(self, name: str, model: ChatOpenAI, system_message: str, stream_output: bool = False):
        self.name = name
        self.model = model
        self.system_message = system_message
        self.stream_output = stream_output

    def _build_graph(self):
        class State(dict):
            pass

        async def call_model(state: State) -> State:
            messages = state["messages"]
            response = await self.model.ainvoke(messages)
            return {"messages": messages + [response]}

        graph = StateGraph(State)
        graph.add_node("call_model", call_model)
        graph.set_entry_point("call_model")
        graph.add_edge("call_model", END)
        return graph.compile()

    async def run(self, task: str, context_messages: list[Any] | None = None) -> AgentTaskResult:
        context_messages = context_messages or []
        initial_messages = [SystemMessage(content=self.system_message), *context_messages, HumanMessage(content=task)]
        app = self._build_graph()
        result = await app.ainvoke({"messages": initial_messages})
        response = result["messages"][-1]
        content = response.content if isinstance(response, AIMessage) else str(response)
        return AgentTaskResult(messages=[AgentMessage(source=self.name, content=content)])

    async def run_stream(self, task: str, context_messages: list[Any] | None = None) -> AsyncGenerator[AgentMessage, None]:
        context_messages = context_messages or []
        input_messages = [SystemMessage(content=self.system_message), *context_messages, HumanMessage(content=task)]
        async for part in self.model.astream(input_messages):
            content = getattr(part, "content", "")
            if content:
                yield AgentMessage(source=self.name, content=content)


load_dotenv()

AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

if not AI_MODEL or not AI_API_KEY:
    raise EnvironmentError("Установите AI_MODEL и AI_API_KEY в .env")

model_client = ChatOpenAI(model=AI_MODEL, api_key=AI_API_KEY, temperature=0)

product_manager = LangGraphAssistantAgent(
    name="ProductManager",
    model=model_client,
    system_message=PRODUCT_MANAGER_SYSTEM_PROMPT,
    stream_output=True,
)

contract_agent = LangGraphAssistantAgent(
    name="ContractAgent", model=model_client, system_message=CONTRACT_AGENT_SYSTEM_PROMPT
)

frontend = LangGraphAssistantAgent(
    name="Frontend", model=model_client, system_message=FRONTEND_SYSTEM_PROMPT
)

backend = LangGraphAssistantAgent(
    name="Backend", model=model_client, system_message=BACKEND_SYSTEM_PROMPT
)

interface = LangGraphAssistantAgent(
    name="Interface", model=model_client, system_message=INTERFACE_SYSTEM_PROMPT
)

AI_AGENT_OBJECTS = {
    "interface": interface,
    "frontend": frontend,
    "backend": backend,
}


def get_ai_agents_by_ids(agent_ids: list[str]) -> list[LangGraphAssistantAgent]:
    agents: list[LangGraphAssistantAgent] = []

    for agent_id in agent_ids:
        key = agent_id.strip()

        if key not in AI_AGENT_OBJECTS:
            error(f"ERROR: agent '{key}' NOT FOUND in AI_AGENT_OBJECTS!")
            raise ValueError(f"AI agent '{key}' not found")

        agent = AI_AGENT_OBJECTS[key]

        if not hasattr(agent, "run_stream"):
            error(f"ERROR: agent '{key}' is not a valid LangGraphAssistantAgent")
            raise TypeError(f"Object '{key}' is not a valid agent instance")

        agents.append(agent)

    return agents
