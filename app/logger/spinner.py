import asyncio
import itertools
import sys


class Spinner:
    def __init__(self, message="Ожидание…", interval=0.2):
        self.message = message
        self.interval = interval
        self._task = None
        self._running = False

    async def _spin(self):
        for frame in itertools.cycle(["⏳", "⌛", "🔄"]):
            if not self._running:
                sys.stdout.write("\r")
                sys.stdout.flush()
                return

            sys.stdout.write(f"\r{frame} {self.message}")
            sys.stdout.flush()
            await asyncio.sleep(self.interval)

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._spin())

    async def stop(self):
        self._running = False
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
