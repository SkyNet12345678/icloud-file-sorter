import logging

from app.icloud.auth import icloud_login
from app.icloud.icloud_service import ICloudService
from app.icloud.session_store import delete_session_directory
from app.settings import SettingsService

logger = logging.getLogger("icloud-sorter")

TRUSTED_SESSION_RESUME_PLACEHOLDER = "__trusted_session_resume__"


class AuthApi:
    def __init__(self, settings_service=None):
        self.api = None
        self.temp_session = None
        self.temp_apple_id = None
        self.icloud = None
        self.settings_service = settings_service or SettingsService()

    def _clear_authenticated_state(self):
        self.api = None
        self.temp_session = None
        self.temp_apple_id = None
        self.icloud = None

    def get_auth_state(self):
        remembered_apple_id = self.settings_service.get_remembered_apple_id()
        return {
            "success": True,
            "has_remembered_apple_id": remembered_apple_id is not None,
            "remembered_apple_id": remembered_apple_id,
        }

    def login(self, apple_id, password):
        result = icloud_login(
            apple_id,
            password,
            settings_service=self.settings_service,
        )

        if not result.get("success"):
            logger.warning("Login failed for %s", apple_id)
            self.temp_session = None
            self.temp_apple_id = None
            return result

        api = result["api"]

        if api.requires_2fa:
            self.temp_session = api
            self.temp_apple_id = apple_id
            return {
                "success": False,
                "2fa_required": True,
                "message": "Enter 2FA code",
            }

        self.api = api
        self.icloud = ICloudService(api)
        self.temp_session = None
        self.temp_apple_id = None
        self.settings_service.set_remembered_apple_id(apple_id)
        logger.info("Login successful for %s", apple_id)
        return {"success": True, "message": "Logged in"}

    def continue_session(self):
        remembered_apple_id = self.settings_service.get_remembered_apple_id()
        if not remembered_apple_id:
            return {
                "success": False,
                "requires_login": True,
                "message": "Sign in required. Please enter your Apple ID and password.",
            }

        result = icloud_login(
            remembered_apple_id,
            TRUSTED_SESSION_RESUME_PLACEHOLDER,
            settings_service=self.settings_service,
        )
        if not result.get("success"):
            self._clear_authenticated_state()
            logger.warning("Trusted session resume failed for %s", remembered_apple_id)
            return {
                "success": False,
                "requires_login": True,
                "message": "Session expired. Please sign in again.",
            }

        api = result["api"]
        if api.requires_2fa:
            self._clear_authenticated_state()
            logger.info(
                "Trusted session resume requires reauthentication for %s",
                remembered_apple_id,
            )
            return {
                "success": False,
                "requires_login": True,
                "2fa_required": True,
                "message": "Session expired. Please sign in again.",
            }

        self.api = api
        self.icloud = ICloudService(api)
        self.temp_session = None
        self.temp_apple_id = None
        logger.info("Trusted session resumed for %s", remembered_apple_id)
        return {"success": True, "message": "Session resumed"}

    def logout(self):
        remembered_apple_id = self.settings_service.get_remembered_apple_id()
        deleted_session = False

        if remembered_apple_id:
            deleted_session = delete_session_directory(
                remembered_apple_id,
                settings_service=self.settings_service,
            )

        self.settings_service.clear_remembered_apple_id()
        self._clear_authenticated_state()
        return {
            "success": True,
            "deleted_session": deleted_session,
            "message": "Signed out locally",
        }

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

            trusted = self.temp_session.trust_session()
            self.api = self.temp_session
            self.icloud = ICloudService(self.api)
            apple_id = self.temp_apple_id
            self.temp_session = None
            self.temp_apple_id = None

            if trusted:
                if apple_id:
                    self.settings_service.set_remembered_apple_id(apple_id)
                logger.info("2FA verification successful and session trusted")
                return {
                    "success": True,
                    "message": "Logged in",
                    "trusted_session": True,
                }

            logger.warning("2FA verification succeeded but session trust failed")
            return {
                "success": True,
                "message": (
                    "Logged in, but iCloud did not trust this session for future "
                    "2FA skips"
                ),
                "trusted_session": False,
            }

        except Exception as e:
            logger.exception("2FA verification error")
            return {"success": False, "message": str(e)}
