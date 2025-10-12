from fastapi import APIRouter
from db import agents as db_agents
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class Agent(BaseModel):
    project_id: int
    agent_id: str
    name: str
    role: str
    status: str
    current_task: Optional[str]

@router.get("/agents/{project_id}")
def get_agents(project_id: int):
    return db_agents.get_agents_by_project(project_id)

@router.post("/agents")
def create_agent(agent: Agent):
    return db_agents.insert_agent(agent)
