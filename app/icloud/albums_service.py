import logging

from app.icloud.icloud_service import ICloudService

logger = logging.getLogger("icloud-sorter")


class AlbumsService:
    def __init__(self, icloud_api):
        self.icloud = ICloudService(icloud_api)

    def get_albums(self):
        if not self.icloud:
            logger.warning("get_albums called but icloud service is not initialized")
            return []

        try:
            logger.info("Fetching albums")
            albums = self.icloud.get_albums()
            logger.info("Fetched %d albums", len(albums))
            return albums

        except Exception as e:
            logger.exception("Failed to fetch albums: %s", str(e))
            return []

    def start_sort(self, selected_indexes):
        if not self.icloud:
            logger.warning("start_sort called but icloud service is not initialized")
            return {"error": "Sorting service unavailable"}

        try:
            logger.info("Starting sort for %d selected album indexes", len(selected_indexes))
            return self.icloud.start_sort(selected_indexes)
        except Exception as e:
            logger.exception("Failed to start sort: %s", str(e))
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
        except Exception as e:
            logger.exception("Failed to get sort progress: %s", str(e))
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Failed to get sort progress",
            }
