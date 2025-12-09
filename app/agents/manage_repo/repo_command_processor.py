import json
import re
from typing import List, Dict, Any


class RepoCommandProcessor:
    """
    Правильный парсер JSON-блоков с файлами.
    Главная особенность: НЕ ТРОГАЕТ content.
    """

    # Ищем ```json ... ``` (даже если не закрыт)
    JSON_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)\s*(```|$)", re.IGNORECASE)

    def extract_messages(self, task_result: Any) -> List[str]:
        """Достаёт сообщения агентов (кроме user/system)."""
        messages = []

        raw_msgs = None
        if hasattr(task_result, "messages"):
            raw_msgs = task_result.messages
        elif isinstance(task_result, dict) and "messages" in task_result:
            raw_msgs = task_result["messages"]
        else:
            return []

        for msg in raw_msgs:
            if hasattr(msg, "source") and hasattr(msg, "content"):
                source = msg.source
                content = msg.content
            elif isinstance(msg, dict):
                source = msg.get("source")
                content = msg.get("content")
            else:
                continue

            if source not in {"user", "system"} and isinstance(content, str):
                messages.append(content.strip())

        return messages

    def extract_json_blocks(self, text: str) -> List[str]:
        return [
            match.group(1).strip()
            for match in self.JSON_BLOCK_RE.finditer(text)
            if match.group(1) and match.group(1).strip()
        ]

    def parse_json_block(self, block: str) -> List[Dict[str, Any]]:
        """Парсим корректный JSON строго через json.loads."""

        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            # пробуем поправить только одиночные кавычки
            try:
                fixed = re.sub(r"(?<!\\)'", '"', block)
                data = json.loads(fixed)
            except:
                return []

        if not isinstance(data, dict):
            return []

        files = []

        for op in ["create", "update"]:
            for item in data.get(op, []):
                if isinstance(item, dict) and "path" in item and "content" in item:
                    files.append(
                        {
                            "path": item["path"],
                            "content": item["content"],  # ВАЖНО: сохраняем как есть!
                            "op": op,
                        }
                    )

        for item in data.get("delete", []):
            if isinstance(item, dict) and "path" in item:
                files.append({"path": item["path"], "op": "delete"})

        return files

    def parse_message(self, message: str) -> List[Dict[str, Any]]:
        """Поддержка как json-блоков, так и голого JSON."""
        files = []

        blocks = self.extract_json_blocks(message)
        if blocks:
            for block in blocks:
                files.extend(self.parse_json_block(block))
        else:
            files.extend(self.parse_json_block(message))

        return files

    def parse_task_result(self, task_result: Any) -> List[Dict[str, Any]]:
        files = []
        for msg_text in self.extract_messages(task_result):
            files.extend(self.parse_message(msg_text))
        return files

    # Удобные обёртки
    def get_files(self, task_result: Any) -> List[Dict[str, Any]]:
        return self.parse_task_result(task_result)

    def get_files_with_agent(self, task_result: Any) -> List[Dict[str, Any]]:
        """Файлы + имя агента"""
        result = []
        messages = []

        if hasattr(task_result, "messages"):
            messages = task_result.messages
        elif isinstance(task_result, dict):
            messages = task_result.get("messages", [])

        for msg in messages:
            if hasattr(msg, "source"):
                source = msg.source
                content = msg.content
            elif isinstance(msg, dict):
                source = msg.get("source")
                content = msg.get("content")
            else:
                continue

            if source in {"user", "system"}:
                continue
            if not isinstance(content, str):
                continue

            for file in self.parse_message(content):
                file["agent"] = source
                result.append(file)

        return result
