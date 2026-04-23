from pathlib import Path
from unittest.mock import patch

from app.icloud.auth import icloud_login
from app.icloud.session_store import apple_id_session_key, get_session_directory
from app.settings import SettingsService


class FakePyiCloudService:
    calls = []

    def __init__(self, apple_id, password, cookie_directory=None):
        self.apple_id = apple_id
        self.password = password
        self.cookie_directory = cookie_directory
        self.requires_2fa = False
        self.calls.append(
            {
                "apple_id": apple_id,
                "password": password,
                "cookie_directory": cookie_directory,
            },
        )


def test_icloud_login_uses_stable_account_specific_cookie_directory(tmp_path):
    settings_service = SettingsService(tmp_path)
    FakePyiCloudService.calls = []

    with patch("app.icloud.auth.PyiCloudService", new=FakePyiCloudService):
        result = icloud_login(
            "Test@iCloud.com ",
            "password",
            settings_service=settings_service,
        )

    expected_dir = tmp_path / "icloud-sessions" / apple_id_session_key(
        "test@icloud.com",
    )

    assert result["success"] is True
    assert FakePyiCloudService.calls == [
        {
            "apple_id": "Test@iCloud.com ",
            "password": "password",
            "cookie_directory": str(expected_dir),
        },
    ]
    assert expected_dir.is_dir()


def test_session_path_is_account_specific_and_normalized(tmp_path):
    sessions_root = tmp_path / "sessions"

    first = get_session_directory("User@iCloud.com", sessions_root=sessions_root)
    same_normalized = get_session_directory(
        " user@icloud.com ",
        sessions_root=sessions_root,
    )
    similar = get_session_directory(
        "user+photos@icloud.com",
        sessions_root=sessions_root,
    )

    assert first == same_normalized
    assert first != similar
    assert first.parent == sessions_root
    assert similar.parent == sessions_root
    assert len(first.name) == 64


def test_settings_service_exposes_public_app_data_and_session_dirs(tmp_path):
    service = SettingsService(tmp_path)

    assert service.get_app_data_dir() == Path(tmp_path)
    assert service.get_icloud_sessions_dir() == Path(tmp_path) / "icloud-sessions"
