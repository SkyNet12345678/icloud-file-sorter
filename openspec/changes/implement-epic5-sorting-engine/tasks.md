## 1. Project Setup and Infrastructure

- [ ] 1.1 Create app/sorting/ and app/state/ directories
- [ ] 1.2 Set up initial module structure with __init__.py files
- [ ] 1.3 Create basic logger configuration if not already present
- [ ] 1.4 Verify Python 3.11 compatibility for new modules

## 2. Settings Persistence Implementation

- [ ] 2.1 Define settings data model with schema_version, icloud_photos_path, last_used_apple_id, sort_mode, multi_album_mode
- [ ] 2.2 Implement atomic JSON write functionality for settings
- [ ] 2.3 Create settings persistence module with load/save functions
- [ ] 2.4 Add default settings initialization and fallback handling
- [ ] 2.5 Implement settings validation and sanitization
- [ ] 2.6 Create unit tests for settings persistence

## 3. Sort State Persistence Implementation

- [ ] 3.1 Define sort state data model with schema_version, last_sync_at, albums array with file tracking
- [ ] 3.2 Implement atomic JSON write functionality for sort state
- [ ] 3.3 Create sort state persistence module with load/save functions
- [ ] 3.4 Add functionality to track individual file processing status
- [ ] 3.5 Implement resume capability from existing state file
- [ ] 3.6 Add state cleanup and version migration handling
- [ ] 3.7 Create unit tests for sort state persistence

## 4. Sorting Engine Core - Matching Logic

- [ ] 4.1 Create matcher module to process iCloud asset metadata
- [ ] 4.2 Implement filename-based matching algorithm (case-insensitive)
- [ ] 4.3 Build local file index from iCloud Photos folder
- [ ] 4.4 Handle ambiguous matches (multiple local files with same name)
- [ ] 4.5 Detect and report unmatched assets (no local file found)
- [ ] 4.6 Create unit tests for matching logic

## 5. Sorting Engine Core - File Operations

- [ ] 5.1 Create file operations module for folder creation and file moving/copying
- [ ] 5.2 Implement album folder creation within iCloud Photos directory
- [ ] 5.3 Add safe file move functionality with error handling
- [ ] 5.4 Add safe file copy functionality with error handling
- [ ] 5.5 Implement behavior selection based on multi-album setting
- [ ] 5.6 Add comprehensive error handling for file operations (permissions, locked files, etc.)
- [ ] 5.7 Create unit tests for file operations

## 6. Sort Job Orchestration

- [ ] 6.1 Create sort job manager class to orchestrate the sorting process
- [ ] 6.2 Implement background processing for sort jobs (non-blocking)
- [ ] 6.3 Add progress tracking (percentage, counts, current operation)
- [ ] 6.4 Implement sort job lifecycle (start, pause, resume, cancel)
- [ ] 6.5 Add periodic state saving during processing
- [ ] 6.6 Handle job completion and final reporting
- [ ] 6.7 Create unit tests for sort job orchestration

## 7. Python Bridge Updates

- [ ] 7.1 Update start_sort() to initiate real sort job and return job ID
- [ ] 7.2 Update get_sort_progress() to return real progress data
- [ ] 7.3 Ensure bridge methods maintain compatibility with existing frontend
- [ ] 7.4 Add error handling in bridge methods for sort job failures
- [ ] 7.5 Create unit tests for bridge method interactions

## 8. Multi-Album Behavior Implementation

- [ ] 8.1 Implement move_first_selected_album behavior logic
- [ ] 8.2 Implement copy_to_each_album behavior logic
- [ ] 8.3 Add settings integration for multi-album behavior selection
- [ ] 8.4 Preserve user selection order for deterministic behavior
- [ ] 8.5 Handle edge cases (empty selection, single album selection)
- [ ] 8.6 Create unit tests for multi-album behavior

## 9. Error Handling and Robustness

- [ ] 9.1 Implement comprehensive error handling for file system operations
- [ ] 9.2 Add retry logic for transient failures where appropriate
- [ ] 9.3 Ensure sort jobs continue despite individual file errors
- [ ] 9.4 Collect and report errors in final sort summary
- [ ] 9.5 Handle critical errors that should abort the entire job
- [ ] 9.6 Create unit tests for error handling scenarios

## 10. Startup Prerequisite Checks

- [ ] 10.1 Implement iCloud for Windows installation detection
- [ ] 10.2 Add iCloud Photos folder existence validation
- [ ] 10.3 Provide user guidance when prerequisites are missing
- [ ] 10.4 Allow user to confirm or override iCloud Photos folder path
- [ ] 10.5 Store confirmed folder path in settings
- [ ] 10.6 Validate folder accessibility before starting sort jobs

## 11. Integration and Testing

- [ ] 11.1 Wire up all new modules in the application startup sequence
- [ ] 11.2 Ensure proper dependency injection and module imports
- [ ] 11.3 Run end-to-end testing of the sort workflow
- [ ] 11.4 Verify bridge communication between Python and frontend
- [ ] 11.5 Test JSON persistence across application restarts
- [ ] 11.6 Validate multi-album behavior with test datasets

## 12. Documentation and Cleanup

- [ ] 12.1 Update README with new functionality description
- [ ] 12.2 Add inline comments and docstrings to new code
- [ ] 12.3 Ensure code follows existing project style and conventions
- [ ] 12.4 Run any existing linters or formatters on new code
- [ ] 12.5 Review and remove any temporary debugging code