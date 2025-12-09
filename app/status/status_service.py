import uuid
import datetime

from app.db.agents import update_agent_state, get_agent_state
from app.db.main import get_session
from app.db.projects import get_project_by_id
from app.db.metrics import update_metrics
from app.logger.console_logger import error
from app.status.sse_status_broadcaster import sse_status_broadcaster
from app.status.enums import (
    PROJECT_STAGE_WEIGHTS,
    AgentStatus,
    AgentTask,
    ProjectStage,
    ProjectStatus,
)


class StatusService:
    """
    Универсальный сервис для обновления статусов агентов и проектов.
    Работает с Enum, обновляет Cassandra, отправляет SSE.
    """

    _stage_progress: dict[uuid.UUID, dict[ProjectStage, int]] = {}

    # =====================================================
    # AGENT STATUS
    # =====================================================

    @staticmethod
    async def set_agent_status(
        project_id: uuid.UUID,
        agent_id: str,
        status: AgentStatus,
        current_task: AgentTask | None = None,
        progress: int | None = None,
    ):
        """
        Обновляет статус конкретного агента и пушит SSE.
        """

        update_agent_state(
            project_id=project_id,
            agent_id=agent_id,
            status=status.value,
            current_task=current_task.value if current_task else None,
            progress=progress,
        )

        await sse_status_broadcaster.send(
            project_id,
            {
                "type": "agent_status",
                "agent_id": agent_id,
                "status": status.value,
                "current_task": current_task.value if current_task else None,
                "progress": progress,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    def get_agent_status(project_id: uuid.UUID, agent_id: str):
        row = get_agent_state(project_id, [agent_id])
        if not row:
            return None

        r = row[0]

        return {
            "agent_id": r.agent_id,
            "status": AgentStatus(r.status),
            "current_task": (
                AgentTask(r.current_task) if r.current_task else AgentTask.NONE
            ),
            "progress": r.progress,
            "updated_at": r.last_updated,
        }

    # =====================================================
    # PROJECT STATUS
    # =====================================================
    @staticmethod
    async def set_project_status(
        project_id: uuid.UUID,
        status: ProjectStatus,
        stage: ProjectStage | None = None,
        stage_progress: int | None = None,
    ):
        """
        Единственный метод для:
        - обновления статуса проекта
        - обновления прогресса этапов
        - расчёта итогового прогресса (0..100)
        - отправки SSE
        """

        now = datetime.datetime.utcnow()
        session = get_session()

        # обновляем статус проекта в БД
        session.execute(
            """
            UPDATE projects
            SET status = %s, last_updated = %s
            WHERE project_id = %s
            """,
            [status.value, now, project_id],
        )

        # Если вызывается PM_TZ START — полностью сбрасываем pipeline
        # RESET — если это первый запуск IN_PROGRESS без указания стадии
        if stage is None and status == ProjectStatus.IN_PROGRESS:
            StatusService._stage_progress[project_id] = {
                st: 0 for st in ProjectStage
            }

        # Инициализация, если нет ключа
        if project_id not in StatusService._stage_progress:
            StatusService._stage_progress[project_id] = {
                st: 0 for st in ProjectStage
            }

        # Обновляем стадию, но только если пришёл stage_progress
        if stage is not None and stage_progress is not None:
            StatusService._stage_progress[project_id][stage] = stage_progress


        # ------------------------------
        # Считаем итоговый прогресс 0..100
        # ------------------------------
        total = 0
        for st, value in StatusService._stage_progress[project_id].items():
            weight = PROJECT_STAGE_WEIGHTS.get(st, 0)
            total += (value / 100) * weight

        total_percent = round(total * 100)

        update_metrics(project_id, {"progress_percent": total_percent})

        # ------------------------------
        # SSE — отдаём только 0..100
        # ------------------------------
        await sse_status_broadcaster.send(
            project_id,
            {
                "type": "project_status",
                "projectId": str(project_id),
                "status": status.value,
                "progress": total_percent,
                "lastUpdate": now.isoformat(),
            },
        )

        return total_percent

    @staticmethod
    def get_project_status(project_id: uuid.UUID):
        row = get_project_by_id(project_id)
        if not row:
            return None

        return ProjectStatus(row.status)

    @staticmethod
    async def push_agent_live_status(
        project_id: uuid.UUID,
        agent_id: str,
        status: str,
        current_task: str | None = None,
        progress: int | None = None,
    ):
        """
        Отправляет *живой* статус агента.
        НЕ сохраняет ничего в БД.
        Используется для анимации прогресса на фронте.
        """

        await sse_status_broadcaster.send(
            project_id,
            {
                "type": "agent_status",
                "agent_id": agent_id,
                "status": status,
                "current_task": current_task,
                "progress": progress,
                "updated_at": datetime.datetime.utcnow().isoformat(),
                "live": True,
            },
        )
