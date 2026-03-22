from pyicloud import PyiCloudService
import webview

DEV_URL = "http://localhost:5173"

def main() -> None:
    webview.create_window(
        "iCloud File Sorter",
        url=DEV_URL,
        width=1024,
        height=768,
        min_size=(800, 600),
    )
    webview.start(debug=True)

if __name__ == "__main__":
    main()
