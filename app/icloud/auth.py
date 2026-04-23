import logging
from pathlib import Path

from app.icloud.session_store import get_session_directory
from app.settings import SettingsService

logger = logging.getLogger("icloud-sorter")

try:
    from pyicloud import PyiCloudService
    from pyicloud.exceptions import PyiCloudFailedLoginException
except ModuleNotFoundError:
    PyiCloudService = None

    class PyiCloudFailedLoginException(Exception):
        pass


def icloud_login(
    apple_id: str,
    password: str,
    *,
    cookie_directory: str | Path | None = None,
    settings_service: SettingsService | None = None,
):
    if not apple_id or not password:
        logger.warning("Login attempted with missing credentials")
        return {"success": False, "message": "Missing credentials"}

    if PyiCloudService is None:
        logger.error("pyicloud is not installed")
        return {"success": False, "message": "iCloud support is unavailable"}

    try:
        if cookie_directory:
            session_dir = Path(cookie_directory)
        else:
            session_dir = get_session_directory(
                apple_id,
                settings_service=settings_service,
            )
        session_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Attempting iCloud login for %s", apple_id)
        api = PyiCloudService(apple_id, password, cookie_directory=str(session_dir))

    except PyiCloudFailedLoginException:
        logger.warning("Invalid credentials for %s", apple_id)
        return {"success": False, "message": "Invalid Apple ID or password"}

    except Exception as e:
        logger.exception("Unexpected login error: %s", str(e))
        return {"success": False, "message": "Login failed"}

    logger.info(
        "iCloud login successful for %s, 2FA required: %s",
        apple_id,
        api.requires_2fa,
    )
    return {
        "success": True,
        "api": api,
        "requires_2fa": api.requires_2fa,
    }
