from __future__ import annotations
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.keyboards import links_keyboard
from bot.services.storage_service import StorageService

router = Router()

def _short_label(p: Path) -> str:
    return p.name[:60]

@router.message(Command("links"))
async def cmd_links(m: Message, storage: StorageService):
    user_id = m.from_user.id
    files = storage.list_link_records(user_id)[:20]
    if not files:
        await m.answer("Nenhum link salvo ainda.")
        return

    items = [{"label": _short_label(p), "file": str(p)} for p in files]
    await m.answer("Histórico (últimos 20):", reply_markup=links_keyboard(items))

@router.callback_query(F.data.startswith("links|send|"))
async def cb_send_link(cq: CallbackQuery, storage: StorageService):
    _, _, file_path = cq.data.split("|", 2)
    p = Path(file_path)
    if not p.exists():
        await cq.answer("Registro não encontrado.", show_alert=True)
        return

    data = storage.read_json(p)
    await cq.message.answer(
        f"Título: {data.get('title')}\nURL: {data.get('original_url')}\nSelecionado: {data.get('selected')}"
    )
    await cq.answer()
