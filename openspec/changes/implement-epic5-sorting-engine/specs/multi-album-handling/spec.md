## ADDED Requirements

### Requirement: Multi-Album Behavior Configuration
The system SHALL provide a user-configurable setting for handling assets that belong to multiple selected albums.

#### Scenario: Default multi-album behavior
- **WHEN** the system is first initialized or no user preference exists
- **THEN** the multi-album behavior SHALL default to `move_first_selected_album`
- **AND** this default SHALL be documented in the user interface

#### Scenario: Change multi-album behavior
- **WHEN** the user selects a different multi-album behavior option
- **THEN** the system SHALL persist the new setting immediately
- **AND** the new behavior SHALL apply to all subsequent sort jobs
- **AND** the change SHALL survive application restarts

#### Scenario: Validate multi-album behavior values
- **WHEN** the system reads the multi-album behavior setting
- **THEN** the value SHALL be one of: `move_first_selected_album` or `copy_to_each_album`
- **AND** any other value SHALL be treated as invalid and defaulted to `move_first_selected_album`

### Requirement: Move First Selected Album Behavior
The system SHALL implement the default behavior for multi-album assets: move/copy to the first selected album's folder.

#### Scenario: Process asset in multiple albums (move first)
- **WHEN** the multi-album behavior is set to `move_first_selected_album`
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL determine the first album in the user's selection order
- **AND** the system SHALL move or copy the file to that album's folder only
- **AND** the system SHALL NOT process the asset for any other selected albums

#### Scenario: Respect selection order
- **WHEN** the user selects albums in a specific order
- **THEN** the system SHALL use that exact order to determine the "first" album
- **AND** changing the selection order SHALL change which folder receives the asset
- **AND** the system SHALL preserve the user's selection order from the UI

### Requirement: Copy To Each Album Behavior
The system SHALL implement the optional behavior for multi-album assets: copy to each selected album's folder.

#### Scenario: Process asset in multiple albums (copy each)
- **WHEN** the multi-album behavior is set to `copy_to_each_album`
- **AND** an asset belongs to multiple selected albums
- **THEN** the system SHALL copy the file to each selected album's folder
- **AND** the system SHALL preserve the original file in its location
- **AND** the system SHALL NOT move the original file (only copy operations)

#### Scenario: Handle copy failures
- **WHEN** the system attempts to copy a file to multiple albums
- **AND** one or more copy operations fail
- **THEN** the system SHALL continue attempting copies to remaining albums
- **AND** the system SHALL record which copies succeeded and which failed
- **AND** the system SHALL consider the asset partially processed if at least one copy succeeded