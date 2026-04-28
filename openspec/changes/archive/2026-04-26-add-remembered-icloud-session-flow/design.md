## Context

The app currently signs in through `AuthApi.login`, which calls `PyiCloudService(apple_id, password, cookie_directory=...)`. After 2FA, `trust_session()` stores trusted pyicloud session data under `%APPDATA%/icloud-sorter/icloud-sessions/<sha256-apple-id>/`.

Because pyicloud can reuse that trusted session on later login attempts, the UI can appear to accept any password after the first successful 2FA flow. The underlying session reuse is useful, but the password prompt is misleading once the app has a valid trusted session.

The app does not currently store the Apple ID separately from the hashed session directory, so it cannot display "signed in as <apple email>" without adding non-secret remembered-user state.

## Goals / Non-Goals

**Goals:**
- Make returning-user session resume explicit in the UI.
- Remember the Apple ID needed for display and session lookup.
- Resume a trusted session without asking for a password when possible.
- Provide a clear **Not you?** action that deletes the remembered user's local session and returns to first login.
- Preserve the existing first-login and 2FA flow.

**Non-Goals:**
- Do not store Apple ID passwords or app-specific passwords.
- Do not replace pyicloud authentication.
- Do not guarantee Apple will require 2FA after logout; the app can only delete its local trusted session and follow iCloud's next authentication response.
- Do not add multi-account switching beyond forgetting the current remembered user and signing in again.

## Decisions

### Remember Apple ID in settings

Store a normalized `remembered_apple_id` field in `settings.json` after successful login/session trust. This is non-secret user state and is needed because the session directory name is a one-way hash.

Alternative considered: infer the Apple ID from session directory contents. This is unreliable because the directory name is hashed and pyicloud cookie files are implementation details.

### Add explicit auth state and resume bridge methods

Expose bridge operations for auth state, session resume, and logout/session deletion instead of overloading `login`:

- `get_auth_state()` returns whether there is a remembered Apple ID.
- `continue_session()` attempts to build an authenticated iCloud API from the remembered Apple ID and existing cookie directory.
- `logout()` forgets the remembered Apple ID, clears in-memory auth services, and deletes that Apple ID's session directory.

Alternative considered: keep using `login(apple_id, password)` for returning users. This preserves the confusing password prompt and does not give the UI a clean way to distinguish first login from session resume.

### Resume using cookie-backed pyicloud construction

For `continue_session()`, construct `PyiCloudService` with the remembered Apple ID, the known cookie directory, and a non-secret placeholder password. The intent is to let pyicloud reuse the trusted session cookie; if the cookie is expired, invalid, or not trusted, the resume attempt must fail or require 2FA and the UI must fall back to the normal login form.

Alternative considered: store the real password for future resume. This is rejected because it increases credential risk and is unnecessary when pyicloud already persists trusted session data.

### Remember only after successful authentication

Persist `remembered_apple_id` only after a successful login path has created an authenticated API session. For 2FA flows, this happens after `validate_2fa_code()` succeeds and `trust_session()` is attempted. If trust fails, the app may still be logged in for the current process, but should avoid promising future passwordless resume unless a usable trusted session exists.

Alternative considered: remember the Apple ID immediately when the user starts login. This could show a returning-user screen for accounts that never completed authentication.

### Treat logout as local session deletion

The **Not you?** action deletes the app's local session directory for the remembered Apple ID and clears the remembered Apple ID from settings. This is a local logout/user-switch action, not a remote Apple account logout.

Alternative considered: call a remote Apple logout endpoint. The current pyicloud integration does not expose a stable product requirement for remote logout, and the local trusted session is the source of the app's confusing resume behavior.

### Use "Continue as" returning-user copy

The returning-user screen will say "Continue as <apple email>" rather than "You are signed in as <apple email>". This is more accurate because the app has remembered the Apple ID, but has not verified the trusted session for the current launch until the user selects **Continue**.

Alternative considered: use "You are signed in as". This is rejected because it overstates the authentication state before session resume succeeds.

### Keep Not you on the returning-user screen only

This change will add **Not you?** only to the returning-user screen. It will not add a persistent logout button inside the albums workflow.

Alternative considered: add logout inside the main app view. This is useful, but it expands the UI scope beyond the immediate confusing-login problem and can be handled as a follow-up change.

## Risks / Trade-offs

- pyicloud may not support placeholder-password cookie resume consistently -> handle resume failure by returning to the normal login form with a clear status message.
- Apple may not require 2FA after local session deletion -> word UI and requirements as "2FA when iCloud requires it," not as a guarantee.
- Deleting the wrong session directory would log out another user locally -> derive the directory only from the normalized remembered Apple ID and avoid broad deletion of the sessions root.
- Remembered Apple ID is personal data -> store only the email identifier needed for display/session lookup, never passwords or 2FA codes.

## Migration Plan

Existing users may already have trusted session directories but no `remembered_apple_id`. They should see the normal first-login form once, because the app cannot safely map a hashed session directory back to an Apple ID. After the next successful login, the Apple ID is remembered and the returning-user flow becomes available.

Rollback is straightforward: ignore or remove `remembered_apple_id` and continue showing the existing login form. Existing pyicloud session directories can remain unless the user chooses **Not you?**.

## Open Questions

None.
