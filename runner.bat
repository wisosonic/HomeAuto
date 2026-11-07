@echo off
rem HomeAuto runner: starts backend (FastAPI) and frontend (Vite) in two windows.
rem Usage:  runner.bat            : mock GPIO (no Raspberry Pi needed), opens the browser
rem         runner.bat nobrowser  : same, without opening the browser
rem Close the two spawned windows (or press Ctrl+C in them) to stop.
setlocal
set "ROOT=%~dp0"

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

rem ---- windows has no GPIO: run the backend with mock pins (UI shows Trigger/Clear buttons)
set HOMEAUTO_MOCK=1

echo [start] backend  at http://localhost:8000  (API docs: /docs)
start "HomeAuto Backend" /D "%ROOT%backend" cmd /k ".venv\Scripts\python.exe -m uvicorn homeauto.api:app --reload --port 8000"

echo [start] frontend at http://localhost:5173
start "HomeAuto Frontend" /D "%ROOT%frontend" cmd /k "npm run dev"

if /i not "%~1"=="nobrowser" (
  timeout /t 4 /nobreak >nul
  start "" "http://localhost:5173"
)
endlocal
