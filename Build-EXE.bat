@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo 请先运行 Start-Windows.bat 完成初始化。
 pause
 exit /b 1
)
.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name LR-StudyPet --add-data "assets;assets" app.py
if errorlevel 1 goto fail
echo 打包完成：dist\LR-StudyPet\LR-StudyPet.exe
pause
exit /b
:fail
echo 打包失败，请查看上述错误。
pause
