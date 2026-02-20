from __future__ import annotations
import asyncio
import shutil
from pathlib import Path

class CleanupService:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds

    async def schedule_delete_dir(self, dir_path: Path) -> None:
        await asyncio.sleep(self.ttl_seconds)
        shutil.rmtree(dir_path, ignore_errors=True)
