class AlbumsService:
    def __init__(self, icloud_service):
        self.icloud = icloud_service

    def get_albums(self):
        if not self.icloud:
            print("icloud is None")
            return []

        try:
            return self.icloud.get_albums()
        except Exception as e:
            print("ERROR in get_albums:", e)
            return []