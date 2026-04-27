import os

import pytest

from app.sorting import file_operations
from app.sorting.file_operations import (
    STATUS_ALREADY_COPIED,
    STATUS_ALREADY_SORTED,
    STATUS_COPIED,
    STATUS_FAILED_FILESYSTEM_ERROR,
    STATUS_MOVED,
    STATUS_READY,
    STATUS_SKIPPED_DESTINATION_EXISTS,
    STATUS_SKIPPED_SOURCE_MISSING,
    copy_file,
    move_file,
    validate_destination_folder,
)


def test_validate_destination_folder_creates_and_confirms_writable_directory(tmp_path):
    destination_folder = tmp_path / "Trips"

    result = validate_destination_folder(destination_folder)

    assert result == {
        "status": STATUS_READY,
        "destination_folder": str(destination_folder),
        "error": None,
    }
    assert destination_folder.is_dir()


def test_move_file_moves_without_overwriting(tmp_path):
    source = tmp_path / "IMG_0001.HEIC"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "Trips" / "IMG_0001.HEIC"

    result = move_file(source, destination)

    assert result["status"] == STATUS_MOVED
    assert result["operation"] == "move"
    assert result["source_path"] == str(source)
    assert result["destination_path"] == str(destination)
    assert result["error"] is None
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "source"


def test_copy_file_copies_without_overwriting_source(tmp_path):
    source = tmp_path / "IMG_0001.HEIC"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "Trips" / "IMG_0001.HEIC"

    result = copy_file(source, destination)

    assert result["status"] == STATUS_COPIED
    assert source.read_text(encoding="utf-8") == "source"
    assert destination.read_text(encoding="utf-8") == "source"


def test_move_file_reports_already_sorted_when_source_equals_destination(tmp_path):
    source = tmp_path / "Trips" / "IMG_0001.HEIC"
    source.parent.mkdir()
    source.write_text("source", encoding="utf-8")

    result = move_file(source, source)

    assert result["status"] == STATUS_ALREADY_SORTED
    assert source.read_text(encoding="utf-8") == "source"


def test_copy_file_reports_already_copied_for_tracked_destination(tmp_path):
    source = tmp_path / "IMG_0001.HEIC"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "Trips" / "IMG_0001.HEIC"
    destination.parent.mkdir()
    destination.write_text("copy", encoding="utf-8")

    result = copy_file(source, destination, tracked_copy_paths=[destination])

    assert result["status"] == STATUS_ALREADY_COPIED
    assert destination.read_text(encoding="utf-8") == "copy"


def test_copy_file_skips_untracked_destination_conflict(tmp_path):
    source = tmp_path / "IMG_0001.HEIC"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "Trips" / "IMG_0001.HEIC"
    destination.parent.mkdir()
    destination.write_text("existing", encoding="utf-8")

    result = copy_file(source, destination, tracked_copy_paths=[])

    assert result["status"] == STATUS_SKIPPED_DESTINATION_EXISTS
    assert destination.read_text(encoding="utf-8") == "existing"


def test_file_operation_skips_missing_source(tmp_path):
    source = tmp_path / "missing.HEIC"
    destination = tmp_path / "Trips" / "missing.HEIC"

    result = copy_file(source, destination)

    assert result["status"] == STATUS_SKIPPED_SOURCE_MISSING
    assert not destination.exists()


def test_file_operation_captures_filesystem_errors(tmp_path, monkeypatch):
    source = tmp_path / "IMG_0001.HEIC"
    source.write_text("source", encoding="utf-8")
    destination = tmp_path / "Trips" / "IMG_0001.HEIC"

    def fail_copy2(_source, _destination):
        raise OSError("copy failed")

    monkeypatch.setattr(file_operations.shutil, "copy2", fail_copy2)

    result = copy_file(source, destination)

    assert result["status"] == STATUS_FAILED_FILESYSTEM_ERROR
    assert "copy failed" in result["error"]
    assert source.exists()


@pytest.mark.skipif(os.name == "nt", reason="Windows permissions differ under test runners")
def test_validate_destination_folder_captures_unwritable_directory(tmp_path):
    destination_folder = tmp_path / "Trips"
    destination_folder.mkdir()
    destination_folder.chmod(0o500)

    try:
        result = validate_destination_folder(destination_folder)
    finally:
        destination_folder.chmod(0o700)

    assert result["status"] == STATUS_FAILED_FILESYSTEM_ERROR
    assert result["error"]
