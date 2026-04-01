from unittest.mock import MagicMock, patch

import pytest

from app.api.auth_api import AuthApi


# Fixtures
@pytest.fixture
def auth_api():
    return AuthApi()

# Mocked PyiCloudService
class FakePyiCloudService:
    def __init__(self, apple_id, password, cookie_directory=None):
        if apple_id != "test@icloud.com" or password != "correctpassword":
            raise Exception("Invalid credentials")
        self.requires_2fa = True
        self.is_trusted_session = False
        self.verified = False

    def validate_2fa_code(self, code):
        if code == "123456":
            self.verified = True
            return True
        return False

    def trust_session(self):
        self.is_trusted_session = True


# E2E test
@patch("app.icloud.auth.PyiCloudService", new=FakePyiCloudService)
def test_full_login_flow(auth_api):
    # Step 1: wrong credentials
    resp = auth_api.login("test@icloud.com", "wrongpassword")
    assert resp["success"] is False
    assert "Login failed" in resp.get("message", "")

    # Step 2: correct credentials → triggers 2FA
    resp = auth_api.login("test@icloud.com", "correctpassword")
    assert resp["success"] is False
    assert resp.get("2fa_required") is True
    assert resp.get("message") == "Enter 2FA code"

    # Step 3: invalid 2FA code
    resp2 = auth_api.verify_2fa("000000")
    assert resp2["success"] is False
    assert resp2["message"] == "Invalid code"

    # Step 4: valid 2FA code
    resp3 = auth_api.verify_2fa("123456")
    assert resp3["success"] is True
    assert resp3["message"] == "Logged in"

    # Step 5: ensure session is promoted
    assert auth_api.api is not None
    assert auth_api.api.verified is True
    assert auth_api.api.is_trusted_session is True
    # temp_session should be cleared
    assert auth_api.temp_session is None