# iCloud Sorter Epic Plan

This is the readable execution plan for the project.

Use the planning files like this:

- [.planning/PROJECT-OVERVIEW.md](/home/mac/code/python/icloud-file-sorter/.planning/PROJECT-OVERVIEW.md): product overview, architecture constraints, and source-of-truth behavior
- [tmp/progress.csv](/home/mac/code/python/icloud-file-sorter/tmp/progress.csv): raw epic/title/status tracking
- this file: normalized epic plan that follows the CSV while correcting it to match the current project direction

## Ground Rules

- keep the existing `pywebview` desktop shell
- keep the current HTML/CSS/vanilla JS frontend shape unless there is a clear need to change it
- use JSON persistence, not SQLite
- keep album browsing lightweight
- perform expensive iCloud asset metadata fetch, local file scanning, and cloud-to-local matching only when sorting starts
- sort inside the iCloud Photos folder for the current MVP direction
- publish release artifacts to S3 and provide downloads through a simple website

## Current Epic Status

The CSV currently shows two epics as already delivered at a baseline level:

- `Project Scaffold & Dev Environment`
- `Authentication & Session Management`

The remaining epics should be treated as the active forward plan, with some CSV items adjusted to fit the current architecture.

## Epic 1: Project Scaffold & Dev Environment

Status: baseline complete, cleanup still needed

Already present in the repo:

- Python project scaffold
- `pywebview` desktop shell
- frontend scaffold in `app/ui/`
- linting/testing/docker baseline
- initial README and test structure

Remaining cleanup:

- align README with the actual stack and current product direction
- fix frontend test drift so the tests reflect the current UI behavior
- verify Python test tooling installs and runs cleanly in the dev setup
- keep dev tooling consistent with the real codebase, not the older assumptions in the CSV

## Epic 2: Authentication & Session Management

Status: baseline complete, hardening remains

Already present in the repo:

- Apple ID login flow via `pyicloud`
- 2FA verification flow
- login and 2FA UI states
- auth-oriented test coverage

Remaining work inside or adjacent to this epic:

- verify cookie/session persistence behavior against the current code
- improve startup session validation
- handle expiry more gracefully before and during later operations
- keep auth responses compatible with the current pywebview bridge

## Epic 3: Album & Asset Metadata Retrieval

Status: next major implementation epic

Scope:

- fetch album list via `pyicloud`
- fetch album names and item counts for browsing
- hold album summaries in memory for the current session
- build the album browser UI around real data
- keep album detail view optional unless it becomes necessary for debugging or support

Important constraint:

- album browsing must remain metadata-only and fast
- do not fetch per-asset metadata during album loading or album browsing
- do not trigger local filesystem matching during album loading

## Epic 4: Local File Scanning & Matching

Status: planned

Scope:

- remove the temporary "Test Asset Fetch" button added in Epic 3 Phase 5
- fetch per-asset metadata from iCloud only after the user starts sorting selected albums
- aggregate asset metadata across the selected albums and preserve ordered album memberships
- scan the local iCloud Photos folder when the user starts sorting
- build a fast filename index for the local folder
- match by filename first, then use size and created-at style fallbacks when needed
- handle filename collisions and ambiguity explicitly
- expose match quality and failure counts to the UI

Corrections applied to the CSV:

- no database-backed `sorted_files` table
- any incremental history should live in JSON state
- iCloud asset metadata fetch and matching happen inside the active sort job, not as a pre-sort preload step

## Epic 5: Sorting Engine

Status: planned

Scope:

- create album subfolders inside the iCloud Photos folder
- move matched files into those folders for the current MVP direction
- define the behavior for files that belong to multiple albums
- default MVP behavior: move the asset into the first selected album folder
- optional MVP setting: copy the asset into each selected album folder
- record sort outcomes in JSON state
- support incremental or resumable behavior where practical
- build the sort manager UI around real progress
- handle filesystem errors without aborting the whole job

Corrections applied to the CSV:

- the current product direction does not use a separate target directory for MVP
- replace database records with JSON-backed sort history/state

## Epic 6: Settings & User Preferences

Status: planned

Scope:

- source folder setting with auto-detect plus manual override
- startup prerequisite detection for iCloud for Windows installation and folder presence
- sort behavior options such as move/copy and multi-album handling
- include an MVP multi-album mode setting with `move_first_selected_album` as the default and `copy_to_each_album` as the initial alternative
- settings UI
- load and save settings on startup via JSON

Corrections applied to the CSV:

- a separate target folder setting is de-scoped for the current product direction
- settings persistence should use JSON only

## Epic 7: Robustness & Error Handling

Status: planned and ongoing across other epics

Scope:

- beta expiry / kill switch policy
- structured logging to file
- session expiry during metadata fetch or sorting
- retry logic for transient iCloud/network failures
- large library performance concerns
- Windows filesystem edge cases
- user-facing error messages that give clear next steps

Notes:

- the CSV mixes beta-expiry and future licensing thoughts in one row; keep those as separate concerns in implementation
- robustness work should be layered onto the core epics, not saved entirely for the end

## Epic 8: Packaging, CI/CD & Distribution

Status: planned after the core local workflow is stable

Scope:

- GitHub Actions test pipeline
- Windows build pipeline for packaged desktop artifacts
- code signing if available
- release artifact upload to S3
- simple website with public download links to S3 objects
- optional auto-update work as a stretch goal

Corrections applied to the CSV:

- replace GitHub Releases as the primary distribution channel with S3-hosted artifacts
- keep the landing page simple; it exists to explain setup and link to downloads

## Recommended Execution Order

Work through the epics in this order unless a bug forces a detour:

1. finish cleanup in `Project Scaffold & Dev Environment`
2. harden `Authentication & Session Management`
3. implement `Album & Asset Metadata Retrieval`
4. implement `Settings & User Preferences`
5. implement `Local File Scanning & Matching`
6. implement `Sorting Engine`
7. layer in `Robustness & Error Handling`
8. finish `Packaging, CI/CD & Distribution`

This ordering keeps the real user path intact:

- startup validation first
- login and albums next
- matching only when sorting starts
- packaging only after the end-to-end workflow is real
