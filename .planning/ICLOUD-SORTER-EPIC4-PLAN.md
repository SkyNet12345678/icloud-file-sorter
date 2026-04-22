# Epic 4: Local File Scanning & Matching

## Alignment To Higher Plan

This detailed plan is aligned to `.planning/ICLOUD-SORTER-PLAN.md` as follows:

- Epic 4 covers local scanning and cloud-to-local matching only.
- Expensive iCloud asset metadata fetch, local scanning, and matching happen only when sorting starts.
- Matching uses the local iCloud Photos source folder, not a separate target directory.
- Match quality and failure counts are exposed to the UI.
- MVP automatic matching is filename-only because local iCloud placeholder metadata is not reliable enough for safe size/date fallback matching.
- The temporary `Test Asset Fetch` button is removed by the end of this epic.

This epic does not introduce new settings scope.

- Source folder persistence and sort-behavior settings belong to Epic 6 at the higher-plan level.
- In the current codebase, the settings baseline already exists and Epic 4 should consume it rather than redesign it.

## Existing Baseline

These pieces already exist and should be treated as dependencies, not new Epic 4 work:

- `app/settings.py`
- `API.get_settings()` / `API.save_settings()` / `API.detect_source_folder()` in `app/main.py`
- settings UI in `app/ui/index.html` and `app/ui/js/settings.js`

Epic 4 should reuse that baseline.

## In Scope

- validate the configured source folder when a sort starts
- fetch per-asset metadata from iCloud only after sort starts
- aggregate selected album assets while preserving album membership order
- scan the local source folder during the active sort job
- build a fast local filename index
- match selected iCloud assets to local files
- detect ambiguity explicitly
- expose exact/not-found/ambiguous counts to progress UI
- keep matching integrated with the current pywebview bridge and sort-progress polling

## Out Of Scope

- new settings schema changes
- startup prerequisite detection beyond what is already implemented elsewhere
- a separate target directory setting
- final file-moving/copying engine details beyond what is needed to hand matched files into Epic 5
- database-backed history

## Dependency Decisions

- Epic 3 album summaries are a hard dependency.
- Per-asset metadata fetch belongs to Epic 4 and must happen only inside the active sort job.
- Matching must operate on the aggregated asset set from selected albums so shared assets are not double-counted.
- Keep the UI bridge stable: `start_sort(selected_album_ids)` should remain the JS contract.
- Pass settings into the sort path by dependency injection in Python, not by adding new frontend parameters to `start_sort()`.

Recommended wiring:

- `app/main.py`: construct `AlbumsService` with the existing `SettingsService`
- `app/icloud/albums_service.py`: pass `SettingsService` into `ICloudService`
- `app/icloud/icloud_service.py`: read `source_folder` and sort behavior from the injected settings service

## Phase 1: Settings Baseline

Status: already implemented

Purpose:

- establish the existing settings dependency used by this epic

Already present:

- JSON-backed settings service
- source folder persistence and detection methods
- sorting approach persistence
- settings UI and copy warning

Verification:

- `pywebview.api.get_settings()` returns current settings
- changing source folder or sorting approach in the UI persists through `save_settings()`
- reloading settings restores the saved values

Done when:

- no additional Epic 4 work is required to create or redesign settings infrastructure

---

## Phase 2: Sort-Time Asset Fetch & Folder Validation

Goal:

- make the sort job validate the configured source folder and fetch selected album asset metadata from iCloud only after sort start

Deliverable:

- starting a sort transitions into a visible `matching` stage and fetches selected album asset metadata from iCloud without changing album-browsing behavior

Implementation:

- validate `source_folder` exists and is a directory
- in `ICloudService.start_sort()`, fetch asset metadata only for the selected album ids
- aggregate assets across selected albums and preserve ordered `album_memberships`
- add job status support for `matching`
- return a clear user-facing error when the source folder is missing or not configured

Aggregated asset shape:

```python
{
  "asset_id": "...",
  "filename": "IMG_1234.HEIC",
  "original_filename": "IMG_1234.HEIC",
  "created_at": "2025-01-15T10:30:00Z",
  "size": 1234567,
  "media_type": "image",
  "album_memberships": [
    {
      "album_id": "album-1",
      "album_name": "Vacation 2025",
      "selection_order": 0,
    }
  ]
}
```

Tests:
- service test proving album browsing still returns only lightweight album summaries
- service test that sort start fetches asset metadata for selected albums only
- service test that overlapping albums produce one aggregated asset with multiple memberships
- service test that `start_sort()` returns a clear error when `source_folder` is unavailable

User verification:

- browse albums without waiting for asset-level fetches
- with a valid source folder configured, start a sort and see the job enter `matching`
- with an invalid source folder configured, start a sort and see a clear error instead of a silent failure

Done when:

- sort start performs folder validation
- iCloud asset metadata fetch happens only after sort start
- progress polling can report `matching`

---

## Phase 3: Local Scan Integration, Exact Matching & Ambiguity Handling

Goal:

- scan the local source folder and match selected assets to local files by filename first while detecting ambiguity explicitly

Deliverable:

- the backend produces structured exact-match results for the aggregated selected assets

Implementation:

- new file: `app/scanner.py`
- create `LocalScanner(source_folder)`
- build a case-insensitive filename index during `scan()`
- add `LocalScanner.match_assets(assets)`
- exact match by normalized filename first
- if one local file matches, mark `match_type: "exact"`
- if multiple local files match the same asset key, mark `match_type: "ambiguous"`
- if no filename match exists, mark `match_type: "none"` for now
- store match summary on the job state

Result shape:

```python
{
  "matched": 1450,
  "fallback_matched": 0,
  "not_found": 12,
  "ambiguous": 3,
  "assets": [
    {
      "asset_id": "...",
      "filename": "IMG_1234.HEIC",
      "local_path": "C:/Users/.../IMG_1234.HEIC",
      "match_type": "exact",
      "album_memberships": [...],
    }
  ]
}
```

Tests:

- `tests/scanner/test_local_scanner.py`
- `tests/scanner/test_matching.py`
- index build from a temporary directory
- case-insensitive filename normalization
- exact match success
- no-match result
- ambiguous match result when duplicate filenames exist locally
- service test proving multi-album assets are matched once from the aggregated asset set

User verification:

- start a sort for an album with known local files and see match counts appear in progress or final status
- select overlapping albums and verify shared assets are not counted twice

Done when:

- local scan happens only after sort-time asset fetch begins
- filename-first matching works on aggregated asset metadata
- ambiguity is counted separately from not-found
- job state contains structured match results

---

## Phase 4: Filename-Only Matching Policy & Match Quality Reporting

Goal:

- lock Epic 4 to filename-only automatic matching for MVP and surface match quality clearly without introducing unsafe metadata fallbacks

Deliverable:

- the plan explicitly rejects size/date fallback matching for MVP and the UI-visible progress reports filename-only match quality

Implementation:

- document the filename-only matching policy for the default flat iCloud Photos source folder
- document that local iCloud placeholder files do not provide reliable size/date metadata for automatic fallback matching
- preserve explicit `match_type` values used by the current matcher: `exact`, `none`, `ambiguous`
- include match summary in sort progress payloads and user-visible status text
- if the backend continues exposing `fallback_matched` for bridge compatibility, keep it at `0` until a verified fallback strategy exists

Why metadata fallback is rejected for MVP:

- local iCloud placeholder files can report placeholder-oriented filesystem metadata rather than trustworthy cloud asset metadata
- local logical file size and timestamps are therefore not reliable enough to use as automatic matching keys
- weak metadata heuristics would create false-positive matches, which is worse than surfacing `none` or `ambiguous`

Tests:

- progress payload includes `match_results`
- unresolved assets remain `none` when no filename match exists
- duplicate filename hits remain `ambiguous`
- no new automatic fallback match type is introduced for MVP

User verification:

- run a sort where at least one asset has no filename hit and verify it is reported as not found instead of being force-matched by metadata
- run a sort against a source tree with duplicate filenames and verify those assets are reported as ambiguous
- confirm the progress text or completion text reports counts similar to `Exact: X | Not found: Z | Ambiguous: A`

Done when:

- the plan and code path both treat filename-only matching as the only automatic matcher for MVP
- UI-visible progress includes filename-only match quality counts

---

## Phase 5: Sort-Path Handoff, Cleanup, And Regression Coverage

Goal:

- finalize Epic 4 so the sort flow hands matched asset data cleanly into Epic 5 and remove temporary Epic 3 debugging UI

Deliverable:

- the sort path uses real match data as its handoff point and the temporary test button is gone

Implementation:

- ensure job state contains the matched asset list needed by the later sorting engine
- keep current mock sorting behavior only as a downstream placeholder
- remove `<button id="test-fetch-btn">` from `app/ui/index.html`
- remove `testFetchAlbumAssets()` wiring from `app/ui/js/albums.js` and `app/ui/js/main.js`
- update bridge/service tests affected by richer progress payloads and matching status

Tests:

- update `tests/test_main_api_bridge.py`
- update `tests/test_sorting_services.py`
- verify existing album metadata tests still pass
- add regression coverage for `matching` status and `match_results` payload shape

User verification:

- log in, load albums, and confirm the temporary test button is no longer shown
- start a sort and confirm the visible workflow is now selection -> matching -> sorting progress

Done when:

- temporary debug UI is removed
- match data is retained in job state for Epic 5
- regression tests cover the updated sort lifecycle

---

## File Plan

### New file

- `app/scanner.py` - local folder scan and asset matching logic

### Modified files

- `app/main.py` - inject existing settings service into the album/sort path
- `app/icloud/albums_service.py` - pass settings dependency into `ICloudService`
- `app/icloud/icloud_service.py` - run scan, matching, and richer progress reporting
- `app/ui/js/albums.js` - render matching progress and remove temporary debug fetch code by Phase 5
- `app/ui/js/main.js` - remove temporary debug button wiring by Phase 5
- `app/ui/index.html` - remove temporary debug button by Phase 5
- `tests/test_main_api_bridge.py` - updated sort lifecycle expectations
- `tests/test_sorting_services.py` - updated sort and matching expectations
- `tests/scanner/test_local_scanner.py` - scanner coverage
- `tests/scanner/test_matching.py` - matching coverage

## Phase Acceptance Checklist

For a phase to count as complete, it must satisfy all of the following:

- the phase deliverable is visible either in the UI, in the API contract, or in automated tests
- the named tests for that phase pass
- the user can perform the verification steps listed for that phase without reading internal code
- the next phase can build on the phase output without revisiting scope already marked complete

## Dependencies

- Epic 3 album and asset metadata retrieval: required
- existing settings baseline: required and already present
- JSON persistence: already present
- `pathlib`, `datetime`, `json`: standard library support available
