from __future__ import annotations
import asyncio
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class DownloadJob:
    user_id: int
    chat_id: int
    message_id: int
    url: str
    format_id: str
    request_id: str

class QueueService:
    def __init__(self, global_concurrency: int, per_user_concurrency: int):
        self.queue: asyncio.Queue[DownloadJob] = asyncio.Queue()
        self.global_sem = asyncio.Semaphore(global_concurrency)
        self.user_sems = defaultdict(lambda: asyncio.Semaphore(per_user_concurrency))

    async def put(self, job: DownloadJob) -> None:
        await self.queue.put(job)

    async def get(self) -> DownloadJob:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()

    def user_sem(self, user_id: int) -> asyncio.Semaphore:
        return self.user_sems[user_id]
