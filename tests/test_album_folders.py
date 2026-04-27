from app.sorting.album_folders import (
    MAX_FOLDER_NAME_LENGTH,
    build_album_folder_mappings,
    persist_album_folder_mappings,
    sanitize_album_folder_name,
)
from app.state.sort_state import SortStateStore, default_sort_state


def test_sanitize_album_folder_name_handles_windows_unsafe_names():
    assert sanitize_album_folder_name('Trip <2025>: "Beach" / Day? *') == (
        "Trip _2025__ _Beach_ _ Day_ _"
    )
    assert sanitize_album_folder_name("Vacation. ") == "Vacation"
    assert sanitize_album_folder_name("CON") == "_CON"
    assert sanitize_album_folder_name("con.txt") == "_con.txt"
    assert sanitize_album_folder_name("   ") == "Album"


def test_sanitize_album_folder_name_truncates_overly_long_names():
    long_name = "A" * (MAX_FOLDER_NAME_LENGTH + 20)

    sanitized = sanitize_album_folder_name(long_name)

    assert sanitized == "A" * MAX_FOLDER_NAME_LENGTH
    assert len(sanitized) == MAX_FOLDER_NAME_LENGTH


def test_build_album_folder_mappings_dedupes_duplicate_sanitized_names(tmp_path):
    mappings = build_album_folder_mappings(
        tmp_path,
        [
            {"id": "album-1", "name": "Trips"},
            {"id": "album-2", "name": "Trips"},
            {"id": "album-3", "name": "Trips?"},
            {"id": "album-4", "name": "Trips*"},
        ],
    )

    assert mappings["album-1"]["folder_name"] == "Trips"
    assert mappings["album-2"]["folder_name"] == "Trips (2)"
    assert mappings["album-3"]["folder_name"] == "Trips_"
    assert mappings["album-4"]["folder_name"] == "Trips_ (2)"
    assert mappings["album-2"]["folder_path"] == str(tmp_path / "Trips (2)")


def test_build_album_folder_mappings_preserves_existing_album_id_mapping(tmp_path):
    existing = {
        "album-1": {
            "album_id": "album-1",
            "album_name": "Old Name",
            "folder_name": "Old Name",
            "folder_path": str(tmp_path / "Old Name"),
        }
    }

    mappings = build_album_folder_mappings(
        tmp_path,
        [
            {"id": "album-2", "name": "Trips"},
            {"id": "album-1", "name": "Renamed Trips"},
        ],
        existing_mappings=existing,
    )

    assert mappings["album-1"]["folder_name"] == "Old Name"
    assert mappings["album-1"]["folder_path"] == str(tmp_path / "Old Name")
    assert mappings["album-1"]["album_name"] == "Renamed Trips"
    assert mappings["album-2"]["folder_name"] == "Trips"


def test_build_album_folder_mappings_reserves_unselected_existing_mappings(tmp_path):
    existing = {
        "album-1": {
            "album_id": "album-1",
            "album_name": "Trips",
            "folder_name": "Trips",
            "folder_path": str(tmp_path / "Trips"),
        }
    }

    mappings = build_album_folder_mappings(
        tmp_path,
        [{"id": "album-2", "name": "Trips"}],
        existing_mappings=existing,
    )

    assert mappings["album-2"]["folder_name"] == "Trips (2)"
    assert mappings["album-2"]["folder_path"] == str(tmp_path / "Trips (2)")


def test_album_folder_mappings_persist_in_sort_state(tmp_path):
    store = SortStateStore(app_data_dir=tmp_path)
    state = default_sort_state()
    mappings = build_album_folder_mappings(
        tmp_path,
        [{"id": "album-1", "name": "Trips"}],
    )

    state = persist_album_folder_mappings(state, mappings)

    assert store.save(state) is True
    reloaded = store.load()
    assert reloaded["album_folder_mappings"]["album-1"]["folder_name"] == "Trips"
    assert reloaded["album_folder_mappings"]["album-1"]["folder_path"] == str(
        tmp_path / "Trips"
    )


def test_album_folder_mappings_persist_merges_existing_mappings(tmp_path):
    state = default_sort_state()
    state["album_folder_mappings"] = {
        "album-1": {
            "album_id": "album-1",
            "album_name": "Trips",
            "folder_name": "Trips",
            "folder_path": str(tmp_path / "Trips"),
        }
    }
    mappings = build_album_folder_mappings(
        tmp_path,
        [{"id": "album-2", "name": "Trips"}],
        existing_mappings=state["album_folder_mappings"],
    )

    state = persist_album_folder_mappings(state, mappings)

    assert state["album_folder_mappings"]["album-1"]["folder_name"] == "Trips"
    assert state["album_folder_mappings"]["album-2"]["folder_name"] == "Trips (2)"
