import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _csv_ints(value: str) -> set[int]:
    if not value:
        return set()
    out = set()
    for part in value.split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out

@dataclass(frozen=True)
class Settings:
    bot_token: str
    data_dir: str
    allowlist: set[int]
    max_upload_mb: int
    temp_ttl_seconds: int
    global_concurrency: int
    per_user_concurrency: int
    force_document: bool
    http_proxy: str | None
    ytdlp_cookies_file: str | None

def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN não definido no .env")

    return Settings(
        bot_token=token,
        data_dir=os.getenv("DATA_DIR", "/data").strip(),
        allowlist=_csv_ints(os.getenv("ALLOWLIST", "").strip()),
        max_upload_mb=int(os.getenv("MAX_UPLOAD_MB", "49")),
        temp_ttl_seconds=int(os.getenv("TEMP_TTL_SECONDS", "300")),
        global_concurrency=int(os.getenv("GLOBAL_CONCURRENCY", "2")),
        per_user_concurrency=int(os.getenv("PER_USER_CONCURRENCY", "1")),
        force_document=os.getenv("FORCE_DOCUMENT", "0").strip() == "1",
        http_proxy=os.getenv("HTTP_PROXY", "").strip() or None,
        ytdlp_cookies_file=os.getenv("YTDLP_COOKIES_FILE", "").strip() or None,
    )
