from unittest.mock import MagicMock

from app.api.auth_api import AuthApi


def test_verify_2fa_success():
    api = AuthApi()

    mock = MagicMock()
    mock.validate_2fa_code.return_value = True
    mock.is_trusted_session = True

    api.temp_session = mock

    result = api.verify_2fa("123456")

    assert result["success"] is True


def test_verify_2fa_fail():
    api = AuthApi()

    mock = MagicMock()
    mock.validate_2fa_code.return_value = False

    api.temp_session = mock

    result = api.verify_2fa("000000")

    assert result["success"] is False