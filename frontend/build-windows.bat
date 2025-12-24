@echo off
REM NatLangChain Windows Build Script
REM This builds a standalone Windows executable using Tauri

echo ========================================
echo   NatLangChain Windows Build Script
echo ========================================
echo.

REM Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed.
    echo Install from: https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found

REM Check for Rust
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Rust is not installed.
    echo Install from: https://rustup.rs
    pause
    exit /b 1
)
echo [OK] Rust found
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Install dependencies
echo Installing npm dependencies...
call npm install
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm install failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Build
echo Building NatLangChain for Windows...
echo This may take several minutes on first build.
echo.

call npm run tauri:build

if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build Complete!
echo ========================================
echo.
echo Output files located at:
echo   Portable EXE: src-tauri\target\release\natlangchain.exe
echo   NSIS Installer: src-tauri\target\release\bundle\nsis\
echo   MSI Installer: src-tauri\target\release\bundle\msi\
echo.
echo The portable EXE can be run directly without installation.
echo.
pause
