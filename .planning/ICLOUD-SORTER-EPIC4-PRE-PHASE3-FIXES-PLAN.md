# Epic 4 Pre-Phase-3 Fixes Plan

## Purpose

This plan isolates the Phase 2 issues that should be fixed before Epic 4 Phase 3 adds local scanning and matching work.

The goal is to correct the sort-job lifecycle now so Phase 3 can build on a stable flow instead of adding more expensive work into the current synchronous `start_sort()` path.

## Why This Exists

Current Phase 2 code introduced the right backend concepts, but three issues should be addressed before moving forward:

- `start_sort()` performs expensive asset fetch work before a job exists and before the UI can poll progress
- `get_sort_progress()` returns the full aggregated asset list on every poll even though the UI does not use it
- `start_sort()` can reuse previously cached asset metadata instead of forcing a fresh sort-time fetch

If left as-is, Phase 3 will likely add local scan and filename matching work to the same pre-job synchronous path, making the later correction larger and riskier.

## Scope

In scope:

- create the sort job before expensive sort-time work begins
- keep the job visibly in `matching` while asset fetch and later scan/match work run
- trim progress payloads to progress-only fields
- force authoritative sort-time asset metadata fetches
- add regression coverage for the updated lifecycle

Out of scope:

- implementing the local scanner itself
- fallback matching rules
- changing the frontend bridge contract for `start_sort(selected_album_ids)`
- removing the temporary debug fetch button unless separately scheduled

## Desired Outcome

After these fixes:

- clicking Start Sort returns a `job_id` quickly
- the UI can immediately begin polling a real job
- the job remains in `matching` while expensive work is underway
- progress payloads stay lightweight
- sort-time asset metadata fetch is fresh and authoritative

## Fix 1: Create The Job Before Expensive Work

### Problem

`ICloudService.start_sort()` currently validates input, fetches selected album assets, and only then creates the job.

That means the expensive iCloud asset metadata fetch happens inside the initial RPC request, not inside a pollable job lifecycle.

### Goal

Move the expensive sort-time work behind a job that exists immediately.

### Implementation

- keep `start_sort(selected_album_ids)` as the frontend API contract
- in `ICloudService.start_sort()`:
  - validate album cache and source folder
  - normalize and validate selected album ids
  - create a job immediately with:
    - `status: "matching"`
    - `processed: 0`
    - `percent: 0`
    - selected album metadata
    - source folder
    - an initial message such as `Preparing matching job...`
  - return `{"job_id": ...}` immediately
- move sort-time asset loading into a separate internal step that runs after job creation
- keep the first expensive step as selected-album asset fetch
- prepare this step so Phase 3 can extend it with local scanning and matching instead of redesigning the lifecycle again

### Recommended Shape

Minimal options, in preferred order:

1. Start the job immediately and advance matching work incrementally from `get_sort_progress()` until preparation is complete.
2. Start the job immediately and kick off background preparation if there is already an acceptable pattern in the app for non-blocking job work.

Prefer option 1 if the goal is the smallest change with the least runtime complexity.

### Tests

- `start_sort()` returns `job_id` without waiting for asset fetch completion
- first `get_sort_progress()` call can observe a real `matching` job
- job remains in `matching` until asset preparation finishes
- job transitions to `running` only after preparation completes
- invalid source folder still returns a clear error before job creation

### Done When

- the user can see a real `matching` stage during sort startup
- expensive sort preparation no longer happens entirely inside the initial `start_sort()` request

## Fix 2: Keep Progress Payloads Lightweight

### Problem

`get_sort_progress()` currently copies `selected_assets` into every poll response.

That payload will grow significantly in Phase 3 and is not needed by the current UI.

### Goal

Return only progress fields the UI needs during polling.

### Implementation

- keep rich asset data in server-side job state
- exclude `selected_assets` from normal progress payloads
- if needed later, expose detailed matched-asset data through a separate endpoint or only in final completion state once there is a concrete consumer
- keep progress payload compatible with existing UI usage:
  - `job_id`
  - `status`
  - `processed`
  - `total`
  - `percent`
  - `message`
  - later `match_results` summary fields when Phase 4 requires them

### Tests

- `get_sort_progress()` does not include `selected_assets`
- job internals still retain aggregated assets for later phases
- frontend tests continue to pass using lightweight progress payloads

### Done When

- polling payload size is bounded and independent of total asset metadata size

## Fix 3: Force Fresh Sort-Time Asset Fetch

### Problem

`start_sort()` currently reuses cached per-album asset metadata if it was loaded earlier.

That weakens the plan requirement that per-asset metadata fetch belongs to the active sort job and happens only at sort time.

### Goal

Make sort preparation fetch selected album assets freshly and intentionally.

### Implementation

- update the sort path to call `get_assets_for_album_ids(..., force_refresh=True)`
- keep normal album browsing lightweight and unchanged
- do not rely on previously warmed asset caches for sort-time preparation
- document that sort-time fetch is authoritative for the active job

### Tests

- if an album asset cache already exists, sort start forces a reload for selected albums
- only selected albums are refreshed
- overlapping albums still aggregate into one asset entry with ordered memberships

### Done When

- sort preparation always uses a fresh asset fetch for the selected albums

## File Plan

Expected files to update:

- `app/icloud/icloud_service.py`
- `tests/test_sorting_services.py`
- `tests/icloud/test_album_asset_loading.py`
- `tests/test_main_api_bridge.py`
- `frontend/tests/albums.test.js`

Possible frontend changes if messaging changes:

- `app/ui/js/albums.js`

## Order Of Work

1. Refactor `start_sort()` so it creates the job before expensive work begins.
2. Update `get_sort_progress()` so matching-stage preparation advances there or via the chosen job runner.
3. Remove `selected_assets` from normal polling payloads.
4. Force fresh selected-album asset fetch during sort preparation.
5. Update regression tests.

## Acceptance Checklist

- `start_sort(selected_album_ids)` still returns the same top-level contract
- the user sees a real `matching` stage while preparation is underway
- progress polling stays lightweight
- sort-time asset fetch is forced fresh for the selected albums
- Phase 3 can add local scan and filename matching on top of this lifecycle without moving work out of `start_sort()` again
