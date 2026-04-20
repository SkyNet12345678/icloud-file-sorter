# Epic 3 Phase 3 Plan: Add Per-Album Asset Metadata Loading

Source documents:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE2-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

## Goal

Add a normalized, lazy per-album asset metadata loader on top of the Phase 2 session-memory album cache so backend code can fetch real iCloud asset records for selected albums without changing the album browser into a file-matching step.

This phase is about backend metadata retrieval and normalization only. It should not introduce local filesystem scanning, JSON persistence, or a UI redesign.

## Why This Phase Exists

Phase 2 left the repo in a good place for album-level lookups, but not yet for asset-level work:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) now keeps `album_cache_loaded`, `album_list_cache`, `album_summaries_by_id`, and `raw_albums_by_id`
- `get_cached_album()` and `get_cached_album_summary()` can resolve a selected album ID to cached album data, but there is still no asset loader built on top of those cached raw album handles
- `start_sort()` still creates a temporary mock job from album names only and does not yet load or reuse any real asset metadata
- there is no normalized asset metadata shape, so later matching work would otherwise have to reach into raw `pyicloud` objects directly

Phase 3 should close that gap by turning the Phase 2 raw album lookup into a safe per-album asset retrieval boundary with explicit normalization and caching.

## Phase 3 Scope

In scope:

- load asset metadata lazily for one album at a time using cached raw album objects from Phase 2
- normalize raw `pyicloud` asset objects into a backend-friendly metadata shape
- cache normalized per-album asset metadata in memory for the active authenticated session
- add helpers for resolving multiple selected album IDs into aggregated asset metadata for later sort preparation
- preserve multi-album membership and selected album ordering in aggregated helper results so later sort settings can distinguish "move to first selected folder" from "copy to each folder"
- make cache lifecycle and refresh semantics explicit and test-covered
- keep the current `get_albums()` bridge response summary-only and lightweight

Out of scope:

- local iCloud Photos folder scanning
- cloud-to-local filename matching
- moving or copying files on disk
- JSON-backed persistence for asset metadata
- eager loading of assets for every album during album browsing
- frontend album detail UI or asset preview UI
- replacing the temporary mock sort-progress flow with a real sort engine

## Current Phase 2 Baseline

The current repo already has the album-level prerequisites Phase 3 should build on:

- `ICloudService.get_albums(force_refresh=False)` reuses a session cache of normalized album summaries
- `raw_albums_by_id` preserves the backend source object needed for later album-specific work
- `get_cached_album()` and `get_cached_album_summary()` fail clearly when the album cache is cold
- `AlbumsService.get_albums()` and `API.get_albums()` already preserve the structured album payload the UI expects
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js) now submits selected album IDs to the backend, but it still does not need asset-level data during browsing

That means Phase 3 should stay mostly inside the Python service layer unless a tiny bridge-safe helper becomes necessary in the same change.

## Target Asset Metadata Shape

Phase 3 should define one normalized asset record shape for the backend to use going forward.

Recommended minimum shape:

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

Normalization rules:

- `asset_id` must come from a stable identifier exposed by `pyicloud`; if the exact raw field differs, normalize it in one helper
- if a raw asset does not expose a usable stable identifier, that asset must be skipped during normalization
- the loader must not emit `asset_id: null` and must not invent an app-generated fallback ID
- skipped assets should not cause the whole album load to fail by themselves; the album load may still succeed with the remaining normalized assets
- `filename` should be the best available filename for later local matching work
- `original_filename` is optional in spirit, but the normalized shape should still include it and set it to `filename` when `pyicloud` does not expose a distinct original-name field
- `created_at` should be normalized to a timezone-aware UTC ISO 8601 string such as `2025-08-05T12:34:56Z` when the source provides a usable datetime value; otherwise use `null`
- `size` should be an integer when reliably available; otherwise use `null`
- `media_type` should normalize to a small controlled set such as `image`, `video`, `live-photo`, or `unknown`
- `album_id` and `album_name` should be copied from the cached album summary so later matching code does not have to re-resolve that context per asset

Practical note:

- the exact raw `pyicloud` fields should be discovered from real or representative fake objects during implementation, but later code should only consume the normalized shape
- implementation should log or otherwise make skipped no-id assets observable for debugging, but Phase 3 does not need a user-facing UI for skipped-asset reporting

## Target Aggregated Asset Shape For Multiple Selected Albums

Per-album asset loading can keep album context directly on each normalized record, but the selected-album aggregation helper should preserve shared asset identity and album membership explicitly.

Recommended grouped result for `get_assets_for_album_ids(...)`:

```json
{
  "success": true,
  "selected_album_ids": [
    "album-123",
    "album-456"
  ],
  "assets": [
    {
      "asset_id": "asset-123",
      "filename": "IMG_1234.HEIC",
      "original_filename": "IMG_1234.HEIC",
      "created_at": "2025-08-05T12:34:56Z",
      "size": 2481934,
      "media_type": "image",
      "album_memberships": [
        {
          "album_id": "album-123",
          "album_name": "Vacation 2025",
          "selection_order": 0
        },
        {
          "album_id": "album-456",
          "album_name": "Favorites",
          "selection_order": 1
        }
      ]
    }
  ],
  "error": null
}
```

Rules:

- the aggregation helper should return one record per unique `asset_id` across the selected albums
- `album_memberships` must preserve the deduped selected album order so later sort code can apply deterministic first-selected-folder behavior
- the aggregation helper should preserve enough membership context for the MVP multi-album modes:
  - default: move the asset into the first selected album folder
  - optional setting: copy the asset into each selected album folder
- Phase 3 should not decide sort behavior itself; it should only preserve the data later sort code needs

## Target Asset Cache Design

Phase 3 should keep the asset cache session-scoped and explicit, similar to the album cache from Phase 2.

Recommended state inside `ICloudService`:

```json
{
  "asset_metadata_by_album_id": {
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
  "asset_cache_loaded_album_ids": [
    "album-123"
  ]
}
```

Notes:

- `asset_metadata_by_album_id` should hold normalized asset records keyed by album ID
- `asset_cache_loaded_album_ids` or an equivalent marker is important so the service can distinguish:
  - a cold cache for that album
  - a successful load that returned zero assets
- asset cache should remain memory-only for Epic 3
- asset cache should be cleared whenever the album cache is fully cleared for a session change
- asset cache should not be populated during `get_albums()`; it should only load when asset metadata is explicitly requested

## Asset Loader Lifecycle Rules

Phase 3 should make per-album loading behavior explicit:

1. Asset loading depends on the album cache already being loaded, because Phase 2 is now the source of truth for album ID to raw album resolution.
2. `get_album_assets(album_id, force_refresh=False)` should fail clearly if the album cache is cold.
3. If the album ID does not exist in the loaded album cache, return a clear album-not-found style failure instead of silently treating it as an empty asset list.
4. On first successful load for a given album ID, cache the normalized asset records for that album.
5. Repeated asset requests for the same album ID should reuse the per-album cache by default.
6. A valid empty asset list for an album should be cacheable as a successful load.
7. `force_refresh=True` should rebuild only the requested album's asset metadata and swap it in atomically.
8. If an asset refresh fails after a prior successful load, keep the last known-good asset cache for that album in place.
9. Refreshing or clearing the album cache should also invalidate all per-album asset cache entries so raw album handles and asset metadata cannot drift apart.
10. Read-only asset lookup helpers should never trigger hidden network work.

## Recommended Service API Shape

The bridge contract does not need to change for this phase, but the internal service API should become ready for later sort-time orchestration.

Recommended additions in [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py):

- `get_album_assets(album_id, force_refresh=False)`
- `get_assets_for_album_ids(selected_album_ids, force_refresh=False)`
- `get_cached_album_assets(album_id)`
- `_load_album_assets(album_id, force_refresh=False)`
- `_normalize_asset_metadata(raw_asset, album_summary)`
- `_iter_raw_album_assets(raw_album)` or an equivalent raw-object adapter helper
- `_clear_asset_cache()` with synchronization from `_clear_album_cache()`

Behavior:

- `get_album_assets(album_id, force_refresh=False)` should return a structured result shape, not raw `pyicloud` objects
- `get_assets_for_album_ids(selected_album_ids, force_refresh=False)` should dedupe album IDs while preserving selected order, reuse per-album cache where possible, and return one aggregated record per unique asset with ordered `album_memberships`
- `_normalize_asset_metadata(...)` should own all asset field cleanup so there is only one normalization path
- `_iter_raw_album_assets(raw_album)` should isolate the quirks of how `pyicloud` exposes album contents
- `get_cached_album_assets(album_id)` should be read-only and should fail clearly or return `None`-style misses when the requested album has not been loaded yet

Recommended result shape for one-album retrieval:

```json
{
  "success": true,
  "album": {
    "id": "album-123",
    "name": "Vacation 2025",
    "item_count": 179,
    "is_system_album": false
  },
  "assets": [],
  "error": null
}
```

Failure case:

```json
{
  "success": false,
  "album": null,
  "assets": [],
  "error": "Album not found"
}
```

Using a structured result keeps asset retrieval consistent with the Phase 1 album-list contract and makes failures easier to distinguish from genuine empty albums.

## Planned File Changes

Primary implementation files:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py) if the orchestration layer exposes or wraps the new backend helpers

Primary test files:

- [tests/icloud/test_album_cache.py](/home/mac/code/python/icloud-file-sorter/tests/icloud/test_album_cache.py)
- `tests/icloud/test_album_asset_metadata.py`
- `tests/icloud/test_album_asset_loading.py`

Files that should not need changes for the default Phase 3 path:

- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py)
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js)
- frontend tests, unless implementation intentionally exposes asset-loading behavior through the bridge in the same change

## Implementation Tasks

### 1. Inspect raw asset objects and define normalization rules

Work:

- inspect how a cached raw album exposes its asset collection
- identify which raw fields can reliably supply asset ID, filename, created-at, size, and media type
- define fallbacks for missing optional metadata
- define and test the skip behavior for raw assets that do not expose a stable identifier
- create representative fake asset fixtures for tests

Output:

- one normalization path from raw `pyicloud` asset objects to backend asset metadata
- fixture coverage for the raw object variability the repo has to tolerate

### 2. Add per-album asset cache state to `ICloudService`

Work:

- add asset-cache structures keyed by album ID
- keep empty-success and cold-cache states distinct
- synchronize asset cache invalidation with album cache invalidation

Output:

- one authoritative session-memory asset cache owned by `ICloudService`

### 3. Implement lazy `get_album_assets(album_id)`

Work:

- resolve the album ID through the existing Phase 2 album cache
- use the cached raw album object to retrieve album contents
- normalize raw assets into the Phase 3 backend metadata shape
- cache the normalized asset records for that album
- return a structured success or failure payload

Output:

- backend can load one album's real asset metadata without touching local filesystem work

### 4. Add grouped selected-album helper for later sort preparation

Work:

- implement `get_assets_for_album_ids(selected_album_ids, force_refresh=False)`
- dedupe selected IDs and preserve deterministic ordering
- reuse cached per-album assets where available
- merge repeated assets across selected albums into one aggregated record per `asset_id`
- preserve ordered `album_memberships` so later sort code can support both move-to-first-selected-folder and copy-to-each-folder modes without re-reading raw `pyicloud` objects

Output:

- later phases get a clean hand-off from selected album IDs to normalized album asset metadata

### 5. Keep album browsing summary-only

Work:

- ensure `get_albums()` remains summary-only and does not load per-album assets
- avoid changing the `pywebview` bridge or current UI unless a concrete requirement appears during implementation
- keep `start_sort()` behavior unchanged in this phase unless a tiny backend-only preloading hook is intentionally introduced and test-covered

Output:

- album browsing stays fast
- Phase 3 does not accidentally turn into sort-engine work

### 6. Add asset-loading tests before later matching work builds on top

Work:

- add unit tests for asset normalization with missing fields
- add tests for per-album cache hits and refresh
- add tests for unknown album IDs and cold-cache failures
- add tests confirming album cache refresh/clear invalidates asset cache safely
- add tests for grouped selected-album asset loading
- add tests confirming shared assets across multiple selected albums preserve ordered memberships in the aggregated result

Output:

- Phase 3 asset semantics are locked down before Epic 4 starts matching local files

## Test Plan

Python unit tests:

- add `tests/icloud/test_album_asset_metadata.py` for raw-asset-to-normalized-metadata coverage
- cover missing `size`, missing `created_at`, and missing or unexpected media-type fields
- cover filename fallback rules and `original_filename` behavior
- cover normalization of a stable `asset_id`
- cover skipping raw assets that do not expose a usable stable identifier
- confirm skipped no-id assets do not produce normalized records with `asset_id: null`
- cover normalization of `created_at` into a timezone-aware UTC ISO 8601 string
- confirm naive or unusable datetime inputs normalize to the canonical UTC format or `null`, rather than leaking inconsistent timestamp strings

Python service tests:

- add `tests/icloud/test_album_asset_loading.py` for:
  - first-load asset cache population per album
  - repeated `get_album_assets()` calls reusing cache
  - `force_refresh=True` for one album only
  - empty successful asset results
  - unknown album IDs returning a clear failure
  - cold-cache behavior when album cache has not been loaded yet
  - clearing or refreshing album cache invalidating per-album asset cache
  - grouped selected-album asset loading through `get_assets_for_album_ids(...)`
  - albums containing a mix of valid assets and no-id assets, confirming the load succeeds and only valid assets are cached
  - albums where all raw assets are skipped for missing IDs, confirming this is treated as a successful empty asset result rather than an album-load failure
  - assets that appear in multiple selected albums, confirming the aggregated helper returns one asset record with ordered `album_memberships`
  - selected album ordering is preserved in aggregated membership output so later first-selected-folder behavior is deterministic

Existing regression coverage to preserve:

- keep [tests/icloud/test_album_cache.py](/home/mac/code/python/icloud-file-sorter/tests/icloud/test_album_cache.py) passing while asset cache is added beside album cache
- keep [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py) passing so the temporary sort mock remains stable while Phase 3 stays backend-only

Frontend tests:

- no frontend changes should be required for the default Phase 3 path
- if a bridge-visible helper is added anyway, update frontend tests in the same change rather than leaving contract drift behind

Test execution target for this phase:

- `pytest`
- `npm --prefix frontend test` only if frontend files are touched

If either tool is unavailable in the environment, keep the tests added and document the execution gap in the implementation notes for the phase.

## Acceptance Criteria

Phase 3 is complete when:

- `ICloudService` can lazily load normalized asset metadata for a selected album using the cached raw album handle from Phase 2
- normalized asset metadata includes a stable upstream `asset_id`, `filename`, album context, and any reliable size/date/media-type fields exposed by `pyicloud`
- raw assets that do not expose a usable stable identifier are skipped rather than normalized with a null or synthetic `asset_id`
- skipped no-id assets do not by themselves cause album asset loading to fail
- missing optional fields are normalized consistently instead of leaking raw-object quirks to callers
- per-album asset metadata is cached in memory by album ID for the active authenticated session
- repeated asset loads for the same album reuse cache by default
- a valid empty album asset list is cacheable as a successful load
- refreshing or clearing the album cache invalidates the asset cache so album and asset state cannot drift apart
- backend callers can load asset metadata for multiple selected album IDs without rediscovering the full album list or touching local file matching
- aggregated selected-album asset results preserve all selected album memberships for shared assets and keep membership ordering deterministic
- `get_albums()` remains summary-only and does not trigger per-album asset loading
- no JSON persistence or database layer is introduced for album or asset metadata
- the existing login -> optional 2FA -> album list flow remains unchanged from the user's perspective
- local filesystem scanning and cloud-to-local matching still do not run during album browsing or simple asset metadata loading

## Risks And Mitigations

Asset object shape variability:

- mitigate by isolating normalization in one helper and building tests around representative fake objects instead of exact production internals

Missing or unstable upstream asset identifiers:

- mitigate by requiring `asset_id` to come from a stable `pyicloud` identifier only
- skip assets that do not expose a usable identifier instead of inventing fallback IDs that would make later dedupe or resumability unsafe

Album membership or ordering loss during multi-album aggregation:

- mitigate by returning one aggregated record per unique asset with ordered `album_memberships`
- preserve deduped selected album order so later MVP sort behavior can reliably choose the first selected folder or copy to each folder

Asset iteration may be slower than expected for large albums:

- mitigate by loading assets lazily per selected album instead of during `get_albums()`
- reuse per-album cache by default once loaded

Album and asset cache drift:

- mitigate by clearing asset cache whenever album cache is cleared or fully refreshed
- keep refresh behavior atomic so a failed reload does not leave mixed state behind

Filename metadata may be inconsistent across asset types:

- mitigate by defining a strict fallback order for `filename` and `original_filename`
- normalize missing values to `null` or a controlled fallback instead of leaking raw fields

Phase 3 accidentally grows into sort-engine work:

- mitigate by keeping the bridge and UI unchanged by default
- keep `start_sort()` as the existing mock workflow unless a narrowly scoped backend hand-off helper is explicitly added and test-covered

## Exit State For Phase 4 And Beyond

When this phase is done, the repo should have a clear backend boundary for:

- album summary retrieval through `get_albums()`
- album ID to raw album resolution through the Phase 2 cache
- per-album asset metadata retrieval through normalized, cached backend helpers

That gives later phases a clean foundation for real sort preparation and local file matching without having to rediscover album data or parse raw `pyicloud` asset objects throughout the codebase.
