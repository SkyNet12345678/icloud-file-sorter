from unittest.mock import MagicMock

from app.icloud.albums_service import AlbumsService


def test_get_albums_returns_failure_when_icloud_service_is_unavailable():
    service = AlbumsService(icloud_api=None)
    service.icloud = None

    result = service.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "Album service unavailable",
    }


def test_get_albums_returns_structured_success_payload():
    service = AlbumsService(icloud_api=None)
    service.icloud = MagicMock()
    service.icloud.get_albums.return_value = {
        "success": True,
        "albums": [{"id": "album-1", "name": "Trips", "item_count": 5, "is_system_album": False}],
        "error": None,
    }

    result = service.get_albums()

    assert result["success"] is True
    assert result["albums"][0]["id"] == "album-1"


def test_get_albums_returns_failure_payload_when_backend_raises():
    service = AlbumsService(icloud_api=None)
    service.icloud = MagicMock()
    service.icloud.get_albums.side_effect = RuntimeError("Session expired")

    result = service.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "Session expired",
    }


def test_get_albums_empty_success_is_distinct_from_failure():
    service = AlbumsService(icloud_api=None)
    service.icloud = MagicMock()
    service.icloud.get_albums.return_value = {
        "success": True,
        "albums": [],
        "error": None,
    }

    result = service.get_albums()

    assert result == {
        "success": True,
        "albums": [],
        "error": None,
    }


def test_get_albums_failure_payload_preserves_error_message():
    service = AlbumsService(icloud_api=None)
    service.icloud = MagicMock()
    service.icloud.get_albums.return_value = {
        "success": False,
        "albums": [],
        "error": "iCloud Photos service unavailable",
    }

    result = service.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "iCloud Photos service unavailable",
    }
