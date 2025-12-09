import difflib
from typing import Sequence, List

from autogen_agentchat.base import TerminationCondition
from autogen_agentchat.messages import StopMessage, BaseChatMessage, BaseAgentEvent


class CircularLoopTermination(TerminationCondition):
    """
    TerminationCondition, который завершает чат при обнаружении циркулярки:
    - последние N сообщений слишком похожи
    - или одинаковые
    - или diversity сообщений слишком низкий

    НЕ ломает чат, просто возвращает StopMessage(reason="loop detected").
    """

    STOP_TOKEN = "<|LOOP_DETECTED|>"

    # параметры контроля
    lookback: int = 6  # сколько последних сообщений анализировать
    similarity_threshold: float = 0.97  # насколько похожими должны быть сообщения
    min_unique_messages: int = 2  # минимальное разнообразие

    def __init__(
        self,
        lookback: int = 6,
        similarity_threshold: float = 0.97,
        min_unique_messages: int = 2,
    ):
        self.lookback = lookback
        self.similarity_threshold = similarity_threshold
        self.min_unique_messages = min_unique_messages

        self._terminated = False
        self._buffer: List[str] = []

    @property
    def terminated(self) -> bool:
        return self._terminated

    async def __call__(self, messages: Sequence[BaseChatMessage | BaseAgentEvent]):
        if self._terminated:
            return None

        # берём последнее реальное сообщение
        if not messages:
            return None

        last = messages[-1]

        # пропускаем системные
        if getattr(last, "source", None) in {"system", "user"}:
            return None

        text = str(getattr(last, "content", "") or "").strip()
        if not text:
            return None

        # добавляем в буфер
        self._buffer.append(text)
        if len(self._buffer) > self.lookback:
            self._buffer.pop(0)

        # если буфера мало — рано анализировать
        if len(self._buffer) < self.lookback:
            return None

        # -----------------------------------------------------
        # 1) Проверка уникальности (diversity)
        # -----------------------------------------------------
        if len(set(self._buffer)) <= self.min_unique_messages:
            self._terminated = True
            return StopMessage(
                content=self.STOP_TOKEN, source="CircularLoopTermination"
            )

        # -----------------------------------------------------
        # 2) Проверка похожести всех сообщений друг на друга
        # -----------------------------------------------------
        all_similar = True
        for i in range(len(self._buffer)):
            for j in range(i + 1, len(self._buffer)):
                a, b = self._buffer[i], self._buffer[j]
                ratio = difflib.SequenceMatcher(None, a, b).ratio()
                if ratio < self.similarity_threshold:
                    all_similar = False
                    break
            if not all_similar:
                break

        if all_similar:
            self._terminated = True
            return StopMessage(
                content=self.STOP_TOKEN, source="CircularLoopTermination"
            )

        return None

    async def reset(self):
        self._terminated = False
        self._buffer.clear()
