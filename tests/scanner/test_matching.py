from app.scanner import LocalScanner


def build_asset(asset_id, filename):
    return {
        "asset_id": asset_id,
        "filename": filename,
        "original_filename": filename,
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_memberships": [
            {
                "album_id": "album-1",
                "album_name": "Trips",
                "selection_order": 0,
            }
        ],
    }


def test_match_assets_returns_exact_match_for_single_filename_hit(tmp_path):
    local_file = tmp_path / "IMG_0001.HEIC"
    local_file.write_text("content", encoding="utf-8")
    scanner = LocalScanner(tmp_path)
    scanner.scan()

    result = scanner.match_assets([build_asset("asset-1", "img_0001.heic")])

    assert result == {
        "matched": 1,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
        "assets": [
            {
                "asset_id": "asset-1",
                "filename": "img_0001.heic",
                "original_filename": "img_0001.heic",
                "created_at": None,
                "size": None,
                "media_type": "image",
                "album_memberships": [
                    {
                        "album_id": "album-1",
                        "album_name": "Trips",
                        "selection_order": 0,
                    }
                ],
                "local_path": str(local_file),
                "match_type": "exact",
            }
        ],
    }


def test_match_assets_returns_none_when_no_local_file_exists(tmp_path):
    scanner = LocalScanner(tmp_path)
    scanner.scan()

    result = scanner.match_assets([build_asset("asset-1", "IMG_4040.HEIC")])

    assert result["matched"] == 0
    assert result["fallback_matched"] == 0
    assert result["not_found"] == 1
    assert result["ambiguous"] == 0
    assert result["assets"] == [
        {
            "asset_id": "asset-1",
            "filename": "IMG_4040.HEIC",
            "original_filename": "IMG_4040.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-1",
                    "album_name": "Trips",
                    "selection_order": 0,
                }
            ],
            "local_path": None,
            "match_type": "none",
        }
    ]


def test_match_assets_returns_ambiguous_when_duplicate_filenames_exist(tmp_path):
    first_dir = tmp_path / "album-a"
    second_dir = tmp_path / "album-b"
    first_dir.mkdir()
    second_dir.mkdir()
    first_file = first_dir / "IMG_DUPLICATE.HEIC"
    second_file = second_dir / "img_duplicate.heic"
    first_file.write_text("first", encoding="utf-8")
    second_file.write_text("second", encoding="utf-8")
    scanner = LocalScanner(tmp_path)
    scanner.scan()

    result = scanner.match_assets([build_asset("asset-1", "IMG_DUPLICATE.HEIC")])

    assert result["matched"] == 0
    assert result["fallback_matched"] == 0
    assert result["not_found"] == 0
    assert result["ambiguous"] == 1
    assert result["assets"] == [
        {
            "asset_id": "asset-1",
            "filename": "IMG_DUPLICATE.HEIC",
            "original_filename": "IMG_DUPLICATE.HEIC",
            "created_at": None,
            "size": None,
            "media_type": "image",
            "album_memberships": [
                {
                    "album_id": "album-1",
                    "album_name": "Trips",
                    "selection_order": 0,
                }
            ],
            "local_path": None,
            "match_type": "ambiguous",
            "candidate_paths": [
                str(first_file),
                str(second_file),
            ],
        }
    ]


def test_match_assets_never_introduces_automatic_fallback_match_type(tmp_path):
    local_file = tmp_path / "IMG_0001.HEIC"
    local_file.write_text("content", encoding="utf-8")
    duplicate_dir = tmp_path / "duplicates"
    duplicate_dir.mkdir()
    duplicate_file = duplicate_dir / "IMG_0002.HEIC"
    duplicate_file.write_text("duplicate", encoding="utf-8")
    second_duplicate_dir = tmp_path / "duplicates-2"
    second_duplicate_dir.mkdir()
    third_file = second_duplicate_dir / "img_0002.heic"
    third_file.write_text("duplicate-2", encoding="utf-8")
    scanner = LocalScanner(tmp_path)
    scanner.scan()

    result = scanner.match_assets(
        [
            build_asset("asset-1", "IMG_0001.HEIC"),
            build_asset("asset-2", "IMG_4040.HEIC"),
            build_asset("asset-3", "IMG_0002.HEIC"),
        ]
    )

    assert result["fallback_matched"] == 0
    assert {asset["match_type"] for asset in result["assets"]} == {
        "exact",
        "none",
        "ambiguous",
    }
