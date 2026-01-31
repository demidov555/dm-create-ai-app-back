import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

from app.agents.prompts import (
    BACKEND_SYSTEM_PROMPT,
    CONTRACT_AGENT_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
    PRODUCT_MANAGER_SYSTEM_PROMPT,
    INTERFACE_SYSTEM_PROMPT,
)

load_dotenv()

AI_MODEL = os.getenv("AI_MODEL")
AI_API_KEY = os.getenv("AI_API_KEY")

if not AI_MODEL or not AI_API_KEY:
    raise EnvironmentError("Установите AI_MODEL и AI_API_KEY в .env")

model_client = OpenAIChatCompletionClient(
    model=AI_MODEL,
    api_key=AI_API_KEY,
)

product_manager = AssistantAgent(
    name="ProductManager",
    model_client=model_client,
    model_client_stream=True,
    system_message=PRODUCT_MANAGER_SYSTEM_PROMPT,
)

contract_agent = AssistantAgent(
    name="ContractAgent", model_client=model_client, system_message=CONTRACT_AGENT_SYSTEM_PROMPT
)

frontend = AssistantAgent(
    name="Frontend", model_client=model_client, system_message=FRONTEND_SYSTEM_PROMPT
)

backend = AssistantAgent(
    name="Backend", model_client=model_client, system_message=BACKEND_SYSTEM_PROMPT
)

interface = AssistantAgent(
    name="Interface", model_client=model_client, system_message=INTERFACE_SYSTEM_PROMPT
)

AI_AGENT_OBJECTS = {
    "interface": interface,
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
