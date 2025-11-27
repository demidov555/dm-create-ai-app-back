from logging import error, info
from github import GithubException
import os


class DeploymentManager:
    def __init__(self, repo_obj, gh, user):
        self.repo_obj = repo_obj
        self.gh = gh
        self.user = user

    def enable_pages(self):
        """
        Включает GitHub Pages для репозитория в режиме workflow.
        """
        requester = self.gh._Github__requester
        owner = self.user.login
        repo = self.repo_obj.name

        try:
            requester.requestJsonAndCheck(
                "POST",
                f"/repos/{owner}/{repo}/pages",
                input={"build_type": "workflow"},
            )
            info("GitHub Pages enabled")
        except GithubException as e:
            error(f"Ошибка включения Pages: {e}")

    def update_pages(self):
        requester = self.gh._Github__requester
        owner = self.user.login
        repo = self.repo_obj.name

        try:
            requester.requestJsonAndCheck(
                "PUT",
                f"/repos/{owner}/{repo}/pages",
                input={"build_type": "workflow"},
            )
            info("GitHub Pages updated")
        except GithubException as e:
            error(f"Ошибка обновления Pages: {e}")

    def push_actions_workflow(self):
        workflow_path_repo = ".github/workflows/pages.yml"
        workflow_path_local = os.path.join(
            os.path.dirname(__file__), "workflows", "pages.yml"
        )

        # Проверяем наличие workflow
        try:
            self.repo_obj.get_contents(workflow_path_repo)
            info("Workflow already exists — skipped.")
        except GithubException as e:
            if e.status != 404:
                error(f"Ошибка проверки workflow: {e}")

        # Читаем локальный файл
        try:
            with open(workflow_path_local, "r", encoding="utf-8") as f:
                workflow_content = f.read()
        except Exception as e:
            return f"Ошибка чтения workflow: {e}"

        # Создаём файл в GitHub
        try:
            self.repo_obj.create_file(
                workflow_path_repo,
                "Add GitHub Pages workflow",
                workflow_content,
            )
            info("Workflow created successfully.")
        except GithubException as e:
            error(f"Ошибка создания workflow: {e}")

    def update_actions_workflow(self):
        workflow_path_repo = ".github/workflows/pages.yml"
        workflow_path_local = os.path.join(
            os.path.dirname(__file__), "workflows", "pages.yml"
        )

        # Читаем локальный файл
        try:
            with open(workflow_path_local, "r", encoding="utf-8") as f:
                workflow_content = f.read()
        except Exception as e:
            return f"Ошибка чтения workflow: {e}"

        # Обновляем файл
        try:
            existing = self.repo_obj.get_contents(workflow_path_repo)
            self.repo_obj.update_file(
                workflow_path_repo,
                "Update GitHub Pages workflow",
                workflow_content,
                sha=existing.sha,
            )
            info("Workflow updated successfully.")
        except GithubException as e:
            error(f"Ошибка обновления workflow: {e}")

    def add_render_yaml(self):
        """
        Добавляет или обновляет backend/render.yaml для деплоя на Render.
        """
        path = "backend/render.yaml"
        yaml_content = """services:
        - type: web
          name: backend-api
          env: python
          plan: free
          rootDir: backend
          buildCommand: pip install -r requirements.txt
          startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
        """

        try:
            file_content = self.repo_obj.get_contents(path)
            self.repo_obj.update_file(
                path,
                "Update Render deploy config",
                yaml_content,
                sha=file_content.sha,
            )
            return f"{path} обновлён."
        except GithubException as e:
            if e.status == 404:
                self.repo_obj.create_file(
                    path,
                    "Add Render deploy config",
                    yaml_content,
                )
                return f"{path} создан."

            return f"Ошибка: {e}"
