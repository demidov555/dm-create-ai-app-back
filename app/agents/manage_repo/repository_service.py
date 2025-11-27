from typing import List, Dict
import uuid
from github import GithubException

from .repo_manager import RepoManager
from app.agents.manage_repo.deployment_manager import DeploymentManager


class RepositoryService:
    """
    Второй уровень управления — бизнес-логика работы над проектом.
    """

    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.manager = RepoManager(project_id)
        self.deployment: DeploymentManager | None = None

    def ensure_repo(self, name: str) -> str:
        if not self.manager.repo_obj:
            repo = self.manager.create_repo(name)
            self._init_deployment()
            self.deployment.enable_pages()
            self.deployment.push_actions_workflow()
            return repo
        self._init_deployment()
        self.deployment.update_pages()
        return f"Repo already exists: {self.manager.repo_url}"

    def push(self, files: List[Dict[str, str]]) -> str:
        init_msg = ""
        if not self.manager.repo_obj:
            init_msg = self.ensure_repo("project-" + str(self.project_id))

        if not self._has_commits():
            result = self.manager.push_commit(files, "Initial commit – full project")
        else:
            result = self.manager.push_commit(files, "Patch update", update=True)

        return (init_msg + "\n" + result).strip()

    def info(self) -> Dict[str, str]:
        return {
            "project_id": str(self.project_id),
            "repo_name": self.manager.repo_name or "not created",
            "repo_url": self.manager.repo_url or "n/a",
            "commits_count": str(
                self.manager.repo_obj.get_commits().totalCount
                if self.manager.repo_obj
                else 0
            ),
        }

    def _init_deployment(self):
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
