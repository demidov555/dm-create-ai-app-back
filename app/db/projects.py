import uuid
from datetime import datetime
from app.db.main import get_session


def create_project(project, short_id: str):
    session = get_session()

    query = """
        INSERT INTO projects (
            project_id,
            short_id,
            name,
            description,
            status,
            agent_count,
            last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    session.execute(
        query,
        [
            project.project_id,
            short_id,
            project.name,
            project.description,
            project.status,
            project.agent_count,
            project.last_updated,
        ],
    )


def get_project_by_id(project_id: uuid.UUID):
    session = get_session()

    query = "SELECT * FROM projects WHERE project_id = %s"
    row = session.execute(query, [project_id]).one()
    return row


def get_project_by_short_id(short_id: str):
    session = get_session()

    query = "SELECT * FROM projects WHERE short_id = %s"
    row = session.execute(query, [short_id]).one()
    return row


def update_project(project_id: uuid.UUID, name: str, description: str):
    session = get_session()

    query = """
        UPDATE projects
        SET name = %s, description = %s, last_updated = %s
        WHERE project_id = %s
    """

    session.execute(query, [name, description, datetime.utcnow(), project_id])


def delete_project(project_id: uuid.UUID):
    session = get_session()

    query = "DELETE FROM projects WHERE project_id = %s"
    session.execute(query, [project_id])
