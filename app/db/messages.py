import uuid
from datetime import datetime
from .main import get_session


# ===============================
#  SAVE MESSAGE
# ===============================
def save_message(msg):
    """
    Сохраняем сообщение и регистрируем bucket в отдельной таблице message_buckets.
    """
    session = get_session()

    bucket = datetime.utcnow().strftime("%Y-%m")

    # 1. Сохраняем само сообщение
    session.execute(
        """
        INSERT INTO messages (project_id, bucket, timestamp, role, message)
        VALUES (%s, %s, now(), %s, %s)
        """,
        [msg.project_id, bucket, msg.role, msg.message],
    )

    # 2. Регистрируем bucket (если он уже есть — Cassandra просто перезапишет запись)
    session.execute(
        """
        INSERT INTO message_buckets (project_id, bucket)
        VALUES (%s, %s)
        """,
        [msg.project_id, bucket],
    )

    return {"status": "created"}


# ===============================
#  GET BUCKETS
# ===============================
def get_buckets_by_project(project_id: uuid.UUID):
    """
    Получаем все уникальные bucket'ы проекта через отдельную таблицу.
    """
    query = """
    SELECT bucket FROM message_buckets
    WHERE project_id = %s
    """

    rows = get_session().execute(query, [project_id])

    return [row.bucket for row in rows]


# ===============================
#  GET MESSAGES BY BUCKET
# ===============================
def get_messages_by_bucket(project_id: uuid.UUID, bucket: str):
    """
    Возвращает все сообщения внутри одного bucket.
    """
    query = """
    SELECT project_id, bucket, timestamp, role, message
    FROM messages
    WHERE project_id = %s AND bucket = %s
    """

    rows = get_session().execute(query, [project_id, bucket])

    return [
        {
            "projectId": row.project_id,
            "bucket": row.bucket,
            "role": row.role,
            "message": row.message,
            "timestamp": row.timestamp,
        }
        for row in rows
    ]


# ===============================
#  GET ALL MESSAGES
# ===============================
def get_all_messages(project_id: uuid.UUID):
    """
    Полностью оптимальный вариант:
    1. Получаем bucket'ы проекта
    2. Для каждого bucket — грузим сообщения
    """
    buckets = get_buckets_by_project(project_id)

    all_messages = []
    for bucket in sorted(buckets):  # сортируем YYYY-MM
        msgs = get_messages_by_bucket(project_id, bucket)
        all_messages.extend(msgs)

    return all_messages
