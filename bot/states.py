from aiogram.fsm.state import StatesGroup, State

class DownloadFlow(StatesGroup):
    waiting_link = State()
    waiting_choice = State()
