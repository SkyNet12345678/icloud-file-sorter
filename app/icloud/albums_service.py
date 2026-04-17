import logging

from app.icloud.icloud_service import ICloudService

logger = logging.getLogger("icloud-sorter")


class AlbumsService:
    def __init__(self, icloud_api):
        self.icloud = ICloudService(icloud_api)

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

    def start_sort(self, selected_album_ids):
        if not self.icloud:
            logger.warning("start_sort called but icloud service is not initialized")
            return {"error": "Sorting service unavailable"}

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
                "message": "Sorting service unavailable",
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

    def _album_failure(self, error_message):
        return {
            "success": False,
            "albums": [],
            "error": error_message,
        }
