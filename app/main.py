from __future__ import annotations

import argparse

from app.webview_app import launch_webview


def run_auth_cli() -> None:
    try:
        from app.icloud.auth import icloud_login
    except ModuleNotFoundError as exc:
        if exc.name == "pyicloud":
            msg = "pyicloud is not installed in this Python environment. Run `pip install -e .` first."
            raise RuntimeError(msg) from exc
        raise

    apple_id = input("Apple ID: ")
    password = input("Password: ")

    api = icloud_login(apple_id, password)

    if not api:
        print("Login failed")
        return

    print("Logged in!")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--auth-cli",
        action="store_true",
        help="run the existing terminal-based iCloud login flow",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.auth_cli:
        run_auth_cli()
        return

    launch_webview()


if __name__ == "__main__":
    main()
