from app import webview_app


def test_desktop_api_delegates_login(monkeypatch):
    calls = []

    class FakeAuthenticator:
        def login(self, apple_id, password):
            calls.append(("login", apple_id, password))
            return {"ok": True, "message": "Logged in.", "requires_2fa": False}

        def submit_2fa_code(self, code):
            calls.append(("submit_2fa_code", code))
            return {"ok": True, "message": "Logged in.", "requires_2fa": False}

    monkeypatch.setattr(webview_app, "ICloudAuthenticator", FakeAuthenticator)

    api = webview_app.DesktopApi()
    result = api.login("dev@example.com", "secret")

    assert result["ok"] is True
    assert calls == [("login", "dev@example.com", "secret")]


def test_desktop_api_delegates_two_factor_submission(monkeypatch):
    calls = []

    class FakeAuthenticator:
        def login(self, apple_id, password):
            calls.append(("login", apple_id, password))
            return {"ok": False, "message": "2FA", "requires_2fa": True}

        def submit_2fa_code(self, code):
            calls.append(("submit_2fa_code", code))
            return {"ok": True, "message": "Logged in.", "requires_2fa": False}

    monkeypatch.setattr(webview_app, "ICloudAuthenticator", FakeAuthenticator)

    api = webview_app.DesktopApi()
    result = api.submit_2fa_code("123456")

    assert result["ok"] is True
    assert calls == [("submit_2fa_code", "123456")]
