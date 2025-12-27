import { writable } from 'svelte/store';

// Helper to create a persistent store that syncs with localStorage
function createPersistentStore(key, initialValue) {
  // Try to get stored value from localStorage
  let storedValue = initialValue;
  if (typeof window !== 'undefined') {
    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        storedValue = JSON.parse(item);
      }
    } catch (e) {
      console.warn(`Failed to load ${key} from localStorage:`, e);
    }
  }

  const store = writable(storedValue);

  // Subscribe to changes and persist to localStorage
  store.subscribe(value => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (e) {
        console.warn(`Failed to save ${key} to localStorage:`, e);
      }
    }
  });

  return store;
}

// Application settings
export const settings = createPersistentStore('natlangchain_settings', {
  debugWindowEnabled: false,
  debugWindowPosition: { x: 20, y: 20 },
  debugWindowSize: { width: 500, height: 400 },
  debugLogLevel: 'info', // 'debug', 'info', 'warn', 'error'
  debugMaxLines: 500,
  theme: 'dark', // Reserved for future use
  animationsEnabled: true,
  compactMode: false
});

// Debug log entries (not persisted - cleared on reload)
export const debugLogs = writable([]);

// Helper function to add a debug log entry
export function addDebugLog(level, category, message, data = null) {
  const entry = {
    id: Date.now() + Math.random(),
    timestamp: new Date().toISOString(),
    level,
    category,
    message,
    data
  };

  debugLogs.update(logs => {
    const newLogs = [...logs, entry];
    // Get current max lines setting
    let maxLines = 500;
    settings.subscribe(s => maxLines = s.debugMaxLines)();
    // Trim to max lines
    if (newLogs.length > maxLines) {
      return newLogs.slice(-maxLines);
    }
    return newLogs;
  });

  // Also log to browser console in dev mode
  const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
  console[consoleMethod](`[${category}] ${message}`, data || '');
}

// Convenience log functions
export const debug = {
  log: (category, message, data) => addDebugLog('debug', category, message, data),
  info: (category, message, data) => addDebugLog('info', category, message, data),
  warn: (category, message, data) => addDebugLog('warn', category, message, data),
  error: (category, message, data) => addDebugLog('error', category, message, data),
  api: (method, url, response) => addDebugLog('info', 'API', `${method} ${url}`, response),
  apiError: (method, url, error) => addDebugLog('error', 'API', `${method} ${url} failed`, error)
};

// Clear all debug logs
export function clearDebugLogs() {
  debugLogs.set([]);
}
