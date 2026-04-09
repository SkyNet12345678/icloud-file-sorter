from app.icloud.albums_service import AlbumsService
from app.icloud.icloud_service import ICloudService


def test_start_sort_creates_job_and_filters_selected_albums():
    service = ICloudService(api=None)

    result = service.start_sort([0, 1, -1, 3, 999])

    assert "job_id" in result

    job = service.jobs[result["job_id"]]
    assert job["status"] == "running"
    assert job["processed"] == 0
    assert job["total"] == 1847
    assert job["percent"] == 0
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
    job_id = service.start_sort([1])["job_id"]

    result = service.get_sort_progress(job_id)

    assert result["job_id"] == job_id
    assert result["status"] == "running"
    assert result["processed"] == 50
    assert result["percent"] == 2
    assert result["message"] == "Processing photo 50 of 1847"


def test_get_sort_progress_marks_job_complete_when_total_is_reached():
    service = ICloudService(api=None)
    job_id = "job-1"
    service.jobs[job_id] = {
        "job_id": job_id,
        "status": "running",
        "processed": 1800,
        "total": 1847,
        "percent": 97,
        "selected_albums": ["Vacation 2025"],
        "message": "Processing photo 1800 of 1847",
    }

    result = service.get_sort_progress(job_id)

    assert result["status"] == "complete"
    assert result["processed"] == 1847
    assert result["percent"] == 100
    assert result["message"] == "Sort complete"


def test_albums_service_start_sort_returns_error_without_icloud():
    service = AlbumsService(icloud_api=None)
    service.icloud = None

    result = service.start_sort([1, 2])

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
