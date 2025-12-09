import uuid
from datetime import datetime
from app.db.agents import delete_agent_states_by_project
from app.db.main import get_session
from app.db.messages import delete_messages_by_project
from app.db.metrics import create_metrics, delete_metrics


def create_project(project, short_id: str):
    session = get_session()

    query = """
        INSERT INTO projects (
            project_id,
            short_id,
            name,
            description,
            status,
            agent_ids,
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
            project.agent_ids,
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


# ================================================================
# PROJECT FILES
# ================================================================
def get_file(project_id: uuid.UUID, file_path: str):
    session = get_session()

    row = session.execute(
        """
        SELECT file_path, content, updated_at
        FROM project_files
        WHERE project_id = %s AND file_path = %s
        """,
        [project_id, file_path],
    ).one()

    return row


def get_all_files(project_id: uuid.UUID):
    session = get_session()

    rows = session.execute(
        """
        SELECT file_path, content
        FROM project_files
        WHERE project_id = %s
        """,
        [project_id],
    )

    return {row.file_path: row.content for row in rows}


def upsert_file(project_id: uuid.UUID, file_path: str, content: str, agent: str):
    session = get_session()

    now = datetime.utcnow()

    # old content (for history)
    old_row = get_file(project_id, file_path)
    old_content = old_row.content if old_row else None

    session.execute(
        """
        INSERT INTO project_files (project_id, file_path, content, updated_at)
        VALUES (%s, %s, %s, %s)
        """,
        [project_id, file_path, content, now],
    )

    insert_file_history(
        project_id=project_id,
        file_path=file_path,
        operation="update" if old_row else "create",
        before=old_content,
        after=content,
        agent=agent,
    )


def delete_file(project_id: uuid.UUID, file_path: str, agent: str):
    session = get_session()

    old = get_file(project_id, file_path)
    old_content = old.content if old else None

    session.execute(
        """
        DELETE FROM project_files
        WHERE project_id = %s AND file_path = %s
        """,
        [project_id, file_path],
    )

    insert_file_history(project_id, file_path, "delete", old_content, None, agent)


# ================================================================
# PROJECT FILE HISTORY
# ================================================================
def insert_file_history(project_id, file_path, operation, before, after, agent):
    session = get_session()

    session.execute(
        """
        INSERT INTO project_file_history
        (project_id, file_path, version_time, operation, content_before, content_after, agent)
        VALUES (%s, %s, toTimestamp(now()), %s, %s, %s, %s)
        """,
        [project_id, file_path, operation, before, after, agent],
    )


def get_file_history(project_id, file_path, limit=20):
    session = get_session()

    rows = session.execute(
        """
        SELECT *
        FROM project_file_history
        WHERE project_id = %s AND file_path = %s
        LIMIT %s
        """,
        [project_id, file_path, limit],
    )
    return list(rows)


# ================================================================
# PROJECT STRUCTURE CACHE
# ================================================================
def get_structure_cache(project_id: uuid.UUID):
    session = get_session()

    row = session.execute(
        "SELECT tree FROM project_structure_cache WHERE project_id = %s",
        [project_id],
    ).one()

    return row.tree if row else ""


def update_structure_cache(project_id: uuid.UUID, file_paths: list[str]):
    session = get_session()

    tree = build_tree(file_paths)

    session.execute(
        """
        INSERT INTO project_structure_cache (project_id, tree, updated_at)
        VALUES (%s, %s, toTimestamp(now()))
        """,
        [project_id, tree],
    )

    return tree


def build_tree(paths: list[str]) -> str:
    root = {}

    for p in paths:
        parts = p.split("/")
        cur = root
        for part in parts:
            cur = cur.setdefault(part, {})

    def render(node, indent=0):
        s = ""
        for name, children in node.items():
            prefix = "  " * indent
            if children:
                s += f"{prefix}{name}/\n"
                s += render(children, indent + 1)
            else:
                s += f"{prefix}{name}\n"
        return s

    return render(root)


# ================================================================
# FILE SUMMARIES
# ================================================================
def get_file_summaries(project_id: uuid.UUID):
    session = get_session()

    rows = session.execute(
        """
        SELECT file_path, summary
        FROM project_file_summaries
        WHERE project_id = %s
        """,
        [project_id],
    )

    return {row.file_path: row.summary for row in rows}


def set_file_summary(project_id: uuid.UUID, file_path: str, summary: str):
    session = get_session()

    session.execute(
        """
        INSERT INTO project_file_summaries
        (project_id, file_path, summary, updated_at)
        VALUES (%s, %s, %s, toTimestamp(now()))
        """,
        [project_id, file_path, summary],
    )


# ================================================================
# AGENT MEMORY
# ================================================================
def get_agent_memory(project_id: uuid.UUID, agent_name: str):
    session = get_session()

    rows = session.execute(
        """
        SELECT key, value
        FROM agent_project_context
        WHERE project_id = %s AND agent_name = %s
        """,
        [project_id, agent_name],
    )

    return {row.key: row.value for row in rows}


def set_agent_memory(project_id: uuid.UUID, agent_name: str, key: str, value: str):
    session = get_session()

    session.execute(
        """
        INSERT INTO agent_project_context
        (project_id, agent_name, key, value, updated_at)
        VALUES (%s, %s, %s, %s, toTimestamp(now()))
        """,
        [project_id, agent_name, key, value],
    )


def create_project_with_defaults(project, metrics, short_id: str):
    create_project(project, short_id)
    update_structure_cache(project.project_id, [])

    for agent in project.agent_ids:
        set_agent_memory(
            project_id=project.project_id, agent_name=agent, key="init", value="{}"
        )

    create_metrics(metrics)


def delete_project_with_data(project_id: uuid.UUID):
    session = get_session()

    # получить файлы до удаления
    file_paths = list(get_all_files(project_id).keys())

    # удалить файлы через delete_file
    for file_path in file_paths:
        delete_file(project_id, file_path, agent="system")

    # удалить историю
    for file_path in file_paths:
        session.execute(
            """
            DELETE FROM project_file_history
            WHERE project_id = %s AND file_path = %s
            """,
            [project_id, file_path],
        )

    # удалить структуру
    session.execute(
        "DELETE FROM project_structure_cache WHERE project_id = %s", [project_id]
    )

    # удалить summaries
    session.execute(
        "DELETE FROM project_file_summaries WHERE project_id = %s", [project_id]
    )

    # удалить проект
    session.execute("DELETE FROM projects WHERE project_id = %s", [project_id])

    # удалить метрики
    delete_metrics(project_id)

    # удалить сообщения
    delete_messages_by_project(project_id)

    # удалить agent state
    delete_agent_states_by_project(project_id)
