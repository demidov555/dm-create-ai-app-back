import json
import re
from typing import List, Dict, Any


class RepoCommandProcessor:
    """
    Парсер файлов из ответов команды AutoGen.
    Работает с:
    • ```json ... ```
    • незакрытыми блоками
    • неэкранированными кавычками внутри content
    • голым JSON
    • tuple от re.findall
    • "null" как строка
    • настоящим TaskResult и dict-муляжом
    """

    # Ищем ```json ... ``` (даже если не закрыт)
    JSON_BLOCK_RE = re.compile(r"```json\s*([\s\S]*?)\s*(```|$)", re.IGNORECASE)

    # Ручной парсинг для экстремальных случаев
    FILE_OBJECT_RE = re.compile(
        r'\{\s*"path"\s*:\s*"([^"]+)"\s*,\s*"content"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*\}',
        re.DOTALL,
    )

    def extract_messages(self, task_result: Any) -> List[str]:
        """Универсально извлекает текстовые сообщения от агентов"""
        messages = []

        # Поддержка TaskResult и dict
        if hasattr(task_result, "messages"):
            raw_msgs = task_result.messages
        elif isinstance(task_result, dict) and "messages" in task_result:
            raw_msgs = task_result["messages"]
        else:
            return []

        for msg in raw_msgs:
            # Объект TextMessage
            if hasattr(msg, "source") and hasattr(msg, "content"):
                source = getattr(msg, "source", "")
                content = getattr(msg, "content", "")
            # dict из муляжа
            elif isinstance(msg, dict):
                source = msg.get("source", "")
                content = msg.get("content", "")
            else:
                continue

            if (
                source not in {"user", "system"}
                and content
                and isinstance(content, str)
            ):
                messages.append(content.strip())

        return messages

    def extract_json_blocks(self, text: str) -> List[str]:
        """Надёжно извлекает содержимое ```json ... ``` — без tuple-ошибки"""
        return [
            match.group(1).strip()
            for match in self.JSON_BLOCK_RE.finditer(text)
            if match.group(1) and match.group(1).strip()
        ]

    def manual_parse_files(self, text: str) -> List[Dict[str, str]]:
        """Ручной парсинг — спасает от неэкранированных кавычек"""
        files = []
        for match in self.FILE_OBJECT_RE.finditer(text):
            path = match.group(1)
            content = match.group(2)
            # Восстанавливаем экранирование
            content = (
                content.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
            files.append({"path": path, "content": content})
        return files

    def safe_json_loads(self, text: str) -> Any:
        """Пытается распарсить JSON, даже если сломан"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Попробуем починить одинарные кавычки
            try:
                fixed = re.sub(r"(?<!\\)'", '"', text)
                return json.loads(fixed)
            except:
                return None

    def parse_json_block(self, block: str) -> List[Dict[str, str]]:
        """Парсит один JSON-блок — с fallback на ручной парсинг"""
        data = self.safe_json_loads(block)
        if data is not None:
            files = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "path" in item and "content" in item:
                        files.append({"path": item["path"], "content": item["content"]})
            elif isinstance(data, dict) and "path" in data and "content" in data:
                files.append({"path": data["path"], "content": data["content"]})
            return files

        # Если json.loads упал — включаем тяжёлую артиллерию
        return self.manual_parse_files(block)

    def parse_message(self, message: str) -> List[Dict[str, str]]:
        """Парсит одно сообщение от агента"""
        all_files = []

        # 1. Сначала ищем ```json блоки
        for block in self.extract_json_blocks(message):
            all_files.extend(self.parse_json_block(block))

        # 2. Если ничего не нашли — пробуем весь текст
        if not all_files:
            all_files.extend(self.parse_json_block(message))

        # 3. Экстремальный fallback — ручной парсинг всего сообщения
        if not all_files:
            all_files.extend(self.manual_parse_files(message))

        return all_files

    def parse_task_result(self, task_result: Any) -> List[Dict[str, str]]:
        """Главная функция — возвращает плоский список всех файлов"""
        files = []
        for msg_text in self.extract_messages(task_result):
            files.extend(self.parse_message(msg_text))
        return files

    # Удобные обёртки
    def get_files(self, task_result: Any) -> List[Dict[str, str]]:
        """Возвращает только файлы"""
        return self.parse_task_result(task_result)

    def get_files_with_agent(self, task_result: Any) -> List[Dict[str, str]]:
        """Возвращает файлы с указанием, кто их создал"""
        result = []
        messages = []

        if hasattr(task_result, "messages"):
            messages = task_result.messages
        elif isinstance(task_result, dict) and "messages" in task_result:
            messages = task_result["messages"]

        for msg in messages:
            source = (
                getattr(msg, "source", None) or msg.get("source", "unknown")
                if isinstance(msg, dict)
                else "unknown"
            )
            if source in {"user", "system"}:
                continue
            content = (
                getattr(msg, "content", "") or msg.get("content", "")
                if isinstance(msg, dict)
                else ""
            )
            if not content:
                continue

            for file in self.parse_message(content):
                file["agent"] = source
                result.append(file)

        return result
