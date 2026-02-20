from __future__ import annotations
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

VIDEO_EXT = {".mp4", ".mkv", ".webm", ".mov"}
AUDIO_EXT = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav"}

async def send_file(bot: Bot, chat_id: int, file_path: Path, caption: str | None, force_document: bool) -> str:
    ext = file_path.suffix.lower()
    f = FSInputFile(str(file_path))

    if force_document:
        msg = await bot.send_document(chat_id=chat_id, document=f, caption=caption)
        return msg.document.file_id

    if ext in VIDEO_EXT:
        msg = await bot.send_video(chat_id=chat_id, video=f, caption=caption, supports_streaming=True)
        return msg.video.file_id

    if ext in AUDIO_EXT:
        msg = await bot.send_audio(chat_id=chat_id, audio=f, caption=caption)
        return msg.audio.file_id

    msg = await bot.send_document(chat_id=chat_id, document=f, caption=caption)
    return msg.document.file_id
