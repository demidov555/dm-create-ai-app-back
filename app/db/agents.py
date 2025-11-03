from .main import get_session


def get_agents_by_project(project_id: int):
    query = "SELECT * FROM agents WHERE project_id = %s"
    return get_session().execute(query, [project_id]).all()


def insert_agent(agent):
    query = """
    INSERT INTO agents (project_id, agent_id, name, role, status, current_task)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    get_session().execute(query, [
        agent.project_id,
        agent.agent_id,
        agent.name,
        agent.role,
        agent.status,
        agent.current_task
    ])
    return {"status": "created"}
