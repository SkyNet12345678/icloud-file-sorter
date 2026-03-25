from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from app.icloud.auth import ICloudAuthenticator

DEFAULT_WINDOW_TITLE = "iCloud Sorter"
DEFAULT_DEV_SERVER_URL = "http://127.0.0.1:5173"
UI_MODE_ENV_VAR = "APP_UI_MODE"
UI_DEV_SERVER_ENV_VAR = "APP_UI_DEV_SERVER_URL"


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_dist_index_path() -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        bundled_index = bundle_root / "frontend" / "dist" / "index.html"
        if bundled_index.exists():
            return bundled_index

    return get_project_root() / "frontend" / "dist" / "index.html"


def is_dev_server_available(url: str, timeout: float = 1.0) -> bool:
    try:
        with urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, URLError, ValueError):
        return False


def resolve_ui_target() -> str:
    ui_mode = os.getenv(UI_MODE_ENV_VAR, "auto").strip().lower()
    dev_server_url = os.getenv(UI_DEV_SERVER_ENV_VAR, DEFAULT_DEV_SERVER_URL).strip()

    if ui_mode == "dev":
        return dev_server_url

    if ui_mode == "prod":
        dist_index = get_dist_index_path()
        if not dist_index.exists():
            raise FileNotFoundError(
                f"Built frontend not found at {dist_index}. Run `npm run build` in `frontend/` first.",
            )
        return dist_index.resolve().as_uri()

    if ui_mode != "auto":
        raise ValueError(
            f"Unsupported {UI_MODE_ENV_VAR} value {ui_mode!r}. Use 'auto', 'dev', or 'prod'.",
        )

    if is_dev_server_available(dev_server_url):
        return dev_server_url

    dist_index = get_dist_index_path()
    if dist_index.exists():
        return dist_index.resolve().as_uri()

    raise FileNotFoundError(
        "No UI source available. Start the Vite dev server or build frontend assets.",
    )


class DesktopApi:
    def __init__(self) -> None:
        self.authenticator = ICloudAuthenticator()

    def login(self, apple_id: str, password: str) -> dict[str, Any]:
        return self.authenticator.login(apple_id, password)

    def submit_2fa_code(self, code: str) -> dict[str, Any]:
        return self.authenticator.submit_2fa_code(code)


def launch_webview() -> None:
    try:
        import webview
    except ModuleNotFoundError as exc:
        if exc.name == "webview":
            msg = "pywebview is not installed in this Python environment. Run `pip install -e .` first."
            raise RuntimeError(msg) from exc
        raise

    webview.create_window(
        DEFAULT_WINDOW_TITLE,
        url=resolve_ui_target(),
        js_api=DesktopApi(),
        width=1280,
        height=800,
    )
    webview.start()
