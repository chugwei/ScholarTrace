import json
import socket
import sys
import threading

import pytest

from scholartrace.launcher import (
    BackgroundServer,
    LauncherError,
    ThreadedServer,
    build_app_url,
    build_loading_html,
    ensure_writable_streams,
    find_free_port,
    open_browser,
    open_desktop_window,
    run_server_in_thread,
    wait_until_listening,
)


def _occupy_port() -> tuple[socket.socket, int]:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server, server.getsockname()[1]


def _release_port(port: int, *, timeout_seconds: float = 2.0) -> None:
    import time

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            probe.settimeout(0.2)
            try:
                probe.connect(("127.0.0.1", port))
            except OSError:
                return
            time.sleep(0.05)


def test_find_free_port_returns_preferred_when_available() -> None:
    port = find_free_port(49152, host="127.0.0.1")

    assert port == 49152


def test_find_free_port_skips_occupied_ports() -> None:
    blocker, occupied = _occupy_port()
    try:
        port = find_free_port(occupied, host="127.0.0.1")
    finally:
        blocker.close()

    assert port == occupied + 1


def test_find_free_port_raises_when_all_attempts_busy() -> None:
    blocker, occupied = _occupy_port()
    try:
        with pytest.raises(LauncherError, match="no free port"):
            find_free_port(occupied, host="127.0.0.1", attempts=1)
    finally:
        blocker.close()


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", "http://127.0.0.1:8000/"),
        ("0.0.0.0", "http://127.0.0.1:8000/"),
        ("", "http://127.0.0.1:8000/"),
        ("::", "http://127.0.0.1:8000/"),
        ("localhost", "http://localhost:8000/"),
    ],
)
def test_build_app_url_normalizes_wildcard_hosts(host: str, expected: str) -> None:
    assert build_app_url(host, 8000) == expected


def test_wait_until_listening_returns_once_socket_accepts() -> None:
    blocker, port = _occupy_port()
    try:
        wait_until_listening("127.0.0.1", port, timeout_seconds=2.0)
    finally:
        blocker.close()


def test_wait_until_listening_raises_on_timeout() -> None:
    blocker, port = _occupy_port()
    blocker.close()

    with pytest.raises(LauncherError, match="did not listen"):
        wait_until_listening("127.0.0.1", port, timeout_seconds=0.2)


async def _health_asgi_app(scope, receive, send):
    if scope["type"] != "http":
        return
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": b'{"status":"ok"}'})


def test_threaded_server_serves_and_stops_cooperatively() -> None:
    import urllib.request

    blocker, port = _occupy_port()
    blocker.close()

    handle = run_server_in_thread(_health_asgi_app, host="127.0.0.1", port=port)
    try:
        wait_until_listening("127.0.0.1", port, timeout_seconds=10.0)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            assert json.loads(response.read()) == {"status": "ok"}
    finally:
        handle.stop(timeout_seconds=10.0)

    assert not handle.thread.is_alive()
    _release_port(port)


def test_threaded_server_is_daemon_named_thread() -> None:
    blocker, port = _occupy_port()
    blocker.close()

    server = ThreadedServer(_health_asgi_app, host="127.0.0.1", port=port)

    assert server.thread.daemon is True
    assert server.thread.name == "scholartrace-app-server"
    server.start()
    try:
        wait_until_listening("127.0.0.1", port, timeout_seconds=10.0)
    finally:
        server.stop(timeout_seconds=10.0)
    _release_port(port)


def test_open_desktop_window_uses_injected_opener_and_reports_closure() -> None:
    opened: list[tuple[str, str]] = []
    closures: list[str] = []

    def fake_opener(url: str, title: str) -> None:
        opened.append((url, title))

    open_desktop_window(
        "http://127.0.0.1:8000/",
        on_close=lambda: closures.append("stopped"),
        window_opener=fake_opener,
    )

    assert opened == [("http://127.0.0.1:8000/", "研迹 ScholarTrace")]
    assert closures == ["stopped"]


def test_open_desktop_window_normalizes_gui_failure_to_launcher_error() -> None:
    closures: list[bool] = []

    def failing_opener(url: str, title: str) -> None:
        raise OSError("WebView2 runtime missing")

    with pytest.raises(LauncherError, match="--browser"):
        open_desktop_window(
            "http://127.0.0.1:8000/",
            on_close=lambda: closures.append(True),
            window_opener=failing_opener,
        )

    assert closures == [True]


def test_open_browser_uses_injected_opener() -> None:
    visited: list[str] = []

    def recording_opener(url: str) -> bool:
        visited.append(url)
        return True

    open_browser("http://127.0.0.1:8000/", opener=recording_opener)

    assert visited == ["http://127.0.0.1:8000/"]


def test_open_browser_raises_when_opener_refuses() -> None:
    with pytest.raises(LauncherError, match="could not open"):
        open_browser("http://127.0.0.1:8000/", opener=lambda _url: False)


def test_open_desktop_window_runs_without_real_webview_import() -> None:
    import sys

    open_desktop_window("http://127.0.0.1:8000/", window_opener=lambda url, title: None)

    assert "webview" not in sys.modules


def test_wait_until_listening_works_from_a_worker_thread() -> None:
    blocker, port = _occupy_port()
    completed: list[bool] = []
    try:
        thread = threading.Thread(
            target=lambda: (
                wait_until_listening("127.0.0.1", port, timeout_seconds=2.0),
                completed.append(True),
            )
        )
        thread.start()
        thread.join(timeout=3.0)
    finally:
        blocker.close()

    assert completed == [True]


def test_background_server_becomes_ready_and_stops() -> None:
    import urllib.request

    blocker, port = _occupy_port()
    blocker.close()
    errors: list[str] = []

    startup = BackgroundServer(
        lambda: _health_asgi_app,
        host="127.0.0.1",
        port=port,
        on_error=errors.append,
    )
    startup.start()
    try:
        startup.wait_ready(timeout_seconds=10.0)
        assert startup.error is None
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            assert json.loads(response.read()) == {"status": "ok"}
    finally:
        startup.stop(timeout_seconds=10.0)

    assert errors == []
    _release_port(port)


def test_background_server_reports_factory_failure() -> None:
    blocker, port = _occupy_port()
    blocker.close()
    errors: list[str] = []

    def failing_factory():
        raise ValueError("bad database path")

    startup = BackgroundServer(
        failing_factory,
        host="127.0.0.1",
        port=port,
        on_error=errors.append,
    )
    startup.start()

    with pytest.raises(LauncherError, match="bad database path"):
        startup.wait_ready(timeout_seconds=10.0)

    assert errors and "bad database path" in errors[0]
    startup.stop(timeout_seconds=10.0)
    _release_port(port)


def test_build_loading_html_polls_target_and_redirects() -> None:
    html = build_loading_html("http://127.0.0.1:8123/")

    assert "http://127.0.0.1:8123/" in html
    assert '"no-cors"' in html
    assert "location.replace(target)" in html
    assert "正在启动研迹 ScholarTrace" in html


def test_ensure_writable_streams_is_noop_with_real_streams() -> None:
    assert ensure_writable_streams() is None
    assert sys.stdout is not None
    assert sys.stderr is not None


def test_ensure_writable_streams_redirects_none_streams_to_log(tmp_path) -> None:
    log_path = tmp_path / "logs" / "app.log"
    real_stdout, real_stderr = sys.stdout, sys.stderr
    sys.stdout = None
    sys.stderr = None
    try:
        returned = ensure_writable_streams(log_path)
        assert returned == log_path
        assert sys.stdout is not None and sys.stderr is not None
        print("窗口模式日志行")
        sys.stdout.flush()
    finally:
        sys.stdout, sys.stderr = real_stdout, real_stderr

    assert "窗口模式日志行" in log_path.read_text(encoding="utf-8")
