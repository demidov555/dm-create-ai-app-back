from db.main import get_session


def get_messages_by_project(project_id: int):
    query = """
    SELECT project_id, user_id, timestamp, role, message
    FROM messages
    WHERE project_id = %s
    """
    session = get_session()
    rows = session.execute(query, [project_id])
    return [dict(row._asdict()) for row in rows]


def insert_message(msg):
    query = """
    INSERT INTO messages (project_id, user_id, timestamp, role, message)
    VALUES (%s, %s, now(), %s, %s)
    """
    session = get_session()
    session.execute(query, [
        msg.project_id,
        msg.user_id,
        msg.role,
        msg.message
    ])
    return {"status": "created"}
