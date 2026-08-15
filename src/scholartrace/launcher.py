"""Fast local application-mode launcher: loopback server plus a desktop window.

The helpers are deliberately small and dependency-injectable so tests can cover
port selection, readiness, and window wiring without a GUI or real network.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path

DEFAULT_WINDOW_TITLE = "研迹 ScholarTrace"


class LauncherError(RuntimeError):
    """Raised when application mode cannot acquire a port, serve, or open a window."""


def ensure_writable_streams(log_path: Path | None = None) -> Path | None:
    """Windowed executables get ``None`` stdout/stderr; redirect them to a log file.

    Returns the log path when streams were redirected, ``None`` when the real
    streams were already present (normal console usage).
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    if log_path is None:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        log_path = Path(base) / "ScholarTrace" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sink = log_path.open("a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = sink
    if sys.stderr is None:
        sys.stderr = sink
    return log_path


def find_free_port(preferred: int, *, host: str = "127.0.0.1", attempts: int = 11) -> int:
    """Return the first bindable port at or after ``preferred``.

    Probing binds and immediately closes a socket; a short race window remains
    before the real server binds, which is acceptable for a local launcher.
    """
    for candidate in range(preferred, preferred + max(attempts, 1)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, candidate))
            except OSError:
                continue
            return candidate
    raise LauncherError(
        f"no free port between {preferred} and {preferred + attempts - 1} on {host}"
    )


def build_app_url(host: str, port: int) -> str:
    """Build the loopback URL a local browser or window should open."""
    display_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}/"


def wait_until_listening(host: str, port: int, *, timeout_seconds: float = 15.0) -> None:
    """Block until the server accepts TCP connections, or raise LauncherError."""
    display_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.25)
            try:
                probe.connect((display_host, port))
            except OSError:
                time.sleep(0.05)
                continue
            return
    raise LauncherError(
        f"server did not listen on {display_host}:{port} within {timeout_seconds:g}s"
    )


class ThreadedServer:
    """A uvicorn server running in a daemon thread with cooperative shutdown."""

    def __init__(self, application: object, *, host: str, port: int) -> None:
        import uvicorn

        config = uvicorn.Config(application, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self._server.run,
            name="scholartrace-app-server",
            daemon=True,
        )

    def start(self) -> None:
        self.thread.start()

    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        self._server.should_exit = True
        if self.thread.is_alive():
            self.thread.join(timeout=timeout_seconds)


def run_server_in_thread(application: object, *, host: str, port: int) -> ThreadedServer:
    """Start serving ``application`` on a daemon thread and return its handle."""
    server = ThreadedServer(application, host=host, port=port)
    server.start()
    return server


class BackgroundServer:
    """Build the app and serve it off the main thread.

    Desktop mode shows a loading window while this bootstrap runs, so GUI
    initialization overlaps interpreter imports, migrations, and server bind.
    """

    def __init__(
        self,
        app_factory: Callable[[], object],
        *,
        host: str,
        port: int,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._app_factory = app_factory
        self._host = host
        self._port = port
        self._on_error = on_error
        self._handle: ThreadedServer | None = None
        self.ready = threading.Event()
        self.error: BaseException | None = None
        self._bootstrap = threading.Thread(
            target=self._run, name="scholartrace-app-bootstrap", daemon=True
        )

    def _run(self) -> None:
        try:
            application = self._app_factory()
            handle = run_server_in_thread(application, host=self._host, port=self._port)
            wait_until_listening(self._host, self._port, timeout_seconds=15.0)
        except BaseException as error:  # surfaced to callers via `error`/`ready`
            self.error = error
            if self._on_error is not None:
                self._on_error(f"应用服务启动失败: {error}")
        else:
            self._handle = handle
        self.ready.set()

    def start(self) -> None:
        self._bootstrap.start()

    def wait_ready(self, *, timeout_seconds: float = 30.0) -> None:
        """Block until the server listens; raise LauncherError on boot failure."""
        if not self.ready.wait(timeout_seconds):
            raise LauncherError(f"application server did not start within {timeout_seconds:g}s")
        if self.error is not None:
            raise LauncherError(f"application server failed to start: {self.error}") from self.error

    def wait_for_exit(self) -> None:
        """Block until the server thread ends (Ctrl+C in browser mode)."""
        handle = self._handle
        if handle is not None and handle.thread.is_alive():
            handle.thread.join()

    def stop(self, *, timeout_seconds: float = 10.0) -> None:
        handle = self._handle
        if handle is not None:
            handle.stop(timeout_seconds=timeout_seconds)
        if self._bootstrap.is_alive():
            self._bootstrap.join(timeout=timeout_seconds)


def build_loading_html(target_url: str, *, max_polls: int = 300) -> str:
    """Inline page shown while the server boots; redirects once /health answers."""
    return f"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>{DEFAULT_WINDOW_TITLE}</title>
<style>
  body {{ margin: 0; display: grid; place-items: center; height: 100vh;
         font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
         background: #f5f6f8; color: #374151; }}
  .box {{ text-align: center; }}
  .ring {{ width: 34px; height: 34px; margin: 0 auto 14px; border-radius: 50%;
          border: 3px solid #d1d5db; border-top-color: #2563eb;
          animation: spin 0.9s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
<div class="box">
  <div class="ring"></div>
  <div id="status">正在启动研迹 ScholarTrace…</div>
</div>
<script>
  const target = {target_url!r};
  let polls = 0;
  function ping() {{
    fetch(target + "health", {{ mode: "no-cors" }})
      .then(() => {{ location.replace(target); }})
      .catch(() => {{
        polls += 1;
        if (polls >= {max_polls}) {{
          document.getElementById("status").textContent =
            "启动超时: 服务未就绪, 关闭窗口后重试, 或改用 --browser 模式。";
          return;
        }}
        setTimeout(ping, 100);
      }});
  }}
  ping();
</script>
</html>"""


WindowOpener = Callable[[str, str], object]


def open_desktop_window(
    url: str,
    *,
    title: str = DEFAULT_WINDOW_TITLE,
    on_close: Callable[[], None] | None = None,
    window_opener: WindowOpener | None = None,
    loading_html: str | None = None,
) -> None:
    """Open the workbench in a native desktop window; block until it closes.

    ``loading_html`` shows immediately while the server boots in the background;
    the page itself redirects to ``url`` once /health responds. pywebview raises
    platform-specific exceptions (for example a missing WebView2 runtime), so
    any failure is normalized to LauncherError with the --browser hint.
    """
    try:
        if window_opener is not None:
            window_opener(url, title)
        else:
            import webview

            if loading_html is None:
                webview.create_window(title, url, width=1440, height=900)
            else:
                webview.create_window(title, html=loading_html, width=1440, height=900)
            webview.start()
    except Exception as error:
        raise LauncherError(
            "desktop window failed to start; retry with --browser to use the default browser"
        ) from error
    finally:
        if on_close is not None:
            on_close()


def open_browser(url: str, *, opener: Callable[[str], bool] | None = None) -> None:
    """Open the default browser at ``url``; raise LauncherError when it refuses."""
    open_url = opener if opener is not None else webbrowser.open
    if not open_url(url):
        raise LauncherError(f"could not open the default browser for {url}")
