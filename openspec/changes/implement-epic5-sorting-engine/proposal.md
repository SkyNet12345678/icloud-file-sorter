## Why

The current implementation has mocked sorting functionality. To deliver the core value of the iCloud Sorter app, we need to implement the actual sorting engine that organizes local files into album-named folders based on iCloud album metadata. This is the next critical step after authentication and album discovery.

## What Changes

- Implement real sorting engine that moves/copies files based on iCloud album membership
- Replace mocked sort job logic with actual file system operations
- Add JSON persistence for sort progress and state while reusing the existing settings service
- Implement multi-album behavior using the existing `first` / `copy` settings values
- Add safe album-folder mapping, destination conflict handling, and non-interactive skipped-file reporting
- Keep recursive local scanning while suppressing app-created copies from future matching
- Add cancellation support for long-running sort jobs without rollback or pause semantics
- Update the Python bridge to expose real sort progress, cancellation, and completion
- Maintain existing pywebview desktop shell and HTML/CSS/JS frontend

## Capabilities

### New Capabilities
- `sorting-engine`: Core sorting logic that matches local files to iCloud assets and organizes them into album folders
- `sort-state-persistence`: JSON-based persistence for sort progress, enabling resumable sorts
- `multi-album-handling`: Configuration and logic for handling assets that belong to multiple selected albums
- `sort-progress-reporting`: Real-time progress reporting during sort operations

### Existing Capabilities Reused
- Existing `app/settings.py` JSON settings persistence, including `source_folder` and `sorting_approach`
- Existing source-folder detection and validation baseline
- Existing recursive filename scanner in `app/scanner.py`
- Existing selected-album asset aggregation and album membership ordering

### Modified Capabilities
- None (no existing capability requirements are changing)

## Impact

- Backend: New modules in `app/sorting/` and sort-state persistence that build on existing scanner/settings services
- Bridge: Enhanced API methods for real sort progress and cancellation while preserving existing calls
- Frontend: Utilizes existing album selection, settings, and progress UI with real data
- Persistence: Introduction of JSON sort state plus reuse/extension of existing settings JSON
- Testing: New unit tests for sorting logic, safe file operations, state persistence, and bridge cancellation
