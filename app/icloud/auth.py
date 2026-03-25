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

        return AuthResponse(ok=True, message="Logged in.").as_dict()

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

        return AuthResponse(ok=True, message="Logged in.").as_dict()


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
