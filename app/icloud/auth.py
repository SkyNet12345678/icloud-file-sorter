import os
import tempfile
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


def icloud_login(apple_id: str, password: str):
    try:
        if os.environ.get("ENV") == "dev":
            session_dir = tempfile.mkdtemp()
            print(f"[DEV] Using temporary session dir: {session_dir}")
        else:
            session_dir = None

        api = PyiCloudService(apple_id, password, cookie_directory=session_dir)

    except PyiCloudFailedLoginException as e:
        print("Login failed:", str(e))
        return None

    return api
