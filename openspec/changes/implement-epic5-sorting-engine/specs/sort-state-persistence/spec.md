## ADDED Requirements

### Requirement: Settings Persistence
The system SHALL persist user settings in a JSON file to maintain preferences across application sessions.

#### Scenario: Save settings to JSON
- **WHEN** the user modifies application settings (such as iCloud Photos path or sort behavior)
- **THEN** the system SHALL write the settings to a JSON file in the user data directory
- **AND** the settings file SHALL use atomic writes to prevent corruption
- **AND** the settings SHALL be loaded automatically on application startup

#### Scenario: Load default settings
- **WHEN** no settings file exists or the file is corrupted
- **THEN** the system SHALL initialize with default settings values
- **AND** the system SHALL create a new settings file with the default values
- **AND** the system SHALL continue operation without blocking the user

### Requirement: Sort State Persistence
The system SHALL persist sort job state in a JSON file to enable recovery from interruptions.

#### Scenario: Save sort state during processing
- **WHEN** a sort job is actively processing files
- **AND** a configurable interval has elapsed or a batch of files has been processed
- **THEN** the system SHALL write the current sort state to a JSON file
- **AND** the state SHALL include:
  * List of processed assets with their status (pending, matched, moved, copied, failed, unmatched, ambiguous)
  * Current progress percentage
  * Timestamps for when processing started and last updated
  * Configuration used for this sort job (selected albums, multi-album behavior)

#### Scenario: Resume sort from persisted state
- **WHEN** a sort job is interrupted (application closed, system reboot, etc.)
- **AND** a valid sort state file exists from a previous session
- **THEN** the system SHALL load the sort state from the JSON file upon restart
- **AND** the system SHALL resume processing from the point of interruption
- **AND** the system SHALL not reprocess assets already marked as completed in the state
- **AND** the system SHALL update the progress indicator to reflect the loaded state

#### Scenario: Handle corrupted state file
- **WHEN** the system attempts to load a sort state file
- **AND** the file is missing, malformed, or contains invalid data
- **THEN** the system SHALL log the error and treat it as no previous state existing
- **AND** the system SHALL start a new sort job if requested, rather than attempting to resume
- **AND** the system SHALL continue normal operation without blocking the user

### Requirement: State File Management
The system SHALL manage the lifecycle and location of state files appropriately.

#### Scenario: Determine state file location
- **WHEN** the system needs to read or write state files
- **THEN** the system SHALL use the user's application data directory (%APPDATA%\icloud-sorter\ on Windows)
- **AND** the system SHALL create the directory if it does not exist
- **AND** the system SHALL use separate files for settings and sort state to prevent conflicts

#### Scenario: Atomic state file writes
- **WHEN** the system writes any state file (settings or sort state)
- **THEN** the system SHALL write to a temporary file first
- **AND** the system SHALL rename the temporary file to the target name only after successful write
- **AND** this approach SHALL prevent corruption from crashes or power loss during writes

#### Scenario: Clean up temporary files
- **WHEN** the system creates temporary files during atomic writes
- **THEN** the system SHALL attempt to remove temporary files after successful rename
- **AND** if removal fails, the system SHALL leave the file for later cleanup rather than blocking operations