from unittest.mock import MagicMock

from app.api.auth_api import AuthApi
from app.icloud.icloud_service import ICloudService
from app.icloud.session_store import get_session_directory
from app.settings import SettingsService


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


def test_login_initializes_icloud_service_after_direct_success(monkeypatch, tmp_path):
    settings_service = SettingsService(tmp_path)
    api = AuthApi(settings_service=settings_service)
    mock = MagicMock()
    mock.requires_2fa = False

    def fake_login(*_args, **_kwargs):
        return {"success": True, "api": mock, "requires_2fa": False}

    monkeypatch.setattr("app.api.auth_api.icloud_login", fake_login)

    result = api.login("test@icloud.com", "password")

    assert result == {"success": True, "message": "Logged in"}
    assert api.api is mock
    assert isinstance(api.icloud, ICloudService)
    assert settings_service.get_remembered_apple_id() == "test@icloud.com"


def test_get_auth_state_reports_remembered_apple_id(tmp_path):
    settings_service = SettingsService(tmp_path)
    settings_service.set_remembered_apple_id("User@iCloud.com")
    api = AuthApi(settings_service=settings_service)

    result = api.get_auth_state()

    assert result == {
        "success": True,
        "has_remembered_apple_id": True,
        "remembered_apple_id": "user@icloud.com",
    }


def test_get_auth_state_reports_no_remembered_apple_id(tmp_path):
    api = AuthApi(settings_service=SettingsService(tmp_path))

    result = api.get_auth_state()

    assert result == {
        "success": True,
        "has_remembered_apple_id": False,
        "remembered_apple_id": None,
    }


def test_verify_2fa_remembers_apple_id_when_session_is_trusted(tmp_path):
    settings_service = SettingsService(tmp_path)
    api = AuthApi(settings_service=settings_service)
    mock = MagicMock()
    mock.validate_2fa_code.return_value = True
    mock.trust_session.return_value = True
    api.temp_session = mock
    api.temp_apple_id = "User@iCloud.com"

    result = api.verify_2fa("123456")

    assert result["success"] is True
    assert settings_service.get_remembered_apple_id() == "user@icloud.com"


def test_verify_2fa_does_not_remember_apple_id_when_trust_fails(tmp_path):
    settings_service = SettingsService(tmp_path)
    api = AuthApi(settings_service=settings_service)
    mock = MagicMock()
    mock.validate_2fa_code.return_value = True
    mock.trust_session.return_value = False
    api.temp_session = mock
    api.temp_apple_id = "User@iCloud.com"

    result = api.verify_2fa("123456")

    assert result["success"] is True
    assert result["trusted_session"] is False
    assert settings_service.get_remembered_apple_id() is None


def test_continue_session_resumes_remembered_apple_id(monkeypatch, tmp_path):
    settings_service = SettingsService(tmp_path)
    settings_service.set_remembered_apple_id("User@iCloud.com")
    api = AuthApi(settings_service=settings_service)
    mock = MagicMock()
    mock.requires_2fa = False
    calls = []

    def fake_login(*args, **kwargs):
        calls.append((args, kwargs))
        return {"success": True, "api": mock, "requires_2fa": False}

    monkeypatch.setattr("app.api.auth_api.icloud_login", fake_login)

    result = api.continue_session()

    assert result == {"success": True, "message": "Session resumed"}
    assert api.api is mock
    assert isinstance(api.icloud, ICloudService)
    assert calls[0][0][:2] == ("user@icloud.com", "__trusted_session_resume__")
    assert calls[0][1]["settings_service"] is settings_service


def test_continue_session_falls_back_when_resume_fails(monkeypatch, tmp_path):
    settings_service = SettingsService(tmp_path)
    settings_service.set_remembered_apple_id("user@icloud.com")
    api = AuthApi(settings_service=settings_service)
    api.api = MagicMock()
    api.temp_session = MagicMock()
    api.temp_apple_id = "user@icloud.com"
    api.icloud = MagicMock()

    def fake_login(*_args, **_kwargs):
        return {"success": False, "message": "Invalid Apple ID or password"}

    monkeypatch.setattr("app.api.auth_api.icloud_login", fake_login)

    result = api.continue_session()

    assert result == {
        "success": False,
        "requires_login": True,
        "message": "Session expired. Please sign in again.",
    }
    assert api.api is None
    assert api.temp_session is None
    assert api.temp_apple_id is None
    assert api.icloud is None


def test_continue_session_clears_auth_state_when_resume_requires_2fa(
    monkeypatch, tmp_path
):
    settings_service = SettingsService(tmp_path)
    settings_service.set_remembered_apple_id("user@icloud.com")
    api = AuthApi(settings_service=settings_service)
    api.api = MagicMock()
    api.temp_session = MagicMock()
    api.temp_apple_id = "user@icloud.com"
    api.icloud = MagicMock()
    mock = MagicMock()
    mock.requires_2fa = True

    def fake_login(*_args, **_kwargs):
        return {"success": True, "api": mock, "requires_2fa": True}

    monkeypatch.setattr("app.api.auth_api.icloud_login", fake_login)

    result = api.continue_session()

    assert result == {
        "success": False,
        "requires_login": True,
        "2fa_required": True,
        "message": "Session expired. Please sign in again.",
    }
    assert api.api is None
    assert api.temp_session is None
    assert api.temp_apple_id is None
    assert api.icloud is None


def test_logout_clears_remembered_user_and_target_session(tmp_path):
    settings_service = SettingsService(tmp_path)
    settings_service.set_remembered_apple_id("User@iCloud.com")
    target_dir = get_session_directory("user@icloud.com", settings_service=settings_service)
    other_dir = get_session_directory("other@icloud.com", settings_service=settings_service)
    target_dir.mkdir(parents=True)
    other_dir.mkdir(parents=True)
    api = AuthApi(settings_service=settings_service)
    api.api = MagicMock()
    api.temp_session = MagicMock()
    api.temp_apple_id = "user@icloud.com"
    api.icloud = MagicMock()

    result = api.logout()

    assert result["success"] is True
    assert result["deleted_session"] is True
    assert settings_service.get_remembered_apple_id() is None
    assert not target_dir.exists()
    assert other_dir.is_dir()
    assert api.api is None
    assert api.temp_session is None
    assert api.temp_apple_id is None
    assert api.icloud is None
