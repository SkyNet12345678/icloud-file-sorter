import logging
import uuid

logger = logging.getLogger("icloud-sorter")

DEFAULT_MOCK_SORT_TOTAL = 1847


def _album_type_name(album):
    return type(album).__name__


class ICloudService:
    def __init__(self, api):
        self.api = api
        self.jobs = {}
        self.album_summaries_by_id = {}

    def get_albums(self):
        if not self.api:
            return self._failure_result("iCloud session unavailable")

        try:
            raw_albums = self._get_raw_albums()
            normalized_albums = []
            summaries_by_id = {}

            for raw_album in raw_albums:
                summary = self._normalize_album_summary(raw_album)
                if summary is None:
                    continue
                normalized_albums.append(summary)
                summaries_by_id[summary["id"]] = summary

            normalized_albums.sort(key=lambda album: album["name"].casefold())
            self.album_summaries_by_id = summaries_by_id
            return {
                "success": True,
                "albums": normalized_albums,
                "error": None,
            }
        except Exception as exc:
            logger.exception("Failed to retrieve albums from iCloud: %s", exc)
            return self._failure_result(str(exc) or "Failed to fetch albums")

    def start_sort(self, selected_album_ids):
        selected_ids = self._filter_known_album_ids(
            self._dedupe_selected_album_ids(selected_album_ids)
        )
        if not selected_ids:
            return {"error": "No albums selected"}

        selected_albums = self._resolve_selected_album_names(selected_ids)

        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "processed": 0,
            "total": DEFAULT_MOCK_SORT_TOTAL,
            "percent": 0,
            "selected_album_ids": selected_ids,
            "selected_albums": selected_albums,
            "message": f"Starting sort for {len(selected_ids)} album(s)...",
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

        if job["status"] == "running":
            job["processed"] = min(job["processed"] + 50, job["total"])
            job["percent"] = int((job["processed"] / job["total"]) * 100) if job["total"] else 100
            job["message"] = f'Processing photo {job["processed"]} of {job["total"]}'

            if job["processed"] >= job["total"]:
                job["status"] = "complete"
                job["percent"] = 100
                job["message"] = "Sort complete"

        return job

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
        if self._is_system_album(album):
            return False
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
        if not self.album_summaries_by_id:
            return selected_album_ids

        return [
            album_id
            for album_id in selected_album_ids
            if album_id in self.album_summaries_by_id
        ]

    def _failure_result(self, error_message):
        return {
            "success": False,
            "albums": [],
            "error": error_message,
        }
