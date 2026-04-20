from app.icloud.albums_service import AlbumsService
from app.icloud.icloud_service import DEFAULT_MOCK_SORT_TOTAL, ICloudService


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


def test_start_sort_creates_job_and_filters_selected_albums():
    service = ICloudService(api=None)
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            },
            {
                "id": "album-2",
                "name": "Screenshots",
                "item_count": 89,
                "is_system_album": False,
            },
        ],
    )

    result = service.start_sort(["album-1", "album-2", "album-1", None, "missing"])

    assert "job_id" in result

    job = service.jobs[result["job_id"]]
    assert job["status"] == "running"
    assert job["processed"] == 0
    assert job["total"] == DEFAULT_MOCK_SORT_TOTAL
    assert job["percent"] == 0
    assert job["selected_album_ids"] == ["album-1", "album-2"]
    assert job["selected_albums"] == ["Vacation 2025", "Screenshots"]
    assert job["message"] == "Starting sort for 2 album(s)..."


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
    seed_album_cache(
        service,
        [
            {
                "id": "album-1",
                "name": "Vacation 2025",
                "item_count": 156,
                "is_system_album": False,
            }
        ],
    )
    job_id = service.start_sort(["album-1"])["job_id"]

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
