from fastapi import APIRouter
from ..db import projects, metrics, agents, messages
from pydantic import BaseModel
from typing import Optional
from pprint import pprint

router = APIRouter()


class Metrica(BaseModel):
    project_id: int
    progress_percent: int
    component_counter: int
    code_string_counter: int
    test_coverage_counter: int


class ProjectInfo(BaseModel):
    project_id: int
    name: str
    description: Optional[str]
    status: str
    agent_count: int
    last_updated: str


class ProjectInfoRequest(BaseModel):
    name: str
    description: str
    agent_count: int


@router.get("/projects")
def get_project():
    query = "SELECT * FROM projects"
    session = projects.get_session()
    rows = session.execute(query)

    return [
        {
            "projectId": row.project_id,
            "agentCount": row.agent_count,
            "description": row.description,
            "lastUpdated": row.last_updated,
            "name": row.name,
            "status": row.status
        }
        for row in rows
    ]


@router.get("/projects/{project_id}")
def get_project(project_id: int):
    project_info = projects.get_project_by_id(project_id)
    agents_rows = agents.get_agents_by_project(project_id)
    metrica_row = metrics.get_metrics(project_id)
    messages_rows = messages.get_messages_by_project(project_id)

    return {
        "projectInfo": {
            "projectId": project_info.project_id,
            "name": project_info.name,
            "description": project_info.description,
            "status": project_info.status,
            "agentCount": project_info.agent_count,
            "lastUpdated": str(project_info.last_updated)
        },
        "agents": [
            {
                "projectId": row.project_id,
                "agentId": row.agent_id,
                "currentTask": row.current_task,
                "role": row.role,
                "name": row.name,
                "status": row.status
            }
            for row in agents_rows
        ],
        "metrica": {
            "progress": {
                "percent": metrica_row.progress_percent,
                "lastUpdate": str(metrica_row.progress_last_update)
            },
            "componentCounter": metrica_row.component_counter,
            "codeStringCoutner": metrica_row.code_string_counter,
            "testOverageCouter": metrica_row.test_coverage_counter
        },
        "messages": messages_rows
    }


@router.post("/project_create")
def create_project(body: ProjectInfoRequest):
    # uuid.uuid4().hex
    new_project = ProjectInfo(
        project_id=2,
        name=body.name,
        description=body.description,
        status="active",
        agent_count=body.agent_count,
        last_updated="",
    )

    new_metrics = Metrica(
        project_id=2,
        progress_percent=0,
        component_counter=0,
        code_string_counter=0,
        test_coverage_counter=0,
    )

    metrics.insert_metrics(new_metrics)

    return projects.insert_project(new_project)
