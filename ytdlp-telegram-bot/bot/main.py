import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_settings
from bot.handlers.start import router as start_router
from bot.handlers.download import router as download_router, worker_loop
from bot.handlers.links import router as links_router
from bot.services.queue_service import QueueService
from bot.services.storage_service import StorageService
from bot.services.cleanup_service import CleanupService

async def main():
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    # Dependências (injeção simples via dp["..."])
    dp["settings"] = settings
    dp["queue"] = QueueService(settings.global_concurrency, settings.per_user_concurrency)
    dp["storage"] = StorageService(settings.data_dir)
    dp["cleanup"] = CleanupService(settings.temp_ttl_seconds)

    # Routers
    dp.include_router(start_router)
    dp.include_router(links_router)
    dp.include_router(download_router)

    # Worker (fila)
    queue = dp["queue"]
    storage = dp["storage"]
    cleanup = dp["cleanup"]
    asyncio.create_task(worker_loop(bot, queue, storage, cleanup, settings))

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
