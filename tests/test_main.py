from app import main


def test_main_launches_webview_by_default(monkeypatch):
    launched = {"called": False}

    def fake_launch_webview():
        launched["called"] = True

    monkeypatch.setattr(main, "launch_webview", fake_launch_webview)

    main.main([])

    assert launched["called"] is True


def test_main_runs_auth_cli_when_requested(monkeypatch):
    auth_cli = {"called": False}

    def fake_run_auth_cli():
        auth_cli["called"] = True

    monkeypatch.setattr(main, "run_auth_cli", fake_run_auth_cli)

    main.main(["--auth-cli"])

    assert auth_cli["called"] is True
