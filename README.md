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

### Running offline for dev
Set the `DEV_BYPASS_LOGIN` environment variable to skip the login page and use mock data.

Run the app from root with:

```bash
DEV_BYPASS_LOGIN=1 python -m app.main # or python3 if needed
```

To go back to login, run the app without that environment variable.

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
