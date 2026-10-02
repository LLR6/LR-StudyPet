@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if errorlevel 1 goto badpath
if exist "bin\LR-StudyPet\LR-StudyPet.exe" goto native
if not exist "app.py" goto missing
if not exist "assets\pet.png" goto missing
if exist "runtime\python.exe" (
 set "PET_PY=runtime\python.exe"
 goto python
)
if exist ".venv\Scripts\python.exe" (
 set "PET_PY=.venv\Scripts\python.exe"
 goto python
)
where py >nul 2>nul
if errorlevel 1 goto missingruntime
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
set "PET_PY=.venv\Scripts\python.exe"
:python
"%PET_PY%" bootstrap.py %*
if errorlevel 1 goto failed
goto done
:native
"bin\LR-StudyPet\LR-StudyPet.exe" %*
if errorlevel 1 goto failed
goto done
:missing
echo Package files missing. Extract the WHOLE Windows ZIP to a normal folder.
goto failed
:missingruntime
echo The Python runtime is missing. Download the Windows ZIP, not Source ZIP.
echo Alternatively install Python 3.12 or 3.13 with the Python Launcher.
goto failed
:badpath
echo Could not open the launcher folder. Extract the ZIP first.
goto failed
:failed
echo Startup failed. Log: %%LOCALAPPDATA%%\LR-StudyPet\startup.log
pause
exit /b 1
:done
popd
endlocal
