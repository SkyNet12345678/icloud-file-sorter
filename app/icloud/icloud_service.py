class ICloudService:
    def __init__(self, api):
        self.api = api

    def get_albums(self):
        # Mock data for now
        return [
            {"name": "Recents", "count": 120},
            {"name": "Favorites", "count": 45},
            {"name": "Vacation 2024", "count": 200},
            {"name": "Family", "count": 80},
        ]
