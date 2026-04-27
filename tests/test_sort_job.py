import threading

from app.sorting.sort_job import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETE,
    JOB_STATUS_MATCHING,
    SortJobManager,
)
from app.state.sort_state import SortStateStore


def test_sort_job_moves_first_album_operation_and_summarizes_skips(tmp_path):
    source_file = tmp_path / "IMG_0001.HEIC"
    source_file.write_text("asset-1", encoding="utf-8")
    duplicate_dir = tmp_path / "duplicates"
    duplicate_dir.mkdir()
    (duplicate_dir / "IMG_DUP.HEIC").write_text("a", encoding="utf-8")
    (tmp_path / "IMG_DUP.HEIC").write_text("b", encoding="utf-8")
    manager = SortJobManager(
        state_store=SortStateStore(app_data_dir=tmp_path / "state"),
        run_async=False,
    )

    result = manager.start_job(
        job_id="job-1",
        selected_album_ids=["album-1", "album-2"],
        selected_albums=selected_albums(),
        source_folder=str(tmp_path),
        sorting_approach="first",
        asset_loader=lambda: asset_result(
            [
                asset("asset-1", "IMG_0001.HEIC", ["album-2", "album-1"]),
                asset("asset-2", "IMG_MISSING.HEIC", ["album-1"]),
                asset("asset-3", "IMG_DUP.HEIC", ["album-1"]),
            ]
        ),
    )

    progress = manager.get_progress(result["job_id"])

    assert progress["status"] == JOB_STATUS_COMPLETE
    assert progress["processed"] == 1
    assert progress["total"] == 1
    assert progress["percent"] == 100
    assert progress["match_results"] == {
        "matched": 1,
        "fallback_matched": 0,
        "not_found": 1,
        "ambiguous": 1,
    }
    assert progress["summary"]["moved"] == 1
    assert progress["summary"]["unmatched"] == 1
    assert progress["summary"]["skipped_ambiguous_match"] == 1
    assert not source_file.exists()
    assert (tmp_path / "Favorites" / "IMG_0001.HEIC").read_text(encoding="utf-8") == "asset-1"


def test_sort_job_copy_mode_preserves_source_and_tracks_created_copy_paths(tmp_path):
    source_file = tmp_path / "IMG_SHARED.HEIC"
    source_file.write_text("shared", encoding="utf-8")
    store = SortStateStore(app_data_dir=tmp_path / "state")
    manager = SortJobManager(state_store=store, run_async=False)

    manager.start_job(
        job_id="job-copy",
        selected_album_ids=["album-1", "album-2"],
        selected_albums=selected_albums(),
        source_folder=str(tmp_path),
        sorting_approach="copy",
        asset_loader=lambda: asset_result(
            [asset("asset-1", "IMG_SHARED.HEIC", ["album-1", "album-2"])]
        ),
    )

    progress = manager.get_progress("job-copy")
    state = store.load()
    copy_paths = state["processed_assets"]["asset-1"]["app_created_copy_paths"]

    assert progress["status"] == JOB_STATUS_COMPLETE
    assert progress["summary"]["copied"] == 2
    assert source_file.read_text(encoding="utf-8") == "shared"
    assert (tmp_path / "Trips" / "IMG_SHARED.HEIC").read_text(encoding="utf-8") == "shared"
    assert (tmp_path / "Favorites" / "IMG_SHARED.HEIC").read_text(encoding="utf-8") == "shared"
    assert copy_paths == [
        str(tmp_path / "Trips" / "IMG_SHARED.HEIC"),
        str(tmp_path / "Favorites" / "IMG_SHARED.HEIC"),
    ]

    manager.start_job(
        job_id="job-copy-rerun",
        selected_album_ids=["album-1", "album-2"],
        selected_albums=selected_albums(),
        source_folder=str(tmp_path),
        sorting_approach="copy",
        asset_loader=lambda: asset_result(
            [asset("asset-1", "IMG_SHARED.HEIC", ["album-1", "album-2"])]
        ),
    )

    rerun_progress = manager.get_progress("job-copy-rerun")
    rerun_state = store.load()

    assert rerun_progress["summary"]["already_copied"] == 2
    assert rerun_state["processed_assets"]["asset-1"]["app_created_copy_paths"] == copy_paths


def test_sort_job_cancel_stops_after_current_operation_and_persists_state(tmp_path):
    for index in range(3):
        (tmp_path / f"IMG_000{index}.HEIC").write_text(str(index), encoding="utf-8")

    manager = None

    def cancel_after_first_operation(job, _operation):
        manager.cancel_job(job["job_id"])

    store = SortStateStore(app_data_dir=tmp_path / "state")
    manager = SortJobManager(
        state_store=store,
        run_async=False,
        operation_callback=cancel_after_first_operation,
    )

    manager.start_job(
        job_id="job-cancel",
        selected_album_ids=["album-1"],
        selected_albums=selected_albums()[:1],
        source_folder=str(tmp_path),
        sorting_approach="first",
        asset_loader=lambda: asset_result(
            [
                asset(f"asset-{index}", f"IMG_000{index}.HEIC", ["album-1"])
                for index in range(3)
            ]
        ),
    )

    progress = manager.get_progress("job-cancel")
    state = store.load()

    assert progress["status"] == JOB_STATUS_CANCELLED
    assert progress["processed"] == 1
    assert progress["summary"]["remaining"] == 2
    assert state["jobs"]["job-cancel"]["status"] == JOB_STATUS_CANCELLED
    assert state["active_job_id"] is None
    assert (tmp_path / "Trips" / "IMG_0000.HEIC").exists()
    assert (tmp_path / "IMG_0001.HEIC").exists()


def test_sort_job_cancel_before_no_operation_plan_persists_cancelled_status(tmp_path):
    loader_called = threading.Event()
    release_loader = threading.Event()
    store = SortStateStore(app_data_dir=tmp_path / "state")
    manager = SortJobManager(state_store=store, run_async=True)

    def blocking_asset_loader():
        loader_called.set()
        release_loader.wait(timeout=2)
        return asset_result([asset("asset-1", "IMG_MISSING.HEIC", ["album-1"])])

    manager.start_job(
        job_id="job-cancel-before-plan",
        selected_album_ids=["album-1"],
        selected_albums=selected_albums()[:1],
        source_folder=str(tmp_path),
        sorting_approach="first",
        asset_loader=blocking_asset_loader,
    )
    assert loader_called.wait(timeout=2)

    manager.cancel_job("job-cancel-before-plan")
    release_loader.set()
    manager.wait_for_job("job-cancel-before-plan", timeout=2)

    progress = manager.get_progress("job-cancel-before-plan")
    state = store.load()

    assert progress["status"] == JOB_STATUS_CANCELLED
    assert progress["processed"] == 0
    assert progress["total"] == 0
    assert progress["summary"]["unmatched"] == 1
    assert state["jobs"]["job-cancel-before-plan"]["status"] == JOB_STATUS_CANCELLED
    assert state["active_job_id"] is None


def test_sort_job_start_is_non_blocking_when_running_async(tmp_path):
    (tmp_path / "IMG_0001.HEIC").write_text("asset-1", encoding="utf-8")
    loader_called = threading.Event()
    release_loader = threading.Event()
    manager = SortJobManager(run_async=True)

    def blocking_asset_loader():
        loader_called.set()
        release_loader.wait(timeout=2)
        return asset_result([asset("asset-1", "IMG_0001.HEIC", ["album-1"])])

    result = manager.start_job(
        job_id="job-async",
        selected_album_ids=["album-1"],
        selected_albums=selected_albums()[:1],
        source_folder=str(tmp_path),
        sorting_approach="first",
        asset_loader=blocking_asset_loader,
    )

    assert result == {"job_id": "job-async"}
    assert loader_called.wait(timeout=2)
    assert manager.get_progress("job-async")["status"] == JOB_STATUS_MATCHING

    release_loader.set()
    manager.wait_for_job("job-async", timeout=2)
    assert manager.get_progress("job-async")["status"] == JOB_STATUS_COMPLETE


def selected_albums():
    return [
        {"id": "album-1", "name": "Trips"},
        {"id": "album-2", "name": "Favorites"},
    ]


def asset(asset_id, filename, album_ids):
    return {
        "asset_id": asset_id,
        "filename": filename,
        "original_filename": filename,
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_memberships": [
            {
                "album_id": album_id,
                "album_name": "Trips" if album_id == "album-1" else "Favorites",
                "selection_order": index,
            }
            for index, album_id in enumerate(album_ids)
        ],
    }


def asset_result(assets):
    return {
        "success": True,
        "selected_album_ids": [],
        "assets": assets,
        "error": None,
    }
