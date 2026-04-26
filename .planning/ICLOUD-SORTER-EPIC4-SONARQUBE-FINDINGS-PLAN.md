# Epic 4 SonarQube Findings Cleanup Plan

## Summary

`sonar-issues.json` contains 14 SonarQube findings from Epic 4. The fixes are small, behavior-preserving cleanups concentrated in:

- `app/icloud/icloud_service.py`
- `app/ui/js/main.js`
- `app/ui/js/settings.js`

No true false positives were found. Several JavaScript findings are convention-only and not functionally required, but they should be fixed if the goal is a clean SonarQube report.

## Findings Assessment

### Real Issues To Fix

- `python:S2583` in `app/icloud/icloud_service.py`: remove the redundant `original_filename = original_filename or filename` assignment. Prior logic already guarantees `original_filename` is populated when execution reaches that line.
- `python:S1481` in `app/icloud/icloud_service.py`: remove the unused `extension` local variable from `_filename_from_download_url`.
- `python:S5713` in `app/icloud/icloud_service.py`: simplify both `_decode_base64_filename` exception tuples to `except ValueError:`. In Python 3.11, both `binascii.Error` and `UnicodeDecodeError` subclass `ValueError`, so listing them with `ValueError` is redundant.
- `python:S1192` in `app/icloud/icloud_service.py`: define one module-level constant for `"Failed to load album assets"` and use it at the three reported call sites.
- `javascript:S1128` in `app/ui/js/main.js`: remove the unused `showCopyWarning` import.
- `javascript:S7764` in `app/ui/js/settings.js`: replace `window.pywebview` and `window.setTimeout` with `globalThis.pywebview` and `globalThis.setTimeout`.
- `javascript:S7718` in `app/ui/js/settings.js`: rename `catch (exc)` to `catch (error_)` in the three reported handlers and update the related `console.error` calls.

### False Positives / Not Needing Fix

- No false positives were identified.
- `javascript:S7764` and `javascript:S7718` are portability/convention findings, not runtime bugs. They can be ignored if only functional correctness matters, but the changes are safe and cheap.
- `python:S1192` is maintainability-only, but fixing it avoids future message drift.
- `python:S5713` is valid on the supported Python version because `binascii.Error` and `UnicodeDecodeError` both inherit from `ValueError`.

## Implementation Plan

1. Update `app/icloud/icloud_service.py`.
   - Add a clear module-level constant such as `FAILED_TO_LOAD_ALBUM_ASSETS = "Failed to load album assets"`.
   - Replace the three duplicate string literals with that constant.
   - Remove the redundant `original_filename` reassignment.
   - Remove the unused `extension` assignment in `_filename_from_download_url`.
   - Replace both `_decode_base64_filename` exception tuples with `except ValueError:`.
   - Remove the now-unused `import binascii`.

2. Update `app/ui/js/main.js`.
   - Remove `showCopyWarning` from the settings import.
   - Do not remove the exported `showCopyWarning` function from `settings.js` unless broader cleanup is intentionally desired.

3. Update `app/ui/js/settings.js`.
   - Use `globalThis.pywebview?.api` and `globalThis.pywebview.api` in `getPywebviewApi`.
   - Use `globalThis.setTimeout(resolve, 50)`.
   - Rename each catch binding from `exc` to `error_`.
   - Update the corresponding `console.error` calls to log `error_`.

## Test Plan

- Run targeted Python tests for album asset behavior:

```powershell
python -m pytest tests/icloud/test_album_asset_loading.py tests/icloud/test_album_asset_metadata.py
```

- Run the broader Python suite if available:

```powershell
python -m pytest
```

- Run frontend tests from `frontend/`:

```powershell
npm test
```

- The current frontend suite is expected to pass. Treat any new frontend failure as a regression unless the failing test is independently confirmed to be unrelated to these cleanup changes.

## Acceptance Criteria

- The 14 SonarQube issues listed in `sonar-issues.json` are resolved or intentionally documented as non-functional convention findings.
- Existing Python behavior for album asset loading, filename extraction, and base64 filename fallback decoding is preserved.
- Existing UI behavior for settings loading, saving, and source folder detection is preserved.
- No bridge API shape changes are introduced.

## Assumptions

- The goal is to clear Epic 4 SonarQube findings without changing behavior.
- Python 3.11 remains the supported runtime for this repository.
- No new tests are required for these mechanical cleanups, but existing targeted tests should still be run for regression confidence.
