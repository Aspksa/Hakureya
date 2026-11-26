@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto fail
set "PYTHONUTF8=1"
set "PY=python"
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
%PY% --version
if errorlevel 1 goto fail
if exist "dist\index.html" goto run
where npm.cmd >nul 2>&1
if errorlevel 1 goto fail
call npm.cmd install --no-audit --no-fund
if errorlevel 1 goto fail
call npm.cmd run build
if errorlevel 1 goto fail
:run
%PY% server.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Hakureya could not start. Check Python 3 and Node.js installation.
pause
exit /b 1
