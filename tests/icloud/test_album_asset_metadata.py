from datetime import datetime, timezone
import binascii
from types import SimpleNamespace

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


class MissingFilenameAsset:
    id = "asset-missing"
    media_type = "image"

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


class MasterRecordFilenameAsset:
    id = "asset-master"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "SU1HX01BU1RFUi5IRUlD".rstrip("="),
            }
        }
    }

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


class MasterRecordDownloadUrlAsset:
    id = "asset-url"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "not-valid-base64",
            },
            "resOriginalRes": {
                "value": {
                    "downloadURL": "https://cvws.icloud-content.com/path/IMG_URL%20NAME.HEIC?token=redacted",
                },
            },
        }
    }

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


class MasterRecordPlainFilenameAsset:
    id = "asset-plain"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "IMG_1234.JPG",
            }
        }
    }

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


class MasterRecordEmptyFilenameEncReadableFilenameAsset:
    id = "asset-empty-filename-enc"
    filename = "IMG_0001.HEIC"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "",
            }
        }
    }


class MasterRecordMalformedFilenameEncReadableFilenameAsset:
    id = "asset-malformed-filename-enc"
    filename = "IMG_0001.HEIC"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "not-valid-base64",
            }
        }
    }


class FakeHeaderResponse:
    def __init__(self, headers):
        self.headers = headers
        self.closed = False

    def close(self):
        self.closed = True


class FakeHeaderSession:
    def __init__(self):
        self.head_response = FakeHeaderResponse(
            {
                "Content-Disposition": "attachment; filename*=UTF-8''IMG_HEADER%20NAME.HEIC",
            }
        )
        self.head_calls = []

    def head(self, url, **kwargs):
        self.head_calls.append((url, kwargs))
        return self.head_response


class MasterRecordHeaderFilenameAsset:
    id = "asset-header"
    media_type = "image"

    def __init__(self):
        self._service = SimpleNamespace(session=FakeHeaderSession())
        self._master_record = {
            "fields": {
                "filenameEnc": {
                    "value": "not-valid-base64",
                },
                "resOriginalRes": {
                    "value": {
                        "downloadURL": "https://example.invalid/resource",
                    },
                },
            }
        }

    @property
    def filename(self):
        raise binascii.Error("Incorrect padding")


class MasterRecordResourceFilenameAsset:
    id = "asset-resource"
    media_type = "image"
    _master_record = {
        "fields": {
            "filenameEnc": {
                "value": "not-valid-base64",
            },
            "resOriginalRes": {
                "value": {
                    "filename": "IMG_RESOURCE.HEIC",
                    "downloadURL": "https://example.invalid/private-token",
                },
            },
        }
    }

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


def test_normalize_asset_metadata_recovers_filename_from_master_record_without_warning(caplog):
    service = ICloudService(api=None)

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        result = service._normalize_asset_metadata(MasterRecordFilenameAsset(), ALBUM_SUMMARY)

    assert result == {
        "asset_id": "asset-master",
        "filename": "IMG_MASTER.HEIC",
        "original_filename": "IMG_MASTER.HEIC",
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }
    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename" in record.message
    ] == []


def test_normalize_asset_metadata_recovers_plain_text_filename_enc_without_warning(caplog):
    service = ICloudService(api=None)

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        result = service._normalize_asset_metadata(
            MasterRecordPlainFilenameAsset(),
            ALBUM_SUMMARY,
        )

    assert result == {
        "asset_id": "asset-plain",
        "filename": "IMG_1234.JPG",
        "original_filename": "IMG_1234.JPG",
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }
    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename" in record.message
    ] == []


def test_normalize_asset_metadata_uses_filename_when_filename_enc_is_empty():
    service = ICloudService(api=None)

    result = service._normalize_asset_metadata(
        MasterRecordEmptyFilenameEncReadableFilenameAsset(),
        ALBUM_SUMMARY,
    )

    assert result["asset_id"] == "asset-empty-filename-enc"
    assert result["filename"] == "IMG_0001.HEIC"
    assert result["original_filename"] == "IMG_0001.HEIC"


def test_normalize_asset_metadata_uses_filename_when_filename_enc_is_malformed():
    service = ICloudService(api=None)

    result = service._normalize_asset_metadata(
        MasterRecordMalformedFilenameEncReadableFilenameAsset(),
        ALBUM_SUMMARY,
    )

    assert result["asset_id"] == "asset-malformed-filename-enc"
    assert result["filename"] == "IMG_0001.HEIC"
    assert result["original_filename"] == "IMG_0001.HEIC"


def test_normalize_asset_metadata_recovers_filename_from_master_record_download_url(caplog):
    service = ICloudService(api=None)

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        result = service._normalize_asset_metadata(MasterRecordDownloadUrlAsset(), ALBUM_SUMMARY)

    assert result == {
        "asset_id": "asset-url",
        "filename": "IMG_URL NAME.HEIC",
        "original_filename": "IMG_URL NAME.HEIC",
        "created_at": None,
        "size": None,
        "media_type": "image",
        "album_id": "album-1",
        "album_name": "Vacation 2025",
    }
    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename" in record.message
    ] == []


def test_normalize_asset_metadata_recovers_filename_from_resource_value(caplog):
    service = ICloudService(api=None)

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        result = service._normalize_asset_metadata(
            MasterRecordResourceFilenameAsset(),
            ALBUM_SUMMARY,
        )

    assert result["asset_id"] == "asset-resource"
    assert result["filename"] == "IMG_RESOURCE.HEIC"
    assert result["original_filename"] == "IMG_RESOURCE.HEIC"
    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename" in record.message
    ] == []


def test_normalize_asset_metadata_recovers_filename_from_resource_headers(caplog):
    service = ICloudService(api=None)
    raw_asset = MasterRecordHeaderFilenameAsset()

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        result = service._normalize_asset_metadata(raw_asset, ALBUM_SUMMARY)

    assert result["asset_id"] == "asset-header"
    assert result["filename"] == "IMG_HEADER NAME.HEIC"
    assert result["original_filename"] == "IMG_HEADER NAME.HEIC"
    assert raw_asset._service.session.head_calls == [
        (
            "https://example.invalid/resource",
            {
                "allow_redirects": True,
                "timeout": 10,
            },
        )
    ]
    assert raw_asset._service.session.head_response.closed is True
    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename" in record.message
    ] == []


def test_normalize_asset_metadata_skips_assets_without_any_readable_filename():
    service = ICloudService(api=None)

    result = service._normalize_asset_metadata(MissingFilenameAsset(), ALBUM_SUMMARY)

    assert result is None


def test_read_field_value_logs_unreadable_asset_field_only_once(caplog):
    service = ICloudService(api=None)

    with caplog.at_level("WARNING", logger="icloud-sorter"):
        assert service._read_field_value(MissingFilenameAsset(), "filename") is None
        assert service._read_field_value(MissingFilenameAsset(), "filename") is None

    assert [
        record.message
        for record in caplog.records
        if "Skipping unreadable asset field filename on MissingFilenameAsset" in record.message
    ] == [
        "Skipping unreadable asset field filename on MissingFilenameAsset: Incorrect padding"
    ]
