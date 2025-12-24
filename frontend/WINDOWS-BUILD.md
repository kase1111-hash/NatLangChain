# NatLangChain Windows Installer Build Guide

This guide explains how to build a standalone Windows executable for NatLangChain.

## Output Options

The build process creates:

1. **Portable EXE** (`natlangchain.exe`) - Single standalone executable, ~5-10 MB
2. **NSIS Installer** (`.exe`) - Traditional Windows installer with Start Menu shortcuts
3. **MSI Installer** (`.msi`) - Enterprise-friendly installer for group policy deployment

## Prerequisites

### 1. Node.js (v18 or later)
Download from: https://nodejs.org

### 2. Rust
Install via rustup: https://rustup.rs

```powershell
# Run in PowerShell
winget install Rustlang.Rustup
# Or download installer from https://rustup.rs
```

### 3. Visual Studio Build Tools
Required for compiling native code:

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

During installation, select:
- "Desktop development with C++"
- Windows 10/11 SDK

### 4. WebView2 Runtime
Usually pre-installed on Windows 10/11. If needed:
https://developer.microsoft.com/en-us/microsoft-edge/webview2/

## Build Instructions

### Quick Build (Recommended)

**PowerShell:**
```powershell
cd frontend
.\build-windows.ps1
```

**Command Prompt:**
```cmd
cd frontend
build-windows.bat
```

### Manual Build

```powershell
cd frontend

# Install dependencies
npm install

# Build for Windows
npm run tauri:build
```

### Development Mode

To run the app in development mode with hot reload:

```powershell
cd frontend
npm install
npm run tauri:dev
```

## Build Output

After a successful build, files are located at:

```
frontend/
└── src-tauri/
    └── target/
        └── release/
            ├── natlangchain.exe          # Portable executable
            └── bundle/
                ├── nsis/
                │   └── NatLangChain_1.0.0_x64-setup.exe
                └── msi/
                    └── NatLangChain_1.0.0_x64_en-US.msi
```

## Distribution

### Portable EXE
- Copy `natlangchain.exe` anywhere
- No installation required
- Runs directly with double-click
- Best for: USB drives, quick testing, users without admin rights

### NSIS Installer
- Traditional "Next > Next > Finish" installer
- Creates Start Menu and Desktop shortcuts
- Includes uninstaller
- Best for: General distribution to end users

### MSI Installer
- Windows Installer package
- Supports silent installation: `msiexec /i NatLangChain.msi /quiet`
- Best for: Enterprise deployment, SCCM/Intune

## Customization

### Application Icon

Replace the icon by:

1. Create a 1024x1024 PNG icon
2. Run: `npx tauri icon path/to/your/icon.png`
3. Rebuild the application

### Backend Connection

By default, the app connects to a local backend at `http://localhost:5000`.

To change this, modify `frontend/src/lib/api.js`:

```javascript
const API_BASE = 'http://your-server:5000';
```

## Troubleshooting

### Build fails with "LINK : fatal error"
Install Visual Studio Build Tools with C++ workload.

### "WebView2 not found" error
Install WebView2 Runtime from Microsoft.

### Build is very slow
First build compiles Rust dependencies (~5-10 min). Subsequent builds are faster (~1 min).

### Antivirus blocks the executable
Some antivirus software flags new executables. Add an exception or sign the executable with a code signing certificate.

## Code Signing (Optional)

For production distribution, sign your executables:

1. Obtain a code signing certificate
2. Update `src-tauri/tauri.conf.json`:
   ```json
   "windows": {
     "certificateThumbprint": "YOUR_CERT_THUMBPRINT",
     "timestampUrl": "http://timestamp.digicert.com"
   }
   ```
3. Rebuild the application

## System Requirements

**Minimum:**
- Windows 10 (version 1803+) or Windows 11
- 4 GB RAM
- 100 MB disk space

**Recommended:**
- Windows 10/11 (latest)
- 8 GB RAM
- SSD storage
