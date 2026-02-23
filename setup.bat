@echo off
echo =================================================
echo  Project Setup
echo =================================================
echo.

REM Controlla Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python non trovato! Installa Python 3.10 o superiore da python.org
    pause
    exit /b 1
)

echo Python trovato
echo.

REM Crea virtual environment
echo Creazione virtual environment...
python -m venv venv

REM Attiva venv
call venv\Scripts\activate.bat

REM Installa dipendenze
echo Installazione dipendenze...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Crea .env se non esiste
if not exist .env (
    echo Creazione file .env...
    copy .env.example .env
    echo.
    echo IMPORTANTE: Modifica il file .env con le tue API keys!
    echo    - OPENAI_API_KEY: https://platform.openai.com/api-keys
    echo    - E2B_API_KEY: https://e2b.dev/dashboard
)

REM Crea directory dati
if not exist app\data mkdir app\data
if not exist src\data mkdir src\data

echo.
echo ========================================
echo Setup completato con successo!
echo ========================================
echo.
echo Per avviare l'applicazione:
echo   1. Configura le API keys in .env
echo   2. Esegui: run.bat
echo.
pause
