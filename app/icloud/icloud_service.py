class ICloudService:
    def __init__(self, api):
        self.api = api

    def get_albums(self):
        # Mock data for now
        return [
            {"name": "All Photos", "photos": 1847, "videos": 234},
            {"name": "Vacation 2025", "photos": 156, "videos": 23},
            {"name": "Family", "photos": 423, "videos": 67},
            {"name": "Screenshots", "photos": 89, "videos": 0},
            {"name": "Work Projects", "photos": 234, "videos": 12},
            {"name": "Pets", "photos": 312, "videos": 45},
            {"name": "Food", "photos": 178, "videos": 8},
            {"name": "Travel", "photos": 567, "videos": 89},
            {"name": "Events", "photos": 201, "videos": 34},
        ]
