import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from app.scanner import LocalScanner
from app.sorting.file_operations import STATUS_READY, validate_destination_folder
from app.sorting.sort_job import SortJobManager
from app.state.sort_state import SortStateStore

logger = logging.getLogger("icloud-sorter")

DEFAULT_MOCK_SORT_TOTAL = 1847
FAILED_TO_LOAD_ALBUM_ASSETS = "Failed to load album assets"


def _album_type_name(album):
    return type(album).__name__


class ICloudService:
    def __init__(self, api, settings_service=None, sort_job_manager=None):
        self.api = api
        self.settings_service = settings_service
        self.sort_job_manager = sort_job_manager or SortJobManager(
            state_store=self._build_sort_state_store(),
            run_async=True,
        )
        self.jobs = self.sort_job_manager.jobs
        self.album_cache_loaded = False
        self.album_list_cache = []
        self.album_summaries_by_id = {}
        self.raw_albums_by_id = {}
        self.asset_metadata_by_album_id = {}
        self.asset_cache_loaded_album_ids = set()
        self._logged_unreadable_asset_fields = set()

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

        selected_albums = self._resolve_selected_album_records(selected_ids)
        sorting_approach = self._get_sorting_approach()

        return self.sort_job_manager.start_job(
            job_id=str(uuid.uuid4()),
            selected_album_ids=selected_ids,
            selected_albums=selected_albums,
            source_folder=source_folder,
            sorting_approach=sorting_approach,
            asset_loader=lambda: self.get_assets_for_album_ids(
                selected_ids,
                force_refresh=True,
            ),
        )

    def get_sort_progress(self, job_id):
        return self.sort_job_manager.get_progress(job_id)

    def cancel_sort(self, job_id):
        return self.sort_job_manager.cancel_job(job_id)

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
            return self._asset_failure_result(str(exc) or FAILED_TO_LOAD_ALBUM_ASSETS)

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
                "error": str(exc) or FAILED_TO_LOAD_ALBUM_ASSETS,
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
        skipped_asset_count = 0
        first_skipped_asset = None

        for raw_asset in self._iter_raw_album_assets(raw_album):
            normalized_asset = self._normalize_asset_metadata(raw_asset, album_summary)
            if normalized_asset is None:
                skipped_asset_count += 1
                if first_skipped_asset is None:
                    first_skipped_asset = raw_asset
                continue
            normalized_assets.append(normalized_asset)

        if skipped_asset_count:
            logger.warning(
                "Skipped %d asset(s) in album %s because required filename or id metadata was unavailable",
                skipped_asset_count,
                album_summary["id"],
            )
            logger.warning(
                "Skipped asset diagnostic for album %s: %s",
                album_summary["id"],
                self._build_skipped_asset_diagnostic(first_skipped_asset),
            )

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
            logger.debug(
                "Skipping asset in album %s because no stable asset id was available",
                album_summary["id"],
            )
            return None

        filename = self._read_best_filename(raw_asset)
        original_filename = (
            self._read_best_original_filename(
                raw_asset,
                use_master_record=not filename,
            )
            or filename
        )

        if not filename and not original_filename:
            logger.debug(
                "Skipping asset %s in album %s because no readable filename metadata was available",
                asset_id,
                album_summary["id"],
            )
            return None

        filename = filename or original_filename
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

    def _resolve_selected_album_records(self, selected_album_ids):
        return [
            {
                "id": album_id,
                "name": self.album_summaries_by_id[album_id]["name"],
            }
            for album_id in selected_album_ids
            if album_id in self.album_summaries_by_id
        ]

    def _get_sorting_approach(self):
        if self.settings_service is None:
            return "first"
        get_sorting_approach = getattr(self.settings_service, "get_sorting_approach", None)
        if not callable(get_sorting_approach):
            return "first"
        return get_sorting_approach()

    def _build_sort_state_store(self):
        if self.settings_service is None:
            return None
        get_app_data_dir = getattr(self.settings_service, "get_app_data_dir", None)
        if not callable(get_app_data_dir):
            return None
        return SortStateStore(settings_service=self.settings_service)

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
        filename = self._read_filename_from_master_record(raw_asset)
        if filename is None:
            filename = self._read_first_value(
                raw_asset,
                "filename",
                "name",
                "original_filename",
                "originalFilename",
            )
        return self._normalize_text_value(filename)

    def _read_best_original_filename(self, raw_asset, use_master_record=True):
        original_filename = None
        if use_master_record:
            original_filename = self._read_filename_from_master_record(raw_asset)
        if original_filename is None:
            original_filename = self._read_first_value(
                raw_asset,
                "original_filename",
                "originalFilename",
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
            self._log_unreadable_asset_field_once(raw_asset, field_name, exc)
            return None

        if callable(value):
            try:
                value = value()
            except TypeError:
                return None
            except Exception as exc:
                self._log_unreadable_asset_field_once(
                    raw_asset,
                    field_name,
                    exc,
                    callable_field=True,
                )
                return None
        return value

        return None

    def _log_unreadable_asset_field_once(
        self,
        raw_asset,
        field_name,
        exc,
        *,
        callable_field=False,
    ):
        log_key = (
            type(raw_asset).__name__,
            field_name,
            type(exc).__name__,
            str(exc),
            callable_field,
        )
        if log_key in self._logged_unreadable_asset_fields:
            return

        self._logged_unreadable_asset_fields.add(log_key)
        field_kind = "callable asset field" if callable_field else "asset field"
        logger.warning(
            "Skipping unreadable %s %s on %s: %s",
            field_kind,
            field_name,
            type(raw_asset).__name__,
            exc,
        )

    def _read_filename_from_master_record(self, raw_asset):
        master_record = getattr(raw_asset, "_master_record", None)
        if not isinstance(master_record, dict):
            return None

        fields = master_record.get("fields")
        if not isinstance(fields, dict):
            return None

        filename_entry = fields.get("filenameEnc")
        if not isinstance(filename_entry, dict):
            return None

        encoded_value = filename_entry.get("value")
        if encoded_value in (None, ""):
            return self._read_filename_from_master_record_resource(raw_asset, fields)

        return (
            self._decode_base64_filename(encoded_value)
            or self._read_plain_filename_enc_value(encoded_value)
            or self._read_filename_from_master_record_resource(raw_asset, fields)
        )

    def _read_filename_from_master_record_resource(self, raw_asset, fields):
        for field_name in (
            "resOriginalRes",
            "resOriginalAltRes",
            "resOriginalVidComplRes",
            "resJPEGMedRes",
            "resJPEGThumbRes",
            "resVidMedRes",
            "resVidSmallRes",
        ):
            field_value = fields.get(field_name)
            if not isinstance(field_value, dict):
                continue

            resource_value = field_value.get("value")
            if not isinstance(resource_value, dict):
                continue

            filename = self._read_filename_from_resource_value(resource_value)
            if filename:
                return filename

            download_url = resource_value.get("downloadURL")
            filename = self._filename_from_download_url(download_url)
            if filename:
                return filename

            filename = self._filename_from_resource_headers(raw_asset, download_url)
            if filename:
                return filename
        return None

    def _read_filename_from_resource_value(self, resource_value):
        for field_name in (
            "filename",
            "fileName",
            "originalFilename",
            "original_filename",
            "name",
        ):
            filename = self._normalize_text_value(resource_value.get(field_name))
            if filename and self._has_media_extension(filename):
                return filename
        return None

    def _filename_from_download_url(self, download_url):
        if not download_url:
            return None

        path = unquote(urlparse(str(download_url)).path)
        filename = Path(path).name
        if not filename:
            return None

        if not self._has_media_extension(filename):
            return None
        return filename

    def _filename_from_resource_headers(self, raw_asset, download_url):
        if not download_url:
            return None

        service = getattr(raw_asset, "_service", None)
        session = getattr(service, "session", None)
        if session is None:
            return None

        for method_name, request_kwargs in (
            ("head", {"allow_redirects": True}),
            ("get", {"stream": True}),
        ):
            request_method = getattr(session, method_name, None)
            if not callable(request_method):
                continue

            response = None
            try:
                response = request_method(
                    download_url,
                    timeout=10,
                    **request_kwargs,
                )
                filename = self._filename_from_content_disposition(
                    getattr(response, "headers", {}).get("Content-Disposition")
                    or getattr(response, "headers", {}).get("content-disposition")
                )
                if filename:
                    return filename
            except Exception as exc:
                logger.debug(
                    "Could not read resource headers for filename recovery: %s",
                    exc,
                )
            finally:
                close_response = getattr(response, "close", None)
                if callable(close_response):
                    close_response()
        return None

    def _filename_from_content_disposition(self, content_disposition):
        if not content_disposition:
            return None

        for part in str(content_disposition).split(";")[1:]:
            key, separator, value = part.strip().partition("=")
            if not separator:
                continue

            normalized_key = key.casefold()
            if normalized_key == "filename*":
                filename = self._decode_extended_content_disposition_value(value)
            elif normalized_key == "filename":
                filename = self._strip_header_filename_value(value)
            else:
                continue

            filename = filename.replace("\\", "/").rsplit("/", 1)[-1]
            if filename and self._has_media_extension(filename):
                return filename
        return None

    def _decode_extended_content_disposition_value(self, value):
        normalized_value = self._strip_header_filename_value(value)
        if "''" in normalized_value:
            _, _, normalized_value = normalized_value.partition("''")
        return unquote(normalized_value)

    def _strip_header_filename_value(self, value):
        return str(value).strip().strip('"')

    def _has_media_extension(self, filename):
        extension = Path(filename).suffix.casefold()
        return extension in {
            ".heic",
            ".heif",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".tif",
            ".tiff",
            ".mov",
            ".mp4",
            ".m4v",
        }

    def _read_plain_filename_enc_value(self, encoded_value):
        filename = self._normalize_text_value(encoded_value)
        if filename and self._has_media_extension(filename):
            return filename
        return None

    def _decode_base64_filename(self, encoded_value):
        if isinstance(encoded_value, bytes):
            normalized_value = encoded_value.decode("utf-8", errors="ignore").strip()
        else:
            normalized_value = str(encoded_value).strip()

        if not normalized_value:
            return None

        normalized_value += "=" * (-len(normalized_value) % 4)
        try:
            return base64.b64decode(normalized_value).decode("utf-8")
        except ValueError:
            try:
                return base64.urlsafe_b64decode(normalized_value).decode("utf-8")
            except ValueError:
                return None

    def _build_skipped_asset_diagnostic(self, raw_asset):
        master_record = getattr(raw_asset, "_master_record", None)
        asset_record = getattr(raw_asset, "_asset_record", None)
        master_fields = self._safe_record_fields(master_record)
        asset_fields = self._safe_record_fields(asset_record)
        filename_entry = master_fields.get("filenameEnc")
        filename_value = None
        if isinstance(filename_entry, dict):
            filename_value = filename_entry.get("value")

        return {
            "asset_type": type(raw_asset).__name__,
            "asset_id": self._safe_asset_id(raw_asset),
            "master_record_type": type(master_record).__name__,
            "asset_record_type": type(asset_record).__name__,
            "master_field_keys": sorted(master_fields.keys()),
            "asset_field_keys": sorted(asset_fields.keys()),
            "filenameEnc_present": "filenameEnc" in master_fields,
            "filenameEnc_value_type": type(filename_value).__name__,
            "filenameEnc_value_length": (
                len(str(filename_value))
                if filename_value not in (None, "")
                else 0
            ),
            "filenameEnc_has_standard_base64_chars": self._has_only_base64_chars(
                filename_value,
                urlsafe=False,
            ),
            "filenameEnc_has_urlsafe_base64_chars": self._has_only_base64_chars(
                filename_value,
                urlsafe=True,
            ),
            "resource_fields": sorted(
                field_name
                for field_name in master_fields
                if field_name.endswith("Res")
            ),
            "resource_value_keys": self._resource_value_key_diagnostic(master_fields),
        }

    def _safe_record_fields(self, record):
        if not isinstance(record, dict):
            return {}
        fields = record.get("fields")
        if not isinstance(fields, dict):
            return {}
        return fields

    def _safe_asset_id(self, raw_asset):
        try:
            return self._read_asset_id(raw_asset)
        except Exception:
            return None

    def _has_only_base64_chars(self, value, *, urlsafe):
        if value in (None, ""):
            return False

        allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        allowed += "-_" if urlsafe else "+/"
        allowed += "="
        return all(char in allowed for char in str(value))

    def _resource_value_key_diagnostic(self, fields):
        resource_keys = {}
        for field_name, field_value in fields.items():
            if not field_name.endswith("Res") or not isinstance(field_value, dict):
                continue

            resource_value = field_value.get("value")
            if not isinstance(resource_value, dict):
                continue

            resource_keys[field_name] = sorted(resource_value.keys())
        return resource_keys

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
            if job.get("_matching_fetch_in_progress"):
                return self._copy_job_progress(job)

            job["_matching_fetch_in_progress"] = True
            try:
                asset_result = self.get_assets_for_album_ids(
                    job["selected_album_ids"],
                    force_refresh=True,
                )
            finally:
                job["_matching_fetch_in_progress"] = False

            if not asset_result.get("success"):
                job["status"] = "error"
                job["processed"] = 0
                job["total"] = 0
                job["percent"] = 0
                job["message"] = asset_result.get("error") or FAILED_TO_LOAD_ALBUM_ASSETS
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
                job["matched_assets"] = [
                    dict(asset)
                    for asset in job["match_results"]["assets"]
                ]
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
        if not os.access(source_path, os.R_OK):
            raise RuntimeError(
                "Configured source folder cannot be read. Check folder permissions in Windows and update Settings if needed."
            )

        write_check = validate_destination_folder(source_path)
        if write_check["status"] != STATUS_READY:
            raise RuntimeError(
                "Configured source folder cannot be written to. Choose a writable iCloud Photos folder in Settings before starting a sort."
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
