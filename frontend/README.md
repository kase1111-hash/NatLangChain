# NatLangChain Frontend

Desktop and web interface for NatLangChain, built with Svelte and Tauri.

## Tech Stack

- **Svelte 4** - Reactive UI framework
- **Vite 5** - Build tool and dev server
- **Tauri 1.6** - Desktop application wrapper (Rust-based)

## Prerequisites

- Node.js 18+
- npm or pnpm
- Rust (for Tauri desktop builds)

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (web only)
npm run dev

# Start Tauri development (desktop app)
npm run tauri:dev
```

The web app runs at `http://localhost:3000` and proxies API requests to the backend at `http://localhost:5000`.

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run tauri:dev` | Start Tauri desktop app in dev mode |
| `npm run tauri:build` | Build desktop application |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Run ESLint with auto-fix |
| `npm run format` | Format code with Prettier |
| `npm run format:check` | Check formatting |

## Project Structure

```
frontend/
├── src/
│   ├── App.svelte          # Main application component
│   ├── main.js             # Entry point
│   ├── components/         # Svelte components
│   │   ├── Dashboard.svelte
│   │   ├── ChainExplorer.svelte
│   │   ├── EntryForm.svelte
│   │   ├── ContractViewer.svelte
│   │   ├── SearchPanel.svelte
│   │   ├── ChatHelper.svelte
│   │   ├── Settings.svelte
│   │   └── ...
│   └── lib/                # Utilities and stores
│       ├── api.js          # Backend API client
│       ├── stores.js       # Svelte stores
│       └── ...
├── src-tauri/              # Tauri (Rust) configuration
│   ├── tauri.conf.json     # Tauri config
│   └── src/                # Rust source (if customized)
├── index.html              # HTML entry point
├── vite.config.js          # Vite configuration
└── package.json
```

## Components

| Component | Purpose |
|-----------|---------|
| `Dashboard` | Overview with blockchain stats |
| `ChainExplorer` | Browse blockchain entries and blocks |
| `EntryForm` | Submit new natural language entries |
| `ContractViewer` | View and manage contracts |
| `SearchPanel` | Semantic search across entries |
| `ChatHelper` | AI-powered assistance |
| `Settings` | Application configuration |
| `DebugWindow` | Development debugging tools |

## Backend Connection

The frontend connects to the NatLangChain API backend. Configure the connection in `src/lib/api.js`:

```javascript
const API_BASE = 'http://localhost:5000';
```

For production, update this to your deployed backend URL.

## Desktop Builds

### Windows
```bash
npm run tauri:build:windows
```

See [WINDOWS-BUILD.md](./WINDOWS-BUILD.md) for detailed Windows build instructions.

### macOS / Linux
```bash
npm run tauri:build
```

Build outputs are in `src-tauri/target/release/`.

## Code Quality

```bash
# Lint JavaScript and Svelte files
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Format all source files
npm run format

# Check formatting (CI)
npm run format:check
```

## Development Notes

- Hot reload works for both web and Tauri dev modes
- The API proxy in `vite.config.js` forwards `/api/*` to the backend
- Stores in `lib/stores.js` manage global application state
- Debug mode can be enabled in Settings for development logging
