"""Local filename scanning and matching for the MVP sort flow.

Automatic matching is intentionally filename-only. iCloud for Windows can expose
placeholder-oriented local metadata, so local size and timestamp values are not
reliable enough for safe fallback matching. Unresolved assets stay as
``none`` or ``ambiguous`` instead of being guessed from weak heuristics.
"""

from __future__ import annotations

from pathlib import Path


def normalize_filename(filename: str | None) -> str | None:
    if filename is None:
        return None

    normalized_value = Path(str(filename).strip()).name
    if not normalized_value:
        return None
    return normalized_value.casefold()


class LocalScanner:
    def __init__(
        self,
        source_folder: str | Path,
        *,
        ignored_paths: set[str] | list[str] | tuple[str, ...] | None = None,
    ):
        self.source_folder = Path(source_folder)
        self.ignored_paths = {
            _normalize_path_key(path)
            for path in ignored_paths or []
            if path
        }
        self.filename_index: dict[str, list[dict]] = {}
        self.scanned_files: list[dict] = []

    def scan(self) -> list[dict]:
        self.filename_index = {}
        self.scanned_files = []

        for path in sorted(self.source_folder.rglob("*")):
            if not path.is_file():
                continue
            if _normalize_path_key(path) in self.ignored_paths:
                continue

            file_record = {
                "filename": path.name,
                "local_path": str(path),
            }
            self.scanned_files.append(file_record)

            normalized_filename = normalize_filename(path.name)
            if normalized_filename is None:
                continue
            self.filename_index.setdefault(normalized_filename, []).append(file_record)

        return [dict(file_record) for file_record in self.scanned_files]

    def match_assets(self, assets: list[dict]) -> dict:
        if not self.scanned_files:
            self.scan()

        match_results = {
            "matched": 0,
            # Kept for bridge compatibility until a verified fallback strategy exists.
            "fallback_matched": 0,
            "not_found": 0,
            "ambiguous": 0,
            "assets": [],
        }

        for asset in assets:
            matched_asset = {
                "asset_id": asset.get("asset_id"),
                "filename": asset.get("filename"),
                "original_filename": asset.get("original_filename"),
                "created_at": asset.get("created_at"),
                "size": asset.get("size"),
                "media_type": asset.get("media_type"),
                "album_memberships": [
                    dict(membership)
                    for membership in asset.get("album_memberships", [])
                ],
                "local_path": None,
                "match_type": "none",
            }

            normalized_filename = normalize_filename(
                asset.get("filename") or asset.get("original_filename")
            )
            candidate_matches = []
            if normalized_filename is not None:
                candidate_matches = self.filename_index.get(normalized_filename, [])

            if len(candidate_matches) == 1:
                matched_asset["local_path"] = candidate_matches[0]["local_path"]
                matched_asset["match_type"] = "exact"
                match_results["matched"] += 1
            elif len(candidate_matches) > 1:
                matched_asset["match_type"] = "ambiguous"
                matched_asset["candidate_paths"] = [
                    candidate["local_path"]
                    for candidate in candidate_matches
                ]
                match_results["ambiguous"] += 1
            else:
                match_results["not_found"] += 1

            match_results["assets"].append(matched_asset)

        return match_results


def _normalize_path_key(path: str | Path) -> str:
    return str(Path(path).resolve(strict=False)).casefold()
