import webview
import os

from app.api.auth_api import AuthApi
from app.icloud.albums_service import AlbumsService
from app.logger import setup_logger

logger= setup_logger()
logger.info("App starting")

# skip login page in dev
# run with "DEV_BYPASS_LOGIN=1 python -m main.py"
DEV_BYPASS_LOGIN = os.getenv("DEV_BYPASS_LOGIN") == "1"

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
            return []
        return self.albums_service.get_albums()
    
    def start_sort(self, selected_indexes):
        if not self.albums_service:
            return {"error": "Sorting service unavailable"}
        return self.albums_service.start_sort(selected_indexes)

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
