# iCloud Sorter

A Windows Desktop app for sorting photos from iCloud into folders.

## Installation
### Linux
```bash
python -m venv .venv # or python3 if needed
source .venv/bin/activate

pip install -e .
```

### Windows
```bash
python -m venv .venv # or python3 if needed
.venv\Scripts\activate

pip install -e --pre .
```
Why --pre? This project uses pywebview, which depends on pythonnet on Windows.
The stable release of pythonnet (v3.0.x) does not support Python 3.14+.
The --pre flag allows pip to install pythonnet 3.1.0rc0, a pre-release version
that adds Python 3.14 support. Without it, the install will fail during wheel building.


## Run locally
```bash
python -m app.main # or python3 if needed
```

### Prerequisites

- Windows with iCloud for Windows syncing Photos locally.
- Python 3.11+ for local development.
- An accessible iCloud Photos source folder. On Windows, the sortable default is `C:\Users\USER\Pictures\iCloud Photos\Photos`, not the parent `iCloud Photos` folder.
- Local files must already be available in the configured source folder. The app reads album metadata from iCloud, then matches local files by filename.

## Usage

1. Start the desktop app with `python -m app.main`.
2. Sign in with your Apple ID. Complete 2FA if iCloud requires it.
3. Open settings and confirm the source folder points at the local iCloud Photos `Photos` folder.
4. Choose the sorting approach.
5. Select albums and start sorting.

Sorting approaches:

- `first`: move each matched file into the first selected album folder.
- `copy`: copy each matched file into every selected album folder while leaving the source file in place.

Sorting creates album-named folders inside the configured source folder only. For example, `C:\Users\mac\Pictures\iCloud Photos\Photos\Trips`.

Album folder names are sanitized for Windows path rules. Destination files are never overwritten automatically. Existing conflicts, ambiguous filename matches, missing local files, and filesystem errors are skipped and reported in progress details.

Copy mode can require significant additional storage for large libraries. It may also cause iCloud for Windows to download files if placeholders are encountered. Placeholder/offline reconciliation is future investigation work, not current MVP behavior.

Cancel stops after the current file operation finishes. It is not undo: files already moved or copied remain where they are. Later sorts are safe to run again because the app scans recursively and tracks app-created copies in JSON state.

## Run tests

```bash
pytest
```

## Run frontend tests

```bash
cd frontend
npm install
npm test
```

## Fetch SonarQube issues

The helper script `get_issues.sh` fetches unresolved issues from the
SonarCloud/SonarQube API into `sonar-issues.json`.

On Linux, macOS, WSL, or Git Bash:

```bash
export SONAR_TOKEN="your-token"
bash get_issues.sh
```

On Windows PowerShell, run the equivalent `curl.exe` command directly:

```powershell
$env:SONAR_TOKEN = "your-token"

curl.exe --fail --silent --show-error `
  -H "Authorization: Bearer $env:SONAR_TOKEN" `
  --get "https://sonarcloud.io/api/issues/search" `
  --data-urlencode "componentKeys=SkyNet12345678_icloud-file-sorter" `
  --data-urlencode "resolved=false" `
  --data-urlencode "ps=500" `
  --data-urlencode "p=1" `
  -o sonar-issues.json
```

Do not commit the token. Treat `sonar-issues.json` as a generated local report.
