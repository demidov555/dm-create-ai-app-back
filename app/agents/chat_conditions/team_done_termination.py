import re
from typing import Sequence, Optional, Set

from autogen_agentchat.base import TerminationCondition
from autogen_agentchat.messages import StopMessage, BaseChatMessage, BaseAgentEvent


class TeamDoneTermination(TerminationCondition):
    """
    Завершает чат, когда ВСЕ ожидаемые роли вывели строку "ГОТОВО: Роль".
    Сам возвращает StopMessage — агенты НЕ должны писать <|TEAM_COMPLETE|>!
    """

    # Токен завершения — можно менять, но должен совпадать с тем, что ты используешь в stop_reason
    DONE_TOKEN = "<|TEAM_COMPLETE|>"

    # Регулярка для захвата роли после "ГОТОВО:"
    READY_RE = re.compile(r"ГОТОВО\s*:\s*([^\n\r]+)", re.IGNORECASE)

    # Pydantic v2 поля
    ready_roles: Set[str] = set()
    expected_roles: Optional[Set[str]] = None
    _terminated: bool = False

    def __init__(self, expected_roles: Optional[list[str]] = None):
        """
        Параметры:
            expected_roles — список строк, например: ["Frontend", "Backend", "DevOps"]
                            Если None — роли определятся автоматически по первым "ГОТОВО:"
        """
        if expected_roles is not None:
            self.expected_roles = {
                role.strip() for role in expected_roles if role.strip()
            }

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(
        self, messages: Sequence[BaseChatMessage | BaseAgentEvent]
    ) -> Optional[StopMessage]:

        if self._terminated:
            return None

        # Автоопределение ролей, если не заданы
        if self.expected_roles is None:
            self.expected_roles = set()

        # Обрабатываем только сообщения от агентов (игнорируем system, user и т.п.)
        for msg in messages:
            if not hasattr(msg, "source"):
                continue
            if getattr(msg, "source", None) in {"system", "user"}:
                continue
            if not hasattr(msg, "content"):
                continue

            text = str(msg.content or "").strip()

            # Ищем "ГОТОВО: Роль"
            if match := self.READY_RE.search(text):
                role = match.group(1).strip()
                self.ready_roles.add(role)

                # Если роли ещё не были заданы — добавляем в ожидаемые
                if not self.expected_roles:
                    self.expected_roles.add(role)

            # ← ВАЖНО: агенты НЕ должны писать DONE_TOKEN!
            # Мы сами решаем, когда завершать

        # Проверяем: все ли роли сказали ГОТОВО?
        if self.expected_roles and self.ready_roles >= self.expected_roles:
            if not self._terminated:
                self._terminated = True
                return StopMessage(
                    content=self.DONE_TOKEN, source="TeamDoneTermination"
                )

        return None

    async def reset(self) -> None:
        """Сброс состояния для повторного использования"""
        self._terminated = False
        self.ready_roles.clear()
        # expected_roles НЕ сбрасываем — они задаются при создании
