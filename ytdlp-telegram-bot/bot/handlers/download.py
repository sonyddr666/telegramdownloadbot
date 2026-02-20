from __future__ import annotations
import asyncio
import time
import uuid

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.states import DownloadFlow
from bot.keyboards import formats_keyboard
from bot.services.queue_service import QueueService, DownloadJob
from bot.services.storage_service import StorageService
from bot.services.cleanup_service import CleanupService
from bot.services.telegram_uploader import send_file
from bot.services import ytdlp_service

router = Router()

# Memória (simples) para requests pendentes:
# request_id -> {"url": str, "info": dict, "options": list[FormatOption], "expires_at": float}
PENDING: dict[str, dict] = {}
CANCEL_FLAGS: dict[int, bool] = {}

def _cleanup_pending():
    now = time.time()
    dead = [rid for rid, v in PENDING.items() if v["expires_at"] < now]
    for rid in dead:
        PENDING.pop(rid, None)

@router.message(F.text)
async def on_text(m: Message, state: FSMContext, storage: StorageService, settings):
    _cleanup_pending()

    if settings.allowlist and m.from_user.id not in settings.allowlist:
        await m.answer("Acesso não autorizado.")
        return

    url = (m.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await m.answer("Envie uma URL válida começando com http:// ou https://")
        return

    await state.set_state(DownloadFlow.waiting_choice)
    msg = await m.answer("Analisando link...")

    try:
        info = await ytdlp_service.extract_info(url, settings.http_proxy, settings.ytdlp_cookies_file)
    except Exception as e:
        await msg.edit_text(f"Falha ao analisar: {type(e).__name__}: {e}")
        await state.set_state(DownloadFlow.waiting_link)
        return

    options = ytdlp_service.build_options(info, settings.max_upload_mb)
    if not options:
        await msg.edit_text("Não encontrei formatos disponíveis para esse link.")
        await state.set_state(DownloadFlow.waiting_link)
        return

    request_id = uuid.uuid4().hex
    PENDING[request_id] = {
        "url": url,
        "info": info,
        "options": options,
        "expires_at": time.time() + 600,  # 10 min
    }

    kb_items = [{"label": o.label, "format_id": o.format_id} for o in options]
    title = info.get("title") or "Sem título"
    await msg.edit_text(f"Título: {title}\nEscolha um formato:", reply_markup=formats_keyboard(request_id, kb_items))

@router.callback_query(F.data.startswith("dl|"))
async def cb_dl(cq: CallbackQuery, state: FSMContext, queue: QueueService, settings):
    _cleanup_pending()

    parts = cq.data.split("|", 2)
    if len(parts) != 3:
        await cq.answer("Callback inválido.", show_alert=True)
        return

    _, request_id, format_id = parts

    if request_id not in PENDING:
        await cq.answer("Essa seleção expirou. Envie o link de novo.", show_alert=True)
        await state.set_state(DownloadFlow.waiting_link)
        return

    if format_id == "__cancel__":
        await cq.message.edit_text("Cancelado.")
        await state.set_state(DownloadFlow.waiting_link)
        await cq.answer()
        return

    job = DownloadJob(
        user_id=cq.from_user.id,
        chat_id=cq.message.chat.id,
        message_id=cq.message.message_id,
        url=PENDING[request_id]["url"],
        format_id=format_id,
        request_id=request_id,
    )
    await queue.put(job)
    await cq.answer("Entrou na fila.")
    await cq.message.edit_text("Na fila. Vou começar assim que possível...")

async def worker_loop(bot, queue: QueueService, storage: StorageService, cleanup: CleanupService, settings):
    while True:
        job = await queue.get()
        try:
            async with queue.global_sem:
                async with queue.user_sem(job.user_id):
                    CANCEL_FLAGS[job.user_id] = False

                    pending = PENDING.get(job.request_id)
                    if not pending:
                        await bot.send_message(job.chat_id, "Pedido expirou. Envie o link novamente.")
                        continue

                    info = pending["info"]
                    temp_dir = storage.temp_dir(job.user_id)

                    last_edit = 0.0
                    progress_text = {"txt": "Iniciando download..."}

                    def cancel_check() -> bool:
                        return bool(CANCEL_FLAGS.get(job.user_id))

                    def progress_cb(d: dict):
                        nonlocal last_edit
                        now = time.time()
                        if now - last_edit < 1.2:
                            return
                        last_edit = now

                        if d.get("status") == "downloading":
                            p = d.get("_percent_str", "").strip()
                            s = d.get("_speed_str", "").strip()
                            eta = d.get("_eta_str", "").strip()
                            progress_text["txt"] = f"Baixando... {p} | {s} | ETA {eta}".strip()
                        elif d.get("status") == "finished":
                            progress_text["txt"] = "Finalizando (pós-processamento)..."

                    await bot.edit_message_text(
                        chat_id=job.chat_id, message_id=job.message_id,
                        text="Baixando... (0%)"
                    )

                    async def progress_pusher():
                        while True:
                            await asyncio.sleep(1.3)
                            try:
                                await bot.edit_message_text(
                                    chat_id=job.chat_id,
                                    message_id=job.message_id,
                                    text=progress_text["txt"],
                                )
                            except Exception:
                                pass
                            if progress_text["txt"].startswith("UPLOAD:"):
                                return

                    pusher_task = asyncio.create_task(progress_pusher())

                    try:
                        file_path = await ytdlp_service.download(
                            job.url,
                            job.format_id,
                            temp_dir,
                            settings.http_proxy,
                            settings.ytdlp_cookies_file,
                            cancel_check,
                            progress_cb,
                        )
                    except ytdlp_service.DownloadCancelled:
                        await bot.edit_message_text(job.chat_id, job.message_id, "Cancelado.")
                        continue
                    except Exception as e:
                        await bot.edit_message_text(job.chat_id, job.message_id, f"Falha no download: {type(e).__name__}: {e}")
                        continue

                    progress_text["txt"] = "UPLOAD: enviando para o Telegram..."
                    await asyncio.sleep(0.2)

                    caption = info.get("title") or None
                    file_id = await send_file(bot, job.chat_id, file_path, caption, settings.force_document)

                    selected = {"format_id": job.format_id, "telegram_file_id": file_id, "filename": file_path.name}
                    storage.save_link_record(job.user_id, info, job.url, selected)

                    await bot.edit_message_text(job.chat_id, job.message_id, "Enviado. Limpando temporários em alguns minutos...")

                    asyncio.create_task(cleanup.schedule_delete_dir(temp_dir))
                    pusher_task.cancel()

        finally:
            queue.task_done()

@router.message(F.text == "/cancel")
async def cmd_cancel(m: Message, storage: StorageService):
    CANCEL_FLAGS[m.from_user.id] = True
    # Limpa temp imediatamente (melhor esforço)
    try:
        temp = storage.temp_dir(m.from_user.id)
        # não deleta a pasta raiz aqui para evitar corrida com worker; apaga conteúdo
        for p in temp.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
    except Exception:
        pass
    await m.answer("Cancelamento solicitado.")
