from types import SimpleNamespace

from app.icloud.icloud_service import ICloudService


class FakeAlbum:
    def __init__(self, album_id, name, item_count=0, fullname=None):
        self.id = album_id
        self.name = name
        self.fullname = fullname or name
        self._item_count = item_count

    def __len__(self):
        if isinstance(self._item_count, Exception):
            raise self._item_count
        return self._item_count


SmartPhotoAlbum = type("SmartPhotoAlbum", (FakeAlbum,), {})
PhotoAlbumFolder = type("PhotoAlbumFolder", (FakeAlbum,), {})


def build_api(albums):
    return SimpleNamespace(photos=SimpleNamespace(albums=albums))


def test_normalize_album_summary_returns_ui_shape_for_user_album():
    service = ICloudService(api=None)
    album = FakeAlbum("album-1", "Vacation 2025", item_count=179)

    result = service._normalize_album_summary(album)

    assert result == {
        "id": "album-1",
        "name": "Vacation 2025",
        "item_count": 179,
        "is_system_album": False,
    }


def test_normalize_album_summary_falls_back_to_zero_when_item_count_fails():
    service = ICloudService(api=None)
    album = FakeAlbum("album-2", "Family", item_count=RuntimeError("count failed"))

    result = service._normalize_album_summary(album)

    assert result["item_count"] == 0


def test_normalize_album_summary_excludes_system_albums():
    service = ICloudService(api=None)
    album = SmartPhotoAlbum("smart-1", "Library", item_count=500)

    assert service._normalize_album_summary(album) is None


def test_normalize_album_summary_excludes_album_folders():
    service = ICloudService(api=None)
    album = PhotoAlbumFolder("folder-1", "Trips", item_count=3)

    assert service._normalize_album_summary(album) is None


def test_get_albums_returns_normalized_user_albums_only():
    service = ICloudService(
        api=build_api(
            [
                FakeAlbum("album-2", "Trips", item_count=50),
                SmartPhotoAlbum("smart-1", "Library", item_count=500),
                FakeAlbum("album-1", "Family", item_count=12),
                PhotoAlbumFolder("folder-1", "Archived", item_count=1),
            ]
        )
    )

    result = service.get_albums()

    assert result == {
        "success": True,
        "albums": [
            {
                "id": "album-1",
                "name": "Family",
                "item_count": 12,
                "is_system_album": False,
            },
            {
                "id": "album-2",
                "name": "Trips",
                "item_count": 50,
                "is_system_album": False,
            },
        ],
        "error": None,
    }


def test_get_albums_returns_successful_empty_result_when_no_eligible_albums_exist():
    service = ICloudService(api=build_api([SmartPhotoAlbum("smart-1", "Library", 500)]))

    result = service.get_albums()

    assert result == {
        "success": True,
        "albums": [],
        "error": None,
    }


def test_get_albums_returns_failure_when_album_lookup_raises():
    class ExplodingPhotosService:
        @property
        def albums(self):
            raise RuntimeError("Session expired")

    service = ICloudService(api=SimpleNamespace(photos=ExplodingPhotosService()))

    result = service.get_albums()

    assert result == {
        "success": False,
        "albums": [],
        "error": "Session expired",
    }
