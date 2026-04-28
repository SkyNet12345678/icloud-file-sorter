## 1. Baseline Alignment

- [x] 1.1 Confirm Epic 5 reuses existing `app/settings.py` instead of creating a parallel settings model
- [x] 1.2 Confirm `source_folder` and `sorting_approach` remain the persisted settings keys
- [x] 1.3 Confirm `sorting_approach` values remain `first` and `copy`
- [x] 1.4 Confirm existing selected-album asset aggregation is the sorting-engine input
- [x] 1.5 Confirm existing recursive filename scanner is reused as the matching baseline

## 2. Sort State Persistence

- [x] 2.1 Define sort state schema with `schema_version`, job metadata, selected albums, album folder mappings, processed assets, statuses, errors, and timestamps
- [x] 2.2 Add canonical/moved path and app-created copy path tracking to state records
- [x] 2.3 Implement atomic JSON write functionality for sort state
- [x] 2.4 Implement sort state load/save helpers using the existing app data directory
- [x] 2.5 Treat missing/stale persisted paths as advisory state, not corruption
- [x] 2.6 Add cleanup/ignore behavior for missing tracked copy paths
- [x] 2.7 Create unit tests for sort state persistence and stale path handling

## 3. Album Folder Mapping

- [x] 3.1 Implement Windows-safe folder-name sanitization for iCloud album names
- [x] 3.2 Handle reserved Windows names, illegal characters, trailing spaces/dots, and overly long names
- [x] 3.3 Persist stable album ID to folder path mappings
- [x] 3.4 Add deterministic suffix handling for duplicate sanitized album names
- [x] 3.5 Keep existing folder mappings stable when iCloud album names/order change
- [x] 3.6 Create unit tests for folder-name sanitization, duplicate names, and mapping stability

## 4. Matching Extension for Recursive Re-Sort

- [x] 4.1 Extend matching/indexing to suppress existing app-created copy paths from candidate matches
- [x] 4.2 Preserve moved files as valid recursive match candidates wherever they currently live
- [x] 4.3 Preserve ambiguous handling for multiple untracked same-filename candidates
- [x] 4.4 Preserve unmatched handling when no local candidate exists
- [x] 4.5 Add tests proving app-created copies do not create future ambiguity
- [x] 4.6 Add tests proving moved files in album folders remain matchable on later sorts

## 5. Safe File Operations

- [x] 5.1 Create file operations module for album folder creation and file moving/copying
- [x] 5.2 Validate destination folders can be created/written before processing operations
- [x] 5.3 Implement safe file move functionality with no automatic overwrite
- [x] 5.4 Implement safe file copy functionality with no automatic overwrite
- [x] 5.5 Implement `already_sorted` when source path equals destination path
- [x] 5.6 Implement `already_copied` when destination exists as a tracked app-created copy
- [x] 5.7 Implement `skipped_destination_exists` when destination exists but is not tracked
- [x] 5.8 Implement `skipped_source_missing` when a previously matched source is gone
- [x] 5.9 Implement filesystem error capture while continuing remaining files where possible
- [x] 5.10 Create unit tests for move/copy/no-op/conflict/error scenarios

## 6. Multi-Album Behavior

- [x] 6.1 Implement `first` behavior as move to the first selected album in selected album list order
- [x] 6.2 Implement `copy` behavior as copy to every selected album folder while preserving source file
- [x] 6.3 Ensure user selection/list order is preserved from the existing UI payload
- [x] 6.4 Handle empty selection and single-album selection edge cases
- [x] 6.5 Ensure copy-mode operations track created copy paths in state
- [x] 6.6 Create unit tests for `first` and `copy` behavior

## 7. Sort Job Orchestration

- [x] 7.1 Create sort job manager/orchestrator for matching handoff, operation planning, execution, progress, and summaries
- [x] 7.2 Replace downstream mocked progress with actual planned file operation counts
- [x] 7.3 Implement background/non-blocking processing for sort jobs
- [x] 7.4 Implement lifecycle states: start, matching/planning, running, cancelling, cancelled, complete, error
- [x] 7.5 Implement cancellation as stop-after-current-operation with no rollback
- [x] 7.6 Persist state periodically during processing and when cancellation/completion occurs
- [x] 7.7 Generate final summary counts and skipped/error details
- [x] 7.8 Create unit tests for orchestration, cancellation, completion, and summary generation

## 8. Python Bridge and Frontend Wiring

- [x] 8.1 Update `start_sort(selected_album_ids)` to start the real sort job and return a job ID
- [x] 8.2 Update `get_sort_progress(job_id)` to return real progress, counts, skipped/error summaries, and terminal statuses
- [x] 8.3 Add `cancel_sort(job_id)` bridge method
- [x] 8.4 Wire the existing frontend Cancel button to `cancel_sort(job_id)`
- [x] 8.5 Preserve bridge compatibility for existing album selection and progress polling
- [x] 8.6 Ensure settings UI continues using existing `source_folder` and `sorting_approach` values
- [x] 8.7 Create/update tests for bridge interactions and frontend cancel behavior where practical

## 9. Source Folder Validation

- [x] 9.1 Keep auto-detection limited to cases where no source folder is configured
- [x] 9.2 Preserve stale configured paths instead of silently replacing them with a newly detected path
- [x] 9.3 Validate source folder existence, directory status, readability, and destination write capability before file operations
- [x] 9.4 Return clear guidance when source-folder validation fails
- [x] 9.5 Treat iCloud for Windows installation detection as advisory/future guidance, not a hard blocker
- [x] 9.6 Keep placeholder/offline file behavior out of MVP implementation scope
- [x] 9.7 Create/update tests for stale path and sort-start validation behavior

## 10. Integration and Testing

- [x] 10.1 Wire new sorting modules into the existing `AlbumsService` / `ICloudService` sort path
- [x] 10.2 Verify album browsing remains lightweight and does not trigger local scanning or asset-level fetches
- [x] 10.3 Verify sorting scans/matches only after sort start
- [x] 10.4 Validate recursive re-sort behavior with moved files and tracked copies
- [x] 10.5 Validate large-job cancellation behavior with partial state persisted
- [x] 10.6 Validate JSON persistence across application restarts
- [x] 10.7 Run Python test suite and update existing mock-progress expectations

## 11. Documentation and Cleanup

- [x] 11.1 Update README or user-facing docs for real sorting behavior
- [x] 11.2 Document that copy mode can require significant storage and may trigger downloads
- [x] 11.3 Document cancellation semantics: cancel is not undo
- [x] 11.4 Document placeholder/offline reconciliation as future investigation, not MVP behavior
- [x] 11.5 Ensure code follows existing project style and conventions
- [x] 11.6 Review and remove temporary/debug sorting code

## 12. PR Quality Gate Cleanup

- [x] 12.1 Refactor `SortJobManager._execute_job` into smaller lifecycle phases to reduce cognitive complexity while preserving current sort behavior
- [x] 12.2 Deduplicate the repeated `Sorting service unavailable` response text in `AlbumsService`
- [x] 12.3 Deduplicate the repeated `Sorting service unavailable` response text in the pywebview `API` bridge
- [ ] 12.4 Re-fetch PR SonarQube issues and confirm the quality gate findings are resolved
