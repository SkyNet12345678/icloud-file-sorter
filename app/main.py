import webview
from app.api.auth_api import AuthApi


def main():
    api = AuthApi()

    webview.create_window(
        "iCloud Sorter",
        "ui/index.html",
        js_api=api,
    )

    webview.start()


if __name__ == "__main__":
    main()
