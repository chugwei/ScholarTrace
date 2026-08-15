@echo off
rem Double-click entry: opens the ScholarTrace workbench in a desktop window.
rem Extra arguments are forwarded, e.g. ScholarTrace.bat --browser
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\app.ps1" %*
