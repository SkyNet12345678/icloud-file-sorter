from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


def icloud_login(apple_id: str, password: str):
    try:
        api = PyiCloudService(apple_id, password)
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
