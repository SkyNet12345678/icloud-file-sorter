import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.scanner import LocalScanner

logger = logging.getLogger("icloud-sorter")

DEFAULT_MOCK_SORT_TOTAL = 1847


def _album_type_name(album):
    return type(album).__name__


class ICloudService:
    def __init__(self, api, settings_service=None):
        self.api = api
        self.settings_service = settings_service
        self.jobs = {}
        self.album_cache_loaded = False
        self.album_list_cache = []
        self.album_summaries_by_id = {}
        self.raw_albums_by_id = {}
        self.asset_metadata_by_album_id = {}
        self.asset_cache_loaded_album_ids = set()

    def get_albums(self, force_refresh=False):
        if not self.api:
            return self._failure_result("iCloud session unavailable")

        try:
            self._load_album_cache(force_refresh=force_refresh)
            return self._success_result(self.album_list_cache)
        except Exception as exc:
            logger.exception("Failed to retrieve albums from iCloud: %s", exc)
            return self._failure_result(str(exc) or "Failed to fetch albums")

    def start_sort(self, selected_album_ids):
        try:
            self._require_album_cache_loaded()
        except RuntimeError as exc:
            return {"error": str(exc)}

        selected_ids = self._filter_known_album_ids(
            self._dedupe_selected_album_ids(selected_album_ids)
        )
        if not selected_ids:
            return {"error": "No albums selected"}

        try:
            source_folder = self._require_source_folder()
        except RuntimeError as exc:
            return {"error": str(exc)}

        selected_albums = self._resolve_selected_album_names(selected_ids)

        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "matching",
            "processed": 0,
            "total": 0,
            "percent": 0,
            "selected_album_ids": selected_ids,
            "selected_albums": selected_albums,
            "selected_assets": [],
            "source_folder": source_folder,
            "match_results": self._empty_match_results(),
            "message": self._build_preparing_message(),
            "_matching_reported": False,
            "_matching_prepared": False,
            "_matching_completed": False,
        }

        return {"job_id": job_id}

    def get_sort_progress(self, job_id):
        job = self.jobs.get(job_id)

        if not job:
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Unknown job id",
            }

        if job["status"] == "matching":
            return self._advance_matching_job(job)

        if job["status"] == "running":
            job["processed"] = min(job["processed"] + 50, job["total"])
            job["percent"] = int((job["processed"] / job["total"]) * 100) if job["total"] else 100
            job["message"] = self._build_processing_message(job)

            if job["processed"] >= job["total"]:
                job["status"] = "complete"
                job["percent"] = 100
                job["message"] = self._build_complete_message(job)

        return self._copy_job_progress(job)

    def get_cached_album(self, album_id):
        self._require_album_cache_loaded()
        normalized_album_id = self._normalize_lookup_album_id(album_id)
        if normalized_album_id is None:
            return None
        return self.raw_albums_by_id.get(normalized_album_id)

    def get_cached_album_summary(self, album_id):
        self._require_album_cache_loaded()
        normalized_album_id = self._normalize_lookup_album_id(album_id)
        if normalized_album_id is None:
            return None
        summary = self.album_summaries_by_id.get(normalized_album_id)
        if summary is None:
            return None
        return dict(summary)

    def get_album_assets(self, album_id, force_refresh=False):
        try:
            self._require_album_cache_loaded()
            normalized_album_id = self._require_known_album_id(album_id)
            album_summary = dict(self.album_summaries_by_id[normalized_album_id])
            assets = self._load_album_assets(
                normalized_album_id,
                force_refresh=force_refresh,
            )
        except Exception as exc:
            logger.exception("Failed to load album assets for %s: %s", album_id, exc)
            return self._asset_failure_result(str(exc) or "Failed to load album assets")

        return self._asset_success_result(album_summary, assets)

    def get_assets_for_album_ids(self, selected_album_ids, force_refresh=False):
        try:
            self._require_album_cache_loaded()
            normalized_ids = self._dedupe_selected_album_ids(selected_album_ids)
            if not normalized_ids:
                raise RuntimeError("No albums selected")

            for album_id in normalized_ids:
                self._require_known_album_id(album_id)

            aggregated_assets = {}
            for selection_order, album_id in enumerate(normalized_ids):
                album_assets = self._load_album_assets(
                    album_id,
                    force_refresh=force_refresh,
                )
                for asset in album_assets:
                    aggregated_asset = aggregated_assets.setdefault(
                        asset["asset_id"],
                        {
                            "asset_id": asset["asset_id"],
                            "filename": asset["filename"],
                            "original_filename": asset["original_filename"],
                            "created_at": asset["created_at"],
                            "size": asset["size"],
                            "media_type": asset["media_type"],
                            "album_memberships": [],
                        },
                    )
                    aggregated_asset["album_memberships"].append(
                        {
                            "album_id": asset["album_id"],
                            "album_name": asset["album_name"],
                            "selection_order": selection_order,
                        }
                    )
        except Exception as exc:
            logger.exception(
                "Failed to load aggregated album assets for %s: %s",
                selected_album_ids,
                exc,
            )
            return {
                "success": False,
                "selected_album_ids": [],
                "assets": [],
                "error": str(exc) or "Failed to load album assets",
            }

        return {
            "success": True,
            "selected_album_ids": list(normalized_ids),
            "assets": [
                self._copy_aggregated_asset(asset)
                for asset in aggregated_assets.values()
            ],
            "error": None,
        }

    def get_cached_album_assets(self, album_id):
        self._require_album_cache_loaded()
        normalized_album_id = self._normalize_lookup_album_id(album_id)
        if normalized_album_id is None:
            return None
        if normalized_album_id not in self.asset_cache_loaded_album_ids:
            return None
        cached_assets = self.asset_metadata_by_album_id.get(normalized_album_id, [])
        return [dict(asset) for asset in cached_assets]

    def _load_album_cache(self, force_refresh=False):
        if self.album_cache_loaded and not force_refresh:
            return

        raw_albums = self._get_raw_albums()
        cache_data = self._build_album_cache(raw_albums)
        self._apply_album_cache(cache_data)

    def _clear_album_cache(self):
        self.album_cache_loaded = False
        self.album_list_cache = []
        self.album_summaries_by_id = {}
        self.raw_albums_by_id = {}
        self._clear_asset_cache()

    def _build_album_cache(self, raw_albums):
        normalized_albums = []
        summaries_by_id = {}
        raw_albums_by_id = {}

        for raw_album in raw_albums:
            summary = self._normalize_album_summary(raw_album)
            if summary is None:
                continue
            normalized_albums.append(summary)
            summaries_by_id[summary["id"]] = summary
            raw_albums_by_id[summary["id"]] = raw_album

        normalized_albums.sort(key=lambda album: album["name"].casefold())
        return {
            "album_list_cache": normalized_albums,
            "album_summaries_by_id": summaries_by_id,
            "raw_albums_by_id": raw_albums_by_id,
        }

    def _apply_album_cache(self, cache_data):
        self._clear_asset_cache()
        self.album_list_cache = cache_data["album_list_cache"]
        self.album_summaries_by_id = cache_data["album_summaries_by_id"]
        self.raw_albums_by_id = cache_data["raw_albums_by_id"]
        self.album_cache_loaded = True

    def _clear_asset_cache(self):
        self.asset_metadata_by_album_id = {}
        self.asset_cache_loaded_album_ids = set()

    def _load_album_assets(self, album_id, force_refresh=False):
        self._require_album_cache_loaded()
        normalized_album_id = self._require_known_album_id(album_id)

        if (
            normalized_album_id in self.asset_cache_loaded_album_ids
            and not force_refresh
        ):
            return [dict(asset) for asset in self.asset_metadata_by_album_id[normalized_album_id]]

        album_summary = self.album_summaries_by_id[normalized_album_id]
        raw_album = self.raw_albums_by_id[normalized_album_id]
        normalized_assets = []

        for raw_asset in self._iter_raw_album_assets(raw_album):
            normalized_asset = self._normalize_asset_metadata(raw_asset, album_summary)
            if normalized_asset is None:
                continue
            normalized_assets.append(normalized_asset)

        cached_assets = [dict(asset) for asset in normalized_assets]
        self.asset_metadata_by_album_id[normalized_album_id] = cached_assets
        self.asset_cache_loaded_album_ids.add(normalized_album_id)
        return [dict(asset) for asset in cached_assets]

    def _iter_raw_album_assets(self, raw_album):
        for candidate in (
            self._resolve_asset_collection(getattr(raw_album, "assets", None)),
            self._resolve_asset_collection(getattr(raw_album, "photos", None)),
            self._resolve_asset_collection(getattr(raw_album, "items", None)),
            self._resolve_asset_collection(raw_album),
        ):
            if candidate is None:
                continue
            for asset in candidate:
                yield asset
            return

        raise RuntimeError("Album asset library unavailable")

    def _resolve_asset_collection(self, value):
        if value is None:
            return None

        if callable(value):
            value = value()

        if value is None:
            return None

        if isinstance(value, dict):
            return list(value.values())

        if isinstance(value, (str, bytes)):
            return None

        try:
            return list(value)
        except TypeError:
            return None

    def _normalize_asset_metadata(self, raw_asset, album_summary):
        asset_id = self._read_asset_id(raw_asset)
        if not asset_id:
            logger.warning(
                "Skipping asset in album %s because no stable asset id was available",
                album_summary["id"],
            )
            return None

        filename = self._read_best_filename(raw_asset)
        original_filename = self._read_best_original_filename(raw_asset) or filename

        return {
            "asset_id": asset_id,
            "filename": filename,
            "original_filename": original_filename,
            "created_at": self._normalize_created_at(
                self._read_first_value(
                    raw_asset,
                    "created_at",
                    "created",
                    "createdAt",
                    "item_date",
                    "date_taken",
                    "addedDate",
                )
            ),
            "size": self._normalize_size(
                self._read_first_value(
                    raw_asset,
                    "size",
                    "item_size",
                    "file_size",
                    "original_size",
                    "bytes",
                )
            ),
            "media_type": self._normalize_media_type(raw_asset),
            "album_id": album_summary["id"],
            "album_name": album_summary["name"],
        }

    def _get_raw_albums(self):
        photos_service = getattr(self.api, "photos", None)
        if photos_service is None:
            raise RuntimeError("iCloud Photos service unavailable")

        albums = getattr(photos_service, "albums", None)
        if albums is None:
            raise RuntimeError("iCloud album library unavailable")

        return list(albums)

    def _normalize_album_summary(self, album):
        if not self._is_album_eligible(album):
            return None

        album_id = self._read_album_id(album)
        album_name = self._read_album_name(album)
        if not album_id or not album_name:
            logger.debug("Skipping album with incomplete metadata: %s", album)
            return None

        return {
            "id": album_id,
            "name": album_name,
            "item_count": self._read_album_item_count(album),
            "is_system_album": self._is_system_album(album),
        }

    def _is_album_eligible(self, album):
        if _album_type_name(album) == "PhotoAlbumFolder":
            return False
        return True

    def _is_system_album(self, album):
        return _album_type_name(album) == "SmartPhotoAlbum"

    def _read_album_id(self, album):
        album_id = getattr(album, "id", None)
        if album_id is None:
            return None
        return str(album_id)

    def _read_album_name(self, album):
        for attr in ("fullname", "name", "title"):
            value = getattr(album, attr, None)
            if isinstance(value, str):
                name = value.strip()
                if name:
                    return name
        return None

    def _read_album_item_count(self, album):
        try:
            count = len(album)
        except Exception as exc:
            logger.warning("Could not read item count for album %s: %s", album, exc)
            return 0

        try:
            return max(int(count), 0)
        except (TypeError, ValueError):
            return 0

    def _dedupe_selected_album_ids(self, selected_album_ids):
        seen = set()
        unique_ids = []

        for album_id in selected_album_ids or []:
            if album_id is None:
                continue
            normalized_id = str(album_id)
            if not normalized_id or normalized_id in seen:
                continue
            seen.add(normalized_id)
            unique_ids.append(normalized_id)

        return unique_ids

    def _resolve_selected_album_names(self, selected_album_ids):
        return [
            self.album_summaries_by_id[album_id]["name"]
            for album_id in selected_album_ids
            if album_id in self.album_summaries_by_id
        ]

    def _filter_known_album_ids(self, selected_album_ids):
        self._require_album_cache_loaded()

        return [
            album_id
            for album_id in selected_album_ids
            if album_id in self.album_summaries_by_id
        ]

    def _require_album_cache_loaded(self):
        if not self.album_cache_loaded:
            raise RuntimeError("Album cache not loaded")

    def _normalize_lookup_album_id(self, album_id):
        if album_id is None:
            return None

        normalized_album_id = str(album_id)
        if not normalized_album_id:
            return None
        return normalized_album_id

    def _require_known_album_id(self, album_id):
        normalized_album_id = self._normalize_lookup_album_id(album_id)
        if normalized_album_id is None or normalized_album_id not in self.album_summaries_by_id:
            raise RuntimeError("Album not found")
        return normalized_album_id

    def _read_asset_id(self, raw_asset):
        asset_id = self._read_first_value(
            raw_asset,
            "id",
            "asset_id",
            "assetId",
            "guid",
            "recordName",
            "photoGuid",
        )
        if asset_id is None:
            return None

        normalized_asset_id = str(asset_id).strip()
        if not normalized_asset_id:
            return None
        return normalized_asset_id

    def _read_best_filename(self, raw_asset):
        filename = self._read_first_value(
            raw_asset,
            "filename",
            "name",
            "original_filename",
            "originalFilename",
        )
        return self._normalize_text_value(filename)

    def _read_best_original_filename(self, raw_asset):
        original_filename = self._read_first_value(
            raw_asset,
            "original_filename",
            "originalFilename",
            "filename",
            "name",
        )
        return self._normalize_text_value(original_filename)

    def _normalize_created_at(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

        if not isinstance(value, datetime):
            return None

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _normalize_size(self, value):
        if value in (None, ""):
            return None

        try:
            normalized_size = int(value)
        except (TypeError, ValueError):
            return None

        if normalized_size < 0:
            return None
        return normalized_size

    def _normalize_media_type(self, raw_asset):
        if self._read_first_value(raw_asset, "is_live_photo", "isLivePhoto") is True:
            return "live-photo"
        if self._read_first_value(raw_asset, "is_video", "isVideo") is True:
            return "video"

        raw_value = self._read_first_value(
            raw_asset,
            "media_type",
            "mediaType",
            "type",
            "asset_type",
            "kind",
        )
        normalized_value = self._normalize_text_value(raw_value)
        if normalized_value is None:
            return "unknown"

        media_type = normalized_value.casefold()
        if media_type in {"image", "photo", "picture", "jpeg", "jpg", "png", "heic"}:
            return "image"
        if media_type in {"video", "movie", "mov", "mp4"}:
            return "video"
        if media_type in {"live-photo", "live photo", "livephoto"}:
            return "live-photo"
        return "unknown"

    def _read_first_value(self, raw_asset, *field_names):
        for field_name in field_names:
            value = self._read_field_value(raw_asset, field_name)
            if value is None:
                continue
            return value
        return None

    def _read_field_value(self, raw_asset, field_name):
        if isinstance(raw_asset, dict):
            return raw_asset.get(field_name)

        try:
            value = getattr(raw_asset, field_name)
        except AttributeError:
            return None
        except Exception as exc:
            logger.warning(
                "Skipping unreadable asset field %s on %s: %s",
                field_name,
                type(raw_asset).__name__,
                exc,
            )
            return None

        if callable(value):
            try:
                value = value()
            except TypeError:
                return None
            except Exception as exc:
                logger.warning(
                    "Skipping unreadable callable asset field %s on %s: %s",
                    field_name,
                    type(raw_asset).__name__,
                    exc,
                )
                return None
        return value

        return None

    def _normalize_text_value(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized_value = value.strip()
        else:
            normalized_value = str(value).strip()
        if not normalized_value:
            return None
        return normalized_value

    def _asset_success_result(self, album_summary, assets):
        return {
            "success": True,
            "album": dict(album_summary),
            "assets": [dict(asset) for asset in assets],
            "error": None,
        }

    def _asset_failure_result(self, error_message):
        return {
            "success": False,
            "album": None,
            "assets": [],
            "error": error_message,
        }

    def _copy_aggregated_asset(self, asset):
        return {
            "asset_id": asset["asset_id"],
            "filename": asset["filename"],
            "original_filename": asset["original_filename"],
            "created_at": asset["created_at"],
            "size": asset["size"],
            "media_type": asset["media_type"],
            "album_memberships": [
                dict(membership)
                for membership in asset["album_memberships"]
            ],
        }

    def _copy_job_progress(self, job):
        progress_keys = (
            "job_id",
            "status",
            "processed",
            "total",
            "percent",
            "message",
        )
        progress = {
            key: job[key]
            for key in progress_keys
        }
        progress["match_results"] = self._copy_match_results_summary(
            job.get("match_results")
        )
        return progress

    def _advance_matching_job(self, job):
        if not job.get("_matching_reported"):
            job["_matching_reported"] = True
            return self._copy_job_progress(job)

        if not job.get("_matching_prepared"):
            asset_result = self.get_assets_for_album_ids(
                job["selected_album_ids"],
                force_refresh=True,
            )
            if not asset_result.get("success"):
                job["status"] = "error"
                job["processed"] = 0
                job["total"] = 0
                job["percent"] = 0
                job["message"] = asset_result.get("error") or "Failed to load album assets"
                return self._copy_job_progress(job)

            selected_assets = asset_result["assets"]
            job["selected_assets"] = selected_assets
            job["processed"] = 0
            job["total"] = len(selected_assets)
            job["percent"] = 0
            job["message"] = self._build_matching_message(selected_assets)
            job["_matching_prepared"] = True
            return self._copy_job_progress(job)

        if not job.get("_matching_completed"):
            try:
                scanner = LocalScanner(job["source_folder"])
                scanner.scan()
                job["match_results"] = scanner.match_assets(job["selected_assets"])
            except Exception as exc:
                logger.exception("Failed to match local files for job %s: %s", job["job_id"], exc)
                job["status"] = "error"
                job["processed"] = 0
                job["total"] = 0
                job["percent"] = 0
                job["message"] = "Failed to scan the local source folder for matching files"
                return self._copy_job_progress(job)

            job["_matching_completed"] = True

        job["status"] = "running"
        job["processed"] = 0
        job["total"] = DEFAULT_MOCK_SORT_TOTAL
        job["percent"] = 0
        job["message"] = self._build_running_message(job)
        return self._copy_job_progress(job)

    def _build_matching_message(self, selected_assets):
        asset_count = len(selected_assets)
        suffix = "asset" if asset_count == 1 else "assets"
        return f"Fetched iCloud metadata for {asset_count} {suffix}. Matching local files..."

    def _build_preparing_message(self):
        return "Preparing matching job..."

    def _build_running_message(self, job):
        match_results = self._copy_match_results_summary(job.get("match_results"))
        return (
            f"Starting sort for {len(job['selected_album_ids'])} album(s). "
            f"{self._build_match_quality_message(match_results)}"
        )

    def _empty_match_results(self):
        return {
            "matched": 0,
            # Kept for bridge compatibility until a verified fallback strategy exists.
            "fallback_matched": 0,
            "not_found": 0,
            "ambiguous": 0,
            "assets": [],
        }

    def _copy_match_results_summary(self, match_results):
        summary = self._empty_match_results()
        if isinstance(match_results, dict):
            for key in ("matched", "fallback_matched", "not_found", "ambiguous"):
                try:
                    summary[key] = int(match_results.get(key, 0))
                except (TypeError, ValueError):
                    summary[key] = 0
        summary.pop("assets")
        return summary

    def _build_processing_message(self, job):
        match_results = self._copy_match_results_summary(job.get("match_results"))
        return (
            f"Processing photo {job['processed']} of {job['total']}. "
            f"{self._build_match_quality_message(match_results)}"
        )

    def _build_complete_message(self, job):
        match_results = self._copy_match_results_summary(job.get("match_results"))
        return f"Sort complete. {self._build_match_quality_message(match_results)}"

    def _build_match_quality_message(self, match_results):
        return (
            "Filename-only matching: "
            f"Exact: {match_results['matched']} | "
            f"Not found: {match_results['not_found']} | "
            f"Ambiguous: {match_results['ambiguous']}"
        )

    def _require_source_folder(self):
        source_folder = None
        if self.settings_service is not None:
            source_folder = self.settings_service.get_source_folder()

        if not source_folder:
            raise RuntimeError(
                "Source folder is not configured. Choose your iCloud Photos folder in Settings before starting a sort."
            )

        source_path = Path(source_folder)
        if not source_path.exists():
            raise RuntimeError(
                "Configured source folder was not found. Update the source folder in Settings before starting a sort."
            )
        if not source_path.is_dir():
            raise RuntimeError(
                "Configured source folder is not a folder. Update the source folder in Settings before starting a sort."
            )

        return str(source_path)

    def _success_result(self, albums):
        return {
            "success": True,
            "albums": [dict(album) for album in albums],
            "error": None,
        }

    def _failure_result(self, error_message):
        return {
            "success": False,
            "albums": [],
            "error": error_message,
        }
