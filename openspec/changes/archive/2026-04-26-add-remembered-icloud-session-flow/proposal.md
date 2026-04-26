## Why

After a successful first iCloud login and 2FA verification, the app stores a trusted pyicloud session. On later launches, the current UI still asks for an Apple ID password even though the trusted session may be what actually authorizes access, making it appear that any password is accepted.

This change makes the trusted-session lifecycle explicit so returning users can continue without a misleading password prompt, while still having a clear way to switch users and delete the stored session.

## What Changes

- Add a returning-user screen that says the user is signed in as the remembered Apple ID.
- Add a **Continue** action that resumes the remembered trusted iCloud session and proceeds to the app when valid.
- Add a **Not you?** action that forgets the remembered Apple ID, deletes that user's local trusted iCloud session, and returns to the first-login screen.
- Keep first-time login behavior: Apple ID and password are required, and 2FA is requested when iCloud requires it.
- Store the remembered Apple ID needed for display and session lookup, but do not store the Apple ID password.
- If a remembered session cannot be resumed, show the normal login flow and request 2FA only when iCloud requires it.

## Capabilities

### New Capabilities
- `trusted-icloud-session`: Covers remembered Apple ID display, trusted session resume, first-login fallback, and local session deletion on user switch/logout.

### Modified Capabilities
- None.

## Impact

- Backend auth bridge gains explicit trusted-session resume and logout/session deletion operations.
- Settings persistence gains a remembered Apple ID field without storing credentials.
- Session storage gains safe deletion for a specific Apple ID's pyicloud cookie directory.
- Login UI gains a returning-user screen and routes Continue/Not you? actions through the bridge.
- Tests should cover first login, remembered session resume, invalid/expired session fallback, and session deletion behavior.
