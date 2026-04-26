## ADDED Requirements

### Requirement: Sorting Engine Core Functionality
The system SHALL implement a sorting engine that organizes local files into album-named folders based on iCloud album metadata.

#### Scenario: Sort assets into album folders
- **WHEN** the user starts a sort job for selected albums
- **THEN** the system SHALL scan the local iCloud Photos folder for files matching assets in those albums
- **AND** the system SHALL create album-named subfolders within the iCloud Photos folder
- **AND** the system SHALL move or copy matched files into the appropriate album folders based on multi-album behavior setting

#### Scenario: Handle unmatched files
- **WHEN** the system encounters an iCloud asset with no matching local file
- **THEN** the system SHALL mark the asset as unmatched and continue processing
- **AND** the system SHALL report unmatched files in the final sort summary

#### Scenario: Handle ambiguous matches
- **WHEN** the system finds multiple local files matching the same iCloud asset filename
- **THEN** the system SHALL mark the asset as having an ambiguous match
- **AND** the system SHALL not move or copy any of the matching files
- **AND** the system SHALL report ambiguous matches in the final sort summary

### Requirement: JSON State Persistence
The system SHALL persist sort progress and state using JSON files to enable resumable sorts and maintain user preferences.

#### Scenario: Save sort state
- **WHEN** a sort job is in progress
- **THEN** the system SHALL periodically save the current state to a JSON file
- **AND** the state SHALL include processed files, matched files, and any errors encountered

#### Scenario: Resume interrupted sort
- **WHEN** a sort job is interrupted and later restarted
- **THEN** the system SHALL load the previous state from the JSON file
- **AND** the system SHALL resume processing from where it left off
- **AND** the system SHALL not reprocess already completed files

#### Scenario: Persist user settings
- **WHEN** the user modifies sort behavior settings
- **THEN** the system SHALL save the settings to a JSON file
- **AND** the settings SHALL be loaded on subsequent application starts

### Requirement: Multi-Album Behavior Handling
The system SHALL provide configurable behavior for assets that belong to multiple selected albums.

#### Scenario: Move to first selected album (default)
- **WHEN** the multi-album behavior is set to `move_first_selected_album` (default)
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL move/copy the file to the folder of the first selected album in the user's selection order

#### Scenario: Copy to each selected album (optional)
- **WHEN** the multi-album behavior is set to `copy_to_each_album`
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL copy the file to each selected album's folder
- **AND** the system SHALL preserve the original file in its location

#### Scenario: Configure multi-album behavior
- **WHEN** the user changes the multi-album behavior setting
- **THEN** the system SHALL persist the setting in JSON
- **AND** the system SHALL apply the new behavior to subsequent sort jobs

### Requirement: Sort Progress Reporting
The system SHALL provide real-time progress reporting during sort operations through the existing Python-JS bridge.

#### Scenario: Report sort progress
- **WHEN** a sort job is running
- **THEN** the system SHALL update progress information including:
  * Percentage of assets processed
  * Number of files matched
  * Number of files moved/copied
  * Number of files failed due to errors
  * Number of unmatched assets
  * Number of ambiguous matches
- **AND** the frontend SHALL be able to retrieve this information via `get_sort_progress(job_id)`

#### Scenario: Report sort completion
- **WHEN** a sort job finishes processing all assets
- **THEN** the system SHALL set progress to 100%
- **AND** the system SHALL provide a summary of the sort operation
- **AND** the summary SHALL include counts of processed, matched, moved/copied, failed, unmatched, and ambiguous files