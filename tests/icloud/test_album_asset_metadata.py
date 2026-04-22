from datetime import datetime, timezone
import binascii

from app.icloud.icloud_service import ICloudService


ALBUM_SUMMARY = {
    "id": "album-1",
    "name": "Vacation 2025",
    "item_count": 12,
    "is_system_album": False,
}


class FakeAsset:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class BrokenFilenameAsset:
    id = "asset-broken"
    name = "IMG_FALLBACK.HEIC"
    media_type = "image"

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


def test_normalize_asset_metadata_returns_backend_shape():
    service = ICloudService(api=None)
    raw_asset = FakeAsset(
        id="asset-123",
        filename="IMG_1234.HEIC",
        original_filename="IMG_1234-original.HEIC",
        created_at=datetime(2025, 8, 5, 12, 34, 56, tzinfo=timezone.utc),
        size="2481934",
        media_type="photo",
    )

    result = service._normalize_asset_metadata(raw_asset, ALBUM_SUMMARY)

    assert result == {
        "asset_id": "asset-123",
        "filename": "IMG_1234.HEIC",
        "original_filename": "IMG_1234-original.HEIC",
        "created_at": "2025-08-05T12:34:56Z",
        "size": 2481934,
        "media_type": "image",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }


def test_normalize_asset_metadata_uses_filename_fallbacks_and_null_optional_fields():
    service = ICloudService(api=None)
    raw_asset = {
        "recordName": "asset-456",
        "name": "MOV_4567.MOV",
        "createdAt": "not-a-date",
        "asset_type": "mystery",
    }

    result = service._normalize_asset_metadata(raw_asset, ALBUM_SUMMARY)

    assert result == {
        "asset_id": "asset-456",
        "filename": "MOV_4567.MOV",
        "original_filename": "MOV_4567.MOV",
        "created_at": None,
        "size": None,
        "media_type": "unknown",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }


def test_normalize_asset_metadata_normalizes_naive_datetime_and_live_photo_flags():
    service = ICloudService(api=None)
    raw_asset = FakeAsset(
        asset_id="asset-789",
        originalFilename="IMG_7890.HEIC",
        created=datetime(2025, 1, 2, 3, 4, 5),
        bytes=125,
        isLivePhoto=True,
    )

    result = service._normalize_asset_metadata(raw_asset, ALBUM_SUMMARY)

    assert result["filename"] == "IMG_7890.HEIC"
    assert result["original_filename"] == "IMG_7890.HEIC"
    assert result["created_at"] == "2025-01-02T03:04:05Z"
    assert result["size"] == 125
    assert result["media_type"] == "live-photo"


def test_normalize_asset_metadata_skips_assets_without_stable_id():
    service = ICloudService(api=None)
    raw_asset = FakeAsset(filename="IMG_0001.HEIC", media_type="image")

    result = service._normalize_asset_metadata(raw_asset, ALBUM_SUMMARY)

    assert result is None


def test_normalize_asset_metadata_uses_fallback_when_filename_property_raises():
    service = ICloudService(api=None)

    result = service._normalize_asset_metadata(BrokenFilenameAsset(), ALBUM_SUMMARY)

    assert result == {
        "asset_id": "asset-broken",
        "filename": "IMG_FALLBACK.HEIC",
        "original_filename": "IMG_FALLBACK.HEIC",
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }
