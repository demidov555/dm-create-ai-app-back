import os
from typing import Any, List, Dict
import uuid
import time
from github import BadCredentialsException, Github, Auth, GithubException, InputGitTreeElement
from github.Repository import Repository
from github.AuthenticatedUser import AuthenticatedUser
from github.GitRef import GitRef
from dotenv import load_dotenv
from app.logger.console_logger import error, info, success


load_dotenv()

GH_PAT = os.getenv("GH_PAT")
if not GH_PAT:
    raise EnvironmentError("Установите GH_PAT в .env")

try:
    token = GH_PAT
    auth = Auth.Token(GH_PAT)
    gh = Github(auth=auth)
    user = gh.get_user()
    info(f"GitHub auth OK. Login:{user.login}")
except BadCredentialsException as e:
    raise RuntimeError("GH_PAT неверный или без прав") from e


class RepoManager:
    def __init__(self, project_id: uuid.UUID):
        self.project_id = project_id
        self.user = user
        self.gh = gh
        self.token = token
        self.repo_name: str | None = None
        self.repo_url: str | None = None
        self.repo_obj: Repository | None = None

        try:
            self.repo_obj = self.user.get_repo(f"project-{project_id}")
            self.repo_url = self.repo_obj.html_url
            self.repo_name = self.repo_obj.name
        except GithubException:
            self.repo_obj = None

    def _wait_for_main_branch(self, timeout=5.0) -> GitRef | None:
        if not self.repo_obj:
            error(f"[REPO_MANAGER] Репозиторий не найден или не инициализирован")
            return None

        start = time.time()
        while time.time() - start < timeout:
            try:
                return self.repo_obj.get_git_ref("heads/main")
            except GithubException:
                time.sleep(0.3)
        raise RuntimeError("Main branch did not appear after repo creation")

    def create_repo(self, name: str, private: bool = False) -> None:
        try:
            try:
                self.repo_obj = self.user.get_repo(name)
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url

            except GithubException:
                if not isinstance(self.user, AuthenticatedUser):
                    error(f"[REPO_MANAGER] Создание репы. Не правильный юзер")
                    return None

                self.repo_obj = self.user.create_repo(
                    name=name, private=private, auto_init=True
                )
                self.repo_name = self.repo_obj.name
                self.repo_url = self.repo_obj.html_url

                self._wait_for_main_branch()
                success(f"[REPO_MANAGER] Репозиторий создан: {self.repo_url}")

        except GithubException as e:
            error(f"[REPO_MANAGER] Ошибка создания репозитория {e}")

    def delete_repo(self) -> None:
        if not self.repo_obj:
            error(f"[REPO_MANAGER] Ошибка удаления. Такой репы не существует")
            return None

        try:
            repo = self.user.get_repo(self.repo_obj.name)
            repo.delete()

            self.repo_obj = None
            self.repo_name = None
            self.repo_url = None

            success("Репозиторий удалён.")

        except GithubException as e:
            error(f"[REPO_MANAGER]Ошибка GitHub API при удалении: {e}")

        except Exception as e:
            error(f"[REPO_MANAGER]Ошибка удаления: {e}")

    def push_commit(self, operations: List[Dict[str, Any]], message: str) -> str | None:
        if not self.repo_obj:
            error(f"[REPO_MANAGER] Репозиторий не инициализирован")
            return None

        try:
            ref = self._wait_for_main_branch()
            if not ref:
                error(f"[REPO_MANAGER] ref === None")
                return None

            latest_commit = self.repo_obj.get_git_commit(ref.object.sha)
            tree_elements: List[InputGitTreeElement] = []

            for op in operations:
                path = op["path"]

                if op["op"] in ("create", "update"):
                    blob = self.repo_obj.create_git_blob(
                        op["content"], "utf-8")
                    tree_elements.append(
                        InputGitTreeElement(
                            path=path,
                            mode="100644",
                            type="blob",
                            sha=blob.sha,
                        )
                    )

                elif op["op"] == "delete":
                    tree_elements.append(
                        InputGitTreeElement(
                            path=path,
                            mode="100644",
                            type="blob",
                            sha=None,
                        )
                    )

            # 2. Создаём новое дерево
            new_tree = self.repo_obj.create_git_tree(
                tree=tree_elements, base_tree=latest_commit.tree
            )

            # 3. Создаём коммит
            new_commit = self.repo_obj.create_git_commit(
                message=message,
                tree=new_tree,
                parents=[latest_commit],
            )

            # 4. Передвигаем HEAD
            ref.edit(new_commit.sha)

            success(f"Коммит создан: {new_commit.sha}")
            return new_commit.sha

        except GithubException as e:
            return f"Ошибка Github API: {e}"
        except Exception as e:
            return f"Ошибка batch commit: {e}"
