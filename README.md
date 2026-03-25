# iCloud Sorter

A desktop app for sorting photos from iCloud into folders.

## Current architecture

- `app/` contains the Python desktop app and iCloud integration.
- `app/main.py` starts the desktop app by default.
- `app/main.py --auth-cli` runs the old terminal auth flow.
- `app/webview_app.py` opens the React UI in `pywebview`.
- `frontend/` contains the React UI built with Vite.

In development, the desktop app runs on the host machine and the React dev
server can run in Docker. This is the recommended setup for a team working on
macOS and Linux while targeting Windows for release.

## Repository layout

- `app/main.py`: desktop entrypoint
- `app/webview_app.py`: chooses between the Vite dev server and built frontend files
- `app/icloud/`: iCloud auth and backend logic
- `frontend/src/`: React application code
- `tests/`: Python tests
- `docker-compose.yml`: shared Docker workflow for frontend and Python tooling

## Development model

Use Docker for:

- React development
- frontend tests
- Python tooling and team consistency

Use the host machine for:

- running `pywebview`
- native desktop debugging
- platform-specific GUI troubleshooting

Do not expect the desktop window itself to run reliably inside Docker on macOS.
For Linux, GUI containers are possible but are not the project default.

## Python setup

The Python app must run in a virtual environment on the host machine.

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
```

Install project dependencies:

```bash
python3 -m pip install -e .
```

## Linux developer setup

On Linux, the base project install is not enough for the desktop app.
`pywebview` also needs a GUI backend installed in the same virtual environment.

Recommended default:

```bash
python3 -m pip install -e .
python3 -m pip install "pywebview[qt]"
```

Then run:

```bash
python3 -m app.main
```

Alternative backend options:

Qt backend:

```bash
python3 -m pip install "pywebview[qt]"
```

GTK backend:

```bash
python3 -m pip install "pywebview[gtk]"
```

If Python packages alone are not enough on your distro, install the matching
system GUI libraries as well. The exact package names vary by distro.

If `python3 -m app.main` fails with a message saying Qt or GTK is required, the
first thing to check is whether you ran `python3 -m pip install "pywebview[qt]"`
inside the project virtual environment.

## macOS developer setup

Use a normal Python install such as Homebrew Python, not the system Python that
ships with macOS.

Example:

```bash
brew install python
python3 -m venv venv
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
python3 -m app.main
```

If `pywebview` opens but keyboard focus or app switching behaves strangely,
double-check that you are not using the built-in macOS Python.

## Frontend development

Frontend code lives in `frontend/`.

Main files:

- `frontend/src/App.jsx`
- `frontend/src/main.jsx`
- `frontend/index.html`

Start the frontend dev server in Docker:

```bash
docker compose up frontend-dev
```

That exposes the Vite app on `http://127.0.0.1:5173`.

While that server is running, the desktop app will use it automatically in
default `auto` mode:

```bash
python3 -m app.main
```

Run frontend tests:

```bash
docker compose run --rm frontend-test
```

## Backend development

Backend code lives in `app/`.

Main areas:

- `app/webview_app.py`: desktop window bootstrapping
- `app/icloud/auth.py`: iCloud authentication
- `app/main.py`: command-line entrypoint and mode selection

Run the desktop app:

```bash
python3 -m app.main
```

Run the terminal auth flow directly:

```bash
python3 -m app.main --auth-cli
```

Run Python tests in Docker:

```bash
docker compose run --rm python-test
```

Open an interactive Python shell in the project container:

```bash
docker compose run --rm python-dev
```

## How the UI is selected

`app/webview_app.py` uses these rules:

- `APP_UI_MODE=auto`: use the Vite dev server if reachable, otherwise use `frontend/dist/index.html`
- `APP_UI_MODE=dev`: always use the dev server
- `APP_UI_MODE=prod`: always use built frontend assets
- `APP_UI_DEV_SERVER_URL`: override the default dev server URL

Examples:

```bash
APP_UI_MODE=dev python3 -m app.main
APP_UI_MODE=prod python3 -m app.main
APP_UI_DEV_SERVER_URL=http://127.0.0.1:5173 python3 -m app.main
```

Build frontend assets for production-mode local testing:

```bash
cd frontend
npm run build
cd ..
APP_UI_MODE=prod python3 -m app.main
```

## Typical workflows

Backend-only work:

```bash
source venv/bin/activate
python3 -m app.main --auth-cli
docker compose run --rm python-test
```

Frontend-only work:

```bash
docker compose up frontend-dev
```

Desktop integration work:

```bash
docker compose up frontend-dev
source venv/bin/activate
python3 -m app.main
```

## Troubleshooting

`python3 -m app.main` says `pywebview is not installed`:

```bash
python3 -m pip install -e .
```

`python3 -m app.main` says Qt or GTK is required on Linux:

```bash
python3 -m pip install "pywebview[qt]"
```

or

```bash
python3 -m pip install "pywebview[gtk]"
```

`python3 -m app.main --auth-cli` says `pyicloud is not installed`:

```bash
python3 -m pip install -e .
```

The app opens old built files instead of the live frontend:

- make sure `docker compose up frontend-dev` is running
- verify `http://127.0.0.1:5173` opens in a browser
- force dev mode with `APP_UI_MODE=dev`

## Notes for the team

- Linux developers need a `pywebview` backend installed locally.
- macOS developers should use Homebrew Python or another non-system Python.
- Frontend work should generally use Docker.
- Desktop integration work should run Python locally on the host.
- Windows packaging should be handled on Windows CI or a Windows machine.
