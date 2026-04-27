from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterable

STATUS_READY = "ready"
STATUS_MOVED = "moved"
STATUS_COPIED = "copied"
STATUS_ALREADY_SORTED = "already_sorted"
STATUS_ALREADY_COPIED = "already_copied"
STATUS_SKIPPED_DESTINATION_EXISTS = "skipped_destination_exists"
STATUS_SKIPPED_SOURCE_MISSING = "skipped_source_missing"
STATUS_FAILED_FILESYSTEM_ERROR = "failed_filesystem_error"


def validate_destination_folder(destination_folder: str | Path) -> dict:
    folder = Path(destination_folder)
    result = {
        "status": STATUS_READY,
        "destination_folder": str(folder),
        "error": None,
    }

    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".icloud-sorter-write-", delete=False) as handle:
            temp_path = Path(handle.name)
        temp_path.unlink(missing_ok=True)
    except OSError as exc:
        result["status"] = STATUS_FAILED_FILESYSTEM_ERROR
        result["error"] = str(exc)

    return result


def move_file(source_path: str | Path, destination_path: str | Path) -> dict:
    return _perform_file_operation("move", source_path, destination_path)


def copy_file(
    source_path: str | Path,
    destination_path: str | Path,
    *,
    tracked_copy_paths: Iterable[str | Path] | None = None,
) -> dict:
    return _perform_file_operation(
        "copy",
        source_path,
        destination_path,
        tracked_copy_paths=tracked_copy_paths,
    )


def _perform_file_operation(
    operation: str,
    source_path: str | Path,
    destination_path: str | Path,
    *,
    tracked_copy_paths: Iterable[str | Path] | None = None,
) -> dict:
    source = Path(source_path)
    destination = Path(destination_path)
    result = _operation_result(operation, source, destination)

    if not source.exists():
        result["status"] = STATUS_SKIPPED_SOURCE_MISSING
        return result

    if _same_path(source, destination):
        result["status"] = STATUS_ALREADY_SORTED
        return result

    if destination.exists():
        if _normalize_path_key(destination) in _tracked_path_keys(tracked_copy_paths):
            result["status"] = STATUS_ALREADY_COPIED
        else:
            result["status"] = STATUS_SKIPPED_DESTINATION_EXISTS
        return result

    folder_result = validate_destination_folder(destination.parent)
    if folder_result["status"] != STATUS_READY:
        result["status"] = STATUS_FAILED_FILESYSTEM_ERROR
        result["error"] = folder_result["error"]
        return result

    try:
        if operation == "move":
            shutil.move(str(source), str(destination))
            result["status"] = STATUS_MOVED
        else:
            shutil.copy2(source, destination)
            result["status"] = STATUS_COPIED
    except OSError as exc:
        result["status"] = STATUS_FAILED_FILESYSTEM_ERROR
        result["error"] = str(exc)

    return result


def _operation_result(operation: str, source: Path, destination: Path) -> dict:
    return {
        "operation": operation,
        "status": None,
        "source_path": str(source),
        "destination_path": str(destination),
        "error": None,
    }


def _same_path(left: Path, right: Path) -> bool:
    return _normalize_path_key(left) == _normalize_path_key(right)


def _tracked_path_keys(paths: Iterable[str | Path] | None) -> set[str]:
    return {
        _normalize_path_key(path)
        for path in paths or []
        if path
    }


def _normalize_path_key(path: str | Path) -> str:
    return str(Path(path).resolve(strict=False)).casefold()
