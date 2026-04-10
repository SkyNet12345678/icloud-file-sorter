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
The app is currenlty set to skip the login page for dev and use mock data.

```JavaScript
// main.js

document.addEventListener('DOMContentLoaded', async () => {
// document.addEventListener('DOMContentLoaded', () => {
```

Run the app with:

```bash
DEV_BYPASS_LOGIN=1 python -m main.py # or python3 if needed
```

To go back to login, swap the commented-out lines in **main.js** and run normally.

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
