# AGENTS.md

## Purpose

This repository is for a Windows desktop app that restores iCloud album structure on disk by organizing files already synced locally by iCloud for Windows.

The user-facing goal is:

1. Sign in to iCloud.
2. Read album metadata from iCloud.
3. Let the user choose albums.
4. Organize matching local files into album-named folders.

## Current Codebase Reality

Work from the code that exists today.

Current implementation:

- Python 3.11 desktop app launched with `python -m app.main`
- `pywebview` window hosting static HTML/CSS/JS from `app/ui/`
- Python-to-JS bridge exposed through the `API` class in `app/main.py`
- Apple auth flow implemented in Python via `pyicloud`
- Album and sorting flows are still mostly mocked
- Frontend is plain JavaScript, not React

Important existing behavior to preserve:

- The pywebview desktop shell
- The current login -> optional 2FA -> album list flow
- The JS bridge shape already used by the UI
- Existing tests unless we intentionally replace them with better coverage
- Defer expensive cloud-to-local file matching until sorting starts
- Check startup prerequisites early: iCloud for Windows presence and iCloud Photos folder existence

## Architecture Direction

Target direction for this repo:

- Desktop runtime: `pywebview`
- Backend/runtime logic: Python modules in `app/`
- Frontend: static HTML/CSS/vanilla JS under `app/ui/`
- Persistence: JSON file, not SQLite
- Release distribution: packaged desktop builds uploaded to S3
- Public download page: simple static HTML page that links to S3-hosted artifacts

Unless the user explicitly asks for a stack rewrite, do not introduce:

- FastAPI
- React
- a relational database
- unnecessary background infrastructure

## Planning Sources

Use the planning artifacts by role:

- [PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md): product overview and architecture constraints
- [ICLOUD-SORTER-PLAN.md](/home/mac/code/python/icloud-file-sorter/.planning/ICLOUD-SORTER-PLAN.md): readable execution plan grouped by epic
- [progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv): raw epic/task/status tracker

When they differ:

- behavior, architecture, and product constraints come from `PROJECT-OVERVIEW.md`
- epic grouping and broad progress tracking come from `tmp/progress.csv`
- implementation-step planning should use both, not either one in isolation

## JSON State Strategy

State should be file-based and simple. Prefer one user data directory such as:

- Windows: `%APPDATA%/icloud-sorter/`
- Dev fallback: a repo-local temp path only for tests

Suggested files:

- `settings.json`: user-configurable app settings
- `state.json`: album/file sync state and sort progress cache

Keep the JSON schema explicit and versioned. Include a top-level `schema_version`.

Suggested shape:

```json
{
  "schema_version": 1,
  "last_sync_at": null,
  "icloud_photos_path": null,
  "albums": [
    {
      "album_id": "album-1",
      "album_name": "Vacation 2025",
      "files": [
        {
          "filename": "IMG_1234.HEIC",
          "status": "pending",
          "error": null
        }
      ]
    }
  ]
}
```

Guidelines:

- Prefer atomic writes for JSON updates.
- Keep state human-readable.
- Avoid storing secrets in JSON.
- Treat JSON as replaceable derived state where possible.

## Repository Map

- [app/main.py](/home/mac/code/python/icloud-file-sorter/app/main.py): app entrypoint and pywebview API bridge
- [app/api/auth_api.py](/home/mac/code/python/icloud-file-sorter/app/api/auth_api.py): login and 2FA orchestration
- [app/icloud/auth.py](/home/mac/code/python/icloud-file-sorter/app/icloud/auth.py): low-level `pyicloud` login wrapper
- [app/icloud/icloud_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/icloud_service.py): album and sort service, currently mocked
- [app/icloud/albums_service.py](/home/mac/code/python/icloud-file-sorter/app/icloud/albums_service.py): adapter used by the bridge
- [app/ui/index.html](/home/mac/code/python/icloud-file-sorter/app/ui/index.html): desktop UI shell
- [app/ui/js/login.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/login.js): login/2FA interactions
- [app/ui/js/albums.js](/home/mac/code/python/icloud-file-sorter/app/ui/js/albums.js): album selection and sort progress UI
- [tests/](/home/mac/code/python/icloud-file-sorter/tests): Python tests
- [frontend/tests/login.test.js](/home/mac/code/python/icloud-file-sorter/frontend/tests/login.test.js): JS tests, currently out of sync with the UI implementation
- [tmp/architecture.drawio](/home/mac/code/python/icloud-file-sorter/tmp/architecture.drawio): architecture sketch focused on local sorting plus web distribution

## Working Rules For Future Changes

1. Preserve the existing desktop shell first.
2. Prefer incremental refactors over rewrites.
3. Update plan/docs when architecture decisions change.
4. Keep the Python bridge contract stable unless the UI is updated in the same change.
5. Prefer small service modules for auth, album discovery, file matching, sorting, and JSON persistence.
6. Keep secrets and auth session material out of the repo and out of plain JSON settings.
7. For long-running sorting, keep progress polling compatible with the current UI unless intentionally redesigned.
8. Keep album browsing lightweight; do local file scanning and cloud-to-local matching only inside the active sort job.
9. Add startup validation before the main workflow when a feature depends on local machine prerequisites such as iCloud for Windows and the synced photos folder.

## Testing Expectations

Python:

- Use `pytest`.
- Add unit tests for any new persistence, file-matching, and sorting logic.
- Prefer temporary directories for filesystem tests.

Frontend:

- Keep JS tests aligned with actual DOM wiring.
- If the UI API changes, update the frontend tests in the same change.

Current test caveats observed during analysis:

- `pytest` could not be run in this environment because `pytest` is not installed.
- `npm test` runs, but the existing login tests fail because they no longer match the current UI/module wiring.

## CI/CD Direction

Release flow should support:

1. Run lint/tests.
2. Build/package desktop artifacts.
3. Upload release assets to S3.
4. Publish or update a simple website that links to the S3 downloads.

Do not assume the website serves the binaries itself. S3 is the artifact source of truth.

## Near-Term Implementation Priorities

1. Replace mocked album/sort logic with real `pyicloud` album discovery and sort-time local file matching.
2. Add startup prerequisite detection for iCloud for Windows installation and local folder availability.
3. Introduce JSON-backed settings/state storage.
4. Add safe filesystem sorting with progress tracking and resumability.
5. Fix test drift so the suite reflects the current app behavior.
6. Add packaging and S3 release automation once the app flow is stable.
