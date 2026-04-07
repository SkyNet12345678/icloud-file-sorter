from app.icloud.icloud_service import ICloudService


class AlbumsService:
    def __init__(self, icloud_api):
        self.icloud = ICloudService(icloud_api)

    def get_albums(self):
        if not self.icloud:
            return []

        try:
            return self.icloud.get_albums()
        except Exception as e:
            print("ERROR in get_albums:", e)
            return []
