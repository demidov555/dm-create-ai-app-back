from datetime import datetime
import json
import uuid
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, StreamingResponse
from nanoid import generate

from app.agents.manage_repo.repository_service import RepositoryService
from app.db import projects, metrics
from pydantic import BaseModel
from typing import Optional

from app.db import agents as db_agents
from app.status.enums import ProjectStatus
from app.status.sse_status_broadcaster import sse_status_broadcaster

router = APIRouter()


class Metrica(BaseModel):
    project_id: uuid.UUID
    progress_percent: int
    component_counter: int
    code_string_counter: int
    test_coverage_counter: int


class ProjectInfo(BaseModel):
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    status: str
    agent_ids: list[str]
    last_updated: datetime


class ProjectInfoRequest(BaseModel):
    name: str
    description: str
    agent_ids: list[str]


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


def generate_short_id() -> str:
    return generate(size=6)


@router.get("/projects")
def get_project():
    query = "SELECT * FROM projects"
    session = projects.get_session()
    rows = session.execute(query)

    return [
        {
            "projectId": str(row.project_id),
            "shortId": getattr(row, "short_id", None),
            "agentIds": row.agent_ids,
            "description": row.description,
            "lastUpdated": row.last_updated,
            "name": row.name,
            "status": row.status,
        }
        for row in rows
    ]


@router.get("/projects/{short_id}")
def get_project_by_short(short_id: str):
    project_info = projects.get_project_by_short_id(short_id)

    if not project_info:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": status.HTTP_404_NOT_FOUND,
                "error": "not_found",
                "message": "Проект не найден",
                "short_id": short_id,
            },
        )

    metrica_row = metrics.get_metrics(project_info.project_id)

    return {
        "projectInfo": {
            "projectId": str(project_info.project_id),
            "shortId": project_info.short_id,
            "name": project_info.name,
            "description": project_info.description,
            "status": project_info.status,
            "agentIds": project_info.agent_ids,
            "lastUpdated": str(project_info.last_updated),
            "metrica": {
                "progress": {
                    "percent": metrica_row.progress_percent,
                    "lastUpdate": str(metrica_row.progress_last_update),
                },
                "componentCounter": metrica_row.component_counter,
                "codeStringCoutner": metrica_row.code_string_counter,
                "testOverageCouter": metrica_row.test_coverage_counter,
            },
        }
    }


@router.post("/project_create")
def create_project(body: ProjectInfoRequest):
    project_id = uuid.uuid4()
    now = datetime.utcnow()
    short_id = generate_short_id()
    new_project = ProjectInfo(
        project_id=project_id,
        name=body.name,
        description=body.description,
        status=ProjectStatus.IN_PROGRESS,
        agent_ids=body.agent_ids,
        last_updated=now,
    )
    new_metrics = Metrica(
        project_id=project_id,
        progress_percent=0,
        component_counter=0,
        code_string_counter=0,
        test_coverage_counter=0,
    )

    try:
        projects.create_project_with_defaults(new_project, new_metrics, short_id)
        repo_service = RepositoryService(project_id)
        repo_service.create_repo("project-" + str(project_id))

        for agent_id in body.agent_ids:
            db_agents.create_agent_state(
                project_id=project_id,
                agent_id=agent_id,
                status="idle",
                current_task=None,
            )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "creation_failed",
                "message": "Ошибка при создании проекта",
                "details": str(e),
            },
        )

    return {
        "projectId": str(project_id),
        "shortId": short_id,
    }


@router.patch("/projects/{project_id}")
def update_project(project_id: uuid.UUID, body: ProjectUpdateRequest):
    if body.name is None and body.description is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "bad_request",
                "message": "Хотя бы одно из полей (name или description) должно быть указано",
            },
        )

    current_project = projects.get_project_by_id(project_id)

    if not current_project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": status.HTTP_404_NOT_FOUND,
                "error": "not_found",
                "message": "Проект не найден",
                "project_id": str(project_id),
            },
        )

    new_name = body.name if body.name is not None else current_project.name
    new_description = (
        body.description
        if body.description is not None
        else current_project.description
    )

    try:
        projects.update_project(
            project_id=project_id,
            name=new_name,
            description=new_description,
        )
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": "Проект не найден"},
        )

    return {
        "projectId": str(project_id),
        "name": new_name,
        "description": new_description,
    }


@router.delete("/projects/{project_id}")
def delete_project(project_id: uuid.UUID):
    project = projects.get_project_by_id(project_id)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status": status.HTTP_404_NOT_FOUND,
                "error": "not_found",
                "message": "Проект не найден",
                "project_id": str(project_id),
            },
        )

    try:
        projects.delete_project_with_data(project_id)
        repo_service = RepositoryService(project_id)
        repo_service.delete_repo()

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "delete_failed",
                "message": "Ошибка при удалении проекта",
                "details": str(e),
            },
        )

    return {
        "projectId": str(project_id),
    }


@router.get("/projects/{project_id}/status/stream")
async def stream_status(project_id: uuid.UUID):
    queue = await sse_status_broadcaster.subscribe(project_id)

    async def event_stream():
        initial = {"type": "init", "status": "connected"}
        yield f"event: init\n"
        yield f"data: {json.dumps(initial)}\n\n"

        try:
            while True:
                data = await queue.get()
                yield f"event: {data['type']}\n"
                yield f"data: {json.dumps(data)}\n\n"
        finally:
            sse_status_broadcaster.unsubscribe(project_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
