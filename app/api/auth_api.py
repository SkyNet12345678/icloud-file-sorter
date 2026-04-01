from app.icloud.auth import icloud_login


class AuthApi:
    def __init__(self):
            self.api = None
            self.temp_session = None

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

            except ValueError:
                return {"success": False, "message": "Verification failed"}

            return {"success": True, "message": "Logged in"}
