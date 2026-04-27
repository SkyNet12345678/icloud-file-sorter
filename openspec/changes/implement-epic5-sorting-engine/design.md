## Context

The iCloud Sorter application has a functional desktop shell with pywebview, HTML/CSS/JS frontend, Apple authentication via pyicloud, real album metadata plumbing, existing JSON-backed settings, and an Epic 4 handoff that already performs selected-album asset aggregation plus recursive filename matching. The remaining Epic 5 work is to replace downstream mocked sort progress with safe, resumable filesystem operations.

Based on the PROJECT-OVERVIEW.md and ICLOUD-SORTER-EPIC4-PLAN.md, we have established architectural constraints:
- Keep the existing pywebview desktop shell
- Maintain current HTML/CSS/vanilla JS frontend shape
- Use JSON persistence instead of SQLite
- Reuse the existing `app/settings.py` settings contract
- Reuse the existing recursive filename scanner and selected-asset aggregation
- Perform expensive iCloud metadata fetch, local scanning, matching, and sorting only during active sort jobs
- Preserve the existing Python-to-JS bridge contract unless the UI is updated in the same change

## Goals / Non-Goals

**Goals:**
- Implement real sorting engine operations that move/copy matched local files based on iCloud album membership
- Replace mocked downstream sort job progress with actual file system operations
- Add JSON persistence for sort job progress/state, enabling safe restarts and resumable/idempotent re-runs
- Reuse and extend existing settings persistence instead of introducing a parallel settings model
- Implement multi-album behavior using existing `sorting_approach` values: `first` and `copy`
- Keep recursive source scanning, while tracking app-created copies so they can be ignored as duplicate copies in future matching
- Add safe album-folder mapping from iCloud album IDs to Windows-safe folder paths
- Add non-interactive skipped-file and error handling for file system operations during sorting
- Add cancellation support for long-running sorts without rollback or pause semantics
- Update the Python bridge to expose real sort progress, cancellation, and completion while maintaining compatibility
- Validate the configured source folder before starting file operations

**Non-Goals:**
- Rewriting the frontend to React or introducing a web server architecture
- Adding SQLite or other relational databases for persistence
- Implementing complex duplicate detection beyond filename matching for MVP
- Supporting two-way sync back to iCloud
- Implementing advanced metadata-based matching (EXIF, file hashes) for MVP
- Creating a separate target directory for sorted files; sorting happens in-place within the configured iCloud Photos folder
- Implementing pause/resume controls; re-running a sort should be safe due to recursive scanning and persisted state
- Detecting or specially handling iCloud placeholder files for MVP
- Treating iCloud for Windows installation detection as a hard prerequisite when the configured source folder is accessible

## Decisions

### Existing Baseline Reuse
**Decision:** Reuse existing settings, source-folder detection, recursive scanning, and selected-asset aggregation as Epic 5 inputs.
**Rationale:**
- Epic 4 explicitly established these as dependencies rather than new Epic 5 work.
- The current UI and saved settings already use `source_folder` and `sorting_approach`.
- Reusing the existing scanner avoids duplicate matching code and preserves current tests.
**Implementation:**
- `app/settings.py` remains the source of truth for settings.
- `sorting_approach = "first"` maps to move-to-first-selected-album behavior.
- `sorting_approach = "copy"` maps to copy-to-each-selected-album behavior.
- `app/scanner.py` remains the recursive filename scanner and should be extended only where needed.

### File Matching Strategy
**Decision:** Use recursive filename-only matching with case-insensitive comparison on Windows, while suppressing app-created copies from the candidate index.
**Rationale:**
- Recursive scanning lets users re-run sorts without remembering where files were previously moved.
- Filename-only matching aligns with Epic 4 and avoids unreliable placeholder metadata.
- App-created copies must not create future ambiguous matches.
**Implementation:**
- Build the local filename index recursively from the configured source folder.
- Treat moved files as canonical candidates wherever they currently live.
- Track app-created copy paths in sort state and exclude existing tracked copies from future matching.
- Treat persisted paths as advisory: missing tracked paths are ignored or cleaned up, not fatal.
- If multiple untracked local candidates match the same filename, mark the asset ambiguous rather than guessing.
**Alternatives Considered:**
- Excluding whole album output folders: rejected because it prevents recursive re-sort behavior after moves.
- Using file size/timestamps: rejected due to unreliability of iCloud placeholder files.
- Hash-based matching: rejected for MVP complexity.

### Multi-Album Behavior
**Decision:** Preserve existing `sorting_approach` settings values and clarify behavior.
**Rationale:**
- Avoids a breaking settings/UI migration.
- Matches the current frontend select values and backend validation.
- Keeps deterministic behavior without tracking checkbox click order.
**Implementation:**
- `first`: move the matched file to the first selected album folder only.
- `copy`: copy the matched file to every selected album folder and leave the source file in place.
- “First selected” means first in the current selected album list order sent by the UI, not checkbox click order.
- Copy mode should remain visibly discouraged because copying large libraries can require significant storage and may trigger downloads.

### Safe Album Folder Mapping
**Decision:** Derive Windows-safe album folder names from iCloud album names, but persist mappings by album ID.
**Rationale:**
- iCloud album names may contain characters invalid in Windows paths.
- iCloud may allow duplicate album names.
- Folder assignment must remain stable across runs even if album ordering changes.
**Implementation:**
- Album ID is identity.
- Album name is display text.
- Folder name/path is derived once and persisted in sort state or managed mapping state.
- Illegal Windows characters, reserved names, trailing spaces/dots, and overly long names are sanitized.
- Duplicate sanitized folder names receive deterministic suffixes such as ` (2)` while preserving album ID mapping.
- If an album is later renamed in iCloud, keep the existing folder mapping for MVP; managed folder rename can be future work.

### Destination Conflict Handling
**Decision:** Sorting is non-interactive. Destination conflicts and no-op cases are skipped and reported after the job.
**Rationale:**
- Target users may process thousands or hundreds of thousands of files.
- Per-file prompts would make the app unusable.
- Never overwriting automatically is safer than guessing.
**Implementation:**
- If source path equals destination path, skip as `already_sorted`.
- If destination file exists and is a tracked app-created copy, skip as `already_copied`.
- If destination file exists but is not tracked, skip as `skipped_destination_exists`.
- If source file is missing, skip as `skipped_source_missing`.
- If a match is ambiguous, skip as `skipped_ambiguous_match`.
- File system failures are recorded as `failed_filesystem_error` and the job continues when possible.
- Final summary includes counts and details for moved, copied, already sorted, skipped, failed, unmatched, and ambiguous assets.

### Persistence Approach
**Decision:** Use existing settings JSON for user settings and add JSON sort-state persistence for job/file state.
**Rationale:**
- Follows the repo direction toward simple JSON persistence.
- Avoids parallel settings schemas.
- Atomic writes prevent corruption.
**Implementation:**
- Settings continue to live in `%APPDATA%\icloud-sorter\settings.json` via `app/settings.py`.
- Sort state uses a separate state file in the same user data directory.
- State includes schema version, active/completed job metadata, selected albums, album folder mappings, processed assets, canonical/moved paths, app-created copy paths, statuses, errors, and timestamps.
- State writes are atomic using temp file plus replace.
- State entries are resilient to user deletion: missing files are treated as absent, not corrupt state.

### Sorting Engine Architecture
**Decision:** Add focused sorting modules for planning operations, safe file operations, job orchestration, and state persistence.
**Rationale:**
- Separates existing matching from filesystem mutations.
- Enables unit testing of dangerous path and conflict behavior independently.
- Keeps bridge methods thin.
**Components:**
- `app/scanner.py`: existing recursive filename scanning and filename-only matching; extended for tracked-copy suppression if needed
- `app/sorting/file_operations.py`: folder creation, safe move/copy, destination conflict checks, Windows-safe path handling
- `app/sorting/sort_job.py`: orchestrates matching handoff, operation planning, execution, progress, cancellation, and final summaries
- `app/state/sort_state.py` or equivalent: JSON read/write for sort job state and managed album/file mappings
- `app/settings.py`: existing settings persistence and source-folder configuration

### Progress Reporting and Cancellation
**Decision:** Preserve existing progress polling and add minimal cancellation.
**Rationale:**
- Existing UI already polls `get_sort_progress(job_id)`.
- Users with large libraries need an escape hatch.
- Pause controls are unnecessary because a later sort can safely continue by rescanning and skipping already-handled files.
**Implementation:**
- `start_sort(selected_album_ids)` returns immediately with a job ID.
- `get_sort_progress(job_id)` returns progress percentage, current operation, counts, and final summary data.
- Add `cancel_sort(job_id)` bridge method.
- Cancel means stop after the current file operation finishes.
- Cancel does not roll back already completed operations.
- Cancel persists completed/skipped state and marks the job `cancelled`.

### Source Folder Prerequisites
**Decision:** The hard prerequisite is an accessible configured source folder, not definitive proof that iCloud for Windows is installed.
**Rationale:**
- Installation detection varies by Store vs legacy iCloud for Windows installs.
- Offline sorting should be allowed when the configured local folder is accessible.
- Folder access is the actual requirement for local file operations.
**Implementation:**
- Auto-detect common iCloud Photos paths only when no source folder is configured.
- Preserve a configured path even if it later becomes stale; do not silently switch to a newly detected folder.
- Before starting file operations, verify the source folder exists, is a directory, is readable, and can contain destination album folders.
- If validation fails, perform no file operations and return clear guidance.
- iCloud for Windows install detection is advisory/future guidance only for MVP.
- Placeholder/offline reconciliation behavior is ignored for MVP and should be investigated later.

## Risks / Trade-offs

**[Risk] Filename collisions causing incorrect matches** -> Mitigation: Detect and report ambiguous untracked matches rather than guessing.

**[Risk] App-created copies pollute future recursive scans** -> Mitigation: Persist app-created copy paths and suppress existing tracked copies during matching.

**[Risk] Windows path/name edge cases break folder creation** -> Mitigation: Sanitize album folder names, persist album ID mappings, and test reserved names/duplicates.

**[Risk] Long-running sort jobs blocking UI** -> Mitigation: Background processing with non-blocking bridge calls; progress polling keeps UI responsive; cancellation stops future work.

**[Risk] JSON corruption from concurrent access or power loss** -> Mitigation: Atomic writes using temp files plus replace; validate JSON on load.

**[Risk] User deletes moved/copied files after sorting** -> Mitigation: Treat persisted paths as advisory; missing paths produce skipped/unmatched results, not state corruption.

**[Risk] Placeholder files may behave differently when moved offline** -> Mitigation: Ignore for MVP and record as future investigation; require only accessible filesystem entries.

## Open Questions

- How detailed should the final skipped-file report be in the initial UI versus persisted state/log output?
- What exact folder-name truncation length should be used to avoid Windows path length issues while preserving readability?
- How should Live Photo pairs (MOV+JPEG) or RAW+JPEG sets be handled after MVP filename-only matching?
- What retry policy should we use for transient iCloud/network failures during metadata fetch?
