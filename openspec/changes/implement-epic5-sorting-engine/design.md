## Context

The iCloud Sorter application currently has a functional desktop shell with pywebview, HTML/CSS/JS frontend, and basic authentication flow via pyicloud. Album discovery is mocked, and sorting functionality is completely mocked. The application needs to progress from mock implementations to real functionality that delivers the core value proposition: organizing locally synced iCloud photos into album-named folders.

Based on the PROJECT-OVERVIEW.md and ICLOUD-SORTER-PLAN.md, we have established architectural constraints:
- Keep the existing pywebview desktop shell
- Maintain current HTML/CSS/vanilla JS frontend shape
- Use JSON persistence instead of SQLite
- Perform expensive operations (iCloud metadata fetch, local scanning, matching) only during active sort jobs
- Preserve the existing Python-to-JS bridge contract

## Goals / Non-Goals

**Goals:**
- Implement real sorting engine that moves/copies files based on iCloud album membership
- Replace mocked sort job logic with actual file system operations
- Add JSON persistence for sort progress and state, enabling resumable sorts
- Implement multi-album behavior configuration (move to first selected album or copy to each)
- Add robust error handling for file system operations during sorting
- Update the Python bridge to expose real sort progress and completion while maintaining compatibility
- Ensure startup prerequisite checks for iCloud for Windows and Photos folder existence

**Non-Goals:**
- Rewriting the frontend to React or introducing a web server architecture
- Adding SQLite or other relational databases for persistence
- Implementing complex duplicate detection beyond filename matching for MVP
- Supporting two-way sync back to iCloud
- Implementing advanced metadata-based matching (EXIF, file hashes) for MVP
- Creating a separate target directory for sorted files (sorting happens in-place within iCloud Photos folder)

## Decisions

### File Matching Strategy
**Decision:** Use filename-only matching with case-insensitive comparison on Windows
**Rationale:** 
- Aligns with PROJECT-OVERVIEW.md guidance to avoid unreliable metadata from iCloud placeholder files
- Provides deterministic results without requiring complex fallback logic
- Matches the MVP approach defined in Epic 4 planning
**Alternatives Considered:**
- Using file size/timestamps: Rejected due to unreliability of iCloud placeholder files
- Hash-based matching: Rejected for MVP complexity; could be added later if needed
- Metadata-based matching (dates, etc.): Rejected per Epic 4 constraints for MVP

### Multi-Album Behavior
**Decision:** Implement both `move_first_selected_album` (default) and `copy_to_each_album` (optional) behaviors
**Rationale:**
- Directly implements the MVP behavior defined in PROJECT-OVERVIEW.md lines 16-19
- Provides user choice through settings while maintaining sensible default
- Preserves album order for deterministic default behavior
**Alternatives Considered:**
- Only move behavior: Rejected as it doesn't fulfill the optional setting requirement
- Only copy behavior: Rejected as it doesn't match the stated MVP default
- Ask user per-conflict: Rejected for MVP complexity; can be considered later

### Persistence Approach
**Decision:** Use JSON files for both settings and state persistence in %APPDATA%\icloud-sorter\
**Rationale:**
- Follows PROJECT-OVERVIEW.md and JSON State Strategy in AGENTS.md
- Human-readable and editable for debugging
- Atomic writes prevent corruption
- Simple to implement and test
**Alternatives Considered:**
- SQLite: Rejected per explicit architectural constraint
- In-memory only: Rejected as it wouldn't support resumable sorts or settings persistence
- Windows Registry: Rejected for complexity and non-portability concerns

### Sorting Engine Architecture
**Decision:** Modular design with separate concerns for matching, file operations, and progress tracking
**Rationale:**
- Separates matching logic (filename-based) from file system operations (move/copy)
- Enables unit testing of matching logic independently
- Allows progress tracking to be centralized
- Follows existing codebase patterns in app/api/ and app/icloud/
**Components:**
- `app/sorting/matcher.py`: Handles iCloud asset metadata processing and local file matching
- `app/sorting/file_operations.py`: Manages folder creation, file moving/copying, error handling
- `app/sorting/sort_job.py`: Orchestrates the sort process, tracks progress, manages lifecycle
- `app/state/persistence.py`: Handles JSON read/write for settings and state
- `app/state/models.py`: Defines data structures for settings and state

### Progress Reporting
**Decision:** Maintain existing bridge method shapes while implementing real progress tracking
**Rationale:**
- Preserves frontend compatibility without requiring UI changes
- Allows incremental implementation where frontend can start receiving real data immediately
- Follows the bridge contract preservation guideline in PROJECT-OVERVIEW.md
**Implementation:**
- `start_sort()` returns immediately with job ID, sorting happens in background
- `get_sort_progress()` returns real progress percentage, current operation, and counts
- Progress includes: files processed, matched, moved/copied, failed, unmatched
- Supports cancellation through existing UI mechanisms

### Error Handling
**Decision:** Continue sorting on individual file errors, collect and report failures at completion
**Rationale:**
- Prevents entire sort job from failing due to single problematic file
- Provides comprehensive failure reporting for user action
- Matches robustness goals in Epic 7 planning
**Implementation:**
- Individual file errors (permissions, locked files, etc.) are caught and recorded
- Sort job continues with remaining files
- Final report includes lists of successfully processed vs failed files
- Critical errors (cannot access source folder) still abort the job immediately

## Risks / Trade-offs

**[Risk] Filename collisions causing incorrect matches** → Mitigation: Detect and report ambiguous matches rather than guessing; ambiguous files remain unplaced with clear error

**[Risk] Long-running sort jobs blocking UI** → Mitigation: Background processing with non-blocking bridge calls; progress polling keeps UI responsive

**[Risk] JSON corruption from concurrent access or power loss** → Mitigation: Atomic writes using temp files + rename; validate JSON on load

**[Risk] Insufficient permissions for file operations** → Mitigation: Check folder accessibility early; provide clear error messages pointing to solution

**[Risk] Memory usage with large photo libraries** → Mitigation: Stream iCloud asset metadata; don't load all assets into memory at once; process in batches

## Open Questions

- What should be the default location for JSON state files on Windows (%APPDATA%\icloud-sorter\ vs local app data)?
- Should we implement a "dry run" mode that shows what would be done without actually moving files?
- How should we handle Live Photo pairs (MOV+JPEG) or RAW+JPEG sets in the initial MVP?
- What retry policy should we use for transient iCloud/network failures during metadata fetch?