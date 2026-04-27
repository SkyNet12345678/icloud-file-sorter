from __future__ import annotations

from pathlib import Path

SORTING_APPROACH_FIRST = "first"
SORTING_APPROACH_COPY = "copy"


def plan_album_file_operations(
    asset: dict,
    album_folder_mappings: dict,
    sorting_approach: str = SORTING_APPROACH_FIRST,
) -> list[dict]:
    """Build file operations for one matched asset and its selected albums."""
    filename = asset.get("filename") or asset.get("original_filename")
    source_path = asset.get("local_path")
    if not filename or not source_path:
        return []

    memberships = _ordered_mapped_memberships(
        asset.get("album_memberships", []),
        album_folder_mappings,
    )
    if not memberships:
        return []

    operation_type = SORTING_APPROACH_COPY if sorting_approach == SORTING_APPROACH_COPY else "move"
    target_memberships = memberships if operation_type == SORTING_APPROACH_COPY else memberships[:1]

    return [
        {
            "asset_id": asset.get("asset_id"),
            "filename": filename,
            "album_id": membership["album_id"],
            "album_name": membership.get("album_name"),
            "operation": operation_type,
            "source_path": str(source_path),
            "destination_path": str(Path(membership["folder_path"]) / filename),
            "status": "planned",
            "error": None,
        }
        for membership in target_memberships
    ]


def plan_sort_operations(
    matched_assets: list[dict],
    album_folder_mappings: dict,
    sorting_approach: str = SORTING_APPROACH_FIRST,
) -> list[dict]:
    operations: list[dict] = []
    for asset in matched_assets:
        if asset.get("match_type") != "exact":
            continue
        operations.extend(
            plan_album_file_operations(
                asset,
                album_folder_mappings,
                sorting_approach=sorting_approach,
            )
        )
    return operations


def _ordered_mapped_memberships(memberships: list[dict], album_folder_mappings: dict) -> list[dict]:
    mapped_memberships = []
    for index, membership in enumerate(memberships or []):
        album_id = membership.get("album_id")
        if album_id is None:
            continue
        album_id = str(album_id)
        mapping = album_folder_mappings.get(album_id)
        if not isinstance(mapping, dict) or not mapping.get("folder_path"):
            continue
        mapped_membership = dict(membership)
        mapped_membership["album_id"] = album_id
        mapped_membership["folder_path"] = mapping["folder_path"]
        mapped_membership["_input_order"] = index
        mapped_memberships.append(mapped_membership)

    return sorted(
        mapped_memberships,
        key=lambda membership: (
            _selection_order(membership.get("selection_order")),
            membership["_input_order"],
        ),
    )


def _selection_order(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
