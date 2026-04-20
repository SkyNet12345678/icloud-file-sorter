# Epic 3 Phase 2 Plan: Build In-Memory Album Cache

Source documents:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md)
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md)
- [ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PHASE1-PLAN.md)
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv)

## Goal

Add an explicit session-memory cache for album metadata so repeated album requests reuse the Phase 1 normalized results instead of repeatedly walking the raw `pyicloud` album collection.

This phase is about cache structure and lifecycle only. It should not introduce persistence, eager per-asset loading, local file scanning, or sort-engine work.

## Why This Phase Exists

Phase 1 established the real album boundary, but the current implementation still behaves like a direct fetch path on every request:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py) rebuilds normalized album summaries each time `get_albums()` runs
- `album_summaries_by_id` is useful for ID-based sort selection, but it is not yet a complete cache with explicit population and invalidation behavior
- there is no stable mapping from album IDs to the raw source album objects, or an equivalent source-handle wrapper, that Phase 3 will need for per-album asset loading
- cache lifecycle is currently implicit rather than documented and test-covered

Phase 2 should turn the existing summary map into a clear session cache so later phases can load selected album assets from a known in-memory source instead of re-querying and re-normalizing album data ad hoc.

## Phase 2 Scope

In scope:

- cache normalized album summaries in memory for the active authenticated session
- cache a lookup from album ID to the source raw album object, or to a backend-only wrapper that still preserves the source handle needed for later per-album asset loading
- define explicit cache population, read, refresh, and clear behavior
- keep cache lifetime tied to the authenticated service lifetime
- add tests for cache hits, cache refresh, and cache invalidation
- preserve the existing bridge contract returned by `get_albums()`

Out of scope:

- per-album asset metadata loading
- asset metadata cache
- local iCloud Photos folder scanning or file matching
- JSON persistence or settings/state storage
- UI redesign or new frontend album interactions

## Current Phase 1 Baseline

The repo already has the core pieces that Phase 2 should build on:

- `ICloudService.get_albums()` returns a structured payload with `success`, `albums`, and `error`
- album selection now uses stable album IDs instead of list indexes
- `album_summaries_by_id` already supports resolving selected album names for the temporary sort flow
- the album UI already handles success, empty, and error cases through the existing `pywebview` bridge

That means Phase 2 can stay internal to the Python service layer unless implementation details force a small bridge update.

## Target Cache Design

Phase 2 should keep the cache simple and session-scoped.

Recommended cache state inside `ICloudService`:

```json
{
  "album_cache_loaded": true,
  "album_list_cache": [
    {
      "id": "album-123",
      "name": "Vacation 2025",
      "item_count": 179,
      "is_system_album": false
    }
  ],
  "album_summaries_by_id": {
    "album-123": {
      "id": "album-123",
      "name": "Vacation 2025",
      "item_count": 179,
      "is_system_album": false
    }
  },
  "raw_albums_by_id": {
    "album-123": "<pyicloud album object>"
  }
}
```

Notes:

- `album_list_cache` should hold the UI-facing normalized summaries in sorted order
- `album_summaries_by_id` should remain available for the existing sort selection flow
- `raw_albums_by_id` or an equivalent backend-only mapping should support later per-album asset loading without another full album discovery pass
- if the implementation avoids storing the exact raw `pyicloud` object, the cached value must still preserve a source handle or wrapper that can load assets later without rediscovering the full album list
- the cache should remain memory-only and should not be written to JSON in Epic 3

## Cache Lifecycle Rules

Phase 2 should make lifecycle behavior explicit:

1. On first successful `get_albums()` call for a service instance, populate the cache from `pyicloud`
2. On later `get_albums()` calls for the same authenticated service instance, return the cached normalized payload by default
3. Provide a small explicit cache-clear path for cases where the session changes or a future refresh action is added
4. If a cache refresh is requested, rebuild all cache structures together so summaries and raw album mappings stay consistent
5. Cache refresh should be atomic from the caller's perspective: build replacement cache data off to the side and swap it in only after the rebuild succeeds
6. If a refresh attempt fails after a prior successful load, keep the last known-good cache in place and return a failure result rather than partially clearing or partially replacing cache state
7. If album loading fails before any successful load has happened, do not mark the cache as successfully loaded
8. Read-only backend lookup helpers should never trigger hidden network work
9. Callers that need album-backed records before `get_albums()` has run must first call an explicit cache-loading path such as `get_albums()` or `_load_album_cache()`
10. If a caller tries to resolve album IDs before the cache is loaded, the service should fail clearly instead of silently treating unknown IDs as valid

Practical repo-specific note:

- today, [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) creates a new `AlbumsService` after successful login or 2FA verification, which naturally gives each authenticated session a fresh `ICloudService` instance
- Phase 2 should preserve that behavior, but still provide an explicit clear/reset helper in the service so the cache rules are testable and not dependent on object replacement alone

## Recommended Service API Shape

The public bridge contract does not need to change for this phase, but the internal service API should become more intentional.

Recommended internal methods in [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py):

- `get_albums(force_refresh=False)`
- `_load_album_cache()`
- `_clear_album_cache()`
- `_build_album_cache(raw_albums)`
- optional lookup helper such as `get_album_by_id(album_id)` or `get_cached_album(album_id)`

Behavior:

- `get_albums(force_refresh=False)` should return cached summaries when available
- `force_refresh=True` should rebuild the entire cache in one pass
- `_build_album_cache(raw_albums)` should own sorting, normalization, and dictionary population so there is only one way the cache is constructed
- `_load_album_cache()` should be the only internal method allowed to fetch raw albums and populate cache state
- lookup helpers should read from cache only and should not trigger new network work implicitly
- if lookup helpers are called before cache is loaded, they should return a clear cache-not-loaded failure or `None`-style miss that callers must handle explicitly

## Planned File Changes

Primary implementation files:

- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py)
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py)
- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py) only if a small bridge-visible refresh/reset behavior becomes necessary

Primary test files:

- [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py)
- `tests/icloud/test_album_cache.py`
- `tests/icloud/test_album_service_get_albums.py` if Phase 1 added or intended this service-level file
- [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) only if bridge-facing behavior changes

Frontend files:

- no frontend changes should be required for the default Phase 2 path
- [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) should only change if implementation accidentally alters the album payload shape or repeat-load behavior exposed to the UI

## Implementation Tasks

### 1. Formalize cache state inside `ICloudService`

Work:

- replace the current summary-only state with a fuller cache model
- keep `album_summaries_by_id` for existing sort behavior
- add a cache-loaded flag and cached ordered album list
- add a backend-only album ID lookup for later Phase 3 work
- require that the backend-only lookup preserves a source handle usable for later asset loading, not just another copy of the UI summary

Output:

- one authoritative in-memory album cache owned by `ICloudService`
- clear distinction between uncached state and cached-empty-success state

### 2. Route `get_albums()` through the cache

Work:

- make the first successful album request populate cache structures
- return cached summaries on repeated calls during the same authenticated session
- keep the existing structured response shape unchanged
- ensure failed fetches do not poison the cache as a successful load

Output:

- repeated album list requests become cheap and deterministic
- the UI still receives the same album payload it already expects

### 3. Add explicit refresh and invalidation helpers

Work:

- add a private or service-internal cache clear/reset helper
- support a deliberate cache rebuild path, even if only used by tests for now
- keep summary cache and raw album lookup invalidation synchronized
- make refresh semantics atomic so a failed rebuild cannot leave behind partially replaced cache state

Output:

- cache invalidation becomes explicit instead of accidental
- later phases can choose when to trust cache versus rebuild it

### 4. Preserve session-lifetime behavior through `AlbumsService`

Work:

- keep `AlbumsService.get_albums()` bridge-friendly and stable
- avoid introducing new bridge fields unless necessary
- document or lightly encode that the cache belongs to the authenticated session lifetime represented by the current service instance

Output:

- cache behavior stays internal to the backend
- login and 2FA flow remain unchanged from the UI perspective

### 5. Prepare cache lookups for later selected-album work

Work:

- add a safe lookup helper by album ID for backend callers
- make sure selected album IDs can resolve to both summary metadata and the source album record needed for Phase 3 asset loading
- keep lookup behavior read-only and cache-backed
- define the precondition clearly: callers must load cache first through an explicit cache-loading path, and lookup helpers must not silently fetch albums on their own

Output:

- later sort preparation can reuse cache instead of rediscovering albums

### 6. Add cache-focused test coverage

Work:

- add unit tests for first-load cache population
- add tests for repeated `get_albums()` calls reusing cache
- add tests for forced refresh or explicit cache reset
- add tests confirming failed fetches do not mark cache as loaded
- add tests for ID-based raw album lookup from cache
- add tests confirming failed refresh keeps the last known-good cache intact
- add tests confirming lookup helpers do not implicitly fetch albums when cache is cold

Output:

- cache semantics are locked down before asset metadata loading builds on top of them

## Test Plan

Python unit tests:

- add `tests/icloud/test_album_cache.py` covering cache population from fake `pyicloud` album objects
- verify that repeated `get_albums()` calls do not repeatedly invoke the raw album fetch path once cache is loaded
- verify cache refresh replaces all cache structures together
- verify refresh failure preserves the previous successful cache rather than partially clearing it
- verify empty successful album results are cacheable as a valid loaded state
- verify a failed album fetch leaves cache unloaded or otherwise clearly invalid
- verify album ID lookup uses cached data and does not re-fetch albums
- verify album ID lookup preserves access to a source record or wrapper that later phases can use for asset loading
- verify cache-dependent lookups fail clearly when cache has not been loaded yet

Python service and bridge tests:

- update `AlbumsService.get_albums()` tests to confirm repeated calls remain stable while the cache is internal
- update [tests/test_sorting_services.py](/home/mac/code/python/icloud-file-sorter/tests/test_sorting_services.py) if needed so existing sort behavior still works with the richer cache state
- update [tests/test_main_api_bridge.py](/home/mac/code/python/icloud-file-sorter/tests/test_main_api_bridge.py) only if this phase adds a bridge-visible refresh/reset path

Frontend tests:

- no new frontend cases should be required if the bridge payload remains unchanged
- keep [frontend/tests/albums.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/albums.test.js) passing without changing its expectations about response shape

Test execution target for this phase:

- `pytest`
- `npm --prefix frontend test` only if frontend files are touched or frontend regression coverage is needed

If either tool is unavailable in the environment, keep the tests added and document the execution gap in the implementation notes for the phase.

## Acceptance Criteria

Phase 2 is complete when:

- the album service has an explicit in-memory cache for the active authenticated session
- repeated `get_albums()` calls reuse cached normalized summaries by default
- album IDs can resolve to cached backend records needed by later phases, not only UI summary names
- the backend album lookup preserves a source handle or wrapper sufficient for later asset loading without rediscovering the full album list
- cache population, refresh, and clear behavior are explicit and test-covered
- a failed album fetch does not leave behind a false successful cache state
- a failed refresh does not destroy or partially replace a previously good cache
- a valid empty album list is cacheable as a successful loaded state
- no JSON persistence or database layer is introduced for album metadata
- the `pywebview` bridge contract for album loading remains stable unless intentionally extended in the same change
- login -> optional 2FA -> album list flow remains unchanged from the user’s perspective
- local filesystem scanning and cloud-to-local matching still do not run during album loading
- cache-dependent backend lookups do not perform hidden network work and have a documented cold-cache behavior

## Risks And Mitigations

Stale session cache:

- mitigate by tying cache ownership to the authenticated service instance and by providing an explicit cache clear/reset helper

Cache mismatch between summaries and raw album records:

- mitigate by rebuilding all cache structures in one helper instead of mutating them independently

Refresh failure leaving cache in a partial state:

- mitigate by building replacement cache data off to the side and swapping it in only after a full successful rebuild

Later phases unable to load assets from cached album IDs:

- mitigate by requiring the cache to retain the raw album object or a source-handle wrapper that preserves later asset-loading capability

Cold-cache backend lookups behaving unpredictably:

- mitigate by documenting that lookup helpers are read-only, never perform hidden fetches, and fail clearly until an explicit cache-loading path has run

Accidental bridge drift:

- mitigate by keeping Phase 2 backend-only unless a bridge change is absolutely necessary, and updating tests if that happens

Overbuilding the cache before Phase 3:

- mitigate by caching only album summaries plus raw album lookup, not full asset metadata

## Exit State For Phase 3

When this phase is done, the next phase can add per-album asset metadata loading on top of a stable session-memory album cache, using album IDs to resolve the source album object without re-fetching and re-normalizing the full album list on every step.
