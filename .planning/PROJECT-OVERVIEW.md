# iCloud Sorter Project Overview

This plan aligns the project with the current codebase and the revised stack decisions:

- keep the existing pywebview desktop app
- keep the current HTML/CSS/JS frontend shape unless there is a strong reason to change it
- use JSON files for persistence instead of SQLite
- plan releases around S3-hosted desktop artifacts plus a simple download page

## 1. Product Goal

iCloud for Windows syncs photos into a flat local folder without preserving iCloud album structure. This app signs into iCloud, reads album metadata, matches those assets against locally synced files, and organizes the files into album-named folders on the user’s Windows machine.

The app should not re-download photos. It should work with the local files already synced by iCloud for Windows.

## 2. Current Baseline

The repository already contains a functional desktop shell and partial auth flow:

- `app/main.py` launches a `pywebview` desktop window
- the UI is static HTML/CSS/vanilla JS under `app/ui/`
- the JS frontend calls Python through the pywebview `js_api`
- Apple login is wired through `pyicloud`
- 2FA verification is implemented
- album loading and sorting are still mocked

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
2. App checks whether iCloud for Windows appears to be installed and whether the local iCloud Photos folder exists.
3. If the prerequisite check fails, the app shows guidance and lets the user choose or confirm the folder path in settings.
4. User signs in with Apple ID.
5. If required, user completes 2FA.
6. App fetches albums from iCloud.
7. User selects albums to organize.
8. User starts sorting for the selected albums.
9. App scans the local iCloud Photos folder as part of that sort job.
10. App matches local files against selected iCloud album assets during that job.
11. App creates album folders and organizes matched files.
12. App shows progress and a completion summary, including failures or unmatched files.

### Startup Prerequisite Checks

On startup, the app should validate that the machine is ready before the user reaches the sorting flow.

- check whether iCloud for Windows appears to be installed
- check whether the expected iCloud Photos folder exists
- if either check fails, show a clear prerequisite/setup message instead of failing later during sorting
- allow the user to point the app at the correct local folder if auto-detection is incomplete
- store the confirmed folder path in settings JSON

## 6. Local File Strategy

The central product assumption is that files already exist locally because iCloud for Windows synced them down into a flat folder.

Expected source folder behavior:

- primary target is the local iCloud Photos sync folder
- users may need to confirm or override the path in settings
- the app should not require a separate export folder to deliver MVP value

Default discovery options:

- common iCloud for Windows folders on Windows
- optional user-selected override path stored in settings JSON
- startup validation that confirms the folder still exists before continuing

## 7. File Matching Strategy

### Primary Match

- match by filename from iCloud metadata to local files
- use case-insensitive matching on Windows

### Fallbacks

- compare file size when duplicate filenames exist
- support related file pairs where practical, such as Live Photo sidecars or RAW+JPEG pairs

### Expected Outcomes

- missing local file: report and continue
- local file not referenced by selected albums: leave untouched
- duplicate or ambiguous match: mark as failed with a clear reason

### When Matching Happens

Cloud-to-local file matching can take a long time, so it should not happen during album browsing or album list loading.

- `get_albums()` should stay lightweight and metadata-focused
- the initial album fetch should retrieve only what the browser needs to render: album name and total item count
- local filesystem scanning should begin only after the user starts sorting
- matching should run inside the sort job lifecycle so progress reporting reflects the real work
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
  "icloud_photos_path": null,
  "last_used_apple_id": null,
  "sort_mode": "move"
}
```

Notes:

- do not store passwords
- be cautious with session identifiers and trust tokens
- `sort_mode` may later support `copy` if needed, but MVP can remain `move`

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

- album data is mocked in `app/icloud/icloud_service.py`
- no real iCloud album enumeration yet

### Sorting

Working:

- UI progress bar and polling loop exist
- backend exposes start/progress methods

Gaps:

- sort jobs are mocked
- no local file scan, matching, folder creation, or move logic exists yet
- cancellation is UI-only and not implemented in Python

### Persistence

Working:

- none beyond in-memory runtime objects

Gaps:

- no JSON persistence layer yet
- current repo `settings.json` is editor config, not app configuration

### Testing

Working:

- Python tests cover some service and auth behavior

Gaps:

- Python test tooling is not installed in the current environment
- frontend login tests are out of date and currently failing

## 11. Non-Goals For Now

- rewriting the app into a web server plus SPA
- introducing a database
- syncing files back to iCloud
- multi-user backend accounts inside the desktop app itself
- solving licensing/purchases before the local sorting flow is real

## 12. Open Decisions To Revisit Later

- whether sorting is strictly `move` in MVP or whether `copy` should exist
- how much session persistence `pyicloud` should support between launches
- exact packaging tool for Windows release builds
- whether cancellation is a real MVP feature or a post-MVP feature
