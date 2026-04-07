import logging
import tempfile

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException

logger = logging.getLogger("icloud-sorter")


def icloud_login(apple_id: str, password: str):
    if not apple_id or not password:
        logger.warning("Login attempted with missing credentials")
        return {"success": False, "message": "Missing credentials"}

    try:
        session_dir = tempfile.mkdtemp()
        logger.info("Attempting iCloud login for %s", apple_id)
        api = PyiCloudService(apple_id, password, cookie_directory=session_dir)

    except PyiCloudFailedLoginException:
        logger.warning("Invalid credentials for %s", apple_id)
        return {"success": False, "message": "Invalid Apple ID or password"}

    except Exception as e:
        logger.exception("Unexpected login error: %s", str(e))
        return {"success": False, "message": "Login failed"}

    logger.info("iCloud login successful for %s, 2FA required: %s", apple_id, api.requires_2fa)
    return {
        "success": True,
        "api": api,
        "requires_2fa": api.requires_2fa,
    }
