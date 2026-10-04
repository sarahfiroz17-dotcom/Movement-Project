@echo off
:: Sets up the Movement Project backend (Python venv) and frontend (Node/npm).
:: Run this from Command Prompt: setup.bat
:: Or double-click it from File Explorer.

setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
set "BACKEND=%PROJECT_ROOT%backend"
set "FRONTEND=%PROJECT_ROOT%frontend"

echo == Backend: Python venv ==

:: Try Python 3.12 then 3.11 (3.13 has no prebuilt wheels for scikit-learn)
set "PY="
for %%C in (py python3.12 python3.11 python) do (
    if not defined PY (
        where %%C >nul 2>&1
        if !errorlevel! == 0 (
            for /f "tokens=*" %%V in ('%%C --version 2^>^&1') do (
                echo %%V | findstr /R "3\.11 3\.12" >nul
                if !errorlevel! == 0 set "PY=%%C"
            )
        )
    )
)

if not defined PY (
    echo.
    echo ERROR: Python 3.11 or 3.12 not found.
    echo Please install Python 3.12 from https://www.python.org/downloads/
    echo Make sure to tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%V in ('"%PY%" --version 2^>^&1') do echo Using %PY% (%%V)

if exist "%BACKEND%\venv" (
    rmdir /s /q "%BACKEND%\venv"
)

"%PY%" -m venv "%BACKEND%\venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

call "%BACKEND%\venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r "%BACKEND%\requirements.txt"
call "%BACKEND%\venv\Scripts\deactivate.bat"
echo Backend venv ready at %BACKEND%\venv

echo.
echo == Frontend: Node ^& npm ==

where node >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Node.js not found.
    echo Please install Node.js from https://nodejs.org/ (LTS version recommended).
    echo After installing, re-run this script.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%V in ('node -v') do echo Node %%V
for /f "tokens=*" %%V in ('npm -v') do echo npm %%V

cd /d "%FRONTEND%"
npm install
if errorlevel 1 (
    echo ERROR: npm install failed.
    pause
    exit /b 1
)

echo.
echo All set. To run the project, open two separate Command Prompt windows:
echo.
echo   Backend:
echo     cd "%BACKEND%"
echo     venv\Scripts\activate
echo     uvicorn main:app --reload
echo.
echo   Frontend:
echo     cd "%FRONTEND%"
echo     npm run dev
echo.
pause
