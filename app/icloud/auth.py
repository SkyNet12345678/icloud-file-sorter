from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AuthResponse:
    ok: bool
    message: str
    requires_2fa: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "requires_2fa": self.requires_2fa,
        }


def _get_pycloud_modules():
    try:
        from pyicloud import PyiCloudService
        from pyicloud.exceptions import PyiCloudFailedLoginException
    except ModuleNotFoundError as exc:
        if exc.name == "pyicloud":
            msg = "pyicloud is not installed in this Python environment. Run `pip install -e .` first."
            raise RuntimeError(msg) from exc
        raise

    return PyiCloudService, PyiCloudFailedLoginException


class ICloudAuthenticator:
    def __init__(self) -> None:
        self.api = None

    def _build_session_summary(self) -> dict[str, Any]:
        if self.api is None:
            return {}

        ds_info = self.api.data.get("dsInfo", {})
        display_name = " ".join(
            part for part in [ds_info.get("firstName"), ds_info.get("lastName")] if part
        )

        summary = {
            "account_name": self.api.account_name,
            "display_name": display_name or self.api.account_name,
            "trusted_session": bool(self.api.is_trusted_session),
            "available_services": sorted(self.api.data.get("webservices", {}).keys()),
        }

        try:
            usage = self.api.account.storage.usage
            summary["storage"] = {
                "used_bytes": usage.used_storage_in_bytes,
                "available_bytes": usage.available_storage_in_bytes,
                "total_bytes": usage.total_storage_in_bytes,
                "used_percent": usage.used_storage_in_percent,
            }
        except Exception:  # noqa: BLE001
            summary["storage"] = None

        try:
            summary["paired_device_count"] = len(self.api.account.devices)
        except Exception:  # noqa: BLE001
            summary["paired_device_count"] = None

        try:
            summary["family_member_count"] = len(self.api.account.family)
        except Exception:  # noqa: BLE001
            summary["family_member_count"] = None

        return summary

    def _success_response(self, message: str) -> dict[str, Any]:
        response = AuthResponse(ok=True, message=message).as_dict()
        response["session_summary"] = self._build_session_summary()
        return response

    def login(self, apple_id: str, password: str) -> dict[str, Any]:
        PyiCloudService, PyiCloudFailedLoginException = _get_pycloud_modules()

        try:
            self.api = PyiCloudService(apple_id, password)
        except PyiCloudFailedLoginException as exc:
            self.api = None
            return AuthResponse(ok=False, message=f"Login failed: {exc}").as_dict()

        if self.api.requires_2fa:
            return AuthResponse(
                ok=False,
                message="Two-factor authentication required.",
                requires_2fa=True,
            ).as_dict()

        return self._success_response("Logged in.")

    def submit_2fa_code(self, code: str) -> dict[str, Any]:
        if self.api is None:
            return AuthResponse(
                ok=False,
                message="No pending iCloud login session. Enter your Apple ID and password first.",
            ).as_dict()

        if not self.api.requires_2fa:
            return AuthResponse(ok=True, message="Logged in.").as_dict()

        if not self.api.validate_2fa_code(code):
            return AuthResponse(
                ok=False,
                message="Invalid verification code.",
                requires_2fa=True,
            ).as_dict()

        if not self.api.is_trusted_session:
            self.api.trust_session()

        return self._success_response("Logged in.")


def icloud_login(apple_id: str, password: str):
    authenticator = ICloudAuthenticator()
    result = authenticator.login(apple_id, password)

    if not result["ok"] and not result["requires_2fa"]:
        print(result["message"])
        return None

    if result["requires_2fa"]:
        print(result["message"])
        code = input("Enter 2FA code: ")
        result = authenticator.submit_2fa_code(code)

        if not result["ok"]:
            print(result["message"])
            return None

    return authenticator.api
