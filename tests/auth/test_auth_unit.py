from unittest.mock import MagicMock

from app.api.auth_api import AuthApi
from app.icloud.icloud_service import ICloudService


def test_verify_2fa_success():
    api = AuthApi()

    mock = MagicMock()
    mock.validate_2fa_code.return_value = True
    mock.trust_session.return_value = True
    mock.is_trusted_session = True

    api.temp_session = mock

    result = api.verify_2fa("123456")

    assert result["success"] is True
    assert result["trusted_session"] is True
    assert api.api is mock
    assert isinstance(api.icloud, ICloudService)


def test_verify_2fa_fail():
    api = AuthApi()

    mock = MagicMock()
    mock.validate_2fa_code.return_value = False

    api.temp_session = mock

    result = api.verify_2fa("000000")

    assert result["success"] is False


def test_verify_2fa_allows_login_when_trust_session_fails():
    api = AuthApi()

    mock = MagicMock()
    mock.validate_2fa_code.return_value = True
    mock.trust_session.return_value = False

    api.temp_session = mock

    result = api.verify_2fa("123456")

    assert result["success"] is True
    assert result["trusted_session"] is False
    assert "did not trust this session" in result["message"]
    assert api.api is mock
    assert isinstance(api.icloud, ICloudService)
    assert api.temp_session is None


def test_login_initializes_icloud_service_after_direct_success(monkeypatch):
    api = AuthApi()
    mock = MagicMock()
    mock.requires_2fa = False

    def fake_login(*_args, **_kwargs):
        return {"success": True, "api": mock, "requires_2fa": False}

    monkeypatch.setattr("app.api.auth_api.icloud_login", fake_login)

    result = api.login("test@icloud.com", "password")

    assert result == {"success": True, "message": "Logged in"}
    assert api.api is mock
    assert isinstance(api.icloud, ICloudService)
