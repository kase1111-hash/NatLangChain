# NatLangChain Windows Build Script
# This script builds a standalone Windows executable using Tauri
#
# Prerequisites:
# 1. Node.js 18+ (https://nodejs.org)
# 2. Rust (https://rustup.rs)
# 3. Visual Studio Build Tools with C++ workload
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
    Write-Host "ERROR: Build failed" -ForegroundColor Red
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
