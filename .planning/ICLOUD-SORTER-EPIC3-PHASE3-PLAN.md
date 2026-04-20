# Epic 3 Phase 3 Plan: Add Per-Album Asset Metadata Loading

Source documents:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

## Goal

Add a normalized, session-memory per-album asset metadata loader so backend code can resolve selected album IDs into real asset records without turning the album browser into a local-file scan or eager metadata preload step.

This phase is specifically about loading and caching cloud asset metadata for albums that the backend asks for. It should not add local filesystem matching, sorting on disk, JSON persistence, or a mandatory album-detail UI.

## Why This Phase Exists

Phase 2 established a usable album summary cache, but the repo still stops at album names and counts:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) caches album summaries and raw album objects, but it has no normalized asset loader
- selected album IDs can resolve back to cached album objects, but there is no backend contract yet for loading asset metadata from those albums
- `start_sort()` still launches only a temporary mock job and cannot yet prepare real selected-album metadata for later matching work
- there is no session-memory asset cache keyed by album ID, so later phases would have to either re-fetch assets ad hoc or overload the album browser path

Phase 3 should fill that gap by making per-album asset metadata available to backend callers while keeping the initial `get_albums()` experience lightweight and fast.

## Phase 3 Scope

In scope:

- define a normalized asset metadata shape for backend use
- add a per-album asset loader that reads from cached raw album objects
- cache normalized asset metadata in memory for the current authenticated session
- support loading assets lazily for one album or a selected subset of albums
- make missing optional asset fields normalize consistently
- add backend tests for normalization, caching, and selected-album asset loading helpers
- keep the existing album browser UI summary-only unless a tiny debug-oriented extension is clearly needed

Out of scope:

- scanning the local iCloud Photos folder
- matching cloud assets to local files
- moving or copying files on disk
- JSON settings or state persistence
- a full album-detail UI that lists every file in an album
- replacing the current temporary sort-progress mock with the real sorting engine

## Current Phase 2 Baseline

The repo already has the right starting points for this phase:

- `ICloudService.get_albums()` returns a structured summary payload with `success`, `albums`, and `error`
- `album_list_cache`, `album_summaries_by_id`, and `raw_albums_by_id` are already maintained in memory
- `get_cached_album()` and `get_cached_album_summary()` provide read-only album ID lookups after the cache is loaded
- the album UI already keys selection by stable album IDs and stays focused on names plus counts

That means Phase 3 can build mostly inside [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) and [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py), with frontend changes remaining optional.

## Target Asset Metadata Contract

Phase 3 should introduce one normalized backend shape for per-asset metadata.

Recommended normalized asset record:

```json
{
  "asset_id": "asset-123",
  "filename": "IMG_1234.HEIC",
  "original_filename": "IMG_1234.HEIC",
  "created_at": "2025-08-05T12:34:56Z",
  "size": 2481934,
  "media_type": "image",
  "album_id": "album-123",
  "album_name": "Vacation 2025"
}
```

Notes:

- `filename` should represent the best filename candidate available for later local matching
- `original_filename` can be kept when `pyicloud` exposes both a display name and a source/original name
- `created_at`, `size`, and `media_type` should be included only when they can be read reliably, but the normalized keys should still exist with `null` values when missing
- `album_id` and `album_name` should be stamped onto each normalized asset so later phases do not need to re-thread album context through every call site
- normalization should happen in one backend helper path rather than being reimplemented in later sorting code

Recommended asset-loading result shape:

```json
{
  "success": true,
  "album_id": "album-123",
  "assets": []
}
```

Failure case:

```json
{
  "success": false,
  "album_id": "album-123",
  "assets": [],
  "error": "Failed to load album assets"
}
```

Notes:

- this result shape can stay internal to the backend for now if the UI does not need it
- a successful empty album asset list must be distinct from a known fetch failure

## Asset Cache Design

Phase 3 should keep asset metadata memory-only and keyed by album ID.

Recommended cache state inside `ICloudService`:

```json
{
  "album_assets_by_id": {
    "album-123": [
      {
        "asset_id": "asset-123",
        "filename": "IMG_1234.HEIC",
        "original_filename": "IMG_1234.HEIC",
        "created_at": "2025-08-05T12:34:56Z",
        "size": 2481934,
        "media_type": "image",
        "album_id": "album-123",
        "album_name": "Vacation 2025"
      }
    ]
  },
  "album_asset_cache_loaded_ids": [
    "album-123"
  ]
}
```

Notes:

- the asset cache should be independent from `album_list_cache` so album browsing stays summary-only
- cache entries should be keyed by album ID because the UI and later sort path already use stable album IDs
- a successfully loaded empty asset list for an album should still count as a cached success for that album
- the cache should not be persisted to JSON in Epic 3

## Asset Cache Lifecycle Rules

Phase 3 should make per-album asset loading explicit:

1. Asset loading must never happen as a side effect of `get_albums()`
2. Asset loading should require the album cache to already be loaded so the service can resolve album IDs against known albums
3. The first successful asset load for an album should populate the asset cache for that album only
4. Repeated asset requests for the same album should reuse cached normalized assets by default
5. Loading assets for one album must not force eager loading of every album in the account
6. Multi-album helper methods should load only the requested album IDs, not the full library
7. If an asset refresh is requested for one album, replace that album's cache atomically and leave other albums untouched
8. If an asset load fails after a prior successful load for that same album, keep the last known-good asset cache in place unless the caller explicitly wants it cleared
9. Read-only asset lookup helpers must not perform hidden network work
10. If a caller asks for assets for an unknown album ID, the service should fail clearly instead of silently fabricating an empty result

## Recommended Service API Shape

The current `pywebview` bridge does not need to expose a new asset-loading method yet unless the UI is intentionally expanded in the same change. The main work should stay inside the service layer.

Recommended additions in [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py):

- `get_album_assets(album_id, force_refresh=False)`
- `get_assets_for_album_ids(album_ids, force_refresh=False)`
- `get_cached_album_assets(album_id)`
- `_load_album_assets(album_id, force_refresh=False)`
- `_normalize_album_asset(raw_asset, album_summary)`
- `_read_raw_album_assets(raw_album)`

Behavior:

- `get_album_assets(album_id, force_refresh=False)` should validate the album cache, resolve the cached album, and return normalized assets for that album
- `get_assets_for_album_ids(album_ids, force_refresh=False)` should dedupe IDs, fail clearly on unknown albums, and return only the requested albums' normalized assets
- `get_cached_album_assets(album_id)` should remain read-only and should not trigger a fetch if the album is cold
- `_read_raw_album_assets(raw_album)` should isolate how raw asset objects are read from `pyicloud`
- `_normalize_album_asset(raw_asset, album_summary)` should own fallback logic for filenames, timestamps, sizes, and media types so later phases can trust one normalized shape

Recommended responsibilities in [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py):

- keep the backend orchestration layer bridge-friendly
- expose a safe selected-album asset-loading path if `start_sort()` needs to prepare real album metadata before the mock job begins
- preserve clear errors for unknown album IDs, unloaded cache state, and asset fetch failures

Recommended bridge behavior in [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py):

- keep `get_albums()` unchanged
- keep the existing login and 2FA flow unchanged
- only add a new bridge method if Phase 3 intentionally introduces a debug album-detail flow or a UI-visible asset inspection action

## Sort-Time Hand-Off Expectations

Phase 3 should prepare the backend hand-off for later sorting work without implementing local matching yet.

That means:

- `start_sort(selected_album_ids)` can remain a mock progress flow for now
- the backend should gain a clear helper for resolving selected album IDs into real album summaries plus cached-or-loaded asset metadata
- comments or helper names should make it obvious that local file scanning and matching still belong to Epic 4
- any temporary sort mock should avoid depending on synthetic album rows once selected album metadata can be resolved from the real cache

## Planned File Changes

Primary implementation files:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py)
- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) only if a bridge-visible helper is deliberately added

Primary test files:

- [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py)
- [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) only if the bridge changes
- `tests/icloud/test_album_asset_metadata.py`
- `tests/icloud/test_album_asset_cache.py`
- `tests/icloud/test_album_asset_loading.py`

Frontend files:

- no frontend changes are required for the default Phase 3 path
- [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) should only change if a UI-facing asset-detail feature is added in the same implementation

## Implementation Tasks

### 1. Inspect raw `pyicloud` asset objects and define normalization rules

Work:

- identify which raw asset fields reliably expose asset ID, filename, created date, size, and media type
- define fallback order for filename extraction when multiple raw name fields exist
- define how timestamps should be normalized when `pyicloud` returns `datetime` objects, strings, or missing values
- define how optional fields should normalize to `null` instead of forcing later code to branch on missing keys

Output:

- one normalization path from raw asset objects to backend asset records
- representative fake asset fixtures for test coverage

### 2. Add per-album asset loading in `ICloudService`

Work:

- add a service method that loads assets for one cached album
- keep album cache validation explicit so unknown or unloaded album IDs fail clearly
- avoid changing `get_albums()` or loading assets eagerly during album browsing
- stamp `album_id` and `album_name` onto every normalized asset record

Output:

- backend callers can request real asset metadata for a specific album on demand

### 3. Add session-memory asset caching by album ID

Work:

- cache normalized asset lists by album ID after successful loads
- return cached assets on repeated requests by default
- support an explicit refresh path for one album without disturbing the whole cache
- keep cache updates atomic per album so failed refreshes do not partially replace good data

Output:

- per-album asset loading becomes cheap and predictable after the first successful fetch

### 4. Add selected-album asset loading helpers

Work:

- add a helper that accepts selected album IDs and returns resolved album summaries plus per-album asset metadata
- dedupe selected IDs and preserve a stable processing order
- fail clearly when the selection includes unknown album IDs
- avoid implicit loading for unrelated albums

Output:

- later sort phases can consume a backend-selected-album metadata hand-off instead of rebuilding it from raw album objects

### 5. Keep the bridge and UI lightweight by default

Work:

- preserve the existing `get_albums()` response shape
- avoid introducing an album-detail page unless it is explicitly wanted for debugging or support
- if a UI-visible asset inspection affordance is added, keep it optional and clearly separate from sorting

Output:

- the login -> album list flow stays fast and familiar

### 6. Add asset-focused test coverage

Work:

- add unit tests for asset normalization with complete and partial fake asset objects
- add tests for per-album cache hits, refreshes, and failed refresh behavior
- add tests for unknown album IDs and cold-cache behavior
- add tests for multi-album loading helpers that only load requested albums
- update mock sort tests as needed so they can work with real selected-album metadata without depending on eager file matching

Output:

- asset loading behavior is locked down before Epic 4 builds local matching on top of it

## Test Plan

Python unit tests:

- add `tests/icloud/test_album_asset_metadata.py` for raw-asset-to-normalized-record conversion
- cover missing filename, missing size, missing created date, and missing media-type cases
- verify timestamp normalization is consistent
- verify album context fields are stamped onto normalized assets

Python cache and service tests:

- add `tests/icloud/test_album_asset_cache.py` for first-load, repeat-load, refresh, and refresh-failure behavior
- add `tests/icloud/test_album_asset_loading.py` for per-album and multi-album load helpers
- verify successful empty asset lists are cacheable as a valid state
- verify unknown album IDs return a clear failure instead of an empty success
- verify cold-cache access fails clearly and does not perform hidden album discovery
- verify `get_assets_for_album_ids()` only loads requested albums and reuses cached results when available

Existing repo test updates:

- update [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py) if Phase 3 adds selected-album metadata helpers used by `start_sort()`
- update [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) only if a new bridge-visible method is added
- leave [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) unchanged unless the frontend gains an asset-detail behavior

Test execution target for this phase:

- `pytest`
- `npm test` only if frontend files are touched

If either tool is unavailable in the environment, keep the tests added and document the execution gap in the implementation notes for the phase.

## Acceptance Criteria

Phase 3 is complete when:

- the backend can load normalized asset metadata for a specific cached album by album ID
- normalized asset metadata includes filename plus any reliable size, timestamp, and media-type fields exposed by `pyicloud`
- missing optional asset fields normalize consistently instead of producing ad hoc shapes
- per-album asset metadata is cached in memory for the active authenticated session
- repeated asset requests for the same album reuse cache by default
- loading assets for one album does not eagerly load every album in the account
- selected album IDs can resolve to real album summaries plus per-album asset metadata for later sort work
- the album browser remains summary-only and does not become a local file scan or eager asset preload path
- no local filesystem scanning or cloud-to-local matching is introduced in this phase
- no JSON persistence or database layer is introduced for album metadata
- backend tests cover normalization, cache semantics, unknown album handling, and selected-album asset loading well enough to support Epic 4

## Risks And Mitigations

`pyicloud` asset shape variability:

- mitigate by isolating all raw-field reading inside normalization helpers and by testing with representative fake objects instead of exact production internals

Missing or unreliable filename fields:

- mitigate by defining a strict fallback order for filename extraction and by normalizing missing values explicitly

Large albums making eager loads expensive:

- mitigate by keeping asset loading per album and on demand, never inside `get_albums()`

Cache inconsistency between album summaries and asset metadata:

- mitigate by requiring album cache resolution before asset loading and by keying asset caches to stable album IDs

Refresh failure clobbering good asset cache:

- mitigate by rebuilding one album's normalized asset list off to the side and swapping it in only after a successful refresh

Bridge drift caused by exposing asset metadata too early:

- mitigate by keeping the default Phase 3 implementation backend-only unless there is a clear UI need in the same change
