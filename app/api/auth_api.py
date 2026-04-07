import logging

from app.icloud.auth import icloud_login
from app.icloud.icloud_service import ICloudService

logger = logging.getLogger("icloud-sorter")


class AuthApi:
    def __init__(self):
        self.api = None
        self.temp_session = None
        self.icloud = None

    def login(self, apple_id, password):
        result = icloud_login(apple_id, password)

        if not result.get("success"):
            logger.warning("Login failed for %s", apple_id)
            return result

        api = result["api"]

        if api.requires_2fa:
            self.temp_session = api
            return {
                "success": False,
                "2fa_required": True,
                "message": "Enter 2FA code",
            }

        self.api = api
        self.icloud = ICloudService(api)
        logger.info("Login successful for %s", apple_id)
        return {"success": True, "message": "Logged in"}

    def verify_2fa(self, code):
        if not self.temp_session:
            logger.warning("2FA verification attempted with no active session")
            return {"success": False, "message": "No active 2FA session"}

        try:
            logger.info("Verifying 2FA code")
            valid = self.temp_session.validate_2fa_code(code)

            if not valid:
                logger.warning("Invalid 2FA code entered")
                return {"success": False, "message": "Invalid 2FA code"}

            self.temp_session.trust_session()
            self.api = self.temp_session
            self.temp_session = None
            logger.info("2FA verification successful")
            return {"success": True, "message": "Logged in"}

        except Exception as e:
            logger.exception("2FA verification error")
            return {"success": False, "message": str(e)}
