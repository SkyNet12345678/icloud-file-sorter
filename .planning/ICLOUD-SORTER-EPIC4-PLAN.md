# Epic 4: Local File Scanning & Matching

## Decisions Confirmed

- **1A**: Auto-detect + manual override for source folder
- **1B**: Remember last used path, auto-detect fallback if missing
- **2A**: Size + created-at secondary matching
- **3A**: Skip ambiguous to error count (iCloud for Windows guarantees unique filenames)
- **4A**: JSON settings with schema version for source_folder persistence
- **4B**: sorting_approach global setting: "first" (default) or "copy"
- **4C**: Copy warning always visible when "copy" is selected
- **5**: Match quality metrics confirmed

## Settings Schema (v1)

```json
{
  "schema_version": 1,
  "source_folder": "C:\\Users\\...\\iCloud Photos",
  "sorting_approach": "first"
}
```

- `source_folder`: Remember last used, auto-detect fallback if missing
- `sorting_approach`: "first" = move to first album folder, "copy" = copy to all albums
- Copy warning: Always show when "copy" approach selected
  > "Copy will download full-resolution files from iCloud before copying. This may take significant time and storage for large albums."

## Startup Validation

- On app start: Check if saved source_folder exists → use it
- If saved folder missing: Auto-detect and update settings
- On sort start: Validate source_folder exists → error if missing

## Auto-Detect Paths

```
Windows:
- %USERPROFILE%\Pictures\iCloud Photos
- %USERPROFILE%\Apple Cloud\Pictures (older)
- Falls back to Pictures/iCloud Photos
```

---

## Phase 1: Settings Infrastructure

### Step 1.1: Create SettingsService

- New file: `app/settings.py`
- JSON persistence to `%APPDATA%/icloud-sorter/settings.json`
- Schema v1: source_folder, sorting_approach
- Load/save methods
- Auto-detect on startup: validate saved path, fallback to auto-detect if missing

### Step 1.2: Add source_folder to API bridge

- Modified: `app/main.py`
- Add `get_settings()`, `save_settings()`, `detect_source_folder()` to API

### Step 1.3: Copy approach warning UI

- New: `app/ui/js/settings.js`
- Show current approach
- Display warning when "copy" is selected
- Allow approach toggle

---

## Phase 2: Local Scanner

### Step 2.1: Create LocalScanner class

- New file: `app/scanner.py`
- `LocalScanner` class with:
  - `__init__(source_folder)`
  - `scan()` - builds filename index
  - `match_assets(assets)` - matches cloud assets to local files
  - `get_index()` - returns current index

### Step 2.2: Index structure

```python
{
  "IMG_1234.HEIC": [
    {"path": "...", "size": 1234567, "created_at": "2025-01-15T10:30:00Z"},
  ],
  "IMG_1234.mp4": [...],
}
```

### Step 2.3: Folder validation

- Validate folder exists before scanning
- Return clear error if missing

### Step 2.4: Expose via service

- Modified: `app/icloud/albums_service.py`
- Add `LocalScanner` to service layer

---

## Phase 3: Matching Logic

### Step 3.1: Filename-first matching

- Exact filename match
- Case-insensitive comparison

### Step 3.2: Size + created-at fallback

- Match if same size ± tolerance AND same date (±1 day)
- Return match type: "exact" | "fallback" | "none"

### Step 3.3: Ambiguity detection

- Multiple files with same filename = report as "ambiguous" (rare per design note)

### Step 3.4: Match result structure

```python
{
  "matched": 1450,
  "fallback_matched": 42,
  "not_found": 12,
  "ambiguous": 0,
  "assets": [
    {
      "asset_id": "...",
      "filename": "...",
      "local_path": "...",
      "match_type": "exact|fallback|none",
    },
  ],
}
```

---

## Phase 4: Integration into Sort Job

### Step 4.1: Update start_sort()

- Modified: `app/icloud/icloud_service.py`
- Call scanner to get match results before sorting

### Step 4.2: Job state updates

```python
{
  "job_id": "...",
  "status": "matching|sorting|complete",
  "match_results": {
    "matched": 1450,
    "fallback_matched": 42,
    "not_found": 12,
    "ambiguous": 0,
  },
  "sort_results": {...},
}
```

### Step 4.3: Validate source folder

- Check source_folder exists before sort starts
- Return clear error if not configured

---

## Phase 5: UI Cleanup

### Step 5.1: Wire test button to real API

- Modified: `app/ui/index.html`
- Keep `<button id="test-fetch-btn">` - wire to get_album_assets for debugging

### Step 5.2: Keep testFetchAlbumAssets wired

- Modified: `app/ui/js/albums.js`
- Keep `testFetchAlbumAssets()` - useful for verifying album fetching

### Step 5.3: Update progress display

- Add match quality counts to progress message
- Example: "Matched: 1450 | Fallback: 42 | Not found: 12"

---

## Phase 6: Tests

### Test files to create

- `tests/scanner/__init__.py`
- `tests/scanner/test_local_scanner.py` - Index building, filename matching
- `tests/scanner/test_matching.py` - Fallback matching, ambiguity
- `tests/test_settings.py` - Load/save, auto-detect

---

## File Summary

### New files
- `app/settings.py` - Settings persistence (schema v1)
- `app/scanner.py` - Local scanner + matching
- `app/ui/js/settings.js` - Settings UI (copy warning)

### Modified files
- `app/main.py` - Add settings API
- `app/icloud/icloud_service.py` - Integrate scanner
- `app/icloud/albums_service.py` - Delegate scanner
- `app/ui/index.html` - Keep test button wired
- `app/ui/js/albums.js` - Keep test function wired, update progress

---

## Dependencies

- **Epic 3** (Album metadata): Working ✓
- **pathlib**: Already in `app/logger.py` ✓
- **JSON**: Standard library ✓