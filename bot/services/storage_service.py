from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from bot.utils.text import slugify

class StorageService:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def user_dir(self, user_id: int) -> Path:
        return self.data_dir / "users" / str(user_id)

    def temp_dir(self, user_id: int) -> Path:
        d = self.user_dir(user_id) / "temp"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def links_dir(self, user_id: int) -> Path:
        d = self.user_dir(user_id) / "links"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_link_record(self, user_id: int, info: dict, original_url: str, selected: dict) -> Path:
        title = info.get("title") or "item"
        vid = info.get("id") or "noid"
        base = slugify(title)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        payload = {
            "timestamp": ts,
            "original_url": original_url,
            "id": vid,
            "title": title,
            "uploader": info.get("uploader") or info.get("channel") or None,
            "duration": info.get("duration"),
            "selected": selected,
        }

        path = self.links_dir(user_id) / f"{base}_{vid}_{ts}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def list_link_records(self, user_id: int) -> list[Path]:
        d = self.links_dir(user_id)
        files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
