import uuid
from app.status.enums import AgentStatus, AgentTask, ProjectStage, ProjectStatus
from app.status.status_service import StatusService


async def set_stage(
    project_id: uuid.UUID,
    stage: ProjectStage,
    progress: int | None,
    status: ProjectStatus = ProjectStatus.IN_PROGRESS,
):
    await StatusService.set_project_status(
        project_id,
        status,
        stage=stage,
        stage_progress=progress,
    )


async def set_error(project_id: uuid.UUID):
    await StatusService.set_project_status(project_id, ProjectStatus.ERROR)


async def set_completed(project_id: uuid.UUID):
    await StatusService.set_project_status(project_id, ProjectStatus.COMPLETED)


async def agent_working(project_id: uuid.UUID, agent_name: str, task: AgentTask):
    await StatusService.set_agent_status(
        project_id,
        agent_id=agent_name,
        status=AgentStatus.WORKING,
        current_task=task,
    )


async def agent_completed(project_id: uuid.UUID, agent_name: str):
    await StatusService.set_agent_status(
        project_id,
        agent_id=agent_name,
        status=AgentStatus.COMPLETED,
        current_task=AgentTask.FINALIZING,
        progress=100,
    )


async def agent_live(project_id: uuid.UUID, agent_name: str, task: AgentTask):
    await StatusService.push_agent_live_status(
        project_id,
        agent_id=agent_name,
        status=AgentStatus.WORKING,
        current_task=task,
    )
