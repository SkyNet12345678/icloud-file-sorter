# Persist Trusted iCloud Sessions

## Summary

Change auth to use `pyicloud`'s real persisted cookie/session support instead of creating a fresh temp cookie directory on every login. The first successful 2FA flow will call `trust_session()` and persist Apple's trusted-session files under the app data directory; later logins with the same Apple ID should reuse that trusted session and skip 2FA unless Apple expires or invalidates it.

## Key Changes

- Add a small auth session path helper, likely in `app/icloud/auth.py` or a new `app/icloud/session_store.py`.
- Add or expose a public app-data/base-dir helper from `SettingsService` instead of reaching into private `_settings_dir` or duplicating `%APPDATA%` path logic.
- Store pyicloud session files under a stable per-user directory: `SettingsService` base dir / `icloud-sessions/`.
- Isolate session files per Apple ID using a deterministic account-specific subdirectory, preferably a hash of the normalized Apple ID, so pyicloud's sanitized `.session` and `.cookiejar` filenames cannot collide.
- Use `%APPDATA%/icloud-sorter/icloud-sessions/` on Windows.
- Replace `tempfile.mkdtemp()` in `icloud_login()` with that stable session directory.
- Keep using real `PyiCloudService`; no mocks or fake data in runtime code.
- Keep the existing bridge responses:
  - `login()` still returns success or `{ "2fa_required": true }`.
  - `verify_2fa()` still validates the code and promotes the session.
- On successful 2FA, call `trust_session()` once, check its return value, and treat only a successful trusted session as a persisted trusted login.
- If Apple expires the trusted session, `pyicloud` may require 2FA again; the UI should continue to show the existing 2FA form in that case.

## Implementation Details

- Update `icloud_login(apple_id, password)` to accept an optional `cookie_directory` or resolve the stable account-specific session directory internally.
- Ensure the session directory is created before calling `PyiCloudService`.
- Do not store Apple ID passwords in JSON or settings.
- Do not store session material in `settings.json`; leave pyicloud's `.session` and `.cookiejar` files in the dedicated session directory.
- Treat `.session` and `.cookiejar` files as sensitive auth material even though they are not passwords.
- Optionally log the root session directory path at debug/info level, but do not log cookies, tokens, passwords, raw session contents, or account-derived session filenames.
- Keep `AuthApi` mostly unchanged, but ensure `self.icloud = ICloudService(api)` is set after successful `verify_2fa()` so the 2FA success path matches the direct-login success path.
- If `trust_session()` returns false after valid 2FA, decide explicitly whether to fail the login response or allow the current in-memory login while warning that persistence failed; do not silently report persisted trust.
- Do not add logout/clear-session UI in this change; clearing `%APPDATA%/icloud-sorter/icloud-sessions/` manually is enough for development reset.

## Tests

- Add or adjust unit tests for `icloud_login()` proving it passes a stable cookie directory to `PyiCloudService`.
- Add a test using a temp app/session directory so tests do not touch real `%APPDATA%`.
- Add a test proving the session path is account-specific and collision-resistant for similar Apple IDs.
- Add a test proving `SettingsService` exposes the app data/session root through a public API rather than callers using `_settings_dir`.
- Update the auth e2e fake to simulate:
  - first login requires 2FA,
  - valid 2FA calls and successfully trusts the session,
  - second login with the same cookie directory does not require 2FA.
- Add coverage for `trust_session()` returning false after valid 2FA so the behavior is intentional and visible.
- Add coverage that `AuthApi.icloud` is initialized after both direct login and 2FA verification.
- Keep existing invalid-credentials and invalid-code coverage.
- Run `pytest tests/auth` and then the full `pytest` suite if dependencies are available.

## Assumptions

- Session persistence should apply to all app runs, including development and packaged desktop usage.
- Re-entering the Apple ID password on login is acceptable for now; the goal is to avoid repeated 2FA prompts, not to implement password storage.
- If Apple invalidates or expires the trusted browser/session, requesting 2FA again is acceptable and should follow the current UI flow.
