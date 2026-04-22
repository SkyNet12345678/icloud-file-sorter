from types import SimpleNamespace

from app.icloud.icloud_service import ICloudService


class FakeAsset:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeAlbum:
    def __init__(self, album_id, name, asset_sequences, item_count=None):
        self.id = album_id
        self.name = name
        self.fullname = name
        self.asset_sequences = list(asset_sequences)
        self.asset_request_count = 0
        self._item_count = item_count if item_count is not None else len(asset_sequences[0])

    def __len__(self):
        return self._item_count

    @property
    def assets(self):
        self.asset_request_count += 1
        index = min(self.asset_request_count - 1, len(self.asset_sequences) - 1)
        current_assets = self.asset_sequences[index]
        if isinstance(current_assets, Exception):
            raise current_assets
        return current_assets


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


class FakeSettingsService:
    def __init__(self, source_folder):
        self.source_folder = source_folder

    def get_source_folder(self):
        return self.source_folder


def build_service(album_sequences):
    photos = TrackingPhotosService(album_sequences)
    api = SimpleNamespace(photos=photos)
    return ICloudService(api=api), photos


def test_get_album_assets_populates_per_album_cache_and_reuses_it():
    album = FakeAlbum(
        "album-1",
        "Trips",
        [[
            FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image"),
            FakeAsset(filename="missing-id.HEIC", media_type="image"),
        ]],
        item_count=2,
    )
    service, _ = build_service([[album]])
    service.get_albums()

    first_result = service.get_album_assets("album-1")
    second_result = service.get_album_assets("album-1")

    assert album.asset_request_count == 1
    assert first_result == {
        "success": True,
        "album": {
            "id": "album-1",
            "name": "Trips",
            "item_count": 2,
            "is_system_album": False,
        },
        "assets": [
            {
                "asset_id": "asset-1",
                "filename": "IMG_0001.HEIC",
                "original_filename": "IMG_0001.HEIC",
                "created_at": None,
                "size": None,
                "media_type": "image",
                "album_id": "album-1",
                "album_name": "Trips",
            }
        ],
        "error": None,
    }
    assert second_result == first_result
    assert service.get_cached_album_assets("album-1") == first_result["assets"]


def test_get_album_assets_force_refresh_reloads_only_requested_album():
    album_one = FakeAlbum(
        "album-1",
        "Trips",
        [
            [FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image")],
            [FakeAsset(id="asset-2", filename="IMG_0002.HEIC", media_type="image")],
        ],
        item_count=1,
    )
    album_two = FakeAlbum(
        "album-2",
        "Family",
        [[FakeAsset(id="asset-9", filename="IMG_1000.HEIC", media_type="image")]],
        item_count=1,
    )
    service, _ = build_service([[album_one, album_two]])
    service.get_albums()

    service.get_album_assets("album-1")
    service.get_album_assets("album-2")
    refreshed_result = service.get_album_assets("album-1", force_refresh=True)

    assert album_one.asset_request_count == 2
    assert album_two.asset_request_count == 1
    assert refreshed_result["assets"][0]["asset_id"] == "asset-2"
    assert service.get_cached_album_assets("album-1")[0]["asset_id"] == "asset-2"
    assert service.get_cached_album_assets("album-2")[0]["asset_id"] == "asset-9"


def test_get_album_assets_treats_all_skipped_assets_as_successful_empty_result():
    album = FakeAlbum(
        "album-1",
        "Trips",
        [[FakeAsset(filename="IMG_0001.HEIC", media_type="image")]],
        item_count=1,
    )
    service, _ = build_service([[album]])
    service.get_albums()

    result = service.get_album_assets("album-1")

    assert result == {
        "success": True,
        "album": {
            "id": "album-1",
            "name": "Trips",
            "item_count": 1,
            "is_system_album": False,
        },
        "assets": [],
        "error": None,
    }
    assert service.get_cached_album_assets("album-1") == []
    assert "album-1" in service.asset_cache_loaded_album_ids


def test_get_album_assets_returns_clear_failures_for_cold_cache_and_unknown_album():
    album = FakeAlbum(
        "album-1",
        "Trips",
        [[FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image")]],
        item_count=1,
    )
    service, _ = build_service([[album]])

    cold_result = service.get_album_assets("album-1")

    service.get_albums()
    missing_result = service.get_album_assets("missing")

    assert cold_result == {
        "success": False,
        "album": None,
        "assets": [],
        "error": "Album cache not loaded",
    }
    assert missing_result == {
        "success": False,
        "album": None,
        "assets": [],
        "error": "Album not found",
    }


def test_failed_asset_refresh_keeps_last_known_good_cache():
    album = FakeAlbum(
        "album-1",
        "Trips",
        [
            [FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image")],
            RuntimeError("Asset fetch failed"),
        ],
        item_count=1,
    )
    service, _ = build_service([[album]])
    service.get_albums()

    initial_result = service.get_album_assets("album-1")
    refreshed_result = service.get_album_assets("album-1", force_refresh=True)

    assert initial_result["success"] is True
    assert refreshed_result == {
        "success": False,
        "album": None,
        "assets": [],
        "error": "Asset fetch failed",
    }
    assert service.get_cached_album_assets("album-1") == initial_result["assets"]


def test_album_cache_refresh_invalidates_loaded_asset_cache():
    first_album = FakeAlbum(
        "album-1",
        "Trips",
        [[FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image")]],
        item_count=1,
    )
    refreshed_album = FakeAlbum(
        "album-1",
        "Trips",
        [[FakeAsset(id="asset-2", filename="IMG_0002.HEIC", media_type="image")]],
        item_count=1,
    )
    service, photos = build_service([[first_album], [refreshed_album]])

    service.get_albums()
    service.get_album_assets("album-1")
    assert service.get_cached_album_assets("album-1")[0]["asset_id"] == "asset-1"

    service.get_albums(force_refresh=True)

    assert photos.request_count == 2
    assert service.get_cached_album_assets("album-1") is None

    reloaded_result = service.get_album_assets("album-1")

    assert reloaded_result["assets"][0]["asset_id"] == "asset-2"
    assert first_album.asset_request_count == 1
    assert refreshed_album.asset_request_count == 1


def test_get_assets_for_album_ids_dedupes_selection_and_preserves_membership_order():
    shared_asset_album_one = FakeAsset(
        id="shared-1",
        filename="IMG_SHARED.HEIC",
        media_type="image",
    )
    shared_asset_album_two = FakeAsset(
        id="shared-1",
        filename="IMG_SHARED.HEIC",
        media_type="image",
    )
    unique_asset = FakeAsset(id="asset-2", filename="IMG_0002.HEIC", media_type="image")
    album_one = FakeAlbum("album-1", "Trips", [[shared_asset_album_one]], item_count=1)
    album_two = FakeAlbum(
        "album-2",
        "Favorites",
        [[shared_asset_album_two, unique_asset]],
        item_count=2,
    )
    service, _ = build_service([[album_one, album_two]])
    service.get_albums()

    result = service.get_assets_for_album_ids(["album-2", "album-1", "album-2"])

    assert result["success"] is True
    assert result["selected_album_ids"] == ["album-2", "album-1"]
    assert len(result["assets"]) == 2

    shared_asset = next(asset for asset in result["assets"] if asset["asset_id"] == "shared-1")
    assert shared_asset["album_memberships"] == [
        {
            "album_id": "album-2",
            "album_name": "Favorites",
            "selection_order": 0,
        },
        {
            "album_id": "album-1",
            "album_name": "Trips",
            "selection_order": 1,
        },
    ]
    assert album_one.asset_request_count == 1
    assert album_two.asset_request_count == 1


def test_start_sort_forces_fresh_asset_refresh_for_selected_albums_only(tmp_path):
    (tmp_path / "IMG_0002.HEIC").write_text("asset-2", encoding="utf-8")
    album_one = FakeAlbum(
        "album-1",
        "Trips",
        [
            [FakeAsset(id="asset-1", filename="IMG_0001.HEIC", media_type="image")],
            [FakeAsset(id="asset-2", filename="IMG_0002.HEIC", media_type="image")],
        ],
        item_count=1,
    )
    album_two = FakeAlbum(
        "album-2",
        "Favorites",
        [[FakeAsset(id="asset-9", filename="IMG_1000.HEIC", media_type="image")]],
        item_count=1,
    )
    service, _ = build_service([[album_one, album_two]])
    service.settings_service = FakeSettingsService(tmp_path)
    service.get_albums()

    service.get_album_assets("album-1")
    service.get_album_assets("album-2")

    result = service.start_sort(["album-1"])
    service.get_sort_progress(result["job_id"])
    matching_progress = service.get_sort_progress(result["job_id"])

    assert matching_progress["status"] == "matching"
    assert matching_progress["total"] == 1
    assert matching_progress["match_results"] == {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }
    assert album_one.asset_request_count == 2
    assert album_two.asset_request_count == 1
    assert service.jobs[result["job_id"]]["selected_assets"] == [
        {
            "asset_id": "asset-2",
            "filename": "IMG_0002.HEIC",
            "original_filename": "IMG_0002.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-1",
                    "album_name": "Trips",
                    "selection_order": 0,
                }
            ],
        }
    ]

    running_progress = service.get_sort_progress(result["job_id"])

    assert running_progress["status"] == "running"
    assert running_progress["match_results"] == {
        "matched": 1,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }
    assert service.jobs[result["job_id"]]["match_results"]["assets"] == [
        {
            "asset_id": "asset-2",
            "filename": "IMG_0002.HEIC",
            "original_filename": "IMG_0002.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-1",
                    "album_name": "Trips",
                    "selection_order": 0,
                }
            ],
            "local_path": str(tmp_path / "IMG_0002.HEIC"),
            "match_type": "exact",
        }
    ]
