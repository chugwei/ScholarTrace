# Build the windowed ScholarTrace application executable (dist/ScholarTrace.exe).
# Requires the dev dependency group (pyinstaller). ASCII-only: powershell.exe
# reads BOM-less UTF-8 scripts as ANSI/GBK.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "..")

uv run pyinstaller scripts/app.spec --noconfirm --distpath dist --workpath build
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
    exit $LASTEXITCODE
}

$exe = Join-Path $PSScriptRoot "..\dist\ScholarTrace.exe"
Write-Host "Built: $exe"
Write-Host "Run it directly; user data lives under %LOCALAPPDATA%\ScholarTrace."
