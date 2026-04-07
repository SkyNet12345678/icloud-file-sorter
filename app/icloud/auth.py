import tempfile

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


def icloud_login(apple_id: str, password: str):
    if not apple_id or not password:
        return {"success": False, "message": "Missing credentials"}
    try:
        session_dir = tempfile.mkdtemp()

        api = PyiCloudService(apple_id, password, cookie_directory=session_dir)

    except PyiCloudFailedLoginException as e:
        print("Login failed:", str(e))
        return None

    return api
