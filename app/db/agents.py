from datetime import datetime
import uuid
from app.db.main import get_session


def create_agent_state(
    project_id: uuid.UUID,
    agent_id: str,
    status: str = "idle",
    current_task: str = None,
    progress: int = 0,
):
    session = get_session()

    query = """
        INSERT INTO agent_state (
            project_id,
            agent_id,
            status,
            current_task,
            progress,
            last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    session.execute(
        query, [project_id, agent_id, status, current_task, progress, datetime.utcnow()]
    )


def get_agent_state(project_id: uuid.UUID, agent_ids: list[str]):
    session = get_session()

    if not agent_ids:
        return []

    placeholders = ", ".join(["%s"] * len(agent_ids))

    query = f"""
        SELECT *
        FROM agent_state
        WHERE project_id = %s AND agent_id IN ({placeholders})
    """

    params = [project_id] + agent_ids
    rows = session.execute(query, params)

    return list(rows)


def update_agent_state(
    project_id: uuid.UUID,
    agent_id: str,
    status: str,
    current_task: str = None,
    progress: int = None,
):

    session = get_session()

    query = """
        UPDATE agent_state
        SET status = %s,
            current_task = %s,
            progress = %s,
            last_updated = %s
        WHERE project_id = %s AND agent_id = %s
    """

    session.execute(
        query, [status, current_task, progress, datetime.utcnow(), project_id, agent_id]
    )


def delete_agent_states_by_project(project_id: uuid.UUID):
    session = get_session()

    rows = session.execute(
        "SELECT agent_id FROM agent_state WHERE project_id = %s", [project_id]
    )

    for row in rows:
        session.execute(
            "DELETE FROM agent_state WHERE project_id = %s AND agent_id = %s",
            [project_id, row.agent_id],
        )

    return {"status": "deleted", "project_id": str(project_id)}


def get_agent(agent_id: str):
    session = get_session()

    query = "SELECT * FROM agents WHERE agent_id = %s"
    return session.execute(query, [agent_id]).one()


def get_agents_by_ids(agent_ids: list[str]):
    session = get_session()

    query = "SELECT * FROM agents WHERE agent_id IN %s"
    rows = session.execute(query, [tuple(agent_ids)])
    return list(rows)


def get_all_agents():
    session = get_session()

    query = "SELECT * FROM agents"
    rows = session.execute(query)
    return list(rows)
