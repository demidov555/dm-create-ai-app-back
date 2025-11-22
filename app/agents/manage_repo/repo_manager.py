import os
from typing import List, Dict
import uuid
from github import Github, Auth, GithubException
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

GH_PAT = os.getenv("GH_PAT")
if not GH_PAT:
    raise EnvironmentError("Установите GH_PAT в .env")

auth = Auth.Token(GH_PAT)
g = Github(auth=auth)
USER = g.get_user()


class RepoManager:
    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.repo_name: str | None = None
        self.repo_url: str | None = None
        self.full_pushed = False
        self.repo_obj = None

    # ------------------- Создание -------------------
    def create_repo(self, name: str, private: bool = False) -> str:
        try:
            try:
                self.repo_obj = USER.get_repo(name)
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url
                return f"Репозиторий уже существует: {self.repo_url}"
            except GithubException:
                self.repo_obj = USER.create_repo(
                    name=name, private=private, auto_init=True
                )
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url
                return f"Репозиторий создан: {self.repo_url}"
        except GithubException as e:
            return f"Ошибка создания репозитория: {e}"

    # ------------------- Коммиты -------------------
    def _commit_files(self, files: List[Dict[str, str]], message: str, update=False):
        if not self.repo_obj:
            return "Репозиторий не инициализирован."

        results = []
        for f in files:
            path = f["path"]
            content = f["content"]
            try:
                file_content = self.repo_obj.get_contents(path)
                if update:
                    self.repo_obj.update_file(
                        path=path,
                        message=message,
                        content=content,
                        sha=file_content.sha,
                    )
                    results.append(f"Обновлён: {path}")
                else:
                    results.append(f"Пропущен (уже есть): {path}")
            except GithubException as e:
                if e.status == 404:
                    self.repo_obj.create_file(
                        path=path, message=message, content=content
                    )
                    results.append(f"Создан: {path}")
                else:
                    results.append(f"Ошибка: {path}: {e}")
        return "\n".join(results)

    def push_full(self, files: List[Dict[str, str]]) -> str:
        if self.full_pushed:
            return "Полный пуш уже выполнен. Используйте push_patch."
        out = self._commit_files(files, "Initial commit – full project")
        self.full_pushed = True
        return out

    def push_patch(self, files: List[Dict[str, str]]) -> str:
        if not self.full_pushed:
            return "Сначала выполните push_full."
        return self._commit_files(files, "Patch update", update=True)

    # ------------------- Pages -------------------
    def enable_pages(self) -> str:
        if not self.repo_obj:
            return "Репозиторий не инициализирован."
        try:
            self.repo_obj.enable_pages(source_branch="main", path="/")
            return f"GitHub Pages включены: https://{USER.login}.github.io/{self.repo_name}"
        except GithubException as e:
            if e.status == 409:
                return f"Pages уже активны: https://{USER.login}.github.io/{self.repo_name}"
            return f"Ошибка Pages: {e}"

    # ------------------- Render YAML -------------------
    def add_render_yaml(self) -> str:
        if not self.repo_obj:
            return "Репозиторий не инициализирован."

        path = "render.yaml"
        yaml_content = """services:
        - type: web
          name: ai-web
          env: python
          plan: free
          buildCommand: pip install -r requirements.txt
          startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
        """

        try:
            file_content = self.repo_obj.get_contents(path)
            self.repo_obj.update_file(
                path=path,
                message="Add Render deploy config",
                content=yaml_content,
                sha=file_content.sha,
            )
            return f"{path} обновлён."
        except GithubException as e:
            if e.status == 404:
                self.repo_obj.create_file(
                    path=path, message="Add Render deploy config", content=yaml_content
                )
                return f"{path} создан."
            return f"Ошибка: {e}"
