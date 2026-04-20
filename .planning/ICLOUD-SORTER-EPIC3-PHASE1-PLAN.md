# Epic 3 Phase 1 Plan: Define Real Album Retrieval Boundary

Source documents:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

## Goal

Replace the mocked album-list boundary with a real, normalized album retrieval flow from `pyicloud` while keeping the current desktop shell and JS bridge stable enough for the existing UI to evolve incrementally.

This phase is specifically about defining and implementing the album-list contract. It does not include local file matching, folder sorting, JSON persistence, or eager asset loading for every album.

## Why This Phase Exists

The current repo still has three blockers at the album boundary:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) returns hardcoded album rows
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py) flattens album-fetch failures into `[]`
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) assumes any successful bridge call returns only a plain array, which prevents the UI from distinguishing a real empty library from an actual backend failure

Phase 1 should fix that boundary first so later Epic 3 phases can safely add caching and per-album asset metadata without carrying mock behavior forward.

## Phase 1 Scope

In scope:

- identify the album collection shape exposed by authenticated `pyicloud`
- define the normalized album summary fields used by the UI
- decide which albums are eligible for the MVP album browser
- replace hardcoded album summaries with real service-backed summaries
- preserve failure versus empty-result distinctions through the service and bridge layers
- update the current album-loading UI path if the bridge contract changes
- switch sort selection from list indexes to stable album IDs
- add backend and frontend tests for the new album-loading contract

Out of scope:

- per-album asset metadata loading
- in-memory asset cache
- local filesystem scanning or matching
- sort-engine changes beyond preserving compatibility with the existing album list flow
- settings or JSON persistence work

## Target Contract For This Phase

`get_albums()` should return a structured payload instead of a bare list:

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
  "error": "Session expired"
}
```

Notes:

- Phase 1 should fetch only the minimum metadata needed for album browsing: `name` and total `item_count`
- album identity and album names shown to the user must come from `pyicloud`, not from mock rows or synthetic placeholders
- `id` is introduced now so sorting and later phases do not depend on list position alone
- exact album contents and richer media metadata stay deferred to the sorting phase
- a genuine empty result is `success: true` with `albums: []`
- a known backend failure is `success: false` with a user-visible `error`

## MVP Album Eligibility Rules

Phase 1 should make filtering explicit and easy to adjust. The initial implementation should:

- prefer user-created albums when `pyicloud` exposes a reliable distinction
- exclude system or smart albums only when the source data makes that determination trustworthy
- fall back to conservative inclusion if filtering signals are incomplete
- centralize the rule in one service helper instead of scattering checks across the UI and bridge

If `pyicloud` album typing is inconsistent, the implementation should keep the filter minimal and document the observed behavior in code comments or test fixtures.

## Planned File Changes

Primary implementation files:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py)
- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py)
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js)

Test files to update or add:

- [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py)
- [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py)
- [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js) if shared UI wiring changes
- `tests/icloud/test_album_normalization.py`
- `tests/icloud/test_album_service_get_albums.py`
- `frontend/tests/albums.test.js`

## Implementation Tasks

### 1. Inspect `pyicloud` album objects and define normalization rules

Work:

- inspect the authenticated album collection shape available from `auth_api.api`
- identify which raw fields can reliably supply album ID, album name, and total item count
- define fallback behavior when total item count is missing or unreliable
- define how system/smart album filtering will work in the MVP

Output:

- one normalization path from raw album objects to UI summaries
- representative fake album fixtures for tests

### 2. Replace mocked album summaries in `ICloudService`

Work:

- remove the current hardcoded album list from `ICloudService.get_albums()`
- add normalization helpers for raw `pyicloud` album objects
- return structured album results instead of a bare list
- keep album loading summary-only and avoid fetching album contents or per-asset metadata in this phase
- ensure album names and IDs used by the UI come only from `pyicloud` data

Output:

- real album retrieval backed by `pyicloud`
- no local matching or sort-time work triggered during album loading

### 3. Preserve failure and empty-state signals in `AlbumsService`

Work:

- stop flattening all failures into `[]`
- log failures with enough detail for debugging
- return a structured failure payload for known errors
- preserve a valid empty album list as success, not failure

Output:

- service layer can distinguish:
  - backend failure
  - successful empty result
  - successful non-empty result

### 4. Update the bridge contract in `API.get_albums()`

Work:

- make [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) return the structured album payload
- return a structured failure payload when the albums service is unavailable
- update `start_sort()` to accept selected album IDs instead of selected indexes
- keep login and 2FA flow unchanged

Output:

- UI receives a consistent album payload whether the request succeeds, returns empty, or fails
- sort requests identify albums by stable IDs rather than current list position

### 5. Align the album UI with the new response shape

Work:

- update [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) to read `result.albums`
- store `album.id` on each checkbox and submit selected album IDs to the backend when sorting starts
- add explicit handling for:
  - successful load with albums
  - successful load with zero eligible albums
  - failed load with a visible error message
- keep the existing checkbox-based selection flow for now, but key it by album ID
- render album name plus total item count only

Output:

- album browser remains lightweight and responsive
- empty and error states become intentional instead of accidental

### 6. Keep current sorting tests compatible with the new boundary

Work:

- update any sorting tests that currently depend on the mocked album list shape
- update `start_sort()` tests to use selected album IDs and verify any temporary sort-progress mock behavior is isolated from fetched album rows

Output:

- Epic 3 Phase 1 does not silently break temporary sort-progress behavior while the real sort pipeline is still pending

## Test Plan

Python unit tests:

- add `tests/icloud/test_album_normalization.py` for raw-album-to-summary normalization
- cover missing optional fields such as `item_count` or system-album markers
- cover inclusion and exclusion rules for eligible albums
- verify `ICloudService.get_albums()` returns:
  - success with normalized albums
  - success with an empty album list
  - failure with an error message

Python service and bridge tests:

- add `tests/icloud/test_album_service_get_albums.py` for `AlbumsService.get_albums()`
- update [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) to assert `API.get_albums()` returns the structured payload
- add a bridge test for the unavailable-service case returning `success: false`
- update [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py) to cover ID-based sort selection and the preserved mock sort assumptions

Frontend tests:

- add `frontend/tests/albums.test.js` for the new album-loading contract
- cover successful render with albums
- cover successful empty state
- cover visible failure state
- cover safe rendering when `item_count` is missing
- cover sort start requests that submit selected album IDs instead of selected indexes

Test execution target for this phase:

- `pytest`
- `npm --prefix frontend test`

If either tool is still unavailable in the environment, keep the tests added and document the execution gap in the implementation notes for the phase.

## Acceptance Criteria

Phase 1 is complete when:

- `ICloudService.get_albums()` no longer returns hardcoded mock album rows
- album summaries are produced through one normalization path
- the app can distinguish a known album-fetch failure from a genuine empty album result
- the current auth -> album-list desktop flow still works through the existing `pywebview` bridge
- the album list fetch only retrieves the minimum data needed for browsing: album name and total item count
- album identity and album names exposed to the user come only from `pyicloud`
- the album UI handles success, empty, and failure states intentionally
- sort selection is submitted and resolved by album ID, not by array position
- local filesystem scanning and cloud-to-local matching still do not run during album browsing
- backend and frontend tests are added or updated for the new album boundary

## Risks And Mitigations

`pyicloud` album shape drift:

- mitigate by isolating normalization in helper methods and testing with representative fake objects

System album detection may be unreliable:

- mitigate by making the filter conservative and easy to adjust without changing the UI contract

Bridge/UI drift during contract change:

- mitigate by updating `albums.js` and its tests in the same phase as the backend change

Sort mock regressions:

- mitigate by isolating any temporary sort-progress mock behavior from album retrieval and removing assumptions about synthetic album rows or names

## Exit State For Phase 2

When this phase is done, the next phase can safely add session-memory album caching on top of a stable real-data contract instead of building cache behavior around mocked or ambiguous album responses.
