## Why

The current implementation has mocked sorting functionality. To deliver the core value of the iCloud Sorter app, we need to implement the actual sorting engine that organizes local files into album-named folders based on iCloud album metadata. This is the next critical step after authentication and album discovery.

## What Changes

- Implement real sorting engine that moves/copies files based on iCloud album membership
- Replace mocked sort job logic with actual file system operations
- Add JSON persistence for sort progress and state
- Implement multi-album behavior (move to first selected album or copy to each)
- Add error handling for file system operations during sorting
- Update the Python bridge to expose real sort progress and completion
- Maintain existing pywebview desktop shell and HTML/CSS/JS frontend

## Capabilities

### New Capabilities
- `sorting-engine`: Core sorting logic that matches local files to iCloud assets and organizes them into album folders
- `sort-state-persistence`: JSON-based persistence for sort progress, enabling resumable sorts
- `multi-album-handling`: Configuration and logic for handling assets that belong to multiple selected albums
- `sort-progress-reporting`: Real-time progress reporting during sort operations

### Modified Capabilities
- None (no existing capability requirements are changing)

## Impact

- Backend: New modules in `app/sorting/` and `app/state/`
- Bridge: Enhanced API methods for sort progress and control
- Frontend: Utilizes existing album selection and progress UI with real data
- Persistence: Introduction of JSON state and settings files
- Testing: New unit tests for sorting logic and state persistence