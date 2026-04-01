from app.icloud.auth import icloud_login
from app.icloud.icloud_service import ICloudService


class AuthApi:
    def __init__(self):
            self.api = None
            self.temp_session = None
            self.icloud = None

    def login(self, apple_id, password):
            result = icloud_login(apple_id, password)

            if not result.get("success"):
                return result

            api = result["api"]

            # 🔥 THIS is where 2FA is handled
            if result.get("requires_2fa"):
                self.temp_session = api
                return {
                    "success": False,
                    "2fa_required": True,
                    "message": "Enter 2FA code",
                }

            self.api = api
            self.icloud = ICloudService(api)
            return {"success": True, "message": "Logged in"}

    def verify_2fa(self, code):
            if not self.temp_session:
                return {"success": False, "message": "No active 2FA session"}

            if not code:
                return {"success": False, "message": "Code required"}

            try:
                valid = self.temp_session.validate_2fa_code(code)

                if not valid:
                    return {"success": False, "message": "Invalid code"}

                if not self.temp_session.is_trusted_session:
                    self.temp_session.trust_session()

                self.api = self.temp_session
                self.temp_session = None
                self.icloud = ICloudService(self.api)

            except ValueError:
                return {"success": False, "message": "Verification failed"}

            return {"success": True, "message": "Logged in"}

    def get_albums(self):
        try:
            print("get_albums called")

            if not self.icloud:
                print("icloud is None")
                return []

            return self.icloud.get_albums()

        except Exception as e:
            print("ERROR in get_albums:", e)
            return []
