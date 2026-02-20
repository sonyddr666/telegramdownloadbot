from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.states import DownloadFlow

router = Router()

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.set_state(DownloadFlow.waiting_link)
    await m.answer(
        "Envie um link (URL) para eu analisar e mostrar as opções.\n"
        "Comandos: /links, /cancel"
    )
