"""Entry point for the packaged windowed ScholarTrace application.

PyInstaller builds this module into a console-less ``ScholarTrace.exe``. A real
console does not exist there, so stdout/stderr are redirected to a log file
before anything tries to print, user data lives under LOCALAPPDATA, and fatal
start-up errors surface as a native message box instead of vanishing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _default_database() -> Path:
    override = os.environ.get("SCHOLARTRACE_APP_DATABASE")
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ScholarTrace" / "scholartrace.db"


def _alert_failure(log_path: Path | None) -> None:
    detail = f"详情见日志: {log_path}" if log_path is not None else "未生成日志。"
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            f"研迹 ScholarTrace 启动失败。\n{detail}",
            "研迹 ScholarTrace",
            0x10,  # MB_ICONERROR
        )
    else:
        print(f"研迹 ScholarTrace 启动失败。{detail}", file=sys.stderr)


def main() -> int:
    from scholartrace.launcher import ensure_writable_streams

    log_path = ensure_writable_streams()

    from scholartrace.cli import app as cli_app

    exit_code: object = 0
    try:
        cli_app(["app", "--database", str(_default_database())])
    except SystemExit as error:
        exit_code = error.code
    if exit_code not in (0, None):
        _alert_failure(log_path)
    return 0 if exit_code in (0, None) else 1


if __name__ == "__main__":
    raise SystemExit(main())
