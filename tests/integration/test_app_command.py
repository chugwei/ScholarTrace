"""Application-mode CLI coverage: real loopback server, faked desktop window."""

import json
import socket
import threading
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import scholartrace.launcher as launcher
from scholartrace.cli import app as cli_app

runner = CliRunner()


def _free_ephemeral_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def _port_accepts_connections(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        try:
            probe.connect(("127.0.0.1", port))
        except OSError:
            return False
        return True


def test_app_help_lists_window_and_browser_options() -> None:
    result = runner.invoke(cli_app, ["app", "--help"])

    assert result.exit_code == 0
    for option in ("--host", "--port", "--database", "--browser"):
        assert option in result.stdout


def test_app_command_serves_workbench_until_window_closes(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "app-mode.db"
    port = _free_ephemeral_port()
    opened: list[tuple[str, str, str]] = []

    def fake_desktop_window(
        url,
        *,
        title=launcher.DEFAULT_WINDOW_TITLE,
        on_close=None,
        window_opener=None,
        loading_html=None,
    ):
        # The server boots in a background thread while the window appears, so
        # poll /health like the real loading page does before asserting readiness.
        deadline = time.monotonic() + 15.0
        health = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{url}health", timeout=5) as response:
                    health = json.loads(response.read())
                break
            except OSError:
                time.sleep(0.1)
        assert health is not None and health["status"] == "ok"
        opened.append((url, title, health["status"]))
        if on_close is not None:
            on_close()

    monkeypatch.setattr(launcher, "open_desktop_window", fake_desktop_window)

    result = runner.invoke(cli_app, ["app", "--database", str(database), "--port", str(port)])

    assert result.exit_code == 0, result.output
    assert f"http://127.0.0.1:{port}/" in result.output
    assert str(database) in result.output
    assert opened == [(f"http://127.0.0.1:{port}/", "研迹 ScholarTrace", "ok")]

    deadline = time.monotonic() + 5.0
    while _port_accepts_connections(port) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _port_accepts_connections(port)


def test_app_command_browser_mode_uses_default_browser_opener(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "app-mode-browser.db"
    port = _free_ephemeral_port()
    visited: list[str] = []
    desktop_calls: list[str] = []

    expired_thread = threading.Thread(target=lambda: None, daemon=True)
    expired_thread.start()
    expired_thread.join()

    def fake_run_server_in_thread(application, *, host, port):
        return SimpleNamespace(
            thread=expired_thread,
            stop=lambda **_kwargs: None,
        )

    monkeypatch.setattr(launcher, "run_server_in_thread", fake_run_server_in_thread)
    monkeypatch.setattr(launcher, "wait_until_listening", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        launcher,
        "open_browser",
        lambda url, *, opener=None: visited.append(url),
    )
    monkeypatch.setattr(
        launcher,
        "open_desktop_window",
        lambda *args, **kwargs: desktop_calls.append(str(args)),
    )

    result = runner.invoke(
        cli_app, ["app", "--database", str(database), "--port", str(port), "--browser"]
    )

    assert result.exit_code == 0, result.output
    assert visited == [f"http://127.0.0.1:{port}/"]
    assert desktop_calls == []
