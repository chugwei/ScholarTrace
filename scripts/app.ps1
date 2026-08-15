# Fast application-mode launcher for ScholarTrace.
# Forward extra arguments, e.g. `.\scripts\app.ps1 --browser` or `--port 8010`.
# SCHOLARTRACE_LLM_* variables from the current session are inherited automatically.
# NOTE: keep this file ASCII-only. powershell.exe (5.1) reads BOM-less UTF-8
# scripts as ANSI/GBK and chokes on non-ASCII characters.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "..")

function Invoke-AppMode {
    # Prefer the venv executable directly: no uv resolution, fastest start.
    $candidates = @(
        (Join-Path $PSScriptRoot "..\.venv\Scripts\scholartrace.exe"),
        (Join-Path $PSScriptRoot "..\.venv\bin\scholartrace")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate app @args
            return $LASTEXITCODE
        }
    }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv run --no-sync scholartrace app @args
        if ($LASTEXITCODE -ne 0) {
            # Fall back to a full sync once, e.g. after dependency changes.
            uv run scholartrace app @args
        }
        return $LASTEXITCODE
    }
    Write-Error "No usable Python environment found. Run 'uv sync' first."
    return 1
}

exit (Invoke-AppMode @args)
