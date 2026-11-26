@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
set "PY=python"
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
%PY% --version
if errorlevel 1 (
  set "PY=python"
  python --version
  if errorlevel 1 goto fail
)
%PY% build_stamp.py
if not errorlevel 1 goto run
where npm.cmd >nul 2>&1
if errorlevel 1 goto fail
if not exist "node_modules\vite\package.json" (
  call npm.cmd install --no-audit --no-fund
  if errorlevel 1 goto fail
)
call npm.cmd run build
if errorlevel 1 goto fail
%PY% build_stamp.py --write
if errorlevel 1 goto fail
:run
if /i "%~1"=="--check" exit /b 0
%PY% server.py %*
if errorlevel 1 goto fail
exit /b 0
:fail
echo Hakureya could not start. Check Python 3, Node.js and data\hakureya.log.
if /i not "%~1"=="--check" pause
exit /b 1
