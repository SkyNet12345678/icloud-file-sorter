import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("icloud-sorter")

SCHEMA_VERSION = 1
SETTINGS_FILENAME = "settings.json"

WINDOWS_KNOWN_PATHS = [
    Path(os.environ.get("USERPROFILE", "")) / "Pictures" / "iCloud Photos",
    Path(os.environ.get("USERPROFILE", "")) / "Apple Cloud" / "Pictures",
    Path(os.environ.get("USERPROFILE", "")) / "Pictures" / "iCloud Photos",
]


def _get_settings_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", ""))
    else:
        base = Path.home() / ".config"
    return base / "icloud-sorter"


def _detect_source_folder() -> str | None:
    for path in WINDOWS_KNOWN_PATHS:
        if path.exists() and path.is_dir():
            logger.info("Auto-detected source folder: %s", path)
            return str(path)
    return None


class SettingsService:
    def __init__(self, settings_dir: Path | None = None):
        self._settings_dir = settings_dir or _get_settings_dir()
        self._settings_file = self._settings_dir / SETTINGS_FILENAME
        self._settings = self._load()

    def _load(self) -> dict:
        if not self._settings_file.exists():
            return self._default_settings()

        try:
            with open(self._settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("schema_version") != SCHEMA_VERSION:
                logger.warning("Settings schema version mismatch, using defaults")
                return self._default_settings()
            return data
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to load settings: %s", exc)
            return self._default_settings()

    def _default_settings(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "source_folder": None,
            "sorting_approach": "first",
        }

    def save(self) -> bool:
        try:
            self._settings_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = self._settings_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
            tmp_file.replace(self._settings_file)
            logger.info("Settings saved to %s", self._settings_file)
            return True
        except IOError as exc:
            logger.error("Failed to save settings: %s", exc)
            return False

    def get_source_folder(self) -> str | None:
        sf = self._settings.get("source_folder")
        if sf and Path(sf).exists():
            return sf
        detected = _detect_source_folder()
        if detected:
            self._settings["source_folder"] = detected
            self.save()
            return detected
        return None

    def set_source_folder(self, path: str | None) -> bool:
        self._settings["source_folder"] = path
        return self.save()

    def get_sorting_approach(self) -> str:
        return self._settings.get("sorting_approach", "first")

    def set_sorting_approach(self, approach: str) -> bool:
        if approach not in ("first", "copy"):
            logger.warning("Invalid sorting_approach: %s", approach)
            return False
        self._settings["sorting_approach"] = approach
        return self.save()

    def get_all(self) -> dict:
        return self._settings.copy()

    def detect_source_folder(self) -> str | None:
        return _detect_source_folder()