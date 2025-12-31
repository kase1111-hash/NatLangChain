@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: NatLangChain Windows Build Script
:: One-click setup and run for NatLangChain
:: ============================================================================

title NatLangChain Build

echo.
echo ============================================================
echo   NatLangChain - One-Click Build Script
echo ============================================================
echo.

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python found: %PYTHON_VERSION%

:: Navigate to script directory
cd /d "%~dp0"
echo [OK] Working directory: %CD%

:: ============================================================================
:: Virtual Environment Setup
:: ============================================================================
echo.
echo [STEP 1/5] Setting up virtual environment...

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate virtual environment
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment activated.

:: ============================================================================
:: Install Dependencies
:: ============================================================================
echo.
echo [STEP 2/5] Installing Python dependencies...

:: Upgrade pip first
python -m pip install --upgrade pip --quiet

:: Install requirements
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo [WARNING] Some packages may have failed. Trying core requirements...
        pip install -r requirements-core.txt --quiet
    )
) else (
    echo [WARNING] requirements.txt not found. Installing from pyproject.toml...
    pip install -e . --quiet
)
echo [OK] Dependencies installed.

:: ============================================================================
:: Environment Configuration
:: ============================================================================
echo.
echo [STEP 3/5] Checking environment configuration...

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Created .env from .env.example
        echo.
        echo ============================================================
        echo   IMPORTANT: Configure your .env file!
        echo ============================================================
        echo   Edit .env and set your ANTHROPIC_API_KEY for LLM features.
        echo   Get your key at: https://console.anthropic.com/
        echo ============================================================
        echo.
    ) else (
        echo [WARNING] No .env.example found. Creating minimal .env...
        echo # NatLangChain Configuration > .env
        echo FLASK_DEBUG=false >> .env
        echo HOST=0.0.0.0 >> .env
        echo PORT=5000 >> .env
    )
) else (
    echo [OK] .env file exists.
)

:: ============================================================================
:: Run Tests (Optional)
:: ============================================================================
echo.
echo [STEP 4/5] Quick validation...

:: Check if pytest is available
python -c "import pytest" 2>nul
if %errorlevel% equ 0 (
    echo Running quick tests...
    python -m pytest tests/test_blockchain.py -v --tb=short -q 2>nul
    if %errorlevel% equ 0 (
        echo [OK] Core tests passed.
    ) else (
        echo [WARNING] Some tests failed. Server may still work.
    )
) else (
    echo [SKIP] pytest not installed. Skipping tests.
)

:: ============================================================================
:: Start Server
:: ============================================================================
echo.
echo [STEP 5/5] Starting NatLangChain API server...
echo.
echo ============================================================
echo   Server starting at http://localhost:5000
echo   Press Ctrl+C to stop the server
echo ============================================================
echo.
echo API Endpoints:
echo   GET  /health         - Health check
echo   GET  /chain          - View blockchain
echo   POST /entry          - Add new entry
echo   POST /mine           - Mine pending entries
echo   POST /search/semantic - Semantic search
echo.
echo ============================================================
echo.

:: Run the API server
python src/api.py

:: Deactivate when done
call venv\Scripts\deactivate.bat 2>nul

pause
