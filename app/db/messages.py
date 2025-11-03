from .main import get_session


def get_messages_by_project(project_id: int):
    query = """
    SELECT project_id, user_id, timestamp, role, message
    FROM messages
    WHERE project_id = %s
    """

    rows = get_session().execute(query, [project_id])

    return [
        {
            "projectId": row.project_id,
            "message": row.message,
            "role": row.role,
            "timestamp": row.timestamp,
            "userId": row.user_id
        }
        for row in rows
    ]


def insert_message(msg):
    query = """
    INSERT INTO messages (project_id, user_id, timestamp, role, message)
    VALUES (%s, %s, now(), %s, %s)
    """

    get_session().execute(query, [
        msg.project_id,
        msg.user_id,
        msg.role,
        msg.message
    ])
    return {"status": "created"}
