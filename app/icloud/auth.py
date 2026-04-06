import os
import tempfile

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


def icloud_login(apple_id: str, password: str):
    try:
        # Determine session_dir based on ENV
        if os.environ.get("ENV") == "dev":
            session_dir = tempfile.mkdtemp()  # new folder every run → forces 2FA
            print(f"[DEV] Using temporary session dir: {session_dir}")
        else:
            session_dir = None  # default persistent directory
            print("[PROD] Using default persistent session directory")

        api = PyiCloudService(apple_id, password, cookie_directory=session_dir)

    except PyiCloudFailedLoginException as e:
        print("Login failed:", str(e))
        return None

    if api.requires_2fa:
        print("2FA required")
        code = input("Enter 2FA code: ")

        if not api.validate_2fa_code(code):
            print("Invalid code")
            return None

        if not api.is_trusted_session:
            api.trust_session()

    return api
