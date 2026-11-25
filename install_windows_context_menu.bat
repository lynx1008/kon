@echo off
setlocal
set "APP_DIR=%~dp0"
set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"
set "APP=%APP_DIR%desktop_app.py"
if not exist "%PYTHON%" (
  echo Cannot find the project virtual environment: %PYTHON%
  pause
  exit /b 1
)
reg add "HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\コン\command" /ve /d "^"%PYTHON%^" ^"%APP%^" ^"%%1^"" /f >nul
echo コン has been added to the PDF right-click menu.
pause
