from typing import List, Dict
import uuid
from github import GithubException

from app.logger.console_logger import error

from .repo_manager import RepoManager
from app.agents.manage_repo.deployment_manager import DeploymentManager


class RepositoryService:
    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.manager = RepoManager(project_id)
        self.deployment: DeploymentManager | None = None

    def create_repo(self, name: str) -> None:
        if not self.manager.repo_obj:
            self.manager.create_repo(name)
            self._init_deployment()

            if not self.deployment:
                error(f"[RepositoryService] deployment не инициализирован")
                return

            self.deployment.enable_pages()
            self.deployment.push_actions_workflow()

        self._init_deployment()

        if not self.deployment:
            error(f"[RepositoryService] deployment не инициализирован")
            return

        self.deployment.update_pages()

    def delete_repo(self) -> None:
        self.manager.delete_repo()
        self.deployment = None

    def push(self, files: List[Dict[str, str]]) -> str | None:
        commit_msg = (
            "Initial commit – full project"
            if not self._has_commits()
            else "Patch update"
        )

        result = self.manager.push_commit(
            operations=files,
            message=commit_msg,
        )

        if not result:
            return None

        return result

    def info(self) -> Dict[str, str]:
        login = getattr(self.manager.user, "login", None)
        repo_name = self.manager.repo_name or "not-created"
        pages_link = f"https://{login}.github.io/{repo_name}/" if login else "n/a"
        commits_count = str(
            self.manager.repo_obj.get_commits().totalCount
            if self.manager.repo_obj
            else 0
        )

        return {
            "project_id": str(self.project_id),
            "repo_name": repo_name,
            "repo_url": self.manager.repo_url or "n/a",
            "pages_link": pages_link,
            "commits_count": commits_count,
        }

    def _init_deployment(self) -> None:
        self.deployment = DeploymentManager(
            repo_obj=self.manager.repo_obj, gh=self.manager.gh, user=self.manager.user
        )

    def _has_commits(self) -> bool:
        if not self.manager.repo_obj:
            return False

        try:
            commits = self.manager.repo_obj.get_commits()
            return commits.totalCount > 0
        except GithubException:
            return False
