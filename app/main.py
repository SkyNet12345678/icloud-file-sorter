import webview

from app.api.auth_api import AuthApi
from app.icloud.albums_service import AlbumsService
from app.logger import setup_logger
from app.settings import SettingsService

logger= setup_logger()
logger.info("App starting")

# --- API Bridge ---
auth_api = AuthApi()
settings_service = SettingsService()

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

    def get_settings(self):
        return {
            "success": True,
            "settings": settings_service.get_all(),
            "source_folder": settings_service.get_source_folder(),
            "sorting_approach": settings_service.get_sorting_approach(),
        }

    def save_settings(self, source_folder=None, sorting_approach=None):
        if source_folder is not None:
            settings_service.set_source_folder(source_folder)
        if sorting_approach is not None:
            settings_service.set_sorting_approach(sorting_approach)
        return {
            "success": True,
            "settings": settings_service.get_all(),
        }

    def detect_source_folder(self):
        detected = settings_service.detect_source_folder()
        return {
            "success": True,
            "source_folder": detected,
        }

# --- Create pywebview window ---
webview.create_window(
    "iCloud Photo Sorter",
    "ui/index.html",
    js_api=API(),
    width=800,
    height=600,
)

webview.start()
