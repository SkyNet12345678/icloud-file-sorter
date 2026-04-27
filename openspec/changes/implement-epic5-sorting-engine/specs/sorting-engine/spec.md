## ADDED Requirements

### Requirement: Sorting Engine Core Functionality
The system SHALL implement a sorting engine that organizes local files into album-named folders based on iCloud album metadata.

#### Scenario: Sort assets into album folders
- **WHEN** the user starts a sort job for selected albums
- **THEN** the system SHALL scan the configured local iCloud Photos source folder recursively for files matching assets in those albums
- **AND** the system SHALL create Windows-safe album-named subfolders within the configured source folder
- **AND** the system SHALL move or copy matched files into the appropriate album folders based on the existing `sorting_approach` setting
- **AND** the system SHALL keep local filesystem scanning, matching, and sorting inside the active sort job lifecycle

#### Scenario: Re-sort after previous moves
- **WHEN** a previous sort moved a matched file into an album folder
- **AND** a later sort recursively scans the configured source folder
- **THEN** the moved file SHALL remain eligible as a canonical match candidate
- **AND** the user SHALL NOT need to move files back to the source folder root before sorting another album

#### Scenario: Ignore app-created copies during future matching
- **WHEN** a previous sort created copy-mode duplicate files
- **AND** those copy paths are tracked in sort state
- **THEN** the system SHALL ignore existing tracked copy paths when building future match candidates
- **AND** tracked copies SHALL NOT cause a future filename match to become ambiguous

### Requirement: Safe Album Folder Mapping
The system SHALL map iCloud albums to stable Windows-safe destination folders.

#### Scenario: Sanitize album folder name
- **WHEN** an iCloud album name contains characters or forms that are invalid or unsafe on Windows
- **THEN** the system SHALL derive a Windows-safe folder name
- **AND** the folder name SHALL avoid illegal characters, reserved names, trailing spaces/dots, and unsafe path lengths

#### Scenario: Handle duplicate album names
- **WHEN** multiple selected iCloud albums produce the same sanitized folder name
- **THEN** the system SHALL assign deterministic distinct folder names
- **AND** the system SHALL persist the mapping by iCloud album ID
- **AND** later runs SHALL preserve the same album ID to folder mapping regardless of album ordering

#### Scenario: Album renamed after mapping exists
- **WHEN** an album has an existing persisted folder mapping
- **AND** the iCloud album display name changes
- **THEN** the system SHALL continue using the existing folder mapping for MVP
- **AND** the system SHALL NOT rename existing managed folders automatically

### Requirement: Non-Interactive Destination Conflict Handling
The system SHALL handle destination conflicts and no-op operations without prompting during a bulk sort.

#### Scenario: File already in target folder
- **WHEN** the matched source path equals the destination path for the selected behavior
- **THEN** the system SHALL skip the operation as `already_sorted`
- **AND** the system SHALL continue processing remaining files

#### Scenario: Tracked copy already exists
- **WHEN** copy mode would create a file at a destination path
- **AND** that destination path already exists as a tracked app-created copy
- **THEN** the system SHALL skip the operation as `already_copied`
- **AND** the system SHALL continue processing remaining files

#### Scenario: Untracked destination file exists
- **WHEN** a destination file already exists
- **AND** the destination file is not a tracked app-created copy
- **THEN** the system SHALL NOT overwrite the destination file
- **AND** the system SHALL skip the operation as `skipped_destination_exists`
- **AND** the system SHALL report the skipped operation in the final summary/details

#### Scenario: Source file missing during operation
- **WHEN** a planned operation source file no longer exists
- **THEN** the system SHALL skip the operation as `skipped_source_missing`
- **AND** the system SHALL continue processing remaining files

### Requirement: Match Outcome Handling
The system SHALL report unresolved or unsafe match outcomes and continue processing when possible.

#### Scenario: Handle unmatched files
- **WHEN** the system encounters an iCloud asset with no matching local file
- **THEN** the system SHALL mark the asset as unmatched or skipped due to missing local source
- **AND** the system SHALL continue processing
- **AND** the system SHALL report unmatched files in the final sort summary/details

#### Scenario: Handle ambiguous matches
- **WHEN** the system finds multiple untracked local files matching the same iCloud asset filename
- **THEN** the system SHALL mark the asset as having an ambiguous match
- **AND** the system SHALL NOT move or copy any of the matching files
- **AND** the system SHALL report ambiguous matches in the final sort summary/details

### Requirement: Source Folder Validation
The system SHALL validate the configured source folder before performing file operations.

#### Scenario: Validate source folder before sort
- **WHEN** the user starts a sort job
- **THEN** the system SHALL verify the configured source folder exists, is a directory, is readable, and can contain destination album folders
- **AND** if validation fails, the system SHALL perform no file operations
- **AND** the system SHALL return clear user-facing guidance

#### Scenario: Preserve stale configured path
- **WHEN** a source folder path is already configured
- **AND** that path no longer exists
- **THEN** the system SHALL preserve the configured value
- **AND** the system SHALL NOT silently replace it with another auto-detected folder
- **AND** sort-start validation SHALL report that the configured folder was not found

#### Scenario: iCloud installation detection is advisory
- **WHEN** the configured source folder is accessible and writable
- **THEN** the system SHALL allow sorting even if iCloud for Windows installation/running state is not conclusively detected
- **AND** iCloud for Windows installation detection SHALL NOT be a hard blocker for MVP sorting

### Requirement: Sort Cancellation
The system SHALL allow the user to cancel an active sort job.

#### Scenario: Cancel active sort
- **WHEN** the user requests cancellation during an active sort job
- **THEN** the system SHALL stop processing after the current file operation completes
- **AND** the system SHALL NOT roll back already completed file operations
- **AND** the system SHALL persist completed and skipped operation state
- **AND** the system SHALL mark the job as `cancelled`
- **AND** the final summary SHALL include counts for completed, skipped, failed, and remaining files

### Requirement: Sort Progress Reporting
The system SHALL provide real-time progress reporting during sort operations through the existing Python-JS bridge.

#### Scenario: Report sort progress
- **WHEN** a sort job is running
- **THEN** the system SHALL update progress information including percentage processed, matched files, moved/copied files, already sorted/copied files, skipped files, failed files, unmatched assets, and ambiguous matches
- **AND** the frontend SHALL be able to retrieve this information via `get_sort_progress(job_id)`

#### Scenario: Report sort completion
- **WHEN** a sort job finishes processing all assets
- **THEN** the system SHALL set progress to 100%
- **AND** the system SHALL provide a summary of the sort operation
- **AND** the summary SHALL include counts and details for processed, moved, copied, already sorted, skipped, failed, unmatched, and ambiguous files
