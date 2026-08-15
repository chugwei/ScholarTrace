"""Regression guard: the CLI entry module must stay cheap to import.

Application mode pays the interpreter + import cost before anything renders, so
``scholartrace.cli`` must not pull langgraph/langchain (graph workflows) or the
GUI/webview stack at module import time. Those imports live inside the commands
that need them.
"""

import subprocess
import sys

GUARD_CODE = (
    "import sys, time\n"
    "start = time.perf_counter()\n"
    "import scholartrace.cli\n"
    "elapsed = time.perf_counter() - start\n"
    "assert 'langgraph' not in sys.modules, 'langgraph imported by scholartrace.cli'\n"
    "assert 'langchain_core' not in sys.modules, 'langchain_core imported by scholartrace.cli'\n"
    "assert 'webview' not in sys.modules, 'webview imported by scholartrace.cli'\n"
    "print(f'{elapsed:.3f}')\n"
)


def test_importing_cli_does_not_load_graph_or_gui_stacks() -> None:
    result = subprocess.run(
        [sys.executable, "-c", GUARD_CODE],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    elapsed_seconds = float(result.stdout.strip())
    # Generous ceiling: CI runners can be slow; the local target is ~0.1s.
    assert elapsed_seconds < 3.0, f"scholartrace.cli import took {elapsed_seconds:.3f}s"
