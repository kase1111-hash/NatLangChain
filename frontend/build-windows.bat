@echo off
REM NatLangChain Windows Build Script
REM This builds a standalone Windows executable using Tauri
REM
REM IMPORTANT: If the build fails with "cannot open input file 'dbghelp.lib'"
REM            Run this from "Developer Command Prompt for VS 2022" instead.
REM            (Search for it in the Start Menu)

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

REM Check for Visual Studio environment
if defined LIB (
    echo [OK] Visual Studio environment detected
) else (
    echo.
    echo Setting up Visual Studio environment...

    REM Try to find vcvarsall.bat
    set "VCVARS="

    REM VS 2022 paths
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    )

    REM VS 2019 paths
    if not defined VCVARS (
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\VC\Auxiliary\Build\vcvars64.bat"
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
        )
        if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
            set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
        )
    )

    if defined VCVARS (
        echo   Found: %VCVARS%
        call "%VCVARS%" >nul 2>&1
        echo [OK] Visual Studio environment configured
    ) else (
        echo.
        echo WARNING: Could not find Visual Studio environment.
        echo.
        echo Please run this script from "Developer Command Prompt for VS 2022"
        echo ^(Search for it in the Start Menu^)
        echo.
        echo Or install Visual Studio Build Tools with Windows SDK:
        echo   1. Download Visual Studio Build Tools
        echo   2. Select "Desktop development with C++"
        echo   3. In Individual Components, ensure "Windows 10/11 SDK" is checked
        echo.
        pause
        exit /b 1
    )
)
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
    echo.
    echo ========================================
    echo   Build Failed
    echo ========================================
    echo.
    echo Common fixes:
    echo   1. Run from "Developer Command Prompt for VS 2022"
    echo   2. Install Windows 10/11 SDK via Visual Studio Installer
    echo   3. Run: rustup update
    echo.
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
