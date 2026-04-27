from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Callable

from app.scanner import LocalScanner
from app.sorting.album_folders import build_album_folder_mappings, persist_album_folder_mappings
from app.sorting.file_operations import (
    STATUS_ALREADY_COPIED,
    STATUS_COPIED,
    STATUS_MOVED,
    copy_file,
    move_file,
)
from app.sorting.multi_album import SORTING_APPROACH_COPY, plan_sort_operations
from app.state.sort_state import (
    clean_missing_tracked_copy_paths,
    create_asset_state,
    create_job_state,
    default_sort_state,
    get_existing_tracked_copy_paths,
    normalize_sort_state,
    utc_now_iso,
)

JOB_STATUS_START = "start"
JOB_STATUS_MATCHING = "matching"
JOB_STATUS_PLANNING = "planning"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_CANCELLING = "cancelling"
JOB_STATUS_CANCELLED = "cancelled"
JOB_STATUS_COMPLETE = "complete"
JOB_STATUS_ERROR = "error"

STATUS_UNMATCHED = "unmatched"
STATUS_SKIPPED_AMBIGUOUS_MATCH = "skipped_ambiguous_match"

TERMINAL_STATUSES = {JOB_STATUS_CANCELLED, JOB_STATUS_COMPLETE, JOB_STATUS_ERROR}


class SortJobManager:
    def __init__(
        self,
        *,
        state_store=None,
        run_async: bool = True,
        operation_callback: Callable[[dict, dict], None] | None = None,
    ):
        self.state_store = state_store
        self.run_async = run_async
        self.operation_callback = operation_callback
        self.jobs: dict[str, dict] = {}
        self._lock = threading.RLock()

    def start_job(
        self,
        *,
        selected_album_ids: list[str],
        selected_albums: list[dict],
        source_folder: str,
        sorting_approach: str,
        asset_loader: Callable[[], dict],
        job_id: str | None = None,
    ) -> dict:
        job_id = job_id or str(uuid.uuid4())
        job = self._create_job(
            job_id=job_id,
            selected_album_ids=selected_album_ids,
            selected_albums=selected_albums,
            source_folder=source_folder,
            sorting_approach=sorting_approach,
        )
        with self._lock:
            self.jobs[job_id] = job

        self._persist_job(job)
        if self.run_async:
            thread = threading.Thread(
                target=self._run_job,
                args=(job_id, asset_loader),
                daemon=True,
            )
            job["_thread"] = thread
            thread.start()
        else:
            self._run_job(job_id, asset_loader)

        return {"job_id": job_id}

    def get_progress(self, job_id: str) -> dict:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return _unknown_job_progress(job_id)
            return self._copy_job_progress(job)

    def cancel_job(self, job_id: str) -> dict:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job:
                return _unknown_job_progress(job_id)
            if job["status"] in TERMINAL_STATUSES:
                return self._copy_job_progress(job)
            job["cancel_requested"] = True
            job["status"] = JOB_STATUS_CANCELLING
            job["message"] = "Cancelling sort after the current file operation..."
            self._update_percent(job)
            progress = self._copy_job_progress(job)
        self._persist_job(job)
        return progress

    def wait_for_job(self, job_id: str, timeout: float | None = None) -> None:
        with self._lock:
            thread = self.jobs.get(job_id, {}).get("_thread")
        if thread is not None:
            thread.join(timeout=timeout)

    def _run_job(self, job_id: str, asset_loader: Callable[[], dict]) -> None:
        try:
            self._execute_job(job_id, asset_loader)
        except Exception as exc:  # pragma: no cover - defensive terminal state
            with self._lock:
                job = self.jobs[job_id]
                job["status"] = JOB_STATUS_ERROR
                job["message"] = str(exc) or "Sort job failed"
                job["errors"].append(job["message"])
                job["completed_at"] = utc_now_iso()
            self._persist_job(job)

    def _execute_job(self, job_id: str, asset_loader: Callable[[], dict]) -> None:
        state = self._load_state()
        with self._lock:
            job = self.jobs[job_id]
            job["status"] = JOB_STATUS_MATCHING
            job["started_at"] = utc_now_iso()
            job["message"] = "Fetching iCloud metadata for selected albums..."
        self._persist_job(job, state=state)

        asset_result = asset_loader()
        if not asset_result.get("success"):
            self._fail_job(job_id, asset_result.get("error") or "Failed to load album assets", state)
            return

        selected_assets = asset_result.get("assets", [])
        with self._lock:
            job = self.jobs[job_id]
            job["selected_assets"] = [dict(asset) for asset in selected_assets]
            job["total_assets"] = len(selected_assets)
            job["message"] = _matching_message(selected_assets)
        self._persist_job(job, state=state)

        tracked_copy_paths = get_existing_tracked_copy_paths(state)
        scanner = LocalScanner(job["source_folder"], ignored_paths=tracked_copy_paths)
        scanner.scan()
        match_results = scanner.match_assets(selected_assets)

        with self._lock:
            job = self.jobs[job_id]
            job["match_results"] = match_results
            job["matched_assets"] = [dict(asset) for asset in match_results["assets"]]
            job["status"] = JOB_STATUS_PLANNING
            job["message"] = "Planning file operations..."
        self._persist_job(job, state=state)

        state = persist_album_folder_mappings(
            state,
            build_album_folder_mappings(
                job["source_folder"],
                job["selected_albums"],
                existing_mappings=state.get("album_folder_mappings", {}),
            ),
        )
        operations = plan_sort_operations(
            match_results["assets"],
            state["album_folder_mappings"],
            sorting_approach=job["sorting_approach"],
        )

        with self._lock:
            job = self.jobs[job_id]
            job["operations"] = [dict(operation) for operation in operations]
            job["total"] = len(operations)
            job["processed"] = 0
            job["summary"] = _empty_summary()
            self._record_match_outcomes(job, match_results["assets"])
            if job.get("cancel_requested"):
                self._mark_job_cancelled(job)
            elif operations:
                job["status"] = JOB_STATUS_RUNNING
                job["message"] = _running_message(job)
            else:
                job["status"] = JOB_STATUS_COMPLETE
                job["message"] = _complete_message(job)
                job["percent"] = 100
                job["completed_at"] = utc_now_iso()
        self._persist_job(job, state=state)

        if job["status"] == JOB_STATUS_CANCELLED or not operations:
            return

        for operation in operations:
            with self._lock:
                job = self.jobs[job_id]
                if job.get("cancel_requested"):
                    self._cancel_job(job, state)
                    return

            result = self._execute_operation(operation, tracked_copy_paths)

            with self._lock:
                job = self.jobs[job_id]
                operation.update(result)
                job["processed"] += 1
                self._record_operation_result(job, operation, state)
                self._update_percent(job)
                job["message"] = _running_message(job)
                if result["status"] == STATUS_COPIED:
                    tracked_copy_paths.add(result["destination_path"])
                if self.operation_callback is not None:
                    self.operation_callback(job, operation)
            self._persist_job(job, state=state)

        with self._lock:
            job = self.jobs[job_id]
            if job.get("cancel_requested"):
                self._cancel_job(job, state)
                return
            job["status"] = JOB_STATUS_COMPLETE
            job["percent"] = 100
            job["message"] = _complete_message(job)
            job["completed_at"] = utc_now_iso()
        self._persist_job(job, state=state)

    def _execute_operation(self, operation: dict, tracked_copy_paths: set[str]) -> dict:
        if operation["operation"] == SORTING_APPROACH_COPY:
            return copy_file(
                operation["source_path"],
                operation["destination_path"],
                tracked_copy_paths=tracked_copy_paths,
            )
        return move_file(operation["source_path"], operation["destination_path"])

    def _cancel_job(self, job: dict, state: dict) -> None:
        self._mark_job_cancelled(job)
        self._persist_job(job, state=state)

    def _mark_job_cancelled(self, job: dict) -> None:
        job["status"] = JOB_STATUS_CANCELLED
        job["summary"]["remaining"] = max(job["total"] - job["processed"], 0)
        job["message"] = "Sort cancelled. Completed operations were not rolled back."
        job["completed_at"] = utc_now_iso()
        self._update_percent(job)

    def _fail_job(self, job_id: str, message: str, state: dict) -> None:
        with self._lock:
            job = self.jobs[job_id]
            job["status"] = JOB_STATUS_ERROR
            job["message"] = message
            job["errors"].append(message)
            job["completed_at"] = utc_now_iso()
        self._persist_job(job, state=state)

    def _create_job(
        self,
        *,
        job_id: str,
        selected_album_ids: list[str],
        selected_albums: list[dict],
        source_folder: str,
        sorting_approach: str,
    ) -> dict:
        return {
            "job_id": job_id,
            "status": JOB_STATUS_START,
            "processed": 0,
            "total": 0,
            "total_assets": 0,
            "percent": 0,
            "selected_album_ids": list(selected_album_ids),
            "selected_albums": [dict(album) for album in selected_albums],
            "selected_album_names": [album.get("name") for album in selected_albums],
            "selected_assets": [],
            "matched_assets": [],
            "operations": [],
            "source_folder": str(source_folder),
            "sorting_approach": sorting_approach,
            "match_results": _empty_match_results(),
            "summary": _empty_summary(),
            "details": [],
            "errors": [],
            "message": "Preparing matching job...",
            "cancel_requested": False,
            "created_at": utc_now_iso(),
            "started_at": None,
            "completed_at": None,
        }

    def _record_match_outcomes(self, job: dict, matched_assets: list[dict]) -> None:
        for asset in matched_assets:
            if asset.get("match_type") == "none":
                self._record_detail(job, asset, STATUS_UNMATCHED)
            elif asset.get("match_type") == "ambiguous":
                self._record_detail(job, asset, STATUS_SKIPPED_AMBIGUOUS_MATCH)

    def _record_operation_result(self, job: dict, operation: dict, state: dict) -> None:
        status = operation["status"]
        summary = job["summary"]
        summary[status] = summary.get(status, 0) + 1
        summary["processed"] = job["processed"]
        summary["remaining"] = max(job["total"] - job["processed"], 0)

        asset_state = self._asset_state_for_operation(job, operation, state)
        job.setdefault("processed_assets", {})[operation["asset_id"]] = asset_state

        if status not in {STATUS_MOVED, STATUS_COPIED}:
            job["details"].append(_operation_detail(operation))

    def _record_detail(self, job: dict, asset: dict, status: str) -> None:
        summary = job["summary"]
        summary[status] = summary.get(status, 0) + 1
        detail = {
            "asset_id": asset.get("asset_id"),
            "filename": asset.get("filename"),
            "status": status,
            "error": None,
        }
        if status == STATUS_SKIPPED_AMBIGUOUS_MATCH:
            detail["candidate_paths"] = list(asset.get("candidate_paths", []))
        job["details"].append(detail)

    def _asset_state_for_operation(self, job: dict, operation: dict, state: dict) -> dict:
        persisted = state.get("processed_assets", {}).get(operation["asset_id"], {})
        current = job.setdefault("processed_assets", {}).get(operation["asset_id"], {})
        persisted = persisted if isinstance(persisted, dict) else {}
        current = current if isinstance(current, dict) else {}
        copy_paths = _merge_copy_paths(
            persisted.get("app_created_copy_paths", []),
            current.get("app_created_copy_paths", []),
        )
        existing = {**persisted, **current}
        moved_path = existing.get("moved_path")
        if (
            operation["status"] in {STATUS_COPIED, STATUS_ALREADY_COPIED}
            and operation["destination_path"] not in copy_paths
        ):
            copy_paths.append(operation["destination_path"])
        if operation["status"] == STATUS_MOVED:
            moved_path = operation["destination_path"]

        return create_asset_state(
            operation["asset_id"],
            filename=operation.get("filename"),
            status=operation["status"],
            canonical_path=operation["source_path"],
            moved_path=moved_path,
            app_created_copy_paths=copy_paths,
            error=operation.get("error"),
        )

    def _copy_job_progress(self, job: dict) -> dict:
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "processed": job["processed"],
            "total": job["total"],
            "percent": job["percent"],
            "message": job["message"],
            "match_results": _copy_match_results_summary(job.get("match_results")),
            "summary": dict(job.get("summary", {})),
            "details": [dict(detail) for detail in job.get("details", [])],
        }

    def _update_percent(self, job: dict) -> None:
        if job["total"]:
            job["percent"] = int((job["processed"] / job["total"]) * 100)
        elif job["status"] in TERMINAL_STATUSES:
            job["percent"] = 100
        else:
            job["percent"] = 0

    def _load_state(self) -> dict:
        if self.state_store is None:
            return default_sort_state()
        return clean_missing_tracked_copy_paths(self.state_store.load())

    def _persist_job(self, job: dict, *, state: dict | None = None) -> None:
        if self.state_store is None:
            return
        state = normalize_sort_state(state or self._load_state())
        job_state = create_job_state(
            job["job_id"],
            selected_albums=job["selected_albums"],
            source_folder=job["source_folder"],
            sorting_approach=job["sorting_approach"],
            album_folder_mappings=state.get("album_folder_mappings", {}),
            status=job["status"],
            now=job["created_at"],
        )
        job_state.update(
            {
                "status": job["status"],
                "processed": job["processed"],
                "total": job["total"],
                "percent": job["percent"],
                "message": job["message"],
                "match_results": _copy_match_results_summary(job.get("match_results")),
                "processed_assets": job.get("processed_assets", {}),
                "summary": dict(job.get("summary", {})),
                "details": [dict(detail) for detail in job.get("details", [])],
                "errors": list(job.get("errors", [])),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "updated_at": utc_now_iso(),
            }
        )
        state["active_job_id"] = None if job["status"] in TERMINAL_STATUSES else job["job_id"]
        state["jobs"][job["job_id"]] = job_state
        for asset_id, asset_state in job.get("processed_assets", {}).items():
            state["processed_assets"][asset_id] = asset_state
        self.state_store.save(state)


def _merge_copy_paths(*path_groups: list[str]) -> list[str]:
    merged = []
    for paths in path_groups:
        for path in paths or []:
            if path and path not in merged:
                merged.append(path)
    return merged


def _empty_match_results() -> dict:
    return {
        "matched": 0,
        "fallback_matched": 0,
        "not_found": 0,
        "ambiguous": 0,
        "assets": [],
    }


def _copy_match_results_summary(match_results: dict | None) -> dict:
    summary = _empty_match_results()
    if isinstance(match_results, dict):
        for key in ("matched", "fallback_matched", "not_found", "ambiguous"):
            try:
                summary[key] = int(match_results.get(key, 0))
            except (TypeError, ValueError):
                summary[key] = 0
    summary.pop("assets")
    return summary


def _empty_summary() -> dict:
    return {
        "processed": 0,
        "remaining": 0,
        "moved": 0,
        "copied": 0,
        "already_sorted": 0,
        "already_copied": 0,
        "skipped_destination_exists": 0,
        "skipped_source_missing": 0,
        "failed_filesystem_error": 0,
        STATUS_UNMATCHED: 0,
        STATUS_SKIPPED_AMBIGUOUS_MATCH: 0,
    }


def _unknown_job_progress(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "status": JOB_STATUS_ERROR,
        "processed": 0,
        "total": 0,
        "percent": 0,
        "message": "Unknown job id",
        "match_results": _copy_match_results_summary(None),
        "summary": _empty_summary(),
        "details": [],
    }


def _matching_message(selected_assets: list[dict]) -> str:
    asset_count = len(selected_assets)
    suffix = "asset" if asset_count == 1 else "assets"
    return f"Fetched iCloud metadata for {asset_count} {suffix}. Matching local files..."


def _running_message(job: dict) -> str:
    return f"Processing file operation {job['processed']} of {job['total']}. {_match_quality_message(job)}"


def _complete_message(job: dict) -> str:
    return f"Sort complete. {_match_quality_message(job)}"


def _match_quality_message(job: dict) -> str:
    match_results = _copy_match_results_summary(job.get("match_results"))
    return (
        "Filename-only matching: "
        f"Exact: {match_results['matched']} | "
        f"Not found: {match_results['not_found']} | "
        f"Ambiguous: {match_results['ambiguous']}"
    )


def _operation_detail(operation: dict) -> dict:
    return {
        "asset_id": operation.get("asset_id"),
        "filename": operation.get("filename"),
        "album_id": operation.get("album_id"),
        "operation": operation.get("operation"),
        "source_path": operation.get("source_path"),
        "destination_path": operation.get("destination_path"),
        "status": operation.get("status"),
        "error": operation.get("error"),
    }
