# iCloud Sorter Project Overview

This plan aligns the project with the current codebase and the revised stack decisions:

- keep the existing pywebview desktop app
- keep the current HTML/CSS/JS frontend shape unless there is a strong reason to change it
- use JSON files for persistence instead of SQLite
- plan releases around S3-hosted desktop artifacts plus a simple download page

## 1. Product Goal

iCloud for Windows syncs photos into a flat local folder without preserving iCloud album structure. This app signs into iCloud, reads album metadata, matches those assets against locally synced files, and organizes the files into album-named folders on the user’s Windows machine.

The app should not re-download photos. It should work with the local files already synced by iCloud for Windows.

For assets that belong to multiple selected albums, MVP behavior should be:

- default: move the asset into the first selected album folder
- optional setting: copy the asset into each selected album folder

## 2. Current Baseline

The repository already contains a functional desktop shell and partial auth flow:

- `app/main.py` launches a `pywebview` desktop window
- the UI is static HTML/CSS/vanilla JS under `app/ui/`
- the JS frontend calls Python through the pywebview `js_api`
- Apple login is wired through `pyicloud`
- 2FA verification is implemented
- album loading and sorting have real backend paths, with Epic 5 integration/docs hardening still in progress

This matters because the repo should evolve from the current baseline rather than being rebuilt around a different stack.

## 3. Architecture Decision

### Keep

- Python 3.11
- `pywebview`
- `pyicloud`
- repo-local frontend files in `app/ui/`
- Python service modules under `app/`

### Architecture Constraints

- do not add FastAPI as the primary app architecture
- do not rewrite the frontend to React unless there is a clear product need
- do not use SQLite for state
- use JSON-backed persistence for settings and sortable album/file state

## 4. Target Architecture

### Desktop App

- Launch with `python -m app.main`
- `app/main.py` remains the application entrypoint
- the pywebview API bridge remains the main boundary between UI and Python services

### Python Layers

- `app/api/`: bridge-friendly orchestration classes
- `app/icloud/`: iCloud auth and album/asset metadata access
- `app/sorting/`: local filesystem matching and move/copy logic
- `app/state/`: JSON settings and state persistence
- `app/logger.py`: logging setup

The last two modules do not exist yet but should be added as the implementation grows.

### Frontend

- Keep the UI in `app/ui/`
- Continue to call Python bridge methods instead of introducing an HTTP API by default
- Expand the current album selection and progress UI rather than replacing it

### Distribution

- CI builds release artifacts
- artifacts are uploaded to S3
- a simple website provides public download links pointing at S3 objects

## 5. End-to-End User Flow

1. User opens the desktop app.
2. App checks whether the configured local iCloud Photos `Photos` folder exists and is accessible; iCloud for Windows installation detection is advisory.
3. If the prerequisite check fails, the app shows guidance and lets the user choose or confirm the folder path in settings.
4. User signs in with Apple ID.
5. If required, user completes 2FA.
6. App fetches albums from iCloud.
7. User selects albums to organize.
8. User starts sorting for the selected albums.
9. App scans the configured local source folder as part of that sort job. On Windows the default source folder is `C:\Users\USER\Pictures\iCloud Photos\Photos`.
10. App matches local files against selected iCloud album assets during that job.
11. App creates album folders and organizes matched files according to the selected multi-album behavior.
12. App shows progress and a completion summary, including failures or unmatched files.

### Startup Prerequisite Checks

On startup, the app should validate that the machine is ready before the user reaches the sorting flow.

- check whether the expected iCloud Photos `Photos` folder exists and can be read/written
- treat iCloud for Windows installation/running-state detection as advisory, not a hard blocker when the source folder is accessible
- if folder validation fails, show a clear prerequisite/setup message instead of failing later during sorting
- allow the user to point the app at the correct local folder if auto-detection is incomplete
- store the confirmed folder path in settings JSON

## 6. Local File Strategy

The central product assumption is that files already exist locally because iCloud for Windows synced them down into a flat folder.

Expected source folder behavior:

- primary target is the local iCloud Photos sync folder that contains the synced photo files
- on Windows the default source folder is `C:\Users\USER\Pictures\iCloud Photos\Photos`, not the parent `C:\Users\USER\Pictures\iCloud Photos`
- if settings contain the parent `iCloud Photos` folder and its `Photos` child exists, normalize the setting to the `Photos` child
- album folders must be created inside the configured source folder, for example `C:\Users\mac\Pictures\iCloud Photos\Photos\Trips`
- users may need to confirm or override the path in settings
- the app should not require a separate export folder to deliver MVP value

Default discovery options:

- `C:\Users\USER\Pictures\iCloud Photos\Photos` on Windows
- optional user-selected override path stored in settings JSON
- startup validation that confirms the folder still exists before continuing

## 7. File Matching Strategy

### Primary Match

- match by filename from iCloud metadata to local files
- use case-insensitive matching on Windows

### MVP Matching Limits

- do not use local file size or local timestamps as automatic fallback match keys for MVP
- iCloud for Windows may expose local placeholder files whose filesystem metadata is not reliable enough for safe automatic fallback matching
- if a filename hit is missing, report the asset as unmatched rather than forcing a metadata-based guess
- support related file pairs such as Live Photo sidecars or RAW+JPEG pairs only after there is a verified local matching strategy for them

### Expected Outcomes

- missing local file: report and continue
- local file not referenced by selected albums: leave untouched
- duplicate or ambiguous match: mark as failed with a clear reason

### Multi-Album Sorting Behavior

Some assets belong to multiple albums, such as `Favorites` plus a user-created album.

For MVP:

- default behavior should be `move_first_selected_album`, meaning the matched local file is moved into the first selected album folder for that asset
- an optional setting should allow `copy_to_each_album`, meaning the matched local file is copied into each selected album folder for that asset
- the metadata pipeline should preserve selected album order so the default behavior is deterministic

### When Matching Happens

Cloud-to-local file matching can take a long time, so it should not happen during album browsing or album list loading.

- `get_albums()` should stay lightweight and metadata-focused
- the initial album fetch should retrieve only what the browser needs to render: album name and total item count
- local filesystem scanning should begin only after the user starts sorting
- matching should run inside the sort job lifecycle so progress reporting reflects the real work
- MVP automatic matching should remain filename-only unless real local metadata proves reliable enough for a later revision
- matched file state can then be written into JSON as part of the active sort run

## 8. JSON Persistence Plan

SQLite is removed from the active plan. JSON files replace database-backed state.

### Storage Location

Use a user data directory outside the repo in normal app runs. For tests, use temp directories.

Suggested runtime files:

- `settings.json`
- `state.json`

### Settings JSON

Suggested fields:

```json
{
  "schema_version": 1,
  "source_folder": null,
  "sorting_approach": "first",
  "remembered_apple_id": null
}
```

Notes:

- do not store passwords
- be cautious with session identifiers and trust tokens
- `sorting_approach` uses `first` by default and `copy` as the initial alternative
- `source_folder` stores the sortable root, normally `C:\Users\USER\Pictures\iCloud Photos\Photos` on Windows

### State JSON

Suggested shape:

```json
{
  "schema_version": 1,
  "last_sync_at": null,
  "albums": [
    {
      "album_id": "album-123",
      "album_name": "Vacation 2025",
      "files": [
        {
          "filename": "IMG_0001.HEIC",
          "status": "pending",
          "error": null
        }
      ]
    }
  ]
}
```

### JSON Write Rules

- use atomic writes
- preserve valid UTF-8 JSON
- prefer stable key ordering and indentation for debuggability
- keep derived state rebuildable from iCloud metadata where possible

## 9. Bridge Contract

The UI currently calls methods directly on `globalThis.pywebview.api`. Build on that.

Existing bridge methods:

- `login(apple_id, password)`
- `verify_2fa(code)`
- `get_albums()`
- `start_sort(selected_album_ids)`
- `get_sort_progress(job_id)`
- `cancel_sort(job_id)`
- `get_settings()` / `save_settings(...)` / `detect_source_folder()`

Recommended evolution:

- preserve these methods while implementation becomes real
- add settings methods only when needed
- if request/response shapes change, update the JS UI and tests in the same change

## 10. Current Gaps Between Code And Plan

### Auth

Working:

- login wrapper exists
- 2FA verification exists

Gaps:

- session persistence is minimal
- no clear user settings or trusted session lifecycle yet

### Album Discovery

Working:

- UI can render an album list

Gaps:

- continue validating real iCloud album enumeration against live accounts and edge-case album shapes

### Sorting

Working:

- UI progress bar and polling loop exist
- backend exposes start/progress methods

Gaps:

- continue validating recursive re-sort behavior, copy tracking, and cancellation on large real libraries
- keep album folders anchored inside the configured source folder

### Persistence

Working:

- JSON-backed settings and sort state exist

Gaps:

- continue hardening recovery from corrupted/stale JSON state

### Testing

Working:

- Python tests cover some service and auth behavior

Gaps:

- keep Python and frontend test suites aligned with the current bridge/UI behavior

## 11. Non-Goals For Now

- rewriting the app into a web server plus SPA
- introducing a database
- syncing files back to iCloud
- multi-user backend accounts inside the desktop app itself
- solving licensing/purchases before the local sorting flow is real

## 12. Open Decisions To Revisit Later

- how much detail the user-facing skipped/error report should show initially
- how much session persistence `pyicloud` should support between launches
- exact packaging tool for Windows release builds
- whether cancellation is a real MVP feature or a post-MVP feature
