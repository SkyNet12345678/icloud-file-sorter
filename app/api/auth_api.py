from app.icloud.auth import icloud_login

class AuthApi:
    def __init__(self):
        self.api = None

    def login(self, apple_id, password):
        print(f"Login called: {apple_id=}")  # debug

        # Attempt login
        self.api = icloud_login(apple_id, password)

        # Check if 2FA is required
        if hasattr(self.api, "requires_2fa") and self.api.requires_2fa:
            self.temp_session = self.api
            return {"success": False, "2fa_required": True, "message": "2FA code required"}

        if not self.api:
            return {"success": False, "message": "Invalid credentials"}

        return {"success": True}

    def verify_2fa(self, code):
        if not self.temp_session:
            return {"success": False, "message": "No 2FA session active"}

        try:
            self.temp_session.validate_2fa_code(code)

            if self.temp_session.is_trusted_session:
                self.api = self.temp_session
                self.temp_session = None
                return {"success": True}
            else:
                return {"success": False, "message": "Invalid 2FA code"}
        except Exception as e:
            return {"success": False, "message": str(e)}