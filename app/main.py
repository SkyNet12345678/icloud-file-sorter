import webview

from app.api.auth_api import AuthApi
from app.icloud.albums_service import AlbumsService
from app.logger import setup_logger

logger= setup_logger()
logger.info("App starting")

# --- API Bridge ---
auth_api = AuthApi()

class API:
    def __init__(self):
        self.albums_service = None

    def login(self, apple_id, password):
        result = auth_api.login(apple_id, password)
        if result.get("success"):
            self.albums_service = AlbumsService(auth_api.api)
        return result

    def verify_2fa(self, code):
        result = auth_api.verify_2fa(code)
        if result.get("success"):
            self.albums_service = AlbumsService(auth_api.api)
        return result

    def get_albums(self):
        if not self.albums_service:
            return {
                "success": False,
                "albums": [],
                "error": "Album service unavailable",
            }
        return self.albums_service.get_albums()
    
    def get_album_assets(self, album_id):
        if not self.albums_service:
            return {
                "success": False,
                "album": None,
                "assets": [],
                "error": "Album service unavailable",
            }
        result = self.albums_service.get_album_assets(album_id)
        if result.get("success"):
            album = result.get("album") or {}
            logger.info(
                "Bridge: get_album_assets returned %d assets for '%s'",
                len(result.get("assets", [])),
                album.get("name", album_id),
            )
        return result

    def start_sort(self, selected_album_ids):
        if not self.albums_service:
            return {"error": "Sorting service unavailable"}
        return self.albums_service.start_sort(selected_album_ids)

    def get_sort_progress(self, job_id):
        if not self.albums_service:
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Sorting service unavailable",
            }
        return self.albums_service.get_sort_progress(job_id)

# --- Create pywebview window ---
webview.create_window(
    "iCloud Photo Sorter",
    "ui/index.html",
    js_api=API(),
    width=800,
    height=600,
)

webview.start()
