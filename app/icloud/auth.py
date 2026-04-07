import tempfile

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


def icloud_login(apple_id: str, password: str):
    if not apple_id or not password:
        return {"success": False, "message": "Missing credentials"}
    try:
        session_dir = tempfile.mkdtemp()

        api = PyiCloudService(apple_id, password, cookie_directory=session_dir)

    except PyiCloudFailedLoginException:
        print("Login failed.")
        return {"success": False, "message": "Invalid Apple ID or password"}

    except Exception:
        return {"success": False, "message": "Login failed"}

    return {
        "success": True,
        "api": api,
        "requires_2fa": api.requires_2fa,
    }
