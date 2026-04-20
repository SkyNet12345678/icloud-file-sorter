# Epic 3 Plan: Album & Asset Metadata Retrieval

This file breaks Epic 3 into implementation-ready steps for the current codebase.

Primary source files:

- [.planning/PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [.planning/ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

Current implementation baseline:

- `app/main.py` exposes the `pywebview` bridge
- `app/icloud/icloud_service.py` still returns mocked album data
- `app/icloud/albums_service.py` wraps album and sorting calls
- `app/ui/js/albums.js` expects `get_albums()` to return lightweight album summary data and should remain fast

## Goal

Replace the mocked album browser flow with real iCloud album metadata retrieval while preserving the existing desktop shell and current bridge-first architecture.

At the end of this epic, the app should:

- fetch real album summaries from `pyicloud`
- display them in the existing album selection UI
- keep album browsing metadata-only and lightweight
- hold album and asset metadata in memory for the active session
- preserve ordered album memberships for assets that belong to multiple selected albums so later sort behavior can remain deterministic
- defer any local filesystem scanning and cloud-to-local matching until sorting begins
- distinguish between known album-fetch failures and a genuine "no albums" result

## Non-Goals

This epic should not:

- scan the local iCloud Photos folder
- match cloud assets to local files
- move or copy files on disk
- introduce SQLite or any other database
- rewrite the frontend to React or replace `pywebview`

## Current Gaps

Today, the repo has the auth shell and album UI flow, but the album layer is still mocked:

- `ICloudService.get_albums()` returns hardcoded album summaries
- temporary sort progress still depends on mocked album data
- there is no in-memory cache for real album metadata
- there is no boundary yet between lightweight album summaries and richer per-asset metadata
- tests currently cover mocked sorting behavior more than real album retrieval behavior

## Epic 3 Scope

Epic 3 from the normalized plan and CSV includes:

1. fetch album list via `pyicloud`
2. fetch assets per album
3. hold albums and assets in memory for the current session
4. build the album browser UI around real data
5. keep album detail view optional

Adjusted for this repo:

- album retrieval must stay fast at initial load
- the UI contract should stay compatible with `albums.js` unless the JS is updated in the same change
- any richer asset metadata should be prepared for later sort-time matching, but not trigger that matching yet
- initial album browsing should fetch only album names and total item counts, not album contents

## Proposed Data Shapes

Keep the bridge response shape close to the current UI expectation.

### Album List Result returned by `get_albums()`

```json
{
  "success": true,
  "albums": []
}
```

or

```json
{
  "success": false,
  "albums": [],
  "error": "Session expired"
}
```

Notes:

- preserve a clear distinction between known failures and a valid empty album list
- if `pyicloud` or the service layer provides a reliable failure signal, surface it to the UI
- if album retrieval succeeds and yields no eligible albums, show a true empty state rather than a generic error
- avoid inventing failures when the backend has no evidence that one occurred

### Album Summary returned by `get_albums()`

```json
{
  "id": "album-123",
  "name": "Vacation 2025",
  "item_count": 179,
  "is_system_album": false
}
```

Notes:

- keep the initial album fetch limited to `name` and total `item_count` so album browsing stays fast
- album IDs and album names shown in the browser should come only from `pyicloud`
- add a stable `id` now so later matching and sort flows do not depend on array position alone
- keep this object lightweight enough for the album list view

### In-Memory Asset Metadata

```json
{
  "asset_id": "asset-123",
  "filename": "IMG_1234.HEIC",
  "created_at": "2025-08-05T12:34:56Z",
  "size": 2481934,
  "media_type": "image",
  "album_id": "album-123",
  "album_name": "Vacation 2025"
}
```

Notes:

- exact fields may need to adapt to what `pyicloud` exposes reliably
- prefer normalizing values in one place before the rest of the app uses them
- keep this cache session-only for Epic 3

### Aggregated Multi-Album Asset Metadata

When backend code resolves multiple selected albums at once, the result should preserve shared asset identity and ordered album membership.

Notes:

- the aggregation helper should return one record per unique asset
- each aggregated asset record should preserve all selected album memberships for that asset
- album memberships should preserve selected album order so later sort behavior can deterministically choose the first selected folder by default
- this epic should preserve the metadata needed for later sort settings, not implement the sort policy itself

## Service Design

Add a clear separation between summary retrieval and deeper asset metadata retrieval.

### `app/icloud/icloud_service.py`

Responsibilities for this epic:

- discover albums from the authenticated `pyicloud` API
- normalize album summary data for the UI
- retrieve asset metadata for one or more albums
- cache album summaries and per-album asset metadata in memory
- expose lookup helpers needed by later sort steps

Recommended internal structure:

- `get_albums()`:
  returns lightweight normalized album summaries for UI display using only album name and total item count
- `get_album_assets(album_id)`:
  returns normalized asset metadata for a single album during sort-time preparation, not during initial album browsing
- `get_assets_for_album_ids(selected_album_ids)`:
  bridge-friendly helper for later sort initiation, converting UI selections into ordered album-aware asset metadata
- private normalization helpers:
  isolate `pyicloud` object quirks and missing fields

### `app/icloud/albums_service.py`

Responsibilities for this epic:

- preserve the bridge-friendly orchestration layer
- keep `get_albums()` safe, log failures clearly, and preserve known failure signals for the UI
- prepare for later sort-time asset loading without doing local matching yet

### `app/main.py`

Bridge work for this epic:

- preserve `get_albums()` as the album-list entry point
- keep current method names stable
- only add new bridge methods if the UI needs them in the same change

## UI Plan

The current UI in `app/ui/js/albums.js` already supports:

- loading state text
- rendering a checkbox list of albums
- displaying album item counts
- starting a later sort flow from selected albums

Epic 3 UI work should stay incremental:

1. keep the current album list screen and DOM wiring
2. make it render real album metadata instead of mocked data
3. improve empty and error states so the UI can distinguish:
   - successful album load with albums
   - successful album load with no eligible albums
   - known album-fetch failure with a user-visible message
4. avoid adding a heavy album detail flow unless debugging or support clearly needs it

Recommended UI tweaks during implementation:

- show album name plus total item count from the lightweight fetch
- show a clear empty state when no eligible albums are found after a successful fetch
- show a failure message when the backend has a known fetch/auth/session error
- submit selected album IDs to the backend so sorting does not depend on album order or filtering stability

## Implementation Phases

## Phase 1: Define Real Album Retrieval Boundary

Deliverables:

- identify the `pyicloud` album objects and fields available after login
- document which album types should be shown in the MVP
- exclude smart/system albums if that is reliably detectable
- define normalization rules for album summaries using only album name and total item count
- switch sort selection from selected indexes to selected album IDs
- remove dependencies on mocked album names or synthetic album rows from the sort boundary

Acceptance criteria:

- there is a single normalization path from raw `pyicloud` album objects to UI album summaries
- the service returns structured album data instead of hardcoded mock rows
- known failures are surfaced to the UI as failures, not flattened into an empty album list
- a genuinely empty album result is treated as a successful fetch with an empty-state message
- album browsing does not fetch album contents; that work remains deferred to sort time
- sort requests identify albums by stable IDs rather than list position
- album names shown in the UI come only from `pyicloud`, and temporary sort mocks do not depend on fetched album rows

## Phase 2: Build In-Memory Album Cache

Deliverables:

- album summaries cached for the authenticated session
- album IDs mapped to source album objects or normalized records
- clear cache lifecycle tied to login/session lifetime

Acceptance criteria:

- repeated album list requests do not needlessly re-fetch heavy metadata
- cache invalidation is simple and explicit
- no persistence layer is introduced for album metadata in this epic

## Phase 3: Add Per-Album Asset Metadata Loading

Deliverables:

- normalized asset metadata loader per album
- session-memory cache for assets keyed by album ID
- data fields chosen to support later filename-based matching
- aggregated multi-album metadata that preserves ordered album memberships for shared assets

Acceptance criteria:

- asset retrieval is available to backend services without changing the album browser into a file-matching step
- metadata includes at least filename and any reliable size/date/media-type fields exposed by `pyicloud`
- missing optional fields are normalized consistently
- multi-album aggregation preserves all selected album memberships for shared assets and keeps selected order deterministic for later sort behavior

## Phase 4: Integrate Real Data Into Album Browser

Deliverables:

- `get_albums()` returns real album summaries to the existing UI
- album UI handles real empty/error/loading cases
- sorting starts from selected album IDs without doing local scanning during load

Acceptance criteria:

- the UI shows real album names and counts after successful auth
- the login -> optional 2FA -> album list flow still works
- the UI can distinguish a known fetch failure from a successful empty result
- no local filesystem work happens during album loading

## Phase 5: Prepare Sort-Time Metadata Hand-Off

Deliverables:

- a backend path for turning selected album IDs into selected album metadata
- ability for `start_sort()` to load or reuse asset metadata for only the selected albums
- comments or small helper abstractions clarifying that local matching belongs to Epic 4, not here

Acceptance criteria:

- selected albums can be resolved to real album metadata instead of mock names
- asset metadata retrieval for selected albums is available when the sort pipeline is implemented
- sort-time local file matching is still not introduced in Epic 3

## File-Level Change Plan

Likely files to touch:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py)
- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py)
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js)
- [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py)
- [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py)
- [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js) or a new frontend album test file if Epic 3 expands the album UI contract enough to justify separate coverage

Possible new test files:

- `tests/icloud/test_album_metadata_service.py`
- `tests/icloud/test_album_normalization.py`
- `frontend/tests/albums.test.js`

## Test Coverage Expectations

Epic 3 should add or update frontend coverage for the album-loading contract, not only backend service tests.

Recommended frontend cases:

- successful album load with one or more albums
- successful album load with zero eligible albums, showing a true empty state
- known album-fetch failure with a visible failure message
- album summaries where `item_count` is missing and the UI still renders safely
- selection flow still working with real album payloads and album ID-based interaction

## Testing Plan

Python coverage should be the main focus for this epic.

Add tests for:

- album summary normalization from raw `pyicloud`-like objects
- exclusion or inclusion rules for system albums
- asset metadata normalization with missing fields
- session-memory caching behavior
- `AlbumsService.get_albums()` error handling
- bridge behavior in `app.main.API.get_albums()`
- selected album ID to selected album resolution for later sort use
- temporary sort progress behavior that does not depend on mocked album names or synthetic album rows

Frontend coverage should stay lightweight and real:

- update or add tests only if the DOM contract changes
- keep tests aligned with the actual vanilla JS module wiring
- verify album rendering and empty/error states if UI behavior changes

## Risks

## `pyicloud` shape variability

Risk:

- album and asset objects may not expose exactly the fields assumed in the CSV

Mitigation:

- isolate normalization in one service layer
- tolerate missing optional fields
- build tests around representative fake objects, not exact production internals

## System album filtering

Risk:

- reliably excluding smart/system albums may be harder than the CSV implies

Mitigation:

- make filtering rules explicit and easy to adjust
- if necessary, ship with conservative filtering and revisit after observing real accounts

## Large libraries

Risk:

- eager per-asset loading for every album may make album browsing slow

Mitigation:

- keep `get_albums()` summary-only
- load per-album assets lazily or only for selected albums
- cache only within the current session

## Bridge drift

Risk:

- backend response changes could silently break the current JS album UI

Mitigation:

- preserve `name` and `item_count`
- update JS and tests in the same change if the response shape evolves

## Mock Boundary Leakage

Risk:

- temporary sort-progress mocks could continue depending on synthetic album rows or mock album names after album retrieval becomes real

Mitigation:

- treat `pyicloud` as the only source of album identity and album names
- isolate any temporary sort-progress mock data from fetched album summaries
- remove assumptions such as special hardcoded album rows from sorting tests and helper code

## Suggested Task Breakdown

1. replace mocked `get_albums()` output with normalized real album summaries
2. add in-memory album cache keyed by album ID
3. add normalized per-album asset metadata loader
4. make `start_sort()` resolve selected album IDs against real album data
5. tighten album-related service and bridge tests
6. update album UI states only where real data requires it

## Definition Of Done

Epic 3 is done when:

- album list loading uses real iCloud data
- the existing auth-to-album flow still works in the desktop shell
- album browsing remains metadata-only and responsive
- per-album asset metadata can be loaded for selected albums in memory
- no local file scanning or matching is triggered during album load
- tests cover album normalization, caching, and bridge/service behavior well enough to support Epic 4
