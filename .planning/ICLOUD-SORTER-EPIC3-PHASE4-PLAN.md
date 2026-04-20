# Epic 3 Phase 4 Plan: Integrate Real Data Into Album Browser

Source documents:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE3-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

## Goal

Complete the UI-facing integration of the Epic 3 backend work so the existing desktop album browser reliably renders real iCloud album data after authentication, handles real loading and failure states intentionally, and starts the temporary sort flow from stable selected album IDs.

This phase is about integrating and hardening the album browser experience around the real backend data path. It should not introduce local filesystem scanning, cloud-to-local matching, JSON persistence, or a real sorting engine.

## Why This Phase Exists

Phases 1 through 3 establish the backend foundations for real album and asset metadata retrieval, but Phase 4 is where the user actually feels whether Epic 3 succeeded:

- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) is the bridge boundary the desktop UI depends on, so any backend progress only matters if this contract stays stable and intentional
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) is still responsible for turning bridge responses into visible UI states, selected-album tracking, and sort-start requests
- the project goal and AGENTS constraints explicitly require preserving the current `pywebview` login -> optional 2FA -> album list flow
- the album browser must remain metadata-only and fast, even now that the backend can load richer per-album asset metadata lazily for later phases

Phase 4 exists to make the real-data album browser a first-class, tested workflow instead of a backend capability that happens to work only indirectly.

## Phase 4 Scope

In scope:

- integrate the real `get_albums()` backend response into the existing album browser flow
- confirm the bridge and UI preserve the structured album result contract from Phase 1
- show intentional loading, empty, and failure states in the album UI
- ensure selected albums are tracked and submitted by stable album IDs
- preserve the current temporary sort-progress behavior while removing any dependency on mocked album rows or list indexes
- add or align backend and frontend tests around the real album browser contract

Out of scope:

- local iCloud Photos folder scanning
- cloud-to-local filename matching
- moving or copying files on disk
- eager asset loading during album browser display
- album detail UI for listing filenames inside an album
- JSON-backed settings or state persistence
- replacing the temporary mock sort engine with the real Epic 4 sorting pipeline

## Current Phase 3 Baseline

The repo already has most of the backend pieces that Phase 4 should build on rather than replace:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) now keeps a session-memory album cache and a per-album asset metadata cache
- `ICloudService.get_albums()` returns a structured payload with `success`, `albums`, and `error`
- `ICloudService.start_sort()` already accepts selected album IDs and resolves them against cached real album summaries
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py) preserves failure payloads instead of flattening everything into an empty list
- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) already returns an album-service-unavailable failure payload when no authenticated albums service exists
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) already contains basic normalization and status handling, but this behavior should be treated as the deliberate Phase 4 contract and locked down with tests

That means this phase should focus on integration quality, UI behavior, and contract verification, not on inventing a new architecture.

## User-Facing Target Behavior

After Phase 4, the intended desktop flow should be:

1. the user logs in with Apple ID and password
2. if required, the user completes 2FA
3. the app calls `get_albums()` through the existing `pywebview` bridge
4. the album browser renders real album names and item counts from iCloud
5. the UI shows one of three intentional states:
   - successful load with albums
   - successful load with no eligible albums
   - known failure with a visible error message
6. when the user starts sorting, the UI submits selected album IDs only
7. the app starts the temporary sort job without scanning local files during album loading

This keeps Epic 3 aligned with the product goal while preserving the "do matching only when sorting starts" rule from [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md).

## Target Bridge And UI Contract

Phase 4 should treat this as the canonical album-load response:

```json
{
  "success": true,
  "albums": [
    {
      "id": "album-123",
      "name": "Vacation 2025",
      "item_count": 179,
      "is_system_album": false
    }
  ],
  "error": null
}
```

Failure case:

```json
{
  "success": false,
  "albums": [],
  "error": "Album service unavailable"
}
```

UI rules for this phase:

- album rendering should use `album.id`, `album.name`, and `album.item_count`
- UI checkbox state and sort submission must be keyed by `album.id`, not array position
- empty-result success must show a real empty state instead of a generic failure message
- known failures must show a visible error message instead of looking like a valid empty library
- album browser rendering must stay summary-only and must not trigger per-album asset loading or local file scanning
- if legacy array responses are still tolerated by the UI helper for compatibility, that fallback should remain internal and test-covered rather than shaping the canonical contract

## Planned File Changes

Primary implementation files:

- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py)
- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) only if small bridge-facing adjustments are needed to preserve the UI contract
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js)

Primary test files:

- [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py)
- [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py)
- `tests/icloud/test_album_service_get_albums.py` if service-layer album contract coverage is expanded here
- [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) should stay in place as the existing album-browser coverage baseline
- [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js) should stay in place if the auth-to-album transition is touched

Files that should not need major change in the default Phase 4 path:

- [app/api/auth_api.py](/home/mac/code/python/icloud-file-sorter/app/api/auth_api.py)
- [app/icloud/auth.py](/home/mac/code/python/icloud-file-sorter/app/icloud/auth.py)
- [app/ui/js/login.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/login.js)

## Implementation Tasks

### 1. Lock down the album browser contract at the bridge boundary

Work:

- confirm `API.get_albums()` always returns the structured payload shape expected by the UI
- keep the unavailable-service case explicit and user-visible
- make sure `AlbumsService.get_albums()` preserves known failure signals instead of flattening them away
- verify `start_sort()` continues to accept selected album IDs only

Output:

- one intentional bridge contract for real album loading
- no dependence on mocked album rows or selected list indexes

### 2. Make album UI states explicit and stable

Work:

- keep [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) focused on summary rendering only
- verify loading text, empty-state text, and known-failure text all map cleanly to real backend results
- ensure the album list safely renders albums with missing or non-numeric `item_count`
- keep the current checkbox-driven selection UI, but make album ID usage and status rendering the deliberate contract

Output:

- the album browser reflects backend reality without ambiguous states
- real album names and counts display after successful auth

### 3. Preserve the existing auth-to-album flow

Work:

- confirm the login -> optional 2FA -> album list transition still works through the existing `pywebview` shell
- avoid introducing new bridge methods unless the UI genuinely needs them in the same change
- keep album loading triggered from the current frontend flow rather than introducing a new view model or architecture

Output:

- the desktop shell behavior remains familiar while the data source becomes real

### 4. Keep sort start lightweight and real-data-backed

Work:

- verify selected albums are submitted as IDs from the UI to `start_sort()`
- keep the temporary sort job setup based on real selected album metadata rather than synthetic album names
- ensure album loading itself does not call asset loaders or local filesystem scanning helpers
- document, in code comments or tests if needed, that file matching still belongs to Epic 4

Output:

- sort initiation is aligned with real album data
- album browsing stays fast and metadata-only

### 5. Add backend contract coverage

Work:

- add or update bridge tests for:
  - successful album payload passthrough
  - album-service-unavailable failure
  - selected album ID handling in `start_sort()`
- add or update service tests for:
  - success payload propagation
  - known failure propagation
  - distinction between empty success and failure

Output:

- backend integration rules become regression-resistant

### 6. Preserve existing frontend coverage and add only missing cases

Work:

- keep [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) as the baseline for:
  - successful album render with real payload shape
  - successful empty album result
  - visible known-failure result
  - safe item-count rendering when the backend omits or nulls the count
  - selected album ID submission to sort start
- keep [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js) aligned with the current login -> album-loading flow
- add new frontend coverage only for gaps that are not already covered by those files, such as a newly introduced bridge/UI contract change or a missing 2FA-to-album transition case
- keep the tests small and aligned with the real DOM wiring instead of abstracting away the current UI structure

Output:

- frontend behavior is verified against the real bridge contract

## Test Plan

Python bridge and service tests:

- verify [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) covers the structured `get_albums()` payload and unavailable-service case
- verify [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py) covers selected album IDs and temporary sort setup that no longer depends on mock album names
- add or expand a service-level album contract test file for:
  - success with albums
  - success with no albums
  - failure with a visible error

Frontend tests:

- keep [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) in place for:
  - loading result normalization
  - rendering of album names and item counts
  - true empty-state messaging
  - visible error-state messaging
  - ID-based selection and sort-start behavior
- keep [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js) in place for the login-to-album transition
- add new frontend tests only for missing Phase 4 cases that are not already covered by the existing files

Manual verification target for this phase:

- launch the app with `python -m app.main`
- log in with a valid authenticated account/session that returns real iCloud album data
- confirm the existing desktop shell still transitions into the album list
- confirm the album list shows real iCloud album names and item counts
- confirm no local filesystem scan is triggered during album loading

Execution target for this phase:

- `pytest`
- `npm --prefix frontend test`

If either test command is unavailable in the environment, the implementation notes for the phase should record that gap explicitly rather than silently skipping verification.

## Acceptance Criteria

Phase 4 is complete when:

- the UI shows real iCloud album names and counts after successful auth
- the login -> optional 2FA -> album list flow still works in the `pywebview` desktop shell
- `get_albums()` is treated as a structured bridge contract, not a mock-only or array-position-based path
- the album UI can distinguish a known fetch failure from a successful empty result
- selected albums are tracked and submitted by stable album IDs
- no local filesystem work happens during album loading
- temporary sort startup no longer depends on synthetic album rows or mock album names
- backend and frontend tests cover the real album browser contract well enough to support Epic 4

## Risks And Mitigations

Bridge/UI drift:

- mitigate by treating the structured payload as canonical and updating JS plus tests in the same change if it evolves

Legacy UI assumptions around arrays or index-based selection:

- mitigate by keeping album-ID selection explicit and testing it directly

Frontend test drift:

- mitigate by adding album-specific tests that match the actual vanilla JS DOM wiring instead of old login-only assumptions

Accidental eager work during album browsing:

- mitigate by testing and reviewing that album load remains summary-only and does not call asset loaders or local file matching

Over-coupling the temporary sort flow to unfinished Epic 4 work:

- mitigate by keeping sort start lightweight and real-data-backed, while clearly deferring file scanning and matching to the next epic
