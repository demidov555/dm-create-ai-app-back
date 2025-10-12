from fastapi import APIRouter
from ..db import projects, agents, messages, metrics
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ProjectInfo(BaseModel):
    project_id: int
    name: str
    description: Optional[str]
    status: str
    agent_count: int
    last_updated: str


@router.get("/projects")
def get_project():
    return projects.get_projects()


@router.get("/projects/{project_id}")
def get_project(project_id: int):
    # Получаем основную информацию о проекте
    project_info = projects.get_project_by_id(project_id)
    if not project_info:
        return {"error": "Project not found"}

    # Получаем агентов проекта
    agents = agents.get_agents_by_project(project_id)

    # Получаем метрику проекта
    metrica_raw = metrics.get_metrics(project_id)
    metrica = {
        "progress": {
            "percent": metrica_raw.progress_percent,
            "lastUpdate": str(metrica_raw.progress_last_update)
        },
        "componentCounter": metrica_raw.component_counter,
        "codeStringCoutner": metrica_raw.code_string_counter,
        "testOverageCouter": metrica_raw.test_coverage_counter
    }

    # Получаем сообщения проекта
    messages = messages.get_messages_by_project(project_id)

    # Собираем финальную модель
    return {
        "projectInfo": {
            "project_id": project_info.project_id,
            "name": project_info.name,
            "description": project_info.description,
            "status": project_info.status,
            "agent_count": project_info.agent_count,
            "last_updated": str(project_info.last_updated)
        },
        "agents": agents,
        "metrica": metrica,
        "messages": messages
    }


@router.post("/project_create")
def create_project(project: ProjectInfo):
    return projects.insert_project(project)
