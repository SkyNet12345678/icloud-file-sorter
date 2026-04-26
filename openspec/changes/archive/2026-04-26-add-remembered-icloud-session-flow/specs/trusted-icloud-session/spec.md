## ADDED Requirements

### Requirement: Remember authenticated Apple ID
The app SHALL remember the authenticated Apple ID after a successful iCloud login without storing the Apple ID password.

#### Scenario: First login completes with 2FA
- **WHEN** the user signs in with Apple ID and password, completes required 2FA, and the app establishes an authenticated iCloud session
- **THEN** the app remembers the Apple ID for future returning-user display and session lookup

#### Scenario: Password is not persisted
- **WHEN** the app remembers the authenticated user
- **THEN** the app MUST NOT store the Apple ID password or 2FA code in app settings or state

### Requirement: Show returning-user screen
The app SHALL show a returning-user screen when a remembered Apple ID exists before prompting for Apple ID and password.

#### Scenario: Remembered Apple ID exists on app start
- **WHEN** the app starts and a remembered Apple ID is present
- **THEN** the UI shows a message identifying the remembered Apple ID with **Continue** and **Not you?** actions

#### Scenario: No remembered Apple ID exists on app start
- **WHEN** the app starts and no remembered Apple ID is present
- **THEN** the UI shows the first-login form that asks for Apple ID and password

### Requirement: Continue resumes trusted session
The app SHALL attempt to resume the remembered user's trusted iCloud session when the user selects **Continue**.

#### Scenario: Trusted session resumes successfully
- **WHEN** the user selects **Continue** and the remembered trusted iCloud session is valid
- **THEN** the app establishes the authenticated iCloud services and opens the main album workflow without asking for a password or 2FA code

#### Scenario: Trusted session cannot be resumed
- **WHEN** the user selects **Continue** and the remembered trusted iCloud session is expired, missing, invalid, or rejected by iCloud
- **THEN** the app shows the first-login form and communicates that sign-in is required again

#### Scenario: iCloud requires 2FA during resume
- **WHEN** the user selects **Continue** and iCloud reports that 2FA is required for the resume attempt
- **THEN** the app does not treat the user as fully logged in until the required authentication flow succeeds

### Requirement: Not you clears remembered session
The app SHALL provide a **Not you?** action that clears the remembered Apple ID and deletes only that Apple ID's local trusted iCloud session.

#### Scenario: User selects Not you
- **WHEN** the user selects **Not you?** from the returning-user screen
- **THEN** the app clears the remembered Apple ID, deletes the local trusted session directory for that Apple ID, clears in-memory authenticated services, and shows the first-login form

#### Scenario: Session directory is already missing
- **WHEN** the user selects **Not you?** and the remembered Apple ID's local session directory does not exist
- **THEN** the app still clears the remembered Apple ID and shows the first-login form without failing the logout action

### Requirement: First-login authentication remains authoritative
The app SHALL preserve the existing first-login behavior where Apple ID and password are submitted to iCloud and 2FA is requested only when iCloud requires it.

#### Scenario: First login requires 2FA
- **WHEN** the user submits valid Apple ID and password and iCloud requires 2FA
- **THEN** the app shows the 2FA form and completes login only after iCloud accepts the verification code

#### Scenario: First login does not require 2FA
- **WHEN** the user submits valid Apple ID and password and iCloud does not require 2FA
- **THEN** the app establishes the authenticated iCloud services and opens the main album workflow

#### Scenario: Invalid first-login credentials
- **WHEN** the user submits invalid Apple ID or password on the first-login form
- **THEN** the app does not open the main album workflow and shows a login failure message
