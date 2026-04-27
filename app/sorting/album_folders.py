from __future__ import annotations

import re
from pathlib import Path

from app.state.sort_state import normalize_sort_state

MAX_FOLDER_NAME_LENGTH = 120
DEFAULT_ALBUM_FOLDER_NAME = "Album"
ILLEGAL_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def sanitize_album_folder_name(
    album_name: str | None,
    *,
    max_length: int = MAX_FOLDER_NAME_LENGTH,
) -> str:
    safe_name = ILLEGAL_WINDOWS_CHARS.sub("_", str(album_name or "").strip())
    safe_name = safe_name.rstrip(" .")
    if not safe_name:
        safe_name = DEFAULT_ALBUM_FOLDER_NAME

    first_component = safe_name.split(".", 1)[0].upper()
    if first_component in RESERVED_WINDOWS_NAMES:
        safe_name = f"_{safe_name}"

    return _truncate_folder_name(safe_name, max_length=max_length)


def build_album_folder_mappings(
    source_folder: str | Path,
    albums: list[dict],
    *,
    existing_mappings: dict | None = None,
    max_folder_name_length: int = MAX_FOLDER_NAME_LENGTH,
) -> dict:
    source_path = Path(source_folder)
    existing_mappings = existing_mappings or {}
    mappings: dict[str, dict] = {}
    used_folder_names: set[str] = {
        _safe_folder_name(mapping["folder_name"]).casefold()
        for mapping in existing_mappings.values()
        if isinstance(mapping, dict) and mapping.get("folder_name")
    }

    for album in albums:
        album_id = _album_value(album, "album_id") or _album_value(album, "id")
        if album_id is None:
            continue
        album_id = str(album_id)
        album_name = str(_album_value(album, "album_name") or _album_value(album, "name") or "")
        existing_mapping = existing_mappings.get(album_id)

        if isinstance(existing_mapping, dict) and existing_mapping.get("folder_name"):
            folder_name = _safe_folder_name(existing_mapping["folder_name"])
            mapping = dict(existing_mapping)
            mapping.update(
                {
                    "album_id": album_id,
                    "album_name": album_name,
                    "folder_name": folder_name,
                    "folder_path": str(source_path / folder_name),
                }
            )
        else:
            base_folder_name = sanitize_album_folder_name(
                album_name,
                max_length=max_folder_name_length,
            )
            folder_name = _dedupe_folder_name(
                base_folder_name,
                used_folder_names,
                max_length=max_folder_name_length,
            )
            mapping = {
                "album_id": album_id,
                "album_name": album_name,
                "folder_name": folder_name,
                "folder_path": str(source_path / folder_name),
            }

        mappings[album_id] = mapping
        used_folder_names.add(mapping["folder_name"].casefold())

    return mappings


def persist_album_folder_mappings(state: dict, mappings: dict) -> dict:
    updated_state = normalize_sort_state(state)
    updated_mappings = {
        str(album_id): dict(mapping)
        for album_id, mapping in updated_state["album_folder_mappings"].items()
        if isinstance(mapping, dict)
    }
    updated_mappings.update({
        str(album_id): dict(mapping)
        for album_id, mapping in mappings.items()
    })
    updated_state["album_folder_mappings"] = updated_mappings
    return updated_state


def _album_value(album: dict, key: str):
    if isinstance(album, dict):
        return album.get(key)
    return getattr(album, key, None)


def _safe_folder_name(folder_name: str) -> str:
    return sanitize_album_folder_name(Path(str(folder_name)).name)


def _dedupe_folder_name(
    base_folder_name: str,
    used_folder_names: set[str],
    *,
    max_length: int,
) -> str:
    folder_name = _truncate_folder_name(base_folder_name, max_length=max_length)
    suffix_number = 2
    while folder_name.casefold() in used_folder_names:
        suffix = f" ({suffix_number})"
        folder_name = _truncate_folder_name(
            base_folder_name,
            suffix=suffix,
            max_length=max_length,
        )
        suffix_number += 1
    return folder_name


def _truncate_folder_name(
    folder_name: str,
    *,
    suffix: str = "",
    max_length: int,
) -> str:
    effective_max = max(1, max_length - len(suffix))
    truncated = folder_name[:effective_max].rstrip(" .")
    if not truncated:
        truncated = DEFAULT_ALBUM_FOLDER_NAME[:effective_max]
    return f"{truncated}{suffix}"
