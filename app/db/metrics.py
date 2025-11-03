from .main import get_session


def get_metrics(project_id: int):
    query = "SELECT * FROM project_metrica WHERE project_id = %s"
    return get_session().execute(query, [project_id]).one()


def insert_metrics(data):
    query = """
    INSERT INTO project_metrica (project_id, progress_percent, progress_last_update,
    component_counter, code_string_counter, test_coverage_counter)
    VALUES (%s, %s, toTimestamp(now()), %s, %s, %s)
    """
    get_session().execute(query, [
        data.project_id,
        data.progress_percent,
        data.component_counter,
        data.code_string_counter,
        data.test_coverage_counter
    ])
    return {"status": "created"}
