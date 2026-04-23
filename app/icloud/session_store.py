import hashlib
from pathlib import Path

from app.settings import SettingsService


def normalize_apple_id(apple_id: str) -> str:
    return apple_id.strip().lower()


def apple_id_session_key(apple_id: str) -> str:
    normalized = normalize_apple_id(apple_id)
    if not normalized:
        msg = "Apple ID is required to resolve an iCloud session directory"
        raise ValueError(msg)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_session_directory(
    apple_id: str,
    *,
    settings_service: SettingsService | None = None,
    sessions_root: Path | None = None,
) -> Path:
    root = sessions_root
    if root is None:
        service = settings_service or SettingsService()
        root = service.get_icloud_sessions_dir()

    return Path(root) / apple_id_session_key(apple_id)
