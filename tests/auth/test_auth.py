from app.icloud.auth import icloud_login


def test_login_invalid_credentials():
    api = icloud_login("fake@example.com", "wrong-password")
    assert api is None
