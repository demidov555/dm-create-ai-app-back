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


def delete_metrics(project_id: uuid.UUID):
    query = "DELETE FROM project_metrica WHERE project_id = %s"
    get_session().execute(query, [project_id])
