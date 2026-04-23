from pathlib import Path
from types import SimpleNamespace

from app import settings as settings_module
from app.icloud.albums_service import AlbumsService
from app.icloud.icloud_service import DEFAULT_MOCK_SORT_TOTAL, ICloudService
from app.settings import SettingsService


class FakeSettingsService:
    def __init__(self, source_folder):
        self.source_folder = source_folder

    def get_source_folder(self):
        return self.source_folder


class FakeAsset:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeAlbum:
    def __init__(self, album_id, name, assets):
        self.id = album_id
        self.name = name
        self.fullname = name
        self._assets = list(assets)
        self.asset_request_count = 0

    def __len__(self):
        return len(self._assets)

    @property
    def assets(self):
        self.asset_request_count += 1
        return list(self._assets)


def seed_album_cache(service, albums):
    service.album_cache_loaded = True
    service.album_list_cache = [dict(album) for album in albums]
    service.album_summaries_by_id = {
        album["id"]: dict(album)
        for album in albums
    }
    service.raw_albums_by_id = {
        album["id"]: object()
        for album in albums
    }


def seed_raw_albums(service, *raw_albums):
    service.raw_albums_by_id = {
        album.id: album
        for album in raw_albums
    }


def test_get_albums_keeps_album_browsing_lightweight():
    album = FakeAlbum(
        "album-1",
        "Vacation 2025",
        [FakeAsset(id="asset-1", filename="IMG_001.HEIC", media_type="image")],
    )
    service = ICloudService(api=SimpleNamespace(photos=SimpleNamespace(albums=[album])))

    result = service.get_albums()

    assert result["success"] is True
    assert result["albums"] == [
        {
            "id": "album-1",
            "name": "Vacation 2025",
            "item_count": 1,
            "is_system_album": False,
        }
    ]
    assert album.asset_request_count == 0


def test_start_sort_creates_matching_job_before_loading_assets(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
    (tmp_path / "IMG_001.HEIC").write_text("asset-1", encoding="utf-8")
    album_one = FakeAlbum(
        "album-1",
        "Vacation 2025",
        [FakeAsset(id="asset-1", filename="IMG_001.HEIC", media_type="image")],
    )
    album_two = FakeAlbum(
        "album-2",
        "Screenshots",
        [FakeAsset(id="asset-2", filename="IMG_002.HEIC", media_type="image")],
    )
    album_three = FakeAlbum(
        "album-3",
        "Unselected",
        [FakeAsset(id="asset-3", filename="IMG_003.HEIC", media_type="image")],
    )
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 1,
                "is_system_album": False,
            },
            {
                "id": "album-2",
                "name": "Screenshots",
                "item_count": 1,
                "is_system_album": False,
            },
            {
                "id": "album-3",
                "name": "Unselected",
                "item_count": 1,
                "is_system_album": False,
            },
        ],
    )
    seed_raw_albums(service, album_one, album_two, album_three)

    result = service.start_sort(["album-1", "album-2", "album-1", None, "missing"])

    assert "job_id" in result

    job = service.jobs[result["job_id"]]
    assert job["status"] == "matching"
    assert job["processed"] == 0
    assert job["total"] == 0
    assert job["percent"] == 0
    assert job["selected_album_ids"] == ["album-1", "album-2"]
    assert job["selected_albums"] == ["Vacation 2025", "Screenshots"]
    assert job["source_folder"] == str(tmp_path)
    assert job["selected_assets"] == []
    assert job["matched_assets"] == []
    assert job["match_results"] == {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
        "assets": [],
    }
    assert job["message"] == "Preparing matching job..."
    assert album_one.asset_request_count == 0
    assert album_two.asset_request_count == 0
    assert album_three.asset_request_count == 0

    initial_matching_progress = service.get_sort_progress(result["job_id"])

    assert initial_matching_progress == {
        "job_id": result["job_id"],
        "status": "matching",
        "processed": 0,
        "total": 0,
        "percent": 0,
        "message": "Preparing matching job...",
        "match_results": {
            "matched": 0,
            "fallback_matched": 0,
            "not_found": 0,
            "ambiguous": 0,
        },
    }
    assert album_one.asset_request_count == 0
    assert album_two.asset_request_count == 0
    assert album_three.asset_request_count == 0

    prepared_matching_progress = service.get_sort_progress(result["job_id"])

    assert prepared_matching_progress == {
        "job_id": result["job_id"],
        "status": "matching",
        "processed": 0,
        "total": 2,
        "percent": 0,
        "message": "Fetched iCloud metadata for 2 assets. Matching local files...",
        "match_results": {
            "matched": 0,
            "fallback_matched": 0,
            "not_found": 0,
            "ambiguous": 0,
        },
    }
    assert len(service.jobs[result["job_id"]]["selected_assets"]) == 2
    assert album_one.asset_request_count == 1
    assert album_two.asset_request_count == 1
    assert album_three.asset_request_count == 0

    running_progress = service.get_sort_progress(result["job_id"])

    assert running_progress == {
        "job_id": result["job_id"],
        "status": "running",
        "processed": 0,
        "total": DEFAULT_MOCK_SORT_TOTAL,
        "percent": 0,
        "message": (
            "Starting sort for 2 album(s). "
            "Filename-only matching: Exact: 1 | Not found: 1 | Ambiguous: 0"
        ),
        "match_results": {
            "matched": 1,
            "fallback_matched": 0,
            "not_found": 1,
            "ambiguous": 0,
        },
    }
    assert service.jobs[result["job_id"]]["matched_assets"] == [
        {
            "asset_id": "asset-1",
            "filename": "IMG_001.HEIC",
            "original_filename": "IMG_001.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-1",
                    "album_name": "Vacation 2025",
                    "selection_order": 0,
                }
            ],
            "local_path": str(tmp_path / "IMG_001.HEIC"),
            "match_type": "exact",
        },
        {
            "asset_id": "asset-2",
            "filename": "IMG_002.HEIC",
            "original_filename": "IMG_002.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-2",
                    "album_name": "Screenshots",
                    "selection_order": 1,
                }
            ],
            "local_path": None,
            "match_type": "none",
        },
    ]
    assert service.jobs[result["job_id"]]["matched_assets"] == service.jobs[
        result["job_id"]
    ]["match_results"]["assets"]


def test_get_sort_progress_does_not_start_duplicate_asset_fetch_while_matching(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
    album = FakeAlbum(
        "album-1",
        "Vacation 2025",
        [FakeAsset(id="asset-1", filename="IMG_001.HEIC", media_type="image")],
    )
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 1,
                "is_system_album": False,
            },
        ],
    )
    seed_raw_albums(service, album)

    result = service.start_sort(["album-1"])
    service.get_sort_progress(result["job_id"])
    service.jobs[result["job_id"]]["_matching_fetch_in_progress"] = True

    progress = service.get_sort_progress(result["job_id"])

    assert progress["status"] == "matching"
    assert progress["message"] == "Preparing matching job..."
    assert album.asset_request_count == 0


def test_start_sort_aggregates_overlapping_album_assets_into_one_job_entry(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
    shared_local_file = tmp_path / "IMG_SHARED.HEIC"
    unique_local_file = tmp_path / "IMG_0002.HEIC"
    shared_local_file.write_text("shared", encoding="utf-8")
    unique_local_file.write_text("unique", encoding="utf-8")
    album_one = FakeAlbum(
        "album-1",
        "Trips",
        [FakeAsset(id="shared-1", filename="IMG_SHARED.HEIC", media_type="image")],
    )
    album_two = FakeAlbum(
        "album-2",
        "Favorites",
        [
            FakeAsset(id="shared-1", filename="IMG_SHARED.HEIC", media_type="image"),
            FakeAsset(id="asset-2", filename="IMG_0002.HEIC", media_type="image"),
        ],
    )
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Trips",
                "item_count": 1,
                "is_system_album": False,
            },
            {
                "id": "album-2",
                "name": "Favorites",
                "item_count": 2,
                "is_system_album": False,
            },
        ],
    )
    seed_raw_albums(service, album_one, album_two)

    result = service.start_sort(["album-2", "album-1"])
    service.get_sort_progress(result["job_id"])
    service.get_sort_progress(result["job_id"])

    shared_asset = next(
        asset
        for asset in service.jobs[result["job_id"]]["selected_assets"]
        if asset["asset_id"] == "shared-1"
    )

    assert len(service.jobs[result["job_id"]]["selected_assets"]) == 2
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

    running_progress = service.get_sort_progress(result["job_id"])

    assert running_progress["match_results"] == {
        "matched": 2,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }
    assert service.jobs[result["job_id"]]["matched_assets"] == [
        {
            "asset_id": "shared-1",
            "filename": "IMG_SHARED.HEIC",
            "original_filename": "IMG_SHARED.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
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
            ],
            "local_path": str(shared_local_file),
            "match_type": "exact",
        },
        {
            "asset_id": "asset-2",
            "filename": "IMG_0002.HEIC",
            "original_filename": "IMG_0002.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-2",
                    "album_name": "Favorites",
                    "selection_order": 0,
                }
            ],
            "local_path": str(unique_local_file),
            "match_type": "exact",
        },
    ]
    assert service.jobs[result["job_id"]]["matched_assets"] == service.jobs[
        result["job_id"]
    ]["match_results"]["assets"]


def test_get_sort_progress_excludes_selected_assets_from_polling_payload(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
    album = FakeAlbum(
        "album-1",
        "Vacation 2025",
        [FakeAsset(id="asset-1", filename="IMG_001.HEIC", media_type="image")],
    )
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 1,
                "is_system_album": False,
            },
        ],
    )
    seed_raw_albums(service, album)

    result = service.start_sort(["album-1"])
    service.get_sort_progress(result["job_id"])
    progress = service.get_sort_progress(result["job_id"])

    assert set(progress) == {
        "job_id",
        "status",
        "processed",
        "total",
        "percent",
        "message",
        "match_results",
    }
    assert "selected_assets" not in progress
    assert "matched_assets" not in progress
    assert progress["match_results"] == {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }
    assert len(service.jobs[result["job_id"]]["selected_assets"]) == 1


def test_get_sort_progress_returns_error_for_unknown_job():
    service = ICloudService(api=None)

    result = service.get_sort_progress("missing-job")

    assert result == {
        "job_id": "missing-job",
        "status": "error",
        "processed": 0,
        "total": 0,
        "percent": 0,
        "message": "Unknown job id",
    }


def test_get_sort_progress_advances_running_job():
    service = ICloudService(api=None)
    job_id = "job-1"
    service.jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "processed": 0,
        "total": DEFAULT_MOCK_SORT_TOTAL,
        "percent": 0,
        "selected_albums": ["Vacation 2025"],
        "message": "Starting sort for 1 album(s)...",
    }

    result = service.get_sort_progress(job_id)

    assert result["job_id"] == job_id
    assert result["status"] == "running"
    assert result["processed"] == 50
    assert result["percent"] == 2
    assert result["message"] == (
        f"Processing photo 50 of {DEFAULT_MOCK_SORT_TOTAL}. "
        "Filename-only matching: Exact: 0 | Not found: 0 | Ambiguous: 0"
    )
    assert result["match_results"] == {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }


def test_get_sort_progress_marks_job_complete_when_total_is_reached():
    service = ICloudService(api=None)
    job_id = "job-1"
    service.jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "processed": 1800,
        "total": DEFAULT_MOCK_SORT_TOTAL,
        "percent": 97,
        "selected_albums": ["Vacation 2025"],
        "message": "Processing photo 1800 of 1847",
    }

    result = service.get_sort_progress(job_id)

    assert result["status"] == "complete"
    assert result["processed"] == DEFAULT_MOCK_SORT_TOTAL
    assert result["percent"] == 100
    assert result["message"] == (
        "Sort complete. Filename-only matching: Exact: 0 | Not found: 0 | Ambiguous: 0"
    )
    assert result["match_results"] == {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
    }


def test_running_progress_message_keeps_filename_only_match_quality_visible(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
    (tmp_path / "IMG_001.HEIC").write_text("asset-1", encoding="utf-8")
    duplicate_dir = tmp_path / "duplicates"
    duplicate_dir.mkdir()
    (duplicate_dir / "IMG_002.HEIC").write_text("a", encoding="utf-8")
    second_duplicate_dir = tmp_path / "duplicates-2"
    second_duplicate_dir.mkdir()
    (second_duplicate_dir / "img_002.heic").write_text("b", encoding="utf-8")
    album = FakeAlbum(
        "album-1",
        "Vacation 2025",
        [
            FakeAsset(id="asset-1", filename="IMG_001.HEIC", media_type="image"),
            FakeAsset(id="asset-2", filename="IMG_002.HEIC", media_type="image"),
            FakeAsset(id="asset-3", filename="IMG_404.HEIC", media_type="image"),
        ],
    )
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 3,
                "is_system_album": False,
            },
        ],
    )
    seed_raw_albums(service, album)

    result = service.start_sort(["album-1"])
    service.get_sort_progress(result["job_id"])
    service.get_sort_progress(result["job_id"])

    running_progress = service.get_sort_progress(result["job_id"])

    assert running_progress["message"] == (
        "Starting sort for 1 album(s). "
        "Filename-only matching: Exact: 1 | Not found: 1 | Ambiguous: 1"
    )
    follow_up_progress = service.get_sort_progress(result["job_id"])
    assert follow_up_progress["message"] == (
        f"Processing photo 50 of {DEFAULT_MOCK_SORT_TOTAL}. "
        "Filename-only matching: Exact: 1 | Not found: 1 | Ambiguous: 1"
    )


def test_start_sort_returns_error_when_album_cache_is_cold():
    service = ICloudService(api=None)

    result = service.start_sort(["album-1"])

    assert result == {"error": "Album cache not loaded"}


def test_albums_service_start_sort_returns_error_without_icloud():
    service = AlbumsService(icloud_api=None)
    service.icloud = None

    result = service.start_sort(["album-1", "album-2"])

    assert result == {"error": "Sorting service unavailable"}


def test_albums_service_get_sort_progress_returns_error_without_icloud():
    service = AlbumsService(icloud_api=None)
    service.icloud = None

    result = service.get_sort_progress("job-1")

    assert result == {
        "job_id": "job-1",
        "status": "error",
        "processed": 0,
        "total": 0,
        "percent": 0,
        "message": "Sorting service unavailable",
    }


def test_albums_service_get_album_assets_delegates_correctly():
    service = AlbumsService(icloud_api=None)
    mock_icloud = ICloudService(api=None)
    seed_album_cache(
        mock_icloud,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 2,
                "is_system_album": False,
            },
        ],
    )
    mock_icloud.asset_metadata_by_album_id["album-1"] = [
        {
            "asset_id": "a1",
            "filename": "IMG_001.HEIC",
            "original_filename": "IMG_001.HEIC",
            "created_at": None,
            "size": 1000,
            "media_type": "image",
            "album_id": "album-1",
            "album_name": "Vacation 2025",
        },
    ]
    mock_icloud.asset_cache_loaded_album_ids.add("album-1")
    service.icloud = mock_icloud

    result = service.get_album_assets("album-1")

    assert result["success"] is True
    assert result["album"]["id"] == "album-1"
    assert len(result["assets"]) == 1


def test_albums_service_get_album_assets_returns_error_without_icloud():
    service = AlbumsService(icloud_api=None)
    service.icloud = None

    result = service.get_album_assets("album-1")

    assert result == {
        "success": False,
        "album": None,
        "assets": [],
        "error": "Album service unavailable",
    }


def test_start_sort_returns_error_when_no_albums_selected():
    service = ICloudService(api=None, settings_service=FakeSettingsService(Path.cwd()))
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            },
        ],
    )

    result = service.start_sort([])

    assert result == {"error": "No albums selected"}


def test_start_sort_returns_clear_error_when_source_folder_is_not_configured():
    service = ICloudService(api=None, settings_service=FakeSettingsService(None))
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            },
        ],
    )

    result = service.start_sort(["album-1"])

    assert result == {
        "error": "Source folder is not configured. Choose your iCloud Photos folder in Settings before starting a sort."
    }


def test_start_sort_reports_stale_configured_source_folder_with_real_settings_service(
    tmp_path,
    monkeypatch,
):
    configured_source_folder = tmp_path / "missing-icloud-photos"
    detected_source_folder = tmp_path / "detected-icloud-photos"
    detected_source_folder.mkdir()
    settings_service = SettingsService(settings_dir=tmp_path / "settings")
    settings_service.set_source_folder(str(configured_source_folder))
    monkeypatch.setattr(
        settings_module,
        "WINDOWS_KNOWN_PATHS",
        [detected_source_folder],
    )
    service = ICloudService(api=None, settings_service=settings_service)
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            },
        ],
    )

    result = service.start_sort(["album-1"])

    expected_error = (
        "Configured source folder was not found. "
        "Update the source folder in Settings before starting a sort."
    )
    assert result == {"error": expected_error}
    assert settings_service.get_source_folder() == str(configured_source_folder)


def test_start_sort_returns_clear_error_when_source_folder_is_not_a_directory(tmp_path):
    source_file = tmp_path / "icloud-photos.txt"
    source_file.write_text("not a folder", encoding="utf-8")
    service = ICloudService(api=None, settings_service=FakeSettingsService(source_file))
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            },
        ],
    )

    result = service.start_sort(["album-1"])

    assert result == {
        "error": "Configured source folder is not a folder. Update the source folder in Settings before starting a sort."
    }
