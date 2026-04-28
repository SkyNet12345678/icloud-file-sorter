import logging

from app.icloud.icloud_service import ICloudService

logger = logging.getLogger("icloud-sorter")

SORTING_SERVICE_UNAVAILABLE = "Sorting service unavailable"


class AlbumsService:
    def __init__(self, icloud_api, settings_service=None):
        self.icloud = ICloudService(
            icloud_api,
            settings_service=settings_service,
        )

    def get_albums(self):
        if not self.icloud:
            logger.warning("get_albums called but icloud service is not initialized")
            return self._album_failure("Album service unavailable")

        try:
            logger.info("Fetching albums")
            result = self.icloud.get_albums()
            if result.get("success"):
                logger.info("Fetched %d albums", len(result["albums"]))
            else:
                logger.warning("Album fetch failed: %s", result.get("error"))
            return result

        except Exception as exc:
            logger.exception("Failed to fetch albums: %s", exc)
            return self._album_failure(str(exc) or "Failed to fetch albums")

    def get_album_assets(self, album_id):
        if not self.icloud:
            logger.warning("get_album_assets called but icloud service is not initialized")
            return {"success": False, "album": None, "assets": [], "error": "Album service unavailable"}

        try:
            logger.info("Fetching assets for album %s", album_id)
            result = self.icloud.get_album_assets(album_id)
            if result.get("success"):
                logger.info("Fetched %d assets for album %s", len(result.get("assets", [])), album_id)
            else:
                logger.warning("Asset fetch failed for album %s: %s", album_id, result.get("error"))
            return result
        except Exception as exc:
            logger.exception("Failed to fetch assets for album %s: %s", album_id, exc)
            return {"success": False, "album": None, "assets": [], "error": str(exc) or "Failed to fetch album assets"}

    def start_sort(self, selected_album_ids):
        if not self.icloud:
            logger.warning("start_sort called but icloud service is not initialized")
            return {"error": SORTING_SERVICE_UNAVAILABLE}

        try:
            logger.info("Starting sort for %d selected album ids", len(selected_album_ids))
            return self.icloud.start_sort(selected_album_ids)
        except Exception as exc:
            logger.exception("Failed to start sort: %s", exc)
            return {"error": "Failed to start sort"}

    def get_sort_progress(self, job_id):
        if not self.icloud:
            logger.warning("get_sort_progress called but icloud service is not initialized")
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": SORTING_SERVICE_UNAVAILABLE,
            }

        try:
            return self.icloud.get_sort_progress(job_id)
        except Exception as exc:
            logger.exception("Failed to get sort progress: %s", exc)
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Failed to get sort progress",
            }

    def cancel_sort(self, job_id):
        if not self.icloud:
            logger.warning("cancel_sort called but icloud service is not initialized")
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": SORTING_SERVICE_UNAVAILABLE,
            }

        try:
            return self.icloud.cancel_sort(job_id)
        except Exception as exc:
            logger.exception("Failed to cancel sort: %s", exc)
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Failed to cancel sort",
            }

    def _album_failure(self, error_message):
        return {
            "success": False,
            "albums": [],
            "error": error_message,
        }
