# repo_command_processor.py

import re
import json
import uuid
from typing import List, Dict, Any, Optional
from autogen_agentchat.messages import TextMessage


class RepoCommandProcessor:
    """
    Парсер и нормализатор команд от ИИ.
    Автоматически добавляет CREATE_REPO, если его не прислал агент.
    """

    PATTERNS = {
        "push": r"(PUSH_FULL|PUSH_PATCH):\s*```json\s*([\s\S]*?)\s*```",
        "deploy_pages": r"DEPLOY_PAGES",
        "deploy_render": r"DEPLOY_RENDER",
    }

    def extract_messages(self, task_result) -> List[str]:
        msgs = []
        for msg in task_result.messages:
            if isinstance(msg, TextMessage):
                if any(k in msg.content for k in ["PUSH_", "DEPLOY_"]):
                    msgs.append(msg.content)
        return msgs

    def parse(self, text: str) -> List[Dict[str, Any]]:
        out = []

        # PUSH_FULL / PUSH_PATCH
        if m := re.search(self.PATTERNS["push"], text, re.IGNORECASE):
            cmd_type, json_raw = m.groups()

            try:
                files = json.loads(json_raw)
                if not isinstance(files, list):
                    files = [files]
            except json.JSONDecodeError as e:
                out.append({"type": "json_error", "error": str(e)})
            else:
                out.append({"type": cmd_type.lower(), "files": files})

        # DEPLOY_* команды
        if re.search(self.PATTERNS["deploy_pages"], text):
            out.append({"type": "deploy_pages"})

        if re.search(self.PATTERNS["deploy_render"], text):
            out.append({"type": "deploy_render"})

        return out

    def parse_task_result(
        self, task_result, project_id: Optional[uuid.UUID]
    ) -> List[Dict[str, Any]]:

        raw_cmds = []
        for msg in self.extract_messages(task_result):
            raw_cmds.extend(self.parse(msg))

        normalized = self._normalize(raw_cmds)
        normalized = self._ensure_repo(normalized, project_id)

        return normalized

    # --------------------------
    # НОРМАЛИЗАЦИЯ
    # --------------------------
    def _normalize(self, cmds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        final = []

        aggregated_full = []
        seen = {
            "deploy_pages": False,
            "deploy_render": False,
        }

        for cmd in cmds:
            t = cmd["type"]

            if t == "json_error":
                final.append(cmd)
                continue

            # PUSH_FULL → объединяем все файлы
            if t == "push_full":
                aggregated_full.extend(cmd["files"])
                continue

            # PUSH_PATCH → добавляем как есть
            if t == "push_patch":
                final.append(cmd)
                continue

            # DEPLOY_ — оставляем только один
            if t in seen:
                if not seen[t]:
                    final.append(cmd)
                    seen[t] = True

        # вставляем единственный push_full
        if aggregated_full:
            final.insert(0, {"type": "push_full", "files": aggregated_full})

        return final

    # --------------------------
    # ОБЕСПЕЧЕНИЕ CREATE_REPO
    # --------------------------
    def _ensure_repo(self, cmds: List[Dict[str, Any]], project_id: Optional[uuid.UUID]):
        repo_name = f"project-{project_id}" if project_id else "generated-repo"

        create_cmd = {"type": "create_repo", "name": repo_name}

        return [create_cmd] + cmds
