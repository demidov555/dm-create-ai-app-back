import os
from typing import List, Dict
import uuid
from github import Github, Auth, GithubException
from dotenv import load_dotenv

load_dotenv()

GH_PAT = os.getenv("GH_PAT")
if not GH_PAT:
    raise EnvironmentError("Установите GH_PAT в .env")

auth = Auth.Token(GH_PAT)
gh = Github(auth=auth)
user = gh.get_user()


class RepoManager:
    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.user = user
        self.gh = gh
        self.repo_name: str | None = None
        self.repo_url: str | None = None
        self.repo_obj = None

    def create_repo(self, name: str, private: bool = False) -> str:
        """
        Создаёт репозиторий или возвращает ссылку, если он уже существует.
        """
        try:
            try:
                self.repo_obj = self.user.get_repo(name)
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url
                return f"Репозиторий уже существует: {self.repo_url}"
            except GithubException:
                self.repo_obj = self.user.create_repo(
                    name=name, private=private, auto_init=True
                )
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url
                return f"Репозиторий создан: {self.repo_url}"
        except GithubException as e:
            return f"Ошибка создания репозитория: {e}"

    def push_commit(
        self, files: List[Dict[str, str]], message: str, update: bool = False
    ) -> str:
        """
        Коммитит список файлов:
        - если update=True → обновляет существующие файлы
        - если update=False → создаёт новые, пропускает существующие
        """
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
