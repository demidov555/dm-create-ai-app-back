from .main import get_session


def get_projects():
    query = "SELECT * FROM projects"
    return get_session().execute(query).one()


def get_project_by_id(project_id: int):
    query = "SELECT * FROM projects WHERE project_id = %s"
    return get_session().execute(query, [project_id]).one()


def insert_project(project):
    query = """
    INSERT INTO projects (project_id, name, description, status, agent_count, last_updated)
    VALUES (%s, %s, %s, %s, %s, toTimestamp(now()))
    """

    get_session().execute(query, [
        project.project_id,
        project.name,
        project.description,
        project.status,
        project.agent_count
    ])

    return {"projectId": project.project_id}
