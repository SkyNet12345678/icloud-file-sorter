from app.sorting.multi_album import plan_album_file_operations, plan_sort_operations


def test_first_behavior_moves_to_first_selected_album_folder(tmp_path):
    asset = matched_asset(
        tmp_path / "IMG_SHARED.HEIC",
        [
            {"album_id": "album-2", "album_name": "Favorites", "selection_order": 1},
            {"album_id": "album-1", "album_name": "Trips", "selection_order": 0},
        ],
    )
    mappings = album_mappings(tmp_path)

    operations = plan_album_file_operations(asset, mappings, sorting_approach="first")

    assert operations == [
        {
            "asset_id": "asset-1",
            "filename": "IMG_SHARED.HEIC",
            "album_id": "album-1",
            "album_name": "Trips",
            "operation": "move",
            "source_path": str(tmp_path / "IMG_SHARED.HEIC"),
            "destination_path": str(tmp_path / "Trips" / "IMG_SHARED.HEIC"),
            "status": "planned",
            "error": None,
        }
    ]


def test_copy_behavior_copies_to_every_selected_album_folder(tmp_path):
    asset = matched_asset(
        tmp_path / "IMG_SHARED.HEIC",
        [
            {"album_id": "album-2", "album_name": "Favorites", "selection_order": 1},
            {"album_id": "album-1", "album_name": "Trips", "selection_order": 0},
        ],
    )
    mappings = album_mappings(tmp_path)

    operations = plan_album_file_operations(asset, mappings, sorting_approach="copy")

    assert [operation["operation"] for operation in operations] == ["copy", "copy"]
    assert [operation["album_id"] for operation in operations] == ["album-1", "album-2"]
    assert [operation["destination_path"] for operation in operations] == [
        str(tmp_path / "Trips" / "IMG_SHARED.HEIC"),
        str(tmp_path / "Favorites" / "IMG_SHARED.HEIC"),
    ]
    assert operations[0]["source_path"] == str(tmp_path / "IMG_SHARED.HEIC")


def test_single_album_selection_keeps_configured_behavior(tmp_path):
    asset = matched_asset(
        tmp_path / "IMG_0001.HEIC",
        [{"album_id": "album-1", "album_name": "Trips", "selection_order": 0}],
    )

    first_operations = plan_album_file_operations(
        asset,
        album_mappings(tmp_path),
        sorting_approach="first",
    )
    copy_operations = plan_album_file_operations(
        asset,
        album_mappings(tmp_path),
        sorting_approach="copy",
    )

    assert [operation["operation"] for operation in first_operations] == ["move"]
    assert [operation["operation"] for operation in copy_operations] == ["copy"]


def test_empty_or_unmapped_album_selection_plans_no_operations(tmp_path):
    asset = matched_asset(tmp_path / "IMG_0001.HEIC", [])

    assert plan_album_file_operations(asset, album_mappings(tmp_path)) == []

    unmapped_asset = matched_asset(
        tmp_path / "IMG_0001.HEIC",
        [{"album_id": "missing", "album_name": "Missing", "selection_order": 0}],
    )
    assert plan_album_file_operations(unmapped_asset, album_mappings(tmp_path)) == []


def test_sort_operation_planning_skips_unmatched_and_ambiguous_assets(tmp_path):
    exact_asset = matched_asset(
        tmp_path / "IMG_0001.HEIC",
        [{"album_id": "album-1", "album_name": "Trips", "selection_order": 0}],
    )
    unmatched_asset = dict(exact_asset, asset_id="asset-2", match_type="none")
    ambiguous_asset = dict(exact_asset, asset_id="asset-3", match_type="ambiguous")

    operations = plan_sort_operations(
        [unmatched_asset, ambiguous_asset, exact_asset],
        album_mappings(tmp_path),
    )

    assert len(operations) == 1
    assert operations[0]["asset_id"] == "asset-1"


def matched_asset(local_path, memberships):
    return {
        "asset_id": "asset-1",
        "filename": local_path.name,
        "original_filename": local_path.name,
        "album_memberships": memberships,
        "local_path": str(local_path),
        "match_type": "exact",
    }


def album_mappings(tmp_path):
    return {
        "album-1": {
            "album_id": "album-1",
            "album_name": "Trips",
            "folder_path": str(tmp_path / "Trips"),
        },
        "album-2": {
            "album_id": "album-2",
            "album_name": "Favorites",
            "folder_path": str(tmp_path / "Favorites"),
        },
    }
