@echo off
REM NatLangChain Standalone Build Script
REM Builds both the Python backend (via PyInstaller) and Tauri frontend with sidecar

setlocal enabledelayedexpansion

echo ============================================================
echo NatLangChain Standalone Build - VERBOSE MODE
echo ============================================================
echo.
echo [INFO] Build started at: %DATE% %TIME%
echo.

REM Setup paths
set "PROJECT_ROOT=%~dp0"
set "SRC_DIR=%PROJECT_ROOT%src"
set "FRONTEND_DIR=%PROJECT_ROOT%frontend"
set "TAURI_DIR=%FRONTEND_DIR%\src-tauri"
set "BINARIES_DIR=%TAURI_DIR%\binaries"

echo [DEBUG] Configuration:
echo [DEBUG]   PROJECT_ROOT  = %PROJECT_ROOT%
echo [DEBUG]   SRC_DIR       = %SRC_DIR%
echo [DEBUG]   FRONTEND_DIR  = %FRONTEND_DIR%
echo [DEBUG]   TAURI_DIR     = %TAURI_DIR%
echo [DEBUG]   BINARIES_DIR  = %BINARIES_DIR%
echo.

REM Verify source directory exists
echo [CHECK] Verifying source directory exists...
if not exist "%SRC_DIR%" (
    echo [ERROR] Source directory not found: %SRC_DIR%
    exit /b 1
)
echo [OK] Source directory found
echo.

REM ============================================================
REM Step 1: Build Python Backend with PyInstaller
REM ============================================================
echo ============================================================
echo [1/4] Building Python Backend...
echo ============================================================
echo.

REM Check Python version
echo [CHECK] Checking Python installation...
python --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    exit /b 1
)
echo [OK] Python found
echo.

REM Check pip
echo [CHECK] Checking pip installation...
pip --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pip is not installed or not in PATH
    exit /b 1
)
echo [OK] pip found
echo.

REM Check for PyInstaller
echo [CHECK] Checking for PyInstaller...
where pyinstaller >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] PyInstaller not found, installing...
    echo [CMD] pip install pyinstaller
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install PyInstaller
        exit /b 1
    )
    echo [OK] PyInstaller installed successfully
) else (
    echo [OK] PyInstaller found
    pyinstaller --version
)
echo.

REM Install core requirements
echo [INFO] Installing core dependencies...
echo [CMD] pip install -r "%PROJECT_ROOT%requirements-core.txt"
pip install -r "%PROJECT_ROOT%requirements-core.txt"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install core dependencies
    echo [ERROR] Exit code: %ERRORLEVEL%
    exit /b 1
)
echo [OK] Core dependencies installed
echo.

REM Verify backend.spec exists
echo [CHECK] Verifying backend.spec exists...
if not exist "%PROJECT_ROOT%backend.spec" (
    echo [ERROR] backend.spec not found at: %PROJECT_ROOT%backend.spec
    exit /b 1
)
echo [OK] backend.spec found
echo.

REM Run PyInstaller
echo [INFO] Running PyInstaller...
echo [CMD] cd /d "%PROJECT_ROOT%"
cd /d "%PROJECT_ROOT%"
echo [DEBUG] Current directory: %CD%
echo.
echo [CMD] pyinstaller --clean --noconfirm backend.spec
echo ------------------------------------------------------------
pyinstaller --clean --noconfirm backend.spec
set PYINSTALLER_EXIT=%ERRORLEVEL%
echo ------------------------------------------------------------
if %PYINSTALLER_EXIT% neq 0 (
    echo [ERROR] PyInstaller failed with exit code: %PYINSTALLER_EXIT%
    exit /b 1
)
echo [OK] PyInstaller completed successfully
echo.

REM Create binaries directory
echo [INFO] Creating binaries directory...
if not exist "%BINARIES_DIR%" (
    echo [CMD] mkdir "%BINARIES_DIR%"
    mkdir "%BINARIES_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create binaries directory
        exit /b 1
    )
    echo [OK] Binaries directory created
) else (
    echo [OK] Binaries directory already exists
)
echo.

REM Copy executable with Tauri naming convention
set "TARGET_TRIPLE=x86_64-pc-windows-msvc"
set "EXE_NAME=natlangchain-backend-%TARGET_TRIPLE%.exe"
set "SOURCE_EXE=%PROJECT_ROOT%dist\natlangchain-backend.exe"
set "DEST_EXE=%BINARIES_DIR%\%EXE_NAME%"

echo [DEBUG] Copy configuration:
echo [DEBUG]   TARGET_TRIPLE = %TARGET_TRIPLE%
echo [DEBUG]   EXE_NAME      = %EXE_NAME%
echo [DEBUG]   SOURCE_EXE    = %SOURCE_EXE%
echo [DEBUG]   DEST_EXE      = %DEST_EXE%
echo.

echo [CHECK] Verifying source executable exists...
if exist "%SOURCE_EXE%" (
    echo [OK] Source executable found
    echo [INFO] File size:
    for %%A in ("%SOURCE_EXE%") do echo [DEBUG]   %SOURCE_EXE% = %%~zA bytes
    echo.
    echo [CMD] copy /Y "%SOURCE_EXE%" "%DEST_EXE%"
    copy /Y "%SOURCE_EXE%" "%DEST_EXE%"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to copy backend executable
        exit /b 1
    )
    echo [OK] Backend executable copied: %EXE_NAME%
) else (
    echo [ERROR] Backend executable not found at: %SOURCE_EXE%
    echo [DEBUG] Listing dist directory contents:
    if exist "%PROJECT_ROOT%dist" (
        dir "%PROJECT_ROOT%dist"
    ) else (
        echo [ERROR] dist directory does not exist
    )
    exit /b 1
)
echo.

REM ============================================================
REM Step 2: Install Frontend Dependencies
REM ============================================================
echo ============================================================
echo [2/4] Installing frontend dependencies...
echo ============================================================
echo.

REM Check Node.js
echo [CHECK] Checking Node.js installation...
node --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    exit /b 1
)
echo [OK] Node.js found
echo.

REM Check npm
echo [CHECK] Checking npm installation...
npm --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not installed or not in PATH
    exit /b 1
)
echo [OK] npm found
echo.

REM Verify frontend directory
echo [CHECK] Verifying frontend directory...
if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found: %FRONTEND_DIR%
    exit /b 1
)
echo [OK] Frontend directory found
echo.

echo [CMD] cd /d "%FRONTEND_DIR%"
cd /d "%FRONTEND_DIR%"
echo [DEBUG] Current directory: %CD%
echo.

echo [CMD] npm install
echo ------------------------------------------------------------
call npm install
set NPM_INSTALL_EXIT=%ERRORLEVEL%
echo ------------------------------------------------------------
if %NPM_INSTALL_EXIT% neq 0 (
    echo [ERROR] npm install failed with exit code: %NPM_INSTALL_EXIT%
    exit /b 1
)
echo [OK] Frontend dependencies installed
echo.

REM ============================================================
REM Step 3: Build Tauri Application
REM ============================================================
echo ============================================================
echo [3/4] Building Tauri application...
echo ============================================================
echo.

REM Check Rust
echo [CHECK] Checking Rust installation...
rustc --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Rust is not installed or not in PATH
    exit /b 1
)
echo [OK] Rust found
echo.

echo [CHECK] Checking Cargo installation...
cargo --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cargo is not installed or not in PATH
    exit /b 1
)
echo [OK] Cargo found
echo.

echo [INFO] Starting Tauri build (this may take several minutes)...
echo [CMD] npm run tauri build
echo ------------------------------------------------------------
call npm run tauri build
set TAURI_BUILD_EXIT=%ERRORLEVEL%
echo ------------------------------------------------------------
if %TAURI_BUILD_EXIT% neq 0 (
    echo [ERROR] Tauri build failed with exit code: %TAURI_BUILD_EXIT%
    echo.
    echo [DEBUG] Common issues:
    echo [DEBUG]   - Missing Visual Studio Build Tools
    echo [DEBUG]   - Missing Windows SDK
    echo [DEBUG]   - Rust toolchain not properly configured
    echo [DEBUG]   - Try running from "Developer Command Prompt for VS 2022"
    exit /b 1
)
echo [OK] Tauri build completed successfully
echo.

REM ============================================================
REM Step 4: Report Results
REM ============================================================
echo ============================================================
echo [4/4] Build Complete!
echo ============================================================
echo.
echo [INFO] Build finished at: %DATE% %TIME%
echo.
echo [INFO] Installers created in:
echo   %TAURI_DIR%\target\release\bundle\nsis\
echo   %TAURI_DIR%\target\release\bundle\msi\
echo.

REM List generated files
echo [DEBUG] Listing generated installer files:
if exist "%TAURI_DIR%\target\release\bundle\nsis" (
    echo [DEBUG] NSIS installers:
    dir /B "%TAURI_DIR%\target\release\bundle\nsis\*.exe" 2>nul
) else (
    echo [WARN] NSIS directory not found
)
if exist "%TAURI_DIR%\target\release\bundle\msi" (
    echo [DEBUG] MSI installers:
    dir /B "%TAURI_DIR%\target\release\bundle\msi\*.msi" 2>nul
) else (
    echo [WARN] MSI directory not found
)
echo.

echo [INFO] The installer includes:
echo   - NatLangChain GUI (Tauri/Svelte)
echo   - Backend server (bundled, starts automatically)
echo.
echo [SUCCESS] No Python installation required on target machine!
echo.

pause
