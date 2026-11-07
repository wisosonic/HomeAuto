@echo off
rem HomeAuto runner: starts backend (FastAPI) and frontend (Vite) in THIS ONE window.
rem Usage:  runner.bat            : mock GPIO (no Raspberry Pi needed), opens the browser
rem         runner.bat nobrowser  : same, without opening the browser
rem Stop with Ctrl+C (answer Y to "Terminate batch job?"), or just close the window.
setlocal
title HomeAuto
set "ROOT=%~dp0"
set "STOPPER=powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\stop-homeauto.ps1""

rem ---- checks
where python >nul 2>nul || (echo [error] Python not found in PATH & exit /b 1)
where node   >nul 2>nul || (echo [error] Node.js not found in PATH & exit /b 1)

rem ---- first-run setup
if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
  echo [setup] creating backend virtual environment...
  python -m venv "%ROOT%backend\.venv" || exit /b 1
  "%ROOT%backend\.venv\Scripts\python.exe" -m pip install -q -r "%ROOT%backend\requirements.txt" || exit /b 1
)
if not exist "%ROOT%frontend\node_modules" (
  echo [setup] installing frontend packages...
  pushd "%ROOT%frontend"
  call npm install || (popd & exit /b 1)
  popd
)

rem ---- free port 8000 if an earlier HomeAuto backend is still running
%STOPPER% || exit /b 1

rem ---- windows has no GPIO: run the backend with mock pins (UI shows Trigger/Clear buttons)
set HOMEAUTO_MOCK=1

echo [start] backend  at http://localhost:8000  (API docs: /docs)
echo [start] frontend at http://localhost:5173
echo [info]  both log into this window. Ctrl+C to stop.
echo.

rem backend: background process sharing this console
start "" /b /d "%ROOT%backend" "%ROOT%backend\.venv\Scripts\python.exe" -m uvicorn homeauto.api:app --reload --port 8000

rem browser: open after a few seconds, from a background helper (no extra window)
if /i not "%~1"=="nobrowser" (
  start "" /b cmd /c "ping -n 5 127.0.0.1 >nul & start http://localhost:5173"
)

rem frontend: foreground, keeps this window busy until you stop it
pushd "%ROOT%frontend"
call npm run dev
popd

rem ---- stopped: make sure the backend goes away too
echo.
echo [stop] shutting down backend...
%STOPPER% >nul
endlocal
