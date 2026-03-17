# from pyicloud import PyiCloudService
import webview


def main():
    webview.create_window('Hello world', 'https://linkedin.com')
    webview.start()
    print("Project started successfully.")
    print("pyicloud import works.")

if __name__ == "__main__":
    main()
