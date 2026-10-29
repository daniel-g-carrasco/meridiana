@echo off
setlocal
set "MERIDIANA_ROOT=%~dp0.."
set "MERIDIANA_PYTHON=%MERIDIANA_ROOT%\.venv\Scripts\pythonw.exe"
if not exist "%MERIDIANA_PYTHON%" set "MERIDIANA_PYTHON=%MERIDIANA_ROOT%\..\meridiana\.venv\Scripts\pythonw.exe"
if not exist "%MERIDIANA_PYTHON%" (
    echo Ambiente Python di Meridiana non trovato.
    pause
    exit /b 1
)
start "" "%MERIDIANA_PYTHON%" "%~dp0meridiana" %*
endlocal
