import uuid
from .main import get_session


def get_metrics(project_id: uuid.UUID):
    query = "SELECT * FROM project_metrica WHERE project_id = %s"
    return get_session().execute(query, [project_id]).one()


def create_metrics(metrics):
    query = """
    INSERT INTO project_metrica (
        project_id,
        progress_percent,
        progress_last_update,
        component_counter,
        code_string_counter,
        test_coverage_counter
    )
    VALUES (%s, %s, toTimestamp(now()), %s, %s, %s)
    """

    get_session().execute(
        query,
        [
            metrics.project_id,
            metrics.progress_percent,
            metrics.component_counter,
            metrics.code_string_counter,
            metrics.test_coverage_counter,
        ],
    )

    return {"status": "created", "projectId": str(metrics.project_id)}


def update_metrics(project_id: uuid.UUID, updates: dict):
    """
    Универсальное обновление метрик проекта.
    Обновляет только те поля, которые переданы в updates.
    progress_last_update обновляется всегда.

    updates пример:
        {
            "progress_percent": 100,
            "code_string_counter": 2530
        }
    """

    if not updates:
        return {"status": "skipped", "reason": "empty update"}

    session = get_session()

    set_clauses = []
    values = []

    # динамически собираем SET выражение
    for field, value in updates.items():
        set_clauses.append(f"{field} = %s")
        values.append(value)

    # progress_last_update ставим всегда
    set_clauses.append("progress_last_update = toTimestamp(now())")

    query = f"""
        UPDATE project_metrica
        SET {", ".join(set_clauses)}
        WHERE project_id = %s
    """

    values.append(project_id)

    session.execute(query, values)

    return {"status": "updated", "projectId": str(project_id)}


def delete_metrics(project_id: uuid.UUID):
    query = "DELETE FROM project_metrica WHERE project_id = %s"
    get_session().execute(query, [project_id])
