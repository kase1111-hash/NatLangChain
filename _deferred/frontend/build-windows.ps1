# NatLangChain Windows Build Script
# This script builds a standalone Windows executable using Tauri
#
# Prerequisites:
# 1. Node.js 18+ (https://nodejs.org)
# 2. Rust (https://rustup.rs)
# 3. Visual Studio Build Tools with C++ AND Windows SDK
# 4. WebView2 Runtime (usually pre-installed on Windows 10/11)

param(
    [switch]$Portable,
    [switch]$Clean,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  NatLangChain Windows Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
function Check-Command {
    param($Command, $Name, $InstallUrl)
    if (!(Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: $Name is not installed." -ForegroundColor Red
        Write-Host "Install from: $InstallUrl" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "[OK] $Name found" -ForegroundColor Green
}

Write-Host "Checking prerequisites..." -ForegroundColor Yellow
Check-Command "node" "Node.js" "https://nodejs.org"
Check-Command "npm" "npm" "https://nodejs.org"
Check-Command "cargo" "Rust/Cargo" "https://rustup.rs"
Write-Host ""

# Setup Visual Studio environment if not already configured
function Setup-VsEnvironment {
    # Check if we already have the Windows SDK in path
    $hasWinSdk = $env:LIB -and ($env:LIB -match "Windows Kits")

    if ($hasWinSdk) {
        Write-Host "[OK] Visual Studio environment detected" -ForegroundColor Green
        return
    }

    Write-Host "Setting up Visual Studio environment..." -ForegroundColor Yellow

    # Try to find and run vcvarsall.bat
    $vsWherePath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"

    if (Test-Path $vsWherePath) {
        $vsPath = & $vsWherePath -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath

        if ($vsPath) {
            $vcvarsall = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"

            if (Test-Path $vcvarsall) {
                Write-Host "  Found: $vcvarsall" -ForegroundColor Gray

                # Run vcvarsall and capture environment
                $cmd = "`"$vcvarsall`" x64 && set"
                $envVars = cmd /c $cmd 2>&1

                foreach ($line in $envVars) {
                    if ($line -match "^([^=]+)=(.*)$") {
                        $name = $matches[1]
                        $value = $matches[2]
                        [Environment]::SetEnvironmentVariable($name, $value, "Process")
                    }
                }

                Write-Host "[OK] Visual Studio environment configured" -ForegroundColor Green
                return
            }
        }
    }

    # Fallback: Try to find Windows SDK directly
    $sdkPaths = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\Lib",
        "${env:ProgramFiles}\Windows Kits\10\Lib"
    )

    foreach ($sdkBase in $sdkPaths) {
        if (Test-Path $sdkBase) {
            $sdkVersions = Get-ChildItem $sdkBase -Directory | Sort-Object Name -Descending
            foreach ($ver in $sdkVersions) {
                $umLib = Join-Path $ver.FullName "um\x64"
                if (Test-Path $umLib) {
                    $ucrtLib = Join-Path $ver.FullName "ucrt\x64"
                    if (Test-Path $ucrtLib) {
                        Write-Host "  Found Windows SDK: $($ver.Name)" -ForegroundColor Gray
                        $env:LIB = "$umLib;$ucrtLib;" + $env:LIB
                        Write-Host "[OK] Windows SDK added to LIB path" -ForegroundColor Green
                        return
                    }
                }
            }
        }
    }

    Write-Host ""
    Write-Host "WARNING: Could not configure Visual Studio environment automatically." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please either:" -ForegroundColor Yellow
    Write-Host "  1. Run this script from 'Developer PowerShell for VS 2022'" -ForegroundColor White
    Write-Host "     (Search for it in Start Menu)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Or install the Windows 10/11 SDK:" -ForegroundColor White
    Write-Host "     - Open Visual Studio Installer" -ForegroundColor Gray
    Write-Host "     - Modify your Build Tools installation" -ForegroundColor Gray
    Write-Host "     - Under 'Individual Components', check:" -ForegroundColor Gray
    Write-Host "       'Windows 10 SDK' or 'Windows 11 SDK'" -ForegroundColor Gray
    Write-Host ""

    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}

Setup-VsEnvironment
Write-Host ""

# Navigate to frontend directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Clean if requested
if ($Clean) {
    Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path "node_modules") { Remove-Item -Recurse -Force "node_modules" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "src-tauri/target") { Remove-Item -Recurse -Force "src-tauri/target" }
    Write-Host "[OK] Cleaned" -ForegroundColor Green
    Write-Host ""
}

# Install dependencies
Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: npm install failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependencies installed" -ForegroundColor Green
Write-Host ""

# Generate icons if needed
if (!(Test-Path "src-tauri/icons/icon.ico")) {
    Write-Host "Note: icon.ico not found. Using placeholder icons." -ForegroundColor Yellow
    Write-Host "For production, generate icons using: npx tauri icon src-tauri/icons/icon.svg" -ForegroundColor Yellow
    Write-Host ""
}

# Development mode
if ($Dev) {
    Write-Host "Starting development mode..." -ForegroundColor Yellow
    npm run tauri:dev
    exit 0
}

# Build
Write-Host "Building NatLangChain for Windows..." -ForegroundColor Yellow
Write-Host "This may take several minutes on first build." -ForegroundColor Gray
Write-Host ""

npm run tauri:build

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Build Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Run from 'Developer PowerShell for VS 2022'" -ForegroundColor White
    Write-Host "  2. Install Windows 10/11 SDK via Visual Studio Installer" -ForegroundColor White
    Write-Host "  3. Run: rustup update" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output files located at:" -ForegroundColor Cyan
Write-Host ""

$OutputDir = "src-tauri/target/release"
$BundleDir = "src-tauri/target/release/bundle"

# Show executable
if (Test-Path "$OutputDir/natlangchain.exe") {
    $ExeSize = (Get-Item "$OutputDir/natlangchain.exe").Length / 1MB
    Write-Host "  Portable EXE: $OutputDir/natlangchain.exe" -ForegroundColor White
    Write-Host "  Size: $([math]::Round($ExeSize, 2)) MB" -ForegroundColor Gray
}

# Show installers
if (Test-Path "$BundleDir/nsis") {
    $NsisFiles = Get-ChildItem "$BundleDir/nsis/*.exe"
    foreach ($file in $NsisFiles) {
        $Size = $file.Length / 1MB
        Write-Host "  NSIS Installer: $($file.FullName)" -ForegroundColor White
        Write-Host "  Size: $([math]::Round($Size, 2)) MB" -ForegroundColor Gray
    }
}

if (Test-Path "$BundleDir/msi") {
    $MsiFiles = Get-ChildItem "$BundleDir/msi/*.msi"
    foreach ($file in $MsiFiles) {
        $Size = $file.Length / 1MB
        Write-Host "  MSI Installer: $($file.FullName)" -ForegroundColor White
        Write-Host "  Size: $([math]::Round($Size, 2)) MB" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "The portable EXE can be run directly without installation." -ForegroundColor Cyan
Write-Host ""
