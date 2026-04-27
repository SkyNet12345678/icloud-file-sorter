import json

from app.state.sort_state import (
    SCHEMA_VERSION,
    SORT_STATE_FILENAME,
    SortStateStore,
    clean_missing_tracked_copy_paths,
    create_asset_state,
    create_job_state,
    default_sort_state,
    get_existing_tracked_copy_paths,
)


def test_sort_state_default_schema_includes_job_and_asset_tracking_fields():
    state = default_sort_state()
    job = create_job_state(
        "job-1",
        selected_albums=[{"id": "album-1", "name": "Trips"}],
        source_folder="C:/Users/me/Pictures/iCloud Photos",
        sorting_approach="copy",
        album_folder_mappings={"album-1": {"folder_name": "Trips"}},
        now="2026-04-27T00:00:00+00:00",
    )
    asset = create_asset_state(
        "asset-1",
        filename="IMG_0001.HEIC",
        album_memberships=[{"album_id": "album-1", "album_name": "Trips"}],
        status="copied",
        canonical_path="C:/Photos/IMG_0001.HEIC",
        moved_path="C:/Photos/Trips/IMG_0001.HEIC",
        app_created_copy_paths=["C:/Photos/Trips/IMG_0001.HEIC"],
        error=None,
        now="2026-04-27T00:00:00+00:00",
    )

    state["active_job_id"] = "job-1"
    state["jobs"]["job-1"] = job
    state["processed_assets"]["asset-1"] = asset

    assert state["schema_version"] == SCHEMA_VERSION
    assert job["selected_albums"] == [{"id": "album-1", "name": "Trips"}]
    assert job["album_folder_mappings"] == {"album-1": {"folder_name": "Trips"}}
    assert asset["status"] == "copied"
    assert asset["canonical_path"] == "C:/Photos/IMG_0001.HEIC"
    assert asset["moved_path"] == "C:/Photos/Trips/IMG_0001.HEIC"
    assert asset["app_created_copy_paths"] == ["C:/Photos/Trips/IMG_0001.HEIC"]
    assert asset["error"] is None


def test_sort_state_store_saves_with_atomic_temp_replace_and_loads(tmp_path):
    store = SortStateStore(app_data_dir=tmp_path)
    state = default_sort_state()
    state["jobs"]["job-1"] = create_job_state("job-1")

    assert store.save(state) is True

    saved_file = tmp_path / SORT_STATE_FILENAME
    assert saved_file.exists()
    assert not list(tmp_path.glob("*.tmp"))
    saved_data = json.loads(saved_file.read_text(encoding="utf-8"))
    assert saved_data["schema_version"] == SCHEMA_VERSION
    assert saved_data["updated_at"] is not None
    assert store.load()["jobs"]["job-1"]["job_id"] == "job-1"


def test_sort_state_store_uses_settings_app_data_dir(tmp_path):
    class FakeSettingsService:
        def get_app_data_dir(self):
            return tmp_path / "app-data"

    store = SortStateStore(settings_service=FakeSettingsService())

    assert store.state_file == tmp_path / "app-data" / SORT_STATE_FILENAME


def test_sort_state_load_treats_missing_malformed_or_wrong_schema_as_empty(tmp_path):
    store = SortStateStore(app_data_dir=tmp_path)

    assert store.load() == default_sort_state()

    store.state_file.write_text("not json", encoding="utf-8")
    assert store.load() == default_sort_state()

    store.state_file.write_text(
        json.dumps({"schema_version": SCHEMA_VERSION + 1, "jobs": {"job": {}}}),
        encoding="utf-8",
    )
    assert store.load() == default_sort_state()


def test_stale_paths_are_advisory_and_missing_copy_paths_can_be_cleaned(tmp_path):
    existing_copy = tmp_path / "Trips" / "IMG_0001.HEIC"
    existing_copy.parent.mkdir()
    existing_copy.write_text("copy", encoding="utf-8")
    missing_copy = tmp_path / "Missing" / "IMG_0001.HEIC"
    missing_canonical = tmp_path / "IMG_0001.HEIC"
    state = default_sort_state()
    state["processed_assets"]["asset-1"] = create_asset_state(
        "asset-1",
        canonical_path=str(missing_canonical),
        moved_path=str(missing_canonical),
        app_created_copy_paths=[str(existing_copy), str(missing_copy)],
    )

    cleaned = clean_missing_tracked_copy_paths(state)

    assert cleaned["processed_assets"]["asset-1"]["canonical_path"] == str(missing_canonical)
    assert cleaned["processed_assets"]["asset-1"]["moved_path"] == str(missing_canonical)
    assert cleaned["processed_assets"]["asset-1"]["app_created_copy_paths"] == [
        str(existing_copy)
    ]
    assert get_existing_tracked_copy_paths(state) == {str(existing_copy)}
