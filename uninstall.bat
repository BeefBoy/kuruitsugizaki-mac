@echo off
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo .venv is missing; run setup.bat first or delete this folder by hand ^(INSTALL.md, To undo the setup^).
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\uninstall.py" %*
echo.
pause
