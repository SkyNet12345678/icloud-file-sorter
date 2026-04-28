## ADDED Requirements

### Requirement: Existing Settings Reuse
The system SHALL reuse the existing JSON-backed settings service for user settings.

#### Scenario: Preserve settings contract
- **WHEN** Epic 5 reads or writes user-configurable settings
- **THEN** the system SHALL use the existing `app/settings.py` service
- **AND** the system SHALL preserve existing `source_folder` and `sorting_approach` settings keys
- **AND** the system SHALL preserve existing `sorting_approach` values `first` and `copy`

#### Scenario: Do not create parallel settings model
- **WHEN** sort state persistence is implemented
- **THEN** the system SHALL NOT introduce a second settings schema for the same source-folder or sort-approach preferences
- **AND** sort state persistence SHALL be separate from user settings persistence

### Requirement: Sort State Persistence
The system SHALL persist sort job state in a JSON file to enable recovery, idempotent re-runs, and managed-copy suppression.

#### Scenario: Save sort state during processing
- **WHEN** a sort job is actively processing files
- **AND** a configurable interval has elapsed, a batch of files has been processed, or the job reaches a terminal state
- **THEN** the system SHALL write the current sort state to a JSON file
- **AND** the state SHALL include processed assets with statuses, current progress percentage, timestamps, selected albums, album folder mappings, canonical/moved paths, app-created copy paths, errors, and the configuration used for the job

#### Scenario: Resume or re-run from persisted state
- **WHEN** a sort job is interrupted or a later sort is started
- **AND** a valid sort state file exists
- **THEN** the system SHALL load relevant previous state
- **AND** the system SHALL use tracked app-created copy paths to suppress duplicate copy candidates during matching
- **AND** the system SHALL not reprocess operations already known to be complete when the current filesystem state confirms they remain complete

#### Scenario: Persist cancellation state
- **WHEN** a sort job is cancelled
- **THEN** the system SHALL persist completed, skipped, failed, and remaining operation state
- **AND** the system SHALL mark the job as `cancelled`
- **AND** a later sort SHALL be able to continue safely by rescanning and skipping already-handled operations

#### Scenario: Handle stale persisted paths
- **WHEN** persisted canonical paths or copy paths no longer exist on disk
- **THEN** the system SHALL treat those paths as stale advisory state
- **AND** missing paths SHALL NOT make the state file invalid
- **AND** the system SHALL ignore or clean up missing tracked copy paths without blocking sorting

#### Scenario: Handle corrupted state file
- **WHEN** the system attempts to load a sort state file
- **AND** the file is missing, malformed, or contains invalid data
- **THEN** the system SHALL log the error and treat it as no usable previous state existing
- **AND** the system SHALL start a new sort job if requested, rather than attempting to resume from invalid state
- **AND** the system SHALL continue normal operation without blocking the user

### Requirement: State File Management
The system SHALL manage the lifecycle and location of state files appropriately.

#### Scenario: Determine state file location
- **WHEN** the system needs to read or write sort state files
- **THEN** the system SHALL use the user's application data directory (`%APPDATA%\icloud-sorter\` on Windows)
- **AND** the system SHALL create the directory if it does not exist
- **AND** the system SHALL use separate files for settings and sort state to prevent conflicts

#### Scenario: Atomic state file writes
- **WHEN** the system writes any sort state file
- **THEN** the system SHALL write to a temporary file first
- **AND** the system SHALL replace the target file only after the temporary file has been successfully written
- **AND** this approach SHALL prevent corruption from crashes or power loss during writes

#### Scenario: Clean up temporary files
- **WHEN** the system creates temporary files during atomic writes
- **THEN** the system SHALL attempt to remove temporary files after successful replacement
- **AND** if removal fails, the system SHALL leave the file for later cleanup rather than blocking operations
