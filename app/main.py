import webview
import uuid
import os

from app.api.auth_api import AuthApi
from app.icloud.albums_service import AlbumsService
from app.logger import setup_logger

logger= setup_logger()
logger.info("App starting")

# skip login page in dev
DEV_BYPASS_LOGIN = os.getenv("DEV_BYPASS_LOGIN") == "1"

# --- API Bridge ---
auth_api = AuthApi()

class API:
    def __init__(self):
        # to skip the login page in dev
        # self.albums_service = None
        self.albums_service = AlbumsService(None) if DEV_BYPASS_LOGIN else None

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
        albums = self.get_albums()
        all_photos = next(album for album in albums if album["name"] == "All Photos")

        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "processed": 0,
            "total": all_photos["photos"],
            "percent": 0,
            "message": "Starting sort...",
        }

        return {"job_id": job_id}

    def get_sort_progress(self, job_id):
        job = self.jobs.get(job_id)

        if not job:
            return {
                "job_id": job_id,
                "status": "error",
                "processed": 0,
                "total": 0,
                "percent": 0,
                "message": "Unknown job id",
            }

        if job["status"] == "running":
            job["processed"] = min(job["processed"] + 50, job["total"])
            job["percent"] = int((job["processed"] / job["total"]) * 100)
            job["message"] = f'Processing photo {job["processed"]} of {job["total"]}'

            if job["processed"] >= job["total"]:
                job["status"] = "complete"
                job["percent"] = 100
                job["message"] = "Sort complete"

        return job

# --- Create pywebview window ---
webview.create_window(
    "iCloud Photo Sorter",
    "ui/index.html",
    js_api=API(),
    width=800,
    height=600,
)

webview.start()
