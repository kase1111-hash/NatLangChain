import { writable, get } from 'svelte/store';
import {
  isEncryptionReady,
  encryptData,
  decryptData,
  isEncrypted,
  initializeEncryption,
  clearEncryption
} from './encryption.js';

// Encryption status store
export const encryptionStatus = writable({
  initialized: false,
  available: typeof window !== 'undefined' && !!window.crypto?.subtle
});

/**
 * Initialize storage encryption with a passphrase
 * @param {string} passphrase - Encryption passphrase
 */
export async function initializeStorageEncryption(passphrase) {
  try {
    await initializeEncryption(passphrase);
    encryptionStatus.set({ initialized: true, available: true });
    console.log('Storage encryption initialized');
    return true;
  } catch (error) {
    console.error('Failed to initialize storage encryption:', error);
    encryptionStatus.set({ initialized: false, available: true, error: error.message });
    return false;
  }
}

/**
 * Clear storage encryption
 */
export function clearStorageEncryption() {
  clearEncryption();
  encryptionStatus.set({ initialized: false, available: true });
}

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

/**
 * Create a persistent store with encryption support for sensitive data
 * @param {string} key - localStorage key
 * @param {any} initialValue - Default value
 * @param {boolean} sensitive - If true, will encrypt when encryption is available
 */
function createSecurePersistentStore(key, initialValue, sensitive = false) {
  let storedValue = initialValue;
  let isLoading = true;

  const store = writable(storedValue);

  // Async initialization
  async function initStore() {
    if (typeof window === 'undefined') {
      isLoading = false;
      return;
    }

    try {
      const item = localStorage.getItem(key);
      if (item !== null) {
        // Check if data is encrypted
        if (isEncrypted(item) && isEncryptionReady()) {
          storedValue = await decryptData(item);
        } else if (isEncrypted(item)) {
          // Data is encrypted but encryption not ready - keep initial value
          console.warn(`${key} is encrypted but encryption not initialized`);
        } else {
          storedValue = JSON.parse(item);
        }
        store.set(storedValue);
      }
    } catch (e) {
      console.warn(`Failed to load ${key} from localStorage:`, e);
    }

    isLoading = false;
  }

  // Initialize asynchronously
  initStore();

  // Subscribe to changes and persist to localStorage
  store.subscribe(async (value) => {
    if (typeof window === 'undefined' || isLoading) return;

    try {
      if (sensitive && isEncryptionReady()) {
        // Encrypt sensitive data
        const encrypted = await encryptData(value);
        localStorage.setItem(key, encrypted);
      } else {
        localStorage.setItem(key, JSON.stringify(value));
      }
    } catch (e) {
      console.warn(`Failed to save ${key} to localStorage:`, e);
    }
  });

  // Add a reload method to re-decrypt after encryption is initialized
  store.reload = async function() {
    await initStore();
  };

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

// Secure stores for sensitive data (encrypted when encryption is initialized)
// These stores will automatically encrypt their contents when stored in localStorage

// User wallet connection data (sensitive - contains wallet addresses)
export const walletData = createSecurePersistentStore('natlangchain_wallet', {
  connected: false,
  address: null,
  type: null
}, true);

// User session data (sensitive - may contain tokens)
export const sessionData = createSecurePersistentStore('natlangchain_session', {
  userId: null,
  authenticated: false,
  preferences: {}
}, true);

// Draft entries (sensitive - may contain personal/financial information)
export const draftEntries = createSecurePersistentStore('natlangchain_drafts', [], true);

// Export encryption utilities for components that need direct access
export {
  isEncryptionReady,
  isEncrypted
} from './encryption.js';
