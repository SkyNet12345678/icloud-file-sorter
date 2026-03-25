# iCloud Sorter

A desktop app for sorting photos from iCloud into folders.

## What this repo looks like today

- `app/` is currently a Python CLI that authenticates with iCloud.
- `frontend/` now contains a minimal Vite + React UI entrypoint.
- The native `pywebview` shell is not wired up yet.

That matters for Docker: the right split for this project is to containerize the
tooling and web UI, not the native desktop window.

## Recommended Docker development model

For a `pywebview + React` desktop app, use Docker for:

- Python dependency consistency
- Python tests and linting
- React/Vite development
- Shared team onboarding on macOS and Linux

Do not use Docker as the primary way to run the desktop shell itself:

- `pywebview` needs direct access to host GUI APIs
- macOS does not provide a practical Docker GUI path for native desktop work
- Linux GUI containers are possible, but not a good team default
- your production target is Windows, which means packaging should happen on
  Windows CI or a Windows VM anyway

## Prerequisites

- Docker with Compose support
- A local Python install for the eventual native `pywebview` shell
- iCloud for Windows on the machine that will run the final packaged app

## Docker workflows

Build the Python image:

```bash
docker compose build python-dev
```

Start the React dev server in Docker:

```bash
docker compose up frontend-dev
```

Run Python tests in Docker:

```bash
docker compose run --rm python-test
```

Run frontend tests in Docker:

```bash
docker compose run --rm frontend-test
```

Open an interactive Python dev shell in Docker:

```bash
docker compose run --rm python-dev
```

## How the desktop app should work in development

Once you add the actual `pywebview` shell, the development loop should be:

1. Run `docker compose up frontend-dev`
2. Run the Python desktop app on the host machine
3. Have `pywebview` open `http://localhost:5173` in development
4. In production, load built frontend assets from `frontend/dist`

This keeps the native window local while still giving the team a shared,
containerized frontend and Python toolchain.

## Local Python setup

If you need to run the current CLI directly on the host:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.main
```

## Findings from the current repo

- The previous `Dockerfile` ran `pip install .` before copying `app/`, so the
  image build was not valid.
- The previous `docker-compose.yml` only wrapped the Python CLI and did not
  reflect a `pywebview + React` development workflow.
- The frontend package had test tooling but no Vite dev script or UI entrypoint,
  so there was nothing meaningful to run in a frontend container.
