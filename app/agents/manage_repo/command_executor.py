from typing import List, Dict, Any
from .repository_service import RepositoryService


class CommandExecutor:
    """
    Принятие структурированных команд от RepoCommandProcessor, вызовы RepositoryService.
    """

    def __init__(self, service: RepositoryService):
        self.service = service

    def execute(self, commands: List[Dict[str, Any]]) -> List[str]:
        results = []

        for cmd in commands:
            t = cmd["type"]

            if t == "create_repo":
                results.append(self.service.ensure_repo(cmd["name"]))

            elif t == "push_full":
                results.append(self.service.push_full(cmd["files"]))

            elif t == "push_patch":
                results.append(self.service.push_patch(cmd["files"]))

            elif t == "json_error":
                results.append(f"JSON error: {cmd['error']}")

            else:
                results.append(f"Неизвестная команда: {cmd}")

        return results
