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
