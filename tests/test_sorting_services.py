from pathlib import Path
from types import SimpleNamespace

from app.icloud.albums_service import AlbumsService
from app.icloud.icloud_service import DEFAULT_MOCK_SORT_TOTAL, ICloudService


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


def test_start_sort_fetches_selected_album_assets_only_and_enters_matching(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
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
    assert job["total"] == 2
    assert job["percent"] == 0
    assert job["selected_album_ids"] == ["album-1", "album-2"]
    assert job["selected_albums"] == ["Vacation 2025", "Screenshots"]
    assert job["source_folder"] == str(tmp_path)
    assert len(job["selected_assets"]) == 2
    assert job["message"] == "Fetched iCloud metadata for 2 assets. Matching local files..."
    assert album_one.asset_request_count == 1
    assert album_two.asset_request_count == 1
    assert album_three.asset_request_count == 0

    matching_progress = service.get_sort_progress(result["job_id"])

    assert matching_progress["status"] == "matching"
    assert matching_progress["total"] == 2
    assert matching_progress["message"] == "Fetched iCloud metadata for 2 assets. Matching local files..."


def test_start_sort_aggregates_overlapping_album_assets_into_one_job_entry(tmp_path):
    service = ICloudService(api=None, settings_service=FakeSettingsService(tmp_path))
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
    assert result["message"] == f"Processing photo 50 of {DEFAULT_MOCK_SORT_TOTAL}"


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
    assert result["message"] == "Sort complete"


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
