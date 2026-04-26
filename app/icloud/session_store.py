import hashlib
import shutil
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


def delete_session_directory(
    apple_id: str,
    *,
    settings_service: SettingsService | None = None,
    sessions_root: Path | None = None,
) -> bool:
    session_dir = get_session_directory(
        apple_id,
        settings_service=settings_service,
        sessions_root=sessions_root,
    )
    if not session_dir.exists():
        return False

    if not session_dir.is_dir():
        msg = f"iCloud session path is not a directory: {session_dir}"
        raise NotADirectoryError(msg)

    shutil.rmtree(session_dir)
    return True
