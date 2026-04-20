from types import SimpleNamespace

import pytest

from app.icloud.icloud_service import ICloudService


class FakeAlbum:
    def __init__(self, album_id, name, item_count=0):
        self.id = album_id
        self.name = name
        self.fullname = name
        self._item_count = item_count

    def __len__(self):
        return self._item_count


class TrackingPhotosService:
    def __init__(self, album_sequences):
        self.album_sequences = list(album_sequences)
        self.request_count = 0

    @property
    def albums(self):
        self.request_count += 1
        index = min(self.request_count - 1, len(self.album_sequences) - 1)
        current_albums = self.album_sequences[index]
        if isinstance(current_albums, Exception):
            raise current_albums
        return current_albums


def build_service(album_sequences):
    photos = TrackingPhotosService(album_sequences)
    api = SimpleNamespace(photos=photos)
    return ICloudService(api=api), photos


def test_get_albums_populates_cache_on_first_successful_load():
    raw_album = FakeAlbum("album-1", "Trips", item_count=5)
    service, photos = build_service([[raw_album]])

    result = service.get_albums()

    assert result == {
        "success": True,
        "albums": [
            {
                "id": "album-1",
                "name": "Trips",
                "item_count": 5,
                "is_system_album": False,
            }
        ],
        "error": None,
    }
    assert photos.request_count == 1
    assert service.album_cache_loaded is True
    assert service.album_list_cache == result["albums"]
    assert service.album_summaries_by_id["album-1"]["name"] == "Trips"
    assert service.raw_albums_by_id["album-1"] is raw_album


def test_get_albums_reuses_loaded_cache_without_refetching():
    first_album = FakeAlbum("album-1", "Trips", item_count=5)
    second_album = FakeAlbum("album-2", "Family", item_count=3)
    service, photos = build_service([[first_album], [second_album]])

    first_result = service.get_albums()
    second_result = service.get_albums()

    assert photos.request_count == 1
    assert second_result == first_result


def test_get_albums_force_refresh_rebuilds_cache_atomically():
    first_album = FakeAlbum("album-1", "Trips", item_count=5)
    refreshed_album = FakeAlbum("album-2", "Family", item_count=3)
    service, photos = build_service([[first_album], [refreshed_album]])

    first_result = service.get_albums()
    refreshed_result = service.get_albums(force_refresh=True)

    assert photos.request_count == 2
    assert first_result["albums"][0]["id"] == "album-1"
    assert refreshed_result["albums"][0]["id"] == "album-2"
    assert service.raw_albums_by_id["album-2"] is refreshed_album
    assert "album-1" not in service.raw_albums_by_id


def test_failed_initial_load_does_not_mark_cache_as_loaded():
    service, photos = build_service([RuntimeError("Session expired")])

    result = service.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "Session expired",
    }
    assert photos.request_count == 1
    assert service.album_cache_loaded is False
    assert service.album_list_cache == []
    assert service.raw_albums_by_id == {}


def test_failed_refresh_keeps_last_known_good_cache():
    first_album = FakeAlbum("album-1", "Trips", item_count=5)
    service, photos = build_service([[first_album], RuntimeError("Refresh failed")])

    first_result = service.get_albums()
    refreshed_result = service.get_albums(force_refresh=True)

    assert photos.request_count == 2
    assert first_result["success"] is True
    assert refreshed_result == {
        "success": False,
        "albums": [],
        "error": "Refresh failed",
    }
    assert service.album_cache_loaded is True
    assert service.album_list_cache == first_result["albums"]
    assert service.raw_albums_by_id["album-1"] is first_album


def test_clear_album_cache_invalidates_all_cache_structures():
    raw_album = FakeAlbum("album-1", "Trips", item_count=5)
    service, _ = build_service([[raw_album]])
    service.get_albums()

    service._clear_album_cache()

    assert service.album_cache_loaded is False
    assert service.album_list_cache == []
    assert service.album_summaries_by_id == {}
    assert service.raw_albums_by_id == {}


def test_get_cached_album_reads_from_loaded_cache_only():
    raw_album = FakeAlbum("album-1", "Trips", item_count=5)
    service, _ = build_service([[raw_album]])
    service.get_albums()

    assert service.get_cached_album("album-1") is raw_album
    assert service.get_cached_album_summary("album-1") == {
        "id": "album-1",
        "name": "Trips",
        "item_count": 5,
        "is_system_album": False,
    }
    assert service.get_cached_album("missing") is None
    assert service.get_cached_album_summary("missing") is None


def test_cache_lookup_helpers_fail_clearly_when_cache_is_cold():
    service, photos = build_service([[FakeAlbum("album-1", "Trips", item_count=5)]])

    with pytest.raises(RuntimeError, match="Album cache not loaded"):
        service.get_cached_album("album-1")

    with pytest.raises(RuntimeError, match="Album cache not loaded"):
        service.get_cached_album_summary("album-1")

    assert photos.request_count == 0
