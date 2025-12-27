@echo off
REM NatLangChain Windows Build Script - VERBOSE MODE
REM This builds a standalone Windows executable using Tauri
REM
REM IMPORTANT: If the build fails with "cannot open input file 'dbghelp.lib'"
REM            Run this from "Developer Command Prompt for VS 2022" instead.
REM            (Search for it in the Start Menu)

setlocal enabledelayedexpansion

echo ========================================
echo   NatLangChain Windows Build Script
echo   VERBOSE MODE
echo ========================================
echo.
echo [INFO] Build started at: %DATE% %TIME%
echo [DEBUG] Script location: %~dp0
echo.

REM ============================================================
REM Step 1: Environment Checks
REM ============================================================
echo ============================================================
echo [1/4] Checking build environment...
echo ============================================================
echo.

REM Check for Node.js
echo [CHECK] Checking Node.js installation...
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo [ERROR] Install from: https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found
node --version
echo.

REM Check npm
echo [CHECK] Checking npm installation...
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] npm is not installed or not in PATH
    pause
    exit /b 1
)
echo [OK] npm found
npm --version
echo.

REM Check for Rust
echo [CHECK] Checking Rust installation...
where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Rust is not installed or not in PATH
    echo [ERROR] Install from: https://rustup.rs
    pause
    exit /b 1
)
echo [OK] Rust found
rustc --version
cargo --version
echo.

REM Check for Visual Studio environment
echo [CHECK] Checking Visual Studio environment...
if defined LIB (
    echo [OK] Visual Studio environment already configured
    echo [DEBUG] LIB = %LIB:~0,80%...
) else (
    echo [WARN] Visual Studio environment not detected, searching...
    echo.

    REM Try to find vcvarsall.bat
    set "VCVARS="

    REM VS 2022 paths
    echo [DEBUG] Searching for VS 2022...
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
        echo [DEBUG]   Found: VS 2022 Community
    )
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
        echo [DEBUG]   Found: VS 2022 Professional
    )
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
        echo [DEBUG]   Found: VS 2022 Enterprise
    )
    if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
        echo [DEBUG]   Found: VS 2022 Build Tools
    )

    REM VS 2019 paths
    if not defined VCVARS (
        echo [DEBUG] Searching for VS 2019...
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
            echo [DEBUG]   Found: VS 2019 Community
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat"
            echo [DEBUG]   Found: VS 2019 Professional
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
            echo [DEBUG]   Found: VS 2019 Enterprise
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
            echo [DEBUG]   Found: VS 2019 Build Tools
        )
    )

    if defined VCVARS (
        echo.
        echo [INFO] Configuring Visual Studio environment...
        echo [CMD] call "%VCVARS%"
        call "%VCVARS%" >nul 2>&1
        if %ERRORLEVEL% neq 0 (
            echo [ERROR] Failed to configure Visual Studio environment
            pause
            exit /b 1
        )
        echo [OK] Visual Studio environment configured
    ) else (
        echo.
        echo [ERROR] Could not find Visual Studio environment
        echo.
        echo [DEBUG] Searched locations:
        echo [DEBUG]   - C:\Program Files\Microsoft Visual Studio\2022\*
        echo [DEBUG]   - C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools
        echo [DEBUG]   - C:\Program Files (x86)\Microsoft Visual Studio\2019\*
        echo.
        echo [INFO] Please run this script from "Developer Command Prompt for VS 2022"
        echo [INFO] (Search for it in the Start Menu)
        echo.
        echo [INFO] Or install Visual Studio Build Tools with Windows SDK:
        echo [INFO]   1. Download Visual Studio Build Tools
        echo [INFO]   2. Select "Desktop development with C++"
        echo [INFO]   3. In Individual Components, ensure "Windows 10/11 SDK" is checked
        echo.
        pause
        exit /b 1
    )
)
echo.

REM ============================================================
REM Step 2: Navigate to script directory
REM ============================================================
echo ============================================================
echo [2/4] Setting up build directory...
echo ============================================================
echo.

echo [CMD] cd /d "%~dp0"
cd /d "%~dp0"
echo [DEBUG] Current directory: %CD%
echo.

REM Verify package.json exists
echo [CHECK] Verifying package.json exists...
if not exist "package.json" (
    echo [ERROR] package.json not found in %CD%
    echo [ERROR] Are you running this from the frontend directory?
    pause
    exit /b 1
)
echo [OK] package.json found
echo.

REM Verify src-tauri exists
echo [CHECK] Verifying src-tauri directory exists...
if not exist "src-tauri" (
    echo [ERROR] src-tauri directory not found
    echo [ERROR] Tauri is not properly configured
    pause
    exit /b 1
)
echo [OK] src-tauri directory found
echo.

REM ============================================================
REM Step 3: Install dependencies
REM ============================================================
echo ============================================================
echo [3/4] Installing npm dependencies...
echo ============================================================
echo.

echo [CMD] npm install
echo ------------------------------------------------------------
call npm install
set NPM_EXIT=%ERRORLEVEL%
echo ------------------------------------------------------------
if %NPM_EXIT% neq 0 (
    echo [ERROR] npm install failed with exit code: %NPM_EXIT%
    echo.
    echo [DEBUG] Common issues:
    echo [DEBUG]   - Network connectivity problems
    echo [DEBUG]   - Corrupted npm cache (try: npm cache clean --force)
    echo [DEBUG]   - Permission issues
    pause
    exit /b 1
)
echo [OK] Dependencies installed successfully
echo.

REM List installed Tauri version
echo [DEBUG] Checking Tauri CLI version...
call npx tauri --version 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARN] Could not determine Tauri CLI version
) else (
    echo [OK] Tauri CLI available
)
echo.

REM ============================================================
REM Step 4: Build
REM ============================================================
echo ============================================================
echo [4/4] Building NatLangChain for Windows...
echo ============================================================
echo.
echo [INFO] This may take several minutes on first build.
echo [INFO] Rust dependencies will be compiled.
echo.

echo [CMD] npm run tauri:build
echo ------------------------------------------------------------
call npm run tauri:build
set BUILD_EXIT=%ERRORLEVEL%
echo ------------------------------------------------------------

if %BUILD_EXIT% neq 0 (
    echo.
    echo ========================================
    echo   [ERROR] Build Failed
    echo ========================================
    echo.
    echo [ERROR] Exit code: %BUILD_EXIT%
    echo.
    echo [DEBUG] Common fixes:
    echo [DEBUG]   1. Run from "Developer Command Prompt for VS 2022"
    echo [DEBUG]   2. Install Windows 10/11 SDK via Visual Studio Installer
    echo [DEBUG]   3. Run: rustup update
    echo [DEBUG]   4. Check for missing WebView2 runtime
    echo [DEBUG]   5. Ensure sufficient disk space
    echo.
    echo [DEBUG] For more details, check the error messages above.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   [SUCCESS] Build Complete!
echo ========================================
echo.
echo [INFO] Build finished at: %DATE% %TIME%
echo.

REM Report output files
echo [INFO] Output files located at:
echo.

set "RELEASE_DIR=src-tauri\target\release"
set "BUNDLE_DIR=%RELEASE_DIR%\bundle"

REM Check portable EXE
echo [CHECK] Checking for portable executable...
if exist "%RELEASE_DIR%\natlangchain.exe" (
    echo [OK] Portable EXE: %RELEASE_DIR%\natlangchain.exe
    for %%A in ("%RELEASE_DIR%\natlangchain.exe") do echo [DEBUG]   Size: %%~zA bytes
) else (
    echo [WARN] Portable EXE not found at expected location
)
echo.

REM Check NSIS installer
echo [CHECK] Checking for NSIS installer...
if exist "%BUNDLE_DIR%\nsis" (
    echo [OK] NSIS Installer directory: %BUNDLE_DIR%\nsis\
    echo [DEBUG] Contents:
    dir /B "%BUNDLE_DIR%\nsis\*.exe" 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARN]   No .exe files found in NSIS directory
    )
) else (
    echo [WARN] NSIS directory not found
)
echo.

REM Check MSI installer
echo [CHECK] Checking for MSI installer...
if exist "%BUNDLE_DIR%\msi" (
    echo [OK] MSI Installer directory: %BUNDLE_DIR%\msi\
    echo [DEBUG] Contents:
    dir /B "%BUNDLE_DIR%\msi\*.msi" 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARN]   No .msi files found in MSI directory
    )
) else (
    echo [WARN] MSI directory not found
)
echo.

echo [INFO] The portable EXE can be run directly without installation.
echo.
pause
