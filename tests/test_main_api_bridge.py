import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

@pytest.fixture
def main_module(monkeypatch):
    fake_webview = types.ModuleType("webview")
    fake_webview.create_window = MagicMock()
    fake_webview.start = MagicMock()

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    yield module

    sys.modules.pop("app.main", None)


def test_api_start_sort_returns_error_when_service_is_unavailable(main_module):
    api = main_module.API()

    result = api.start_sort([1, 2])

    assert result == {"error": "Sorting service unavailable"}


def test_api_start_sort_delegates_to_albums_service(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.start_sort.return_value = {"job_id": "job-123"}

    result = api.start_sort([1, 2])

    assert result == {"job_id": "job-123"}
    api.albums_service.start_sort.assert_called_once_with([1, 2])


def test_api_get_sort_progress_returns_error_when_service_is_unavailable(main_module):
    api = main_module.API()

    result = api.get_sort_progress("job-123")

    assert result == {
        "job_id": "job-123",
        "status": "error",
        "processed": 0,
        "total": 0,
        "percent": 0,
        "message": "Sorting service unavailable",
    }


def test_api_get_sort_progress_delegates_to_albums_service(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.get_sort_progress.return_value = {
        "job_id": "job-123",
        "status": "running",
        "processed": 50,
        "total": 1847,
        "percent": 2,
        "message": "Processing photo 50 of 1847",
    }

    result = api.get_sort_progress("job-123")

    assert result["status"] == "running"
    assert result["processed"] == 50
    api.albums_service.get_sort_progress.assert_called_once_with("job-123")
