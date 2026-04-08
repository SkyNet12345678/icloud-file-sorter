import webview
import uuid

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
            return []
        return self.albums_service.get_albums()
    
    def start_sort(self, selected_indexes):
        job_id = str(uuid.uuid4())
        album_data = self.get_albums()
        print(album_data)
        return {"job_id": job_id}
    
#     def get_sort_progress(job_id):
#         payload = {
#   "job_id": "string",
#   "status": "idle | running | complete | error",
#   "processed": 120,
#   "total": 1847,
#   "percent": 6,
#   "message": "Processing photo 120 of 1847"
# }
#         return

# --- Create pywebview window ---
webview.create_window(
    "iCloud Photo Sorter",
    "ui/index.html",
    js_api=API(),
    width=800,
    height=600,
)

webview.start()
