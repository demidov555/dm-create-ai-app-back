import uuid
from fastapi import APIRouter
from app.db import agents as db_agents
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class Agent(BaseModel):
    project_id: uuid.UUID
    agent_id: str
    name: str
    role: str
    status: str
    current_task: Optional[str]


@router.get("/agents/{project_id}")
def get_agents(project_id: uuid.UUID):
    agents_rows = db_agents.get_agents_by_project(project_id)

    return {
        "agents": [
            {
                "projectId": row.project_id,
                "agentId": row.agent_id,
                "currentTask": row.current_task,
                "role": row.role,
                "name": row.name,
                "status": row.status,
            }
            for row in agents_rows
        ],
    }
