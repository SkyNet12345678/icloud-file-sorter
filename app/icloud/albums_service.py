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
