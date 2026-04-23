# iCloud Sorter

A Windows Desktop app for sorting photos from iCloud into folders.

## Installation
```bash
python -m venv .venv # or python3 if needed
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -e .
```

## Run locally
```bash
python -m app.main # or python3 if needed
```

### Prerequisites

TODO

## Usage
 
TODO

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
