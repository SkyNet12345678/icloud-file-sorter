from app.scanner import LocalScanner, normalize_filename


def test_scan_builds_recursive_filename_index(tmp_path):
    root_file = tmp_path / "IMG_0001.HEIC"
    root_file.write_text("root", encoding="utf-8")
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested_file = nested_dir / "IMG_0002.HEIC"
    nested_file.write_text("nested", encoding="utf-8")

    scanner = LocalScanner(tmp_path)

    scanned_files = scanner.scan()

    assert scanned_files == [
        {
            "filename": "IMG_0001.HEIC",
            "local_path": str(root_file),
        },
        {
            "filename": "IMG_0002.HEIC",
            "local_path": str(nested_file),
        },
    ]
    assert scanner.filename_index == {
        "img_0001.heic": [
            {
                "filename": "IMG_0001.HEIC",
                "local_path": str(root_file),
            }
        ],
        "img_0002.heic": [
            {
                "filename": "IMG_0002.HEIC",
                "local_path": str(nested_file),
            }
        ],
    }


def test_normalize_filename_is_case_insensitive_and_uses_basename_only():
    assert normalize_filename("IMG_0001.HEIC") == "img_0001.heic"
    assert normalize_filename("nested/IMG_0001.HEIC") == "img_0001.heic"
    assert normalize_filename("nested\\IMG_0001.HEIC") == "img_0001.heic"
