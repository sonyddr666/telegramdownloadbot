from __future__ import annotations
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yt_dlp

class DownloadCancelled(Exception):
    pass

@dataclass(frozen=True)
class FormatOption:
    format_id: str
    label: str
    filesize_mb: float | None

def _filesize_mb(fmt: dict) -> float | None:
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if not size:
        return None
    return float(size) / (1024 * 1024)

def build_options(info: dict, max_upload_mb: int) -> list[FormatOption]:
    out = []
    for f in info.get("formats", []):
        fid = f.get("format_id")
        if not fid:
            continue

        ext = f.get("ext") or "?"
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        height = f.get("height")
        abr = f.get("abr")

        mb = _filesize_mb(f)
        size_txt = f"{mb:.1f}MB" if mb is not None else "?"
        ok = (mb is not None and mb <= max_upload_mb)
        flag = "OK" if ok else "GRANDE"

        if vcodec and vcodec != "none":
            qual = f"{height}p" if height else "video"
            label = f"🎥 {qual} {ext} — {size_txt} [{flag}]"
        elif acodec and acodec != "none":
            qual = f"{int(abr)}kbps" if abr else "audio"
            label = f"🎵 {qual} {ext} — {size_txt} [{flag}]"
        else:
            label = f"📦 {ext} — {size_txt} [{flag}]"

        out.append(FormatOption(format_id=fid, label=label, filesize_mb=mb))

    def _score(o: FormatOption) -> tuple:
        # Prefer menores (cabem), depois maiores
        fits = 0 if (o.filesize_mb is not None and o.filesize_mb <= max_upload_mb) else 1
        size = o.filesize_mb if o.filesize_mb is not None else 10**9
        return (fits, size)

    out.sort(key=_score)
    return out[:30]

def _extract_info_sync(url: str, proxy: str | None, cookies_file: str | None) -> dict:
    opts = {"quiet": True, "noprogress": True}
    if proxy:
        opts["proxy"] = proxy
    if cookies_file:
        opts["cookiefile"] = cookies_file
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)

async def extract_info(url: str, proxy: str | None, cookies_file: str | None) -> dict:
    return await asyncio.to_thread(_extract_info_sync, url, proxy, cookies_file)

def _download_sync(
    url: str,
    format_id: str,
    out_dir: Path,
    proxy: str | None,
    cookies_file: str | None,
    cancel_check: Callable[[], bool],
    progress_cb: Callable[[dict], None],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    def hook(d: dict):
        if cancel_check():
            raise DownloadCancelled("cancelled")
        progress_cb(d)

    opts = {
        "quiet": True,
        "format": format_id,
        "outtmpl": str(out_dir / "%(title).80s_%(id)s.%(ext)s"),
        "progress_hooks": [hook],
        "noplaylist": True,
        "retries": 3,
    }
    if proxy:
        opts["proxy"] = proxy
    if cookies_file:
        opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    # Pega o arquivo mais recente no diretório
    files = sorted(out_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise RuntimeError("Download finalizou, mas nenhum arquivo foi encontrado.")
    return files[0]

async def download(
    url: str,
    format_id: str,
    out_dir: Path,
    proxy: str | None,
    cookies_file: str | None,
    cancel_check: Callable[[], bool],
    progress_cb: Callable[[dict], None],
) -> Path:
    return await asyncio.to_thread(
        _download_sync, url, format_id, out_dir, proxy, cookies_file, cancel_check, progress_cb
    )
