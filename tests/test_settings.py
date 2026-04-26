import json

from app import settings as settings_module
from app.settings import SCHEMA_VERSION, SETTINGS_FILENAME, SettingsService


def test_get_source_folder_preserves_stale_configured_path(
    tmp_path,
    monkeypatch,
):
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir()
    stale_source_folder = tmp_path / "missing-icloud-photos"
    detected_source_folder = tmp_path / "detected-icloud-photos"
    detected_source_folder.mkdir()
    settings_file = settings_dir / SETTINGS_FILENAME
    settings_file.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "source_folder": str(stale_source_folder),
                "sorting_approach": "first",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        settings_module,
        "WINDOWS_KNOWN_PATHS",
        [detected_source_folder],
    )

    service = SettingsService(settings_dir=settings_dir)

    assert service.get_source_folder() == str(stale_source_folder)
    saved_settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved_settings["source_folder"] == str(stale_source_folder)


def test_get_source_folder_autodetects_when_configured_path_is_blank(
    tmp_path,
    monkeypatch,
):
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir()
    detected_source_folder = tmp_path / "detected-icloud-photos"
    detected_source_folder.mkdir()
    settings_file = settings_dir / SETTINGS_FILENAME
    settings_file.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "source_folder": " ",
                "sorting_approach": "first",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        settings_module,
        "WINDOWS_KNOWN_PATHS",
        [detected_source_folder],
    )

    service = SettingsService(settings_dir=settings_dir)

    assert service.get_source_folder() == str(detected_source_folder)
    saved_settings = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved_settings["source_folder"] == str(detected_source_folder)


def test_remembered_apple_id_is_normalized_and_persisted(tmp_path):
    service = SettingsService(settings_dir=tmp_path)

    assert service.set_remembered_apple_id(" User@iCloud.com ") is True

    reloaded = SettingsService(settings_dir=tmp_path)
    saved_settings = json.loads((tmp_path / SETTINGS_FILENAME).read_text(encoding="utf-8"))

    assert reloaded.get_remembered_apple_id() == "user@icloud.com"
    assert saved_settings["remembered_apple_id"] == "user@icloud.com"
    assert "password" not in saved_settings
    assert "2fa" not in saved_settings


def test_clear_remembered_apple_id_persists_none(tmp_path):
    service = SettingsService(settings_dir=tmp_path)
    service.set_remembered_apple_id("user@icloud.com")

    assert service.clear_remembered_apple_id() is True

    reloaded = SettingsService(settings_dir=tmp_path)
    assert reloaded.get_remembered_apple_id() is None


def test_existing_schema_settings_merge_new_defaults(tmp_path):
    settings_file = tmp_path / SETTINGS_FILENAME
    settings_file.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "source_folder": "C:/iCloud Photos",
                "sorting_approach": "first",
            }
        ),
        encoding="utf-8",
    )

    service = SettingsService(settings_dir=tmp_path)

    assert service.get_remembered_apple_id() is None
    assert "remembered_apple_id" in service.get_all()
