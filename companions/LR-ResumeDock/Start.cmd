@echo off
setlocal
cd /d "%~dp0"
if exist "bin\LR-ResumeDock\LR-ResumeDock.exe" (
 "bin\LR-ResumeDock\LR-ResumeDock.exe" %*
 goto done
)
if not exist ".venv\Scripts\python.exe" (
 py -3 -m venv .venv
 if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe app.py %*
if errorlevel 1 goto fail
:done
exit /b 0
:fail
echo Startup failed. Install Python 3.12 or download the complete Windows package.
pause
exit /b 1
