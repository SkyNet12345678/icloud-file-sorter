import uuid


class ICloudService:
    def __init__(self, api):
        self.api = api
        self.jobs = {}

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

    def start_sort(self, selected_indexes):
        albums = self.get_albums()
        all_photos = next(album for album in albums if album["name"] == "All Photos")
        selected_albums = [
            albums[index]["name"]
            for index in selected_indexes
            if 0 <= index < len(albums) and albums[index]["name"] != "All Photos"
        ]

        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "processed": 0,
            "total": all_photos["photos"],
            "percent": 0,
            "selected_albums": selected_albums,
            "message": f"Starting sort for {len(selected_albums)} album(s)...",
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
            job["percent"] = int((job["processed"] / job["total"]) * 100) if job["total"] else 100
            job["message"] = f'Processing photo {job["processed"]} of {job["total"]}'

            if job["processed"] >= job["total"]:
                job["status"] = "complete"
                job["percent"] = 100
                job["message"] = "Sort complete"

        return job
