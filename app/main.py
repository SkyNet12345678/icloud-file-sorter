from app.icloud.auth import icloud_login


def main():
    apple_id = input("Apple ID: ")
    password = input("Password: ")

    api = icloud_login(apple_id, password)

    if not api:
        print("Login failed")
        return

    print("Logged in!")

if __name__ == "__main__":
    main()
