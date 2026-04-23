from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_temporary_asset_fetch_button_is_removed_from_ui():
    index_html = (ROOT / "app" / "ui" / "index.html").read_text(encoding="utf-8")

    assert 'id="test-fetch-btn"' not in index_html
    assert "Test: Fetch album assets" not in index_html


def test_temporary_asset_fetch_wiring_is_removed_from_js():
    albums_js = (ROOT / "app" / "ui" / "js" / "albums.js").read_text(
        encoding="utf-8"
    )
    main_js = (ROOT / "app" / "ui" / "js" / "main.js").read_text(
        encoding="utf-8"
    )

    assert "testFetchAlbumAssets" not in albums_js
    assert "test-fetch-btn" not in albums_js
    assert "testFetchAlbumAssets" not in main_js
    assert "test-fetch-btn" not in main_js
