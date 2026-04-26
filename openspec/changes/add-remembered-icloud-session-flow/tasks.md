## 1. Settings And Session Storage

- [ ] 1.1 Add remembered Apple ID accessors to `SettingsService` without storing passwords or 2FA codes
- [ ] 1.2 Add a session-store helper that deletes only the session directory for a specific normalized Apple ID
- [ ] 1.3 Add unit tests for remembered Apple ID persistence and targeted session directory deletion

## 2. Backend Auth Flow

- [ ] 2.1 Add auth state retrieval that reports whether a remembered Apple ID exists
- [ ] 2.2 Persist the remembered Apple ID after successful first-login authentication
- [ ] 2.3 Add trusted-session resume behavior that attempts cookie-backed pyicloud authentication for the remembered Apple ID
- [ ] 2.4 Add logout behavior that clears remembered Apple ID, deletes that user's session directory, and clears in-memory auth services
- [ ] 2.5 Update the pywebview bridge to expose auth state, continue session, and logout operations
- [ ] 2.6 Add unit tests for successful resume, failed resume fallback, and logout/session deletion behavior

## 3. Frontend Auth UI

- [ ] 3.1 Add a returning-user view that displays the remembered Apple ID with **Continue** and **Not you?** actions
- [ ] 3.2 Initialize the login screen by checking auth state before showing the first-login form
- [ ] 3.3 Wire **Continue** to resume the trusted session and load albums on success
- [ ] 3.4 Wire **Not you?** to logout, clear the remembered session, and show the first-login form
- [ ] 3.5 Show a clear sign-in-required message when session resume fails or expires

## 4. Verification

- [ ] 4.1 Add or update frontend tests for returning-user, continue, not-you, and failed-resume UI paths
- [ ] 4.2 Run Python tests for auth/settings/session behavior
- [ ] 4.3 Run frontend tests for login UI behavior
- [ ] 4.4 Manually verify first login with 2FA, app restart continue, and not-you logout behavior when pyicloud credentials are available
