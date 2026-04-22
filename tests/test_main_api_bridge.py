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
    fake_pycloud = types.ModuleType("pyicloud")
    fake_pycloud.PyiCloudService = MagicMock()
    fake_pycloud_exceptions = types.ModuleType("pyicloud.exceptions")
    fake_pycloud_exceptions.PyiCloudFailedLoginException = Exception

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setitem(sys.modules, "pyicloud", fake_pycloud)
    monkeypatch.setitem(sys.modules, "pyicloud.exceptions", fake_pycloud_exceptions)
    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    yield module

    sys.modules.pop("app.main", None)


def test_api_start_sort_returns_error_when_service_is_unavailable(main_module):
    api = main_module.API()

    result = api.start_sort(["album-1", "album-2"])

    assert result == {"error": "Sorting service unavailable"}


def test_api_start_sort_delegates_to_albums_service(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.start_sort.return_value = {"job_id": "job-123"}

    result = api.start_sort(["album-1", "album-2"])

    assert result == {"job_id": "job-123"}
    api.albums_service.start_sort.assert_called_once_with(["album-1", "album-2"])


def test_api_get_albums_returns_failure_when_service_is_unavailable(main_module):
    api = main_module.API()

    result = api.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "Album service unavailable",
    }


def test_api_get_albums_delegates_structured_payload(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.get_albums.return_value = {
        "success": True,
        "albums": [{"id": "album-1", "name": "Trips", "item_count": 5, "is_system_album": False}],
        "error": None,
    }

    result = api.get_albums()

    assert result["success"] is True
    assert result["albums"][0]["id"] == "album-1"
    api.albums_service.get_albums.assert_called_once_with()


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


def test_api_get_albums_empty_success_passthrough(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.get_albums.return_value = {
        "success": True,
        "albums": [],
        "error": None,
    }

    result = api.get_albums()

    assert result == {
        "success": True,
        "albums": [],
        "error": None,
    }


def test_api_get_album_assets_returns_failure_when_service_is_unavailable(main_module):
    api = main_module.API()

    result = api.get_album_assets("album-1")

    assert result == {
        "success": False,
        "album": None,
        "assets": [],
        "error": "Album service unavailable",
    }


def test_api_get_album_assets_delegates_to_albums_service(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.get_album_assets.return_value = {
        "success": True,
        "album": {"id": "album-1", "name": "Vacation 2025", "item_count": 3, "is_system_album": False},
        "assets": [
            {"asset_id": "a1", "filename": "IMG_001.HEIC"},
            {"asset_id": "a2", "filename": "IMG_002.HEIC"},
            {"asset_id": "a3", "filename": "IMG_003.HEIC"},
        ],
        "error": None,
    }

    result = api.get_album_assets("album-1")

    assert result["success"] is True
    assert len(result["assets"]) == 3
    assert result["album"]["name"] == "Vacation 2025"
    api.albums_service.get_album_assets.assert_called_once_with("album-1")


def test_api_start_sort_error_passthrough_from_service(main_module):
    api = main_module.API()
    api.albums_service = MagicMock()
    api.albums_service.start_sort.return_value = {"error": "Album cache not loaded"}

    result = api.start_sort(["album-1"])

    assert result == {"error": "Album cache not loaded"}
