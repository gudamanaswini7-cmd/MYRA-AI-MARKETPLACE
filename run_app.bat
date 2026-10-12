@echo off
setlocal ENABLEEXTENSIONS
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
	where py >nul 2>nul
	if not errorlevel 1 (
		py -3.12 -m venv .venv
		if errorlevel 1 py -3 -m venv .venv
	) else (
		python -m venv .venv
	)
)

if not exist "%PYTHON_EXE%" (
	echo Could not create the Python environment. Install Python 3.12 or newer.
	pause
	exit /b 1
)

"%PYTHON_EXE%" -c "import flask" >nul 2>nul
if errorlevel 1 (
	"%PYTHON_EXE%" -m pip install --upgrade pip
	"%PYTHON_EXE%" -m pip install -r requirements.txt
	if errorlevel 1 (
		echo Failed to install Python requirements.
		pause
		exit /b 1
	)
)

set "PORT_FILE=%TEMP%\myra-port-%RANDOM%-%RANDOM%.txt"
"%PYTHON_EXE%" -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()" > "%PORT_FILE%"
if errorlevel 1 (
	del /q "%PORT_FILE%" >nul 2>nul
	echo Could not select an available local port.
	pause
	exit /b 1
)
set /p PORT=<"%PORT_FILE%"
del /q "%PORT_FILE%" >nul 2>nul
if not defined PORT (
	echo Could not select an available local port.
	pause
	exit /b 1
)
set "APP_URL=http://127.0.0.1:%PORT%"

cls
echo Starting MYRA app...
echo Using available port %PORT%
echo Opening %APP_URL%

rem Allow the Flask server a moment to start before opening the browser
timeout /t 2 /nobreak >nul
start "" "%APP_URL%"

"%PYTHON_EXE%" -m backend.app