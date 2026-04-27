# Review Follow-ups

This file captures functional review findings from the Epic 4/Epic 5 sort and matching path.

## 1. Preserve Invalid Configured Source Folder Errors

Status: addressed in Epic 5 source-folder validation work.

Location: `app/settings.py`

Problem:

- When a user has already saved a source folder and that folder later disappears, the settings service currently falls through to auto-detection.
- If auto-detection finds another iCloud Photos folder, it can overwrite or return that detected folder instead of preserving the user's configured value as invalid.
- This can make `start_sort()` scan a folder the user did not configure.
- It also makes the explicit validation path for `"Configured source folder was not found"` unreachable through the real settings service.

Expected behavior:

- Auto-detection should only populate the source folder when the setting is unset or blank.
- A stale configured source folder should remain the configured value and should be reported as invalid during sort validation.
- Sorting should not silently switch to a newly detected folder when the user already configured a path.
- On Windows, the preferred source folder is `C:\Users\USER\Pictures\iCloud Photos\Photos`, not the parent `C:\Users\USER\Pictures\iCloud Photos`.
- If a configured path points at the parent `iCloud Photos` folder and its `Photos` child exists, normalize the setting to the `Photos` child because that is the sortable iCloud Photos root.
- Album folders must remain inside the configured source folder.

Proposed fix:

- In the source-folder resolution/settings method, distinguish between:
  - no configured path: run iCloud Photos folder auto-detection and persist/use the detected path if found.
  - configured path exists on disk: return it.
  - configured path does not exist: return/preserve it as configured, or return an invalid-state result that lets the sort validation raise the configured-folder-not-found error.
- Do not overwrite a non-empty configured path solely because it no longer exists.

Suggested tests:

- Add or update a settings test where `settings.json` contains a source folder path that no longer exists and auto-detection would otherwise find a different valid folder.
- Assert that the saved stale path is not replaced by the auto-detected path.
- Add or update a sort/start validation test proving the user-facing configured-folder-not-found error is reachable with the real settings service.

## 2. Try `filename` After Master-record Filename Recovery Fails

Location: `app/icloud/icloud_service.py`

Problem:

- `_read_best_filename()` first tries `_read_filename_from_master_record()`.
- If that returns `None`, it builds fallback fields from `name`, `original_filename`, and `originalFilename`.
- It only includes `filename` if `_has_master_record_filename_entry()` is false.
- `_has_master_record_filename_entry()` returns true when `_master_record.fields.filenameEnc` exists as a dict, even if that entry is empty, malformed, undecodable, or otherwise unusable.
- As a result, an asset can be skipped even when `asset.filename` is readable.

Example failing shapes:

```python
asset._master_record = {
    "fields": {
        "filenameEnc": {"value": ""}
    }
}
asset.filename == "IMG_0001.HEIC"
```

```python
asset._master_record = {
    "fields": {
        "filenameEnc": {"value": "not-valid-base64"}
    }
}
asset.filename == "IMG_0001.HEIC"
```

```python
asset._master_record = {
    "fields": {
        "filenameEnc": {"value": None}
    }
}
asset.filename == "IMG_0001.HEIC"
```

Why this is plausible:

- `_master_record` is private pyicloud/iCloud metadata and may be incomplete, partially hydrated, or shaped differently across asset types.
- `filenameEnc` may be present but not decodable by this app's recovery logic.
- The `filename` property may still be readable because pyicloud can derive it from another field, cached metadata, a resource record, or its own normalization path.

Expected behavior:

- Master-record filename recovery should still be preferred first because it avoids the known pyicloud broken `filename` property case.
- If master-record recovery returns `None`, the code should still attempt `filename`.
- Attempting `filename` is safe because `_read_field_value()` already catches exceptions from `getattr(raw_asset, "filename")` and returns `None`.

Proposed fix:

- Change `_read_best_filename()` so fallback fields include `filename` after master-record recovery fails.
- A likely fallback order is:
  - `filename`
  - `name`
  - `original_filename`
  - `originalFilename`
- Remove or narrow the `_has_master_record_filename_entry()` gate so mere presence of `filenameEnc` does not suppress a valid `filename` attribute.

Suggested tests:

- Add a test asset with `_master_record.fields.filenameEnc.value == ""` and `filename == "IMG_0001.HEIC"`; assert normalization keeps the asset.
- Add a test asset with malformed `filenameEnc.value` and a readable `filename`; assert normalization keeps the asset.
- Keep existing tests where `filename` raises and master-record recovery succeeds; those should still avoid warning/noise when master recovery provides the filename.
