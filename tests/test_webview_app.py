import pytest

from app import webview_app


def test_resolve_ui_target_uses_dev_server_in_auto_mode(monkeypatch):
    monkeypatch.delenv(webview_app.UI_MODE_ENV_VAR, raising=False)
    monkeypatch.delenv(webview_app.UI_DEV_SERVER_ENV_VAR, raising=False)
    monkeypatch.setattr(webview_app, "is_dev_server_available", lambda url: url.endswith(":5173"))

    ui_target = webview_app.resolve_ui_target()

    assert ui_target == webview_app.DEFAULT_DEV_SERVER_URL


def test_resolve_ui_target_uses_built_assets_when_dev_server_is_down(monkeypatch, tmp_path):
    dist_index = tmp_path / "frontend" / "dist" / "index.html"
    dist_index.parent.mkdir(parents=True)
    dist_index.write_text("<!doctype html>", encoding="utf-8")

    monkeypatch.delenv(webview_app.UI_MODE_ENV_VAR, raising=False)
    monkeypatch.setattr(webview_app, "is_dev_server_available", lambda url: False)
    monkeypatch.setattr(webview_app, "get_dist_index_path", lambda: dist_index)

    ui_target = webview_app.resolve_ui_target()

    assert ui_target == dist_index.resolve().as_uri()


def test_resolve_ui_target_requires_dist_assets_in_prod_mode(monkeypatch, tmp_path):
    missing_dist_index = tmp_path / "frontend" / "dist" / "index.html"

    monkeypatch.setenv(webview_app.UI_MODE_ENV_VAR, "prod")
    monkeypatch.setattr(webview_app, "get_dist_index_path", lambda: missing_dist_index)

    with pytest.raises(FileNotFoundError):
        webview_app.resolve_ui_target()


def test_resolve_ui_target_rejects_invalid_mode(monkeypatch):
    monkeypatch.setenv(webview_app.UI_MODE_ENV_VAR, "staging")

    with pytest.raises(ValueError):
        webview_app.resolve_ui_target()
