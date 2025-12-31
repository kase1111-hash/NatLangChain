@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: NatLangChain Full Build Script (Backend + Frontend)
:: Builds both the Python API and Svelte/Tauri desktop app
:: ============================================================================

title NatLangChain Full Build

echo.
echo ============================================================
echo   NatLangChain - Full Build (Backend + Desktop App)
echo ============================================================
echo.

:: Navigate to script directory
cd /d "%~dp0"

:: ============================================================================
:: Step 1: Build Backend
:: ============================================================================
echo [PHASE 1] Building Python Backend...
echo.

call build.bat
if %errorlevel% neq 0 (
    echo [ERROR] Backend build failed.
    pause
    exit /b 1
)

:: ============================================================================
:: Step 2: Check Frontend Prerequisites
:: ============================================================================
echo.
echo ============================================================
echo [PHASE 2] Building Desktop Application...
echo ============================================================
echo.

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed.
    echo Install from: https://nodejs.org
    echo.
    echo Backend is ready. Run 'build.bat' to start the API server.
    pause
    exit /b 1
)
for /f "tokens=1" %%i in ('node --version') do set NODE_VERSION=%%i
echo [OK] Node.js found: %NODE_VERSION%

:: Check Rust
where rustc >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Rust is not installed.
    echo Install from: https://rustup.rs
    echo.
    echo Backend is ready. Run 'build.bat' to start the API server.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('rustc --version') do set RUST_VERSION=%%i
echo [OK] Rust found: %RUST_VERSION%

:: ============================================================================
:: Step 3: Build Frontend
:: ============================================================================
echo.
echo Installing frontend dependencies...

cd frontend

:: Install npm dependencies
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed.
    cd ..
    pause
    exit /b 1
)
echo [OK] npm dependencies installed.

:: Build Tauri app
echo.
echo Building Tauri desktop application...
echo This may take 5-10 minutes on first build...
echo.

call npm run tauri:build
if %errorlevel% neq 0 (
    echo [ERROR] Tauri build failed.
    echo.
    echo Common fixes:
    echo   1. Install Visual Studio Build Tools with C++ workload
    echo   2. Install WebView2 Runtime
    echo   3. See frontend/WINDOWS-BUILD.md for details
    cd ..
    pause
    exit /b 1
)

cd ..

:: ============================================================================
:: Success
:: ============================================================================
echo.
echo ============================================================
echo   BUILD COMPLETE!
echo ============================================================
echo.
echo Backend:
echo   Run 'build.bat' to start the API server
echo.
echo Desktop App:
echo   EXE: frontend\src-tauri\target\release\natlangchain.exe
echo   Installer: frontend\src-tauri\target\release\bundle\nsis\
echo   MSI: frontend\src-tauri\target\release\bundle\msi\
echo.
echo ============================================================

pause
