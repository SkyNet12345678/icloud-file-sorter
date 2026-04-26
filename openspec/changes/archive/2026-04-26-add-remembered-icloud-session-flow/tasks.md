## 1. Settings And Session Storage

- [x] 1.1 Add remembered Apple ID accessors to `SettingsService` without storing passwords or 2FA codes
- [x] 1.2 Add a session-store helper that deletes only the session directory for a specific normalized Apple ID
- [x] 1.3 Add unit tests for remembered Apple ID persistence and targeted session directory deletion

## 2. Backend Auth Flow

- [x] 2.1 Add auth state retrieval that reports whether a remembered Apple ID exists
- [x] 2.2 Persist the remembered Apple ID after successful first-login authentication
- [x] 2.3 Add trusted-session resume behavior that attempts cookie-backed pyicloud authentication for the remembered Apple ID
- [x] 2.4 Add logout behavior that clears remembered Apple ID, deletes that user's session directory, and clears in-memory auth services
- [x] 2.5 Update the pywebview bridge to expose auth state, continue session, and logout operations
- [x] 2.6 Add unit tests for successful resume, failed resume fallback, and logout/session deletion behavior

## 3. Frontend Auth UI

- [x] 3.1 Add a returning-user view that displays the remembered Apple ID with **Continue** and **Not you?** actions
- [x] 3.2 Initialize the login screen by checking auth state before showing the first-login form
- [x] 3.3 Wire **Continue** to resume the trusted session and load albums on success
- [x] 3.4 Wire **Not you?** to logout, clear the remembered session, and show the first-login form
- [x] 3.5 Show a clear sign-in-required message when session resume fails or expires

## 4. Verification

- [x] 4.1 Add or update frontend tests for returning-user, continue, not-you, and failed-resume UI paths
- [x] 4.2 Run Python tests for auth/settings/session behavior
- [x] 4.3 Run frontend tests for login UI behavior
- [x] 4.4 Manually verify first login with 2FA, app restart continue, and not-you logout behavior when pyicloud credentials are available

## 5. Review Follow-ups

- [x] 5.1 Clear in-memory authenticated services and bridge album service state when remembered-session resume fails or requires reauthentication
- [x] 5.2 Prevent the first-login form from flashing before auth state resolves for remembered users
