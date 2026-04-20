# Epic 3 – Phase 5: Sort-Time Metadata Hand-Off

Source: [ICLOUD-SORTER-EPIC3-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-EPIC3-PLAN.md), Phase 5 (lines 282–294)

## Goal

Wire the existing per-album asset metadata loading through the service and bridge layers so the asset-fetching pipeline is available for Epic 4's sort implementation. Add a temporary verification button so a teammate can confirm the pipeline works end-to-end without needing to read code.

## What Already Exists

- `ICloudService.get_album_assets(album_id)` — loads and normalizes assets for one album
- `ICloudService.get_assets_for_album_ids(selected_album_ids)` — aggregates across multiple albums with ordered memberships
- `AlbumsService` wraps album/sort calls but does **not** expose the asset-fetching methods
- `API` bridge in `main.py` has no method to call asset fetching
- `start_sort()` still uses `DEFAULT_MOCK_SORT_TOTAL` — updating it to use real asset counts is deferred to Epic 4

## Deliverables

### 1. Wire asset fetching through `AlbumsService`

Add `get_album_assets(album_id)` to `AlbumsService`.

- Delegate to `self.icloud.get_album_assets(album_id)`
- Wrap with safe error handling and logging, same pattern as `get_albums()` and `start_sort()`
- Return the result dict unchanged on success

### 2. Expose a bridge method in `API`

Add `get_album_assets(self, album_id)` to the `API` class in `app/main.py`.

- Guard with the usual `if not self.albums_service` check
- Log the returned asset count to the Python terminal for verification
- Return the result dict to the frontend

### 3. Temporary "Test Asset Fetch" button

A temporary UI button so a teammate can verify the asset-fetching pipeline works. This button will be removed when Epic 4 wires real sorting.

#### HTML (`app/ui/index.html`)

Add a button above `download-btn` inside `.albums-footer`:

```html
<button id="test-fetch-btn" disabled>⬇ Test: Fetch album assets</button>
```

#### JS (`app/ui/js/albums.js`)

- Enable the button when one or more albums are checked
- On click, call `pywebview.api.get_album_assets(albumId)` for each selected album
- Log the full result to the browser console
- Show a brief summary in the `albums-status` element (e.g. "Fetched 179 assets for Vacation 2025")
- Disable the button while a fetch is in progress

#### Python terminal output

The `get_album_assets` bridge method logs the returned asset count and album name to the Python terminal so verification is visible in the console too.

### 4. Tests

Python:

- `AlbumsService.get_album_assets()` delegates correctly and handles errors
- `API.get_album_assets()` bridge returns failure when service is unavailable

Frontend (optional):

- Test-fetch button is disabled with no selection and enabled with one or more

## Files Touched

| File | Changes |
|---|---|
| `app/icloud/albums_service.py` | Add `get_album_assets(album_id)` |
| `app/main.py` | Add `get_album_assets(album_id)` bridge method |
| `app/ui/index.html` | Add temporary test button |
| `app/ui/js/albums.js` | Add click handler and enable/disable logic for test button |
| `tests/test_main_api_bridge.py` | Bridge test for new method |
| `tests/test_sorting_services.py` | Add `AlbumsService.get_album_assets()` tests |

## What Stays Out

- No local file scanning or matching
- No filesystem moves or copies
- No persistence — everything is session-memory only
- The test button is explicitly temporary and removed when Epic 4 wires real sorting

## Acceptance Criteria

- Asset metadata retrieval for selected albums is wired through all layers and available for Epic 4's sort implementation
- `start_sort()` is unchanged — real asset counts are deferred to Epic 4
- Sort-time local file matching is still not introduced
- A teammate can click the test button, select one or more albums, and see real asset metadata logged in the terminal and summarized in the UI
