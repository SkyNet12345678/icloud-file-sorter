from app.icloud import auth


class FakeLoginFailure(Exception):
    pass


class FakePyiCloudService:
    should_fail = False
    requires_2fa = False
    is_trusted_session = True
    validate_2fa_result = True

    def __init__(self, apple_id, password):
        if self.should_fail:
            raise FakeLoginFailure("bad credentials")

        self.apple_id = apple_id
        self.account_name = apple_id
        self.password = password
        self.data = {"dsInfo": {}, "webservices": {}}
        self.requires_2fa = type(self).requires_2fa
        self.is_trusted_session = type(self).is_trusted_session
        self.trust_session_called = False

    def validate_2fa_code(self, code):
        self.code = code
        return type(self).validate_2fa_result

    def trust_session(self):
        self.trust_session_called = True
        self.is_trusted_session = True


def stub_pycloud(monkeypatch):
    monkeypatch.setattr(
        auth,
        "_get_pycloud_modules",
        lambda: (FakePyiCloudService, FakeLoginFailure),
    )


def test_login_invalid_credentials(monkeypatch):
    stub_pycloud(monkeypatch)
    FakePyiCloudService.should_fail = True

    authenticator = auth.ICloudAuthenticator()
    result = authenticator.login("fake@example.com", "wrong-password")

    assert result == {
        "ok": False,
        "message": "Login failed: bad credentials",
        "requires_2fa": False,
    }

    FakePyiCloudService.should_fail = False


def test_login_requires_two_factor(monkeypatch):
    stub_pycloud(monkeypatch)
    FakePyiCloudService.requires_2fa = True

    authenticator = auth.ICloudAuthenticator()
    result = authenticator.login("test@example.com", "secret")

    assert result == {
        "ok": False,
        "message": "Two-factor authentication required.",
        "requires_2fa": True,
    }

    FakePyiCloudService.requires_2fa = False


def test_login_success_includes_session_summary(monkeypatch):
    stub_pycloud(monkeypatch)

    authenticator = auth.ICloudAuthenticator()
    authenticator.api = None
    result = authenticator.login("test@example.com", "secret")

    assert result["ok"] is True
    assert result["session_summary"] == {
        "account_name": "test@example.com",
        "display_name": "test@example.com",
        "trusted_session": True,
        "available_services": [],
        "storage": None,
        "paired_device_count": None,
        "family_member_count": None,
    }


def test_submit_2fa_code_trusts_session(monkeypatch):
    stub_pycloud(monkeypatch)
    FakePyiCloudService.requires_2fa = True
    FakePyiCloudService.is_trusted_session = False
    FakePyiCloudService.validate_2fa_result = True

    authenticator = auth.ICloudAuthenticator()
    authenticator.login("test@example.com", "secret")
    result = authenticator.submit_2fa_code("123456")

    assert result == {
        "ok": True,
        "message": "Logged in.",
        "requires_2fa": False,
        "session_summary": {
            "account_name": "test@example.com",
            "display_name": "test@example.com",
            "trusted_session": True,
            "available_services": [],
            "storage": None,
            "paired_device_count": None,
            "family_member_count": None,
        },
    }
    assert authenticator.api.trust_session_called is True

    FakePyiCloudService.requires_2fa = False
    FakePyiCloudService.is_trusted_session = True


def test_submit_2fa_code_rejects_invalid_code(monkeypatch):
    stub_pycloud(monkeypatch)
    FakePyiCloudService.requires_2fa = True
    FakePyiCloudService.validate_2fa_result = False

    authenticator = auth.ICloudAuthenticator()
    authenticator.login("test@example.com", "secret")
    result = authenticator.submit_2fa_code("000000")

    assert result == {
        "ok": False,
        "message": "Invalid verification code.",
        "requires_2fa": True,
    }

    FakePyiCloudService.requires_2fa = False
    FakePyiCloudService.validate_2fa_result = True
