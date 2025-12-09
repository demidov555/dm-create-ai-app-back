import uuid
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.agents.agent_metadata import AGENT_METADATA
from app.db import agents as db_agents
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class Agent(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str
    current_task: Optional[str]


class AgentsRequest(BaseModel):
    agent_ids: List[str]


class AgentsRequestWithProject(BaseModel):
    project_id: uuid.UUID
    agent_ids: List[str]


@router.get("/agents/available")
def get_available_agents():
    return {
        "list": [
            {
                "agentId": agent_id,
                "name": meta["name"],
                "role": meta["role"],
                "required": agent_id == "ProductManager",
            }
            for agent_id, meta in AGENT_METADATA.items()
        ]
    }


@router.post("/agents/by_ids")
def get_agents_with_state(request: AgentsRequestWithProject):
    agent_ids = request.agent_ids

    agents_meta = []
    for agent_id in agent_ids:
        meta = AGENT_METADATA.get(agent_id)
        if meta:
            agents_meta.append(
                {
                    "agent_id": agent_id,
                    "name": meta["name"],
                    "role": meta["role"],
                }
            )

    state_rows = db_agents.get_agent_state(request.project_id, agent_ids)
    state_map = {row.agent_id: row for row in state_rows}

    result = []
    for meta in agents_meta:
        a_id = meta["agent_id"]
        state = state_map.get(a_id)

        result.append(
            {
                "agentId": a_id,
                "name": meta["name"],
                "role": meta["role"],
                "status": state.status if state else None,
                "currentTask": state.current_task if state else None,
            }
        )

    return {"list": result}
