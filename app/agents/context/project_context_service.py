import uuid
from typing import List, Dict

from app.db import projects as db


class ProjectContextService:
    """
    Управляет состоянием проекта в Cassandra:
    """

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id

    # ==========================================================
    # MAIN ENTRYPOINT
    # ==========================================================
    def apply_operations(self, operations: List[Dict[str, str]]):
        self._apply_files(operations)
        self._update_structure()
        self._update_summaries()

    # ==========================================================
    # APPLY FILE OPERATIONS (Cassandra)
    # ==========================================================
    def _apply_files(self, operations: List[Dict[str, str]]):
        for op in operations:
            action = op["op"]
            path = op["path"]
            agent = op.get("agent", "ai")

            # ----------------------
            # CREATE / UPDATE
            # ----------------------
            if action in ("create", "update"):
                content = op.get("content", "")

                db.upsert_file(
                    project_id=self.project_id,
                    file_path=path,
                    content=content,
                    agent=agent,
                )

                db.set_agent_memory(
                    project_id=self.project_id,
                    agent_name=agent,
                    key=f"touched::{path}",
                    value="updated",
                )

            # ----------------------
            # DELETE
            # ----------------------
            elif action == "delete":
                db.delete_file(
                    project_id=self.project_id,
                    file_path=path,
                    agent=agent,
                )

                # удаляем summary
                db.set_file_summary(
                    project_id=self.project_id, file_path=path, summary=""
                )

                db.set_agent_memory(
                    project_id=self.project_id,
                    agent_name=agent,
                    key=f"deleted::{path}",
                    value="true",
                )

            # ----------------------
            # UNKNOWN OPERATION
            # ----------------------
            else:
                print(f"[WARN] Unknown operation '{action}' for path '{path}'")

    # ==========================================================
    # STRUCTURE
    # ==========================================================
    def _update_structure(self):
        file_paths = list(db.get_all_files(self.project_id).keys())
        db.update_structure_cache(self.project_id, file_paths)

    # ==========================================================
    # SUMMARIES
    # ==========================================================
    def _update_summaries(self):
        files = db.get_all_files(self.project_id)

        for path, content in files.items():
            summary = self._summarize(content)
            db.set_file_summary(self.project_id, path, summary)

    def _summarize(self, content: str) -> str:
        if not content:
            return "Пустой файл."

        text = content.strip()
        if len(text) > 200:
            return text[:200] + "..."

        return text
