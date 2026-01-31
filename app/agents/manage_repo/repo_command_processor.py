import json
import re
from typing import List, Dict, Any, Optional


class RepoCommandProcessor:
    # Закрывающий ``` считаем только если он стоит отдельной строкой
    JSON_BLOCK_RE = re.compile(
        r"```json\s*\n([\s\S]*?)\n```(?:\s*\n|$)",
        re.IGNORECASE | re.MULTILINE,
    )

    def extract_messages(self, task_result: Any) -> List[str]:
        """Достаёт сообщения агентов (кроме user/system)."""
        messages: List[str] = []

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

    def _decode_escaped_string_once(self, s: str) -> Optional[str]:
        """
        Декодирует JSON-экранированную строку вида: \\n, \\", \\uXXXX.
        Возвращает строку или None если не удалось.
        """
        try:
            return json.loads(f'"{s}"')
        except Exception:
            return None

    def _maybe_unescape_content(self, content: Any) -> Any:
        """
        Приводит content к "сырому" тексту файла.
        Убирает двойное экранирование, которое часто возвращают LLM:
        - \\\" -> "
        - \\\\n -> \\n -> newline
        """
        if not isinstance(content, str):
            return content

        # Быстрый выход: нет признаков экранирования
        if '\\"' not in content and "\\n" not in content and "\\t" not in content and "\\u" not in content:
            return content

        # 1) decode один раз
        once = self._decode_escaped_string_once(content)
        if not isinstance(once, str):
            return content

        # Если после одного decode всё ещё остались escape-последовательности — это двойное экранирование
        if '\\"' in once or "\\n" in once or "\\t" in once or "\\u" in once:
            twice = self._decode_escaped_string_once(once)
            if isinstance(twice, str):
                return twice
            return once

        return once

    def parse_json_block(self, block: str) -> List[Dict[str, Any]]:
        """Парсим корректный JSON строго через json.loads."""
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            # пробуем поправить только одиночные кавычки
            try:
                fixed = re.sub(r"(?<!\\)'", '"', block)
                data = json.loads(fixed)
            except Exception:
                return []

        if not isinstance(data, dict):
            return []

        files: List[Dict[str, Any]] = []

        for op in ["create", "update"]:
            for item in data.get(op, []):
                if isinstance(item, dict) and "path" in item and "content" in item:
                    files.append(
                        {
                            "path": item["path"],
                            "content": self._maybe_unescape_content(item["content"]),
                            "op": op,
                        }
                    )

        for item in data.get("delete", []):
            if isinstance(item, dict) and "path" in item:
                files.append({"path": item["path"], "op": "delete"})

        return files

    def _extract_first_json_line(self, text: str) -> Optional[str]:
        """Единый формат: первая строка — JSON."""
        lines = text.strip().splitlines()
        if not lines:
            return None
        first = lines[0].strip()
        if first.startswith("{") and first.endswith("}"):
            return first
        return None

    def _extract_json_object_fallback(self, text: str) -> Optional[str]:
        """Fallback: достать JSON-объект по первой '{' и последней '}'."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start: end + 1]

    def parse_message(self, message: str) -> List[Dict[str, Any]]:
        """
        Поддержка:
        1) ```json ... ``` (старый формат)
        2) ЕДИНЫЙ формат: первая строка JSON, вторая строка ГОТОВО
        3) fallback: первый JSON-объект по скобкам
        """
        message = message.strip()
        files: List[Dict[str, Any]] = []

        blocks = self.extract_json_blocks(message)
        if blocks:
            for block in blocks:
                files.extend(self.parse_json_block(block))
            return files

        first_line_json = self._extract_first_json_line(message)
        if first_line_json is not None:
            files.extend(self.parse_json_block(first_line_json))
            return files

        fallback = self._extract_json_object_fallback(message)
        if fallback is not None:
            files.extend(self.parse_json_block(fallback))
            return files

        return files

    def parse_task_result(self, task_result: Any) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        for msg_text in self.extract_messages(task_result):
            files.extend(self.parse_message(msg_text))
        return files
