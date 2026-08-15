# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the windowed ScholarTrace application executable.
# Build: uv run pyinstaller scripts/app.spec --noconfirm  (see scripts/build-app.ps1)

from pathlib import Path

REPO = Path(SPECPATH).parent
PACKAGE = REPO / "src" / "scholartrace"

a = Analysis(
    [str(PACKAGE / "app_entry.py")],
    pathex=[str(REPO / "src")],
    binaries=[],
    datas=[
        (str(PACKAGE / "static"), "scholartrace/static"),
        (
            str(PACKAGE / "persistence" / "migrations"),
            "scholartrace/persistence/migrations",
        ),
    ],
    hiddenimports=[
        "webview",
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
    ],
    excludes=[
        # Graph-workflow and dev tooling are not reachable from the app entry.
        "langgraph",
        "langchain",
        "langchain_core",
        "langsmith",
        "pytest",
        "ruff",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="ScholarTrace",
    console=False,
    icon=str(PACKAGE / "static" / "icons" / "app.ico"),
    uac_admin=False,
)
