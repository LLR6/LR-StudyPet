@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto run
where py >nul 2>nul
if errorlevel 1 (
  echo 请先安装 Python 3.12 或 3.13，安装时勾选 Add Python to PATH。
  echo https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
:run
.venv\Scripts\python.exe -c "import PySide6" >nul 2>nul
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe app.py
if errorlevel 1 goto fail
exit /b
:fail
echo 启动失败。请保留本窗口的错误内容。
pause
