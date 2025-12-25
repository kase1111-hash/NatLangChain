@echo off
REM NatLangChain Standalone Build Script
REM Builds both the Python backend (via PyInstaller) and Tauri frontend with sidecar

setlocal enabledelayedexpansion

echo ============================================================
echo NatLangChain Standalone Build
echo ============================================================
echo.

set "PROJECT_ROOT=%~dp0"
set "SRC_DIR=%PROJECT_ROOT%src"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "TAURI_DIR=%FRONTEND_DIR%\src-tauri"
set "BINARIES_DIR=%TAURI_DIR%\binaries"

REM Step 1: Build Python Backend with PyInstaller
echo [1/4] Building Python Backend...

REM Check for PyInstaller
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Install core requirements
echo Installing core dependencies...
pip install -r "%PROJECT_ROOT%requirements-core.txt"

REM Run PyInstaller
cd /d "%PROJECT_ROOT%"
pyinstaller --clean --noconfirm backend.spec

REM Create binaries directory
if not exist "%BINARIES_DIR%" mkdir "%BINARIES_DIR%"

REM Copy executable with Tauri naming convention
set "TARGET_TRIPLE=x86_64-pc-windows-msvc"
set "EXE_NAME=natlangchain-backend-%TARGET_TRIPLE%.exe"
set "SOURCE_EXE=%PROJECT_ROOT%dist\natlangchain-backend.exe"
set "DEST_EXE=%BINARIES_DIR%\%EXE_NAME%"

if exist "%SOURCE_EXE%" (
    copy /Y "%SOURCE_EXE%" "%DEST_EXE%"
    echo Backend built: %EXE_NAME%
) else (
    echo ERROR: Backend executable not found
    exit /b 1
)

REM Step 2: Install Frontend Dependencies
echo.
echo [2/4] Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call npm install

REM Step 3: Build Tauri Application
echo.
echo [3/4] Building Tauri application...
call npm run tauri build

REM Step 4: Report Results
echo.
echo ============================================================
echo Build Complete!
echo ============================================================
echo.
echo Installers created in:
echo   %TAURI_DIR%\target\release\bundle\nsis\
echo   %TAURI_DIR%\target\release\bundle\msi\
echo.
echo The installer includes:
echo   - NatLangChain GUI (Tauri/Svelte)
echo   - Backend server (bundled, starts automatically)
echo.
echo No Python installation required on target machine!
echo.

pause
