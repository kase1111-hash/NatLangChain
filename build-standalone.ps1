# NatLangChain Standalone Build Script
# Builds both the Python backend (via PyInstaller) and Tauri frontend with sidecar

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NatLangChain Standalone Build" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = $PSScriptRoot
$SrcDir = Join-Path $ProjectRoot "src"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$TauriDir = Join-Path $FrontendDir "src-tauri"
$BinariesDir = Join-Path $TauriDir "binaries"

# Step 1: Build Python Backend with PyInstaller
if (-not $SkipBackend) {
    Write-Host "[1/4] Building Python Backend..." -ForegroundColor Yellow

    # Check for PyInstaller
    $pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
    if (-not $pyinstaller) {
        Write-Host "Installing PyInstaller..." -ForegroundColor Gray
        pip install pyinstaller
    }

    # Install core requirements
    Write-Host "Installing core dependencies..." -ForegroundColor Gray
    pip install -r (Join-Path $ProjectRoot "requirements-core.txt")

    # Run PyInstaller
    Push-Location $ProjectRoot
    try {
        pyinstaller --clean --noconfirm backend.spec

        # Create binaries directory in Tauri
        if (-not (Test-Path $BinariesDir)) {
            New-Item -ItemType Directory -Path $BinariesDir -Force | Out-Null
        }

        # Copy the built executable to Tauri binaries
        # Tauri expects platform-specific naming: name-{target_triple}{.exe}
        $TargetTriple = "x86_64-pc-windows-msvc"
        $ExeName = "natlangchain-backend-$TargetTriple.exe"
        $SourceExe = Join-Path $ProjectRoot "dist" "natlangchain-backend.exe"
        $DestExe = Join-Path $BinariesDir $ExeName

        if (Test-Path $SourceExe) {
            Copy-Item $SourceExe $DestExe -Force
            Write-Host "Backend built: $ExeName" -ForegroundColor Green
        } else {
            Write-Host "ERROR: Backend executable not found at $SourceExe" -ForegroundColor Red
            exit 1
        }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[1/4] Skipping backend build" -ForegroundColor Gray
}

# Step 2: Install Frontend Dependencies
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "[2/4] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        npm install
    } finally {
        Pop-Location
    }
}

# Step 3: Build Tauri Application
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "[3/4] Building Tauri application..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        if ($Debug) {
            npm run tauri build -- --debug
        } else {
            npm run tauri build
        }
    } finally {
        Pop-Location
    }
}

# Step 4: Report Results
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installers created in:" -ForegroundColor White
Write-Host "  $TauriDir\target\release\bundle\nsis\" -ForegroundColor Gray
Write-Host "  $TauriDir\target\release\bundle\msi\" -ForegroundColor Gray
Write-Host ""
Write-Host "The installer includes:" -ForegroundColor White
Write-Host "  - NatLangChain GUI (Tauri/Svelte)" -ForegroundColor Gray
Write-Host "  - Backend server (bundled, starts automatically)" -ForegroundColor Gray
Write-Host ""
Write-Host "No Python installation required on target machine!" -ForegroundColor Green
