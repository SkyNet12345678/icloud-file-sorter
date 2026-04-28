## ADDED Requirements

### Requirement: Multi-Album Behavior Configuration
The system SHALL use the existing `sorting_approach` setting for handling assets that belong to multiple selected albums.

#### Scenario: Default multi-album behavior
- **WHEN** the system is first initialized or no user preference exists
- **THEN** the `sorting_approach` setting SHALL default to `first`
- **AND** `first` SHALL mean move the file to the first selected album folder only
- **AND** this default SHALL be documented in the user interface

#### Scenario: Change multi-album behavior
- **WHEN** the user selects a different sorting approach option
- **THEN** the system SHALL persist the new `sorting_approach` setting using the existing settings service
- **AND** the new behavior SHALL apply to subsequent sort jobs
- **AND** the change SHALL survive application restarts

#### Scenario: Validate multi-album behavior values
- **WHEN** the system reads the `sorting_approach` setting
- **THEN** the value SHALL be one of: `first` or `copy`
- **AND** any other value SHALL be treated as invalid and defaulted or rejected according to existing settings validation behavior

### Requirement: First Selected Album Behavior
The system SHALL implement the default behavior for multi-album assets as moving to the first selected album folder.

#### Scenario: Process asset in multiple albums with first behavior
- **WHEN** `sorting_approach` is set to `first`
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL determine the first album in the selected album list order sent by the UI
- **AND** the system SHALL move the file to that album's folder only
- **AND** the system SHALL NOT process the asset for any other selected albums in that sort job

#### Scenario: Respect selected album list order
- **WHEN** the user starts a sort with multiple selected albums
- **THEN** the system SHALL use the selected album order provided by the existing frontend payload
- **AND** the system SHALL NOT require tracking checkbox click order for MVP
- **AND** the behavior SHALL be deterministic for a given selected album list

#### Scenario: File already in first selected album folder
- **WHEN** `sorting_approach` is set to `first`
- **AND** the matched file is already located at the target path for the first selected album
- **THEN** the system SHALL skip the operation as `already_sorted`
- **AND** the system SHALL report it in the final summary/details without prompting the user

### Requirement: Copy To Each Album Behavior
The system SHALL implement the optional behavior for multi-album assets as copying to each selected album folder.

#### Scenario: Process asset in multiple albums with copy behavior
- **WHEN** `sorting_approach` is set to `copy`
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL copy the file to each selected album's folder
- **AND** the system SHALL preserve the source file in its current location
- **AND** the system SHALL track app-created copy paths in sort state

#### Scenario: Handle existing copy destinations
- **WHEN** the system attempts to copy a file to multiple albums
- **AND** one or more destination files already exist
- **THEN** the system SHALL skip existing tracked app-created copies as `already_copied`
- **AND** the system SHALL skip untracked destination conflicts as `skipped_destination_exists`
- **AND** the system SHALL continue attempting copies to remaining albums
- **AND** the system SHALL record which copies succeeded and which were skipped or failed

#### Scenario: Warn about copy behavior
- **WHEN** the user selects copy behavior
- **THEN** the user interface SHOULD warn that copying large libraries may require significant storage and may trigger downloads
