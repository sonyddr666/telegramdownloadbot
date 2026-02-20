from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def formats_keyboard(request_id: str, items: list[dict]) -> InlineKeyboardMarkup:
    # items: [{label, format_id}]
    rows = []
    for it in items[:30]:
        rows.append([InlineKeyboardButton(text=it["label"], callback_data=f"dl|{request_id}|{it['format_id']}")])
    rows.append([InlineKeyboardButton(text="Cancelar", callback_data=f"dl|{request_id}|__cancel__")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def links_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    # items: [{label, file_path}]
    rows = []
    for it in items[:30]:
        rows.append([InlineKeyboardButton(text=it["label"], callback_data=f"links|send|{it['file']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
