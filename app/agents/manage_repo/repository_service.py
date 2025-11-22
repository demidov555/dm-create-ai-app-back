from typing import List, Dict
import uuid

from app.agents.manage_repo.deployer_service import DeployerService
from .repo_manager import RepoManager


class RepositoryService:
    """
    Второй уровень управления — бизнес-логика работы над проектом.
    """

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.manager = RepoManager(project_id)
        self.deployer = DeployerService(self.manager)

    # --------------------------------------------------------------
    # Базовые операции
    # --------------------------------------------------------------
    def ensure_repo(self, name: str) -> str:
        if not self.manager.repo_obj:
            return self.manager.create_repo(name)
        return f"Repo already exists: {self.manager.repo_url}"

    def push_full(self, files: List[Dict[str, str]]) -> str:
        """Первоначальная структура проекта"""
        init_msg = ""
        if not self.manager.repo_obj:
            init_msg = self.ensure_repo("project-" + str(self.project_id))

        result = self.manager.push_full(files)
        return (init_msg + "\n" + result).strip()

    def push_patch(self, files: List[Dict[str, str]]) -> str:
        """Обновление файлов"""
        if not self.manager.repo_obj:
            return "Repo not initialized"
        return self.manager.push_patch(files)

    def enable_pages(self) -> str:
        if not self.manager.repo_obj:
            return "Repo not initialized"
        return self.manager.enable_pages()

    def add_render(self) -> str:
        if not self.manager.repo_obj:
            return "Repo not initialized"
        return self.manager.add_render_yaml()

    # --------------------------------------------------------------
    # Сложные сценарии
    # --------------------------------------------------------------
    # def full_init_and_deploy(self, repo_name: str, files: List[Dict[str, str]]) -> str:
    #     messages = []
    #     messages.append(self.ensure_repo(repo_name))
    #     messages.append(self.manager.push_full(files))
    #     messages.append(self.manager.enable_pages())
    #     return "\n".join(messages)
    
    def enable_pages(self):
        return self.deployer.deploy_pages()

    def enable_render(self):
        return self.deployer.deploy_render()

    # --------------------------------------------------------------
    # Информация
    # --------------------------------------------------------------
    def info(self) -> Dict[str, str]:
        return {
            "project_id": str(self.project_id),
            "repo_name": self.manager.repo_name or "not created",
            "repo_url": self.manager.repo_url or "n/a",
            "full_pushed": str(self.manager.full_pushed),
        }
