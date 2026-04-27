from __future__ import annotations

import copy
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from app.settings import SettingsService

logger = logging.getLogger("icloud-sorter")

SCHEMA_VERSION = 1
SORT_STATE_FILENAME = "sort_state.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_sort_state() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "active_job_id": None,
        "jobs": {},
        "album_folder_mappings": {},
        "processed_assets": {},
        "updated_at": None,
    }


def create_job_state(
    job_id: str,
    *,
    selected_albums: list[dict] | None = None,
    source_folder: str | None = None,
    sorting_approach: str = "first",
    album_folder_mappings: dict | None = None,
    status: str = "pending",
    now: str | None = None,
) -> dict:
    timestamp = now or utc_now_iso()
    return {
        "job_id": str(job_id),
        "status": status,
        "source_folder": source_folder,
        "sorting_approach": sorting_approach,
        "selected_albums": [dict(album) for album in selected_albums or []],
        "album_folder_mappings": copy.deepcopy(album_folder_mappings or {}),
        "processed_assets": {},
        "summary": {},
        "errors": [],
        "created_at": timestamp,
        "updated_at": timestamp,
        "started_at": None,
        "completed_at": None,
    }


def create_asset_state(
    asset_id: str,
    *,
    filename: str | None = None,
    album_memberships: list[dict] | None = None,
    status: str = "pending",
    canonical_path: str | None = None,
    moved_path: str | None = None,
    app_created_copy_paths: list[str] | None = None,
    error: str | None = None,
    now: str | None = None,
) -> dict:
    timestamp = now or utc_now_iso()
    return {
        "asset_id": str(asset_id),
        "filename": filename,
        "album_memberships": [dict(item) for item in album_memberships or []],
        "status": status,
        "canonical_path": canonical_path,
        "moved_path": moved_path,
        "app_created_copy_paths": list(app_created_copy_paths or []),
        "error": error,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def normalize_sort_state(data: dict | None) -> dict:
    state = default_sort_state()
    if not isinstance(data, dict):
        return state
    if data.get("schema_version") != SCHEMA_VERSION:
        return state

    state.update(data)
    if not isinstance(state.get("jobs"), dict):
        state["jobs"] = {}
    if not isinstance(state.get("album_folder_mappings"), dict):
        state["album_folder_mappings"] = {}
    if not isinstance(state.get("processed_assets"), dict):
        state["processed_assets"] = {}
    state["schema_version"] = SCHEMA_VERSION
    return state


def clean_missing_tracked_copy_paths(
    state: dict,
    *,
    path_exists: Callable[[Path], bool] | None = None,
) -> dict:
    cleaned_state = normalize_sort_state(copy.deepcopy(state))
    exists = path_exists or Path.exists

    def clean_asset_records(processed_assets: dict) -> None:
        for asset in processed_assets.values():
            if not isinstance(asset, dict):
                continue
            copy_paths = asset.get("app_created_copy_paths") or []
            asset["app_created_copy_paths"] = [
                path
                for path in copy_paths
                if path and exists(Path(path))
            ]

    clean_asset_records(cleaned_state["processed_assets"])
    for job in cleaned_state["jobs"].values():
        if isinstance(job, dict) and isinstance(job.get("processed_assets"), dict):
            clean_asset_records(job["processed_assets"])

    return cleaned_state


def get_existing_tracked_copy_paths(
    state: dict,
    *,
    path_exists: Callable[[Path], bool] | None = None,
) -> set[str]:
    cleaned_state = clean_missing_tracked_copy_paths(
        state,
        path_exists=path_exists,
    )
    paths: set[str] = set()

    def collect(processed_assets: dict) -> None:
        for asset in processed_assets.values():
            if isinstance(asset, dict):
                paths.update(asset.get("app_created_copy_paths") or [])

    collect(cleaned_state["processed_assets"])
    for job in cleaned_state["jobs"].values():
        if isinstance(job, dict) and isinstance(job.get("processed_assets"), dict):
            collect(job["processed_assets"])
    return paths


class SortStateStore:
    def __init__(
        self,
        *,
        settings_service: SettingsService | None = None,
        app_data_dir: str | Path | None = None,
        filename: str = SORT_STATE_FILENAME,
    ):
        if app_data_dir is not None:
            self.app_data_dir = Path(app_data_dir)
        else:
            service = settings_service or SettingsService()
            self.app_data_dir = service.get_app_data_dir()
        self.state_file = self.app_data_dir / filename

    def load(self) -> dict:
        if not self.state_file.exists():
            return default_sort_state()

        try:
            with open(self.state_file, "r", encoding="utf-8") as handle:
                return normalize_sort_state(json.load(handle))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load sort state from %s: %s", self.state_file, exc)
            return default_sort_state()

    def save(self, state: dict) -> bool:
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        normalized_state = normalize_sort_state(state)
        normalized_state["updated_at"] = utc_now_iso()
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.app_data_dir,
                prefix=f"{self.state_file.stem}-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(normalized_state, handle, indent=2)
                handle.write("\n")
            temp_path.replace(self.state_file)
            return True
        except OSError as exc:
            logger.error("Failed to save sort state to %s: %s", self.state_file, exc)
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove temporary sort state file %s", temp_path)
            return False
