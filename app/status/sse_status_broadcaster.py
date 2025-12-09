import asyncio
from typing import Dict, List
import uuid


class SSEStatusBrodcaster:
    def __init__(self):
        self.listeners: Dict[uuid.UUID, List[asyncio.Queue]] = {}

    async def subscribe(self, project_id: uuid.UUID) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.listeners.setdefault(project_id, []).append(queue)
        return queue

    async def send(self, project_id: uuid.UUID, payload: dict):
        queues = self.listeners.get(project_id)
        if not queues:
            return

        for q in queues:
            await q.put(payload)

    def unsubscribe(self, project_id: uuid.UUID, queue: asyncio.Queue):
        if project_id in self.listeners:
            self.listeners[project_id].remove(queue)
            if not self.listeners[project_id]:
                del self.listeners[project_id]


sse_status_broadcaster = SSEStatusBrodcaster()
