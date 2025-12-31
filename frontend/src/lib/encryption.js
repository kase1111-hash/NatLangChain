/**
 * NatLangChain - Frontend Encryption Utility
 *
 * Provides secure encryption/decryption for localStorage data using
 * the Web Crypto API with AES-GCM encryption.
 *
 * Security Features:
 * - AES-256-GCM for authenticated encryption
 * - PBKDF2 key derivation from passphrase
 * - Random IV for each encryption operation
 * - Secure key storage in sessionStorage (cleared on tab close)
 */

// Constants
const SALT_SIZE = 16; // 128 bits
const IV_SIZE = 12; // 96 bits for GCM
const PBKDF2_ITERATIONS = 600000; // OWASP recommended
const ENCRYPTED_PREFIX = 'ENC:FE:'; // Frontend encrypted data marker

// In-memory encryption key (derived from passphrase)
let derivedKey = null;

/**
 * Convert ArrayBuffer to base64 string
 */
function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Convert base64 string to ArrayBuffer
 */
function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Generate a random encryption key
 * @returns {Promise<string>} Base64-encoded random key
 */
export async function generateEncryptionKey() {
  const key = crypto.getRandomValues(new Uint8Array(32));
  return arrayBufferToBase64(key);
}

/**
 * Derive an encryption key from a passphrase using PBKDF2
 * @param {string} passphrase - User passphrase
 * @param {Uint8Array} salt - Salt for key derivation
 * @returns {Promise<CryptoKey>} Derived AES-GCM key
 */
async function deriveKey(passphrase, salt) {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(passphrase),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt,
      iterations: PBKDF2_ITERATIONS,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Initialize encryption with a passphrase
 * @param {string} passphrase - Encryption passphrase
 */
export async function initializeEncryption(passphrase) {
  if (!passphrase) {
    throw new Error('Passphrase is required');
  }

  // Generate a fixed salt from the passphrase for consistent key derivation
  // This allows the same passphrase to decrypt data across sessions
  const encoder = new TextEncoder();
  const passphraseBytes = encoder.encode(passphrase);
  const hashBuffer = await crypto.subtle.digest('SHA-256', passphraseBytes);
  const salt = new Uint8Array(hashBuffer.slice(0, SALT_SIZE));

  derivedKey = await deriveKey(passphrase, salt);

  // Store a verification token in sessionStorage
  const verificationToken = await encryptData('natlangchain_encryption_active');
  sessionStorage.setItem('nlc_encryption_verified', verificationToken);
}

/**
 * Check if encryption is initialized and ready
 * @returns {boolean} True if encryption is ready
 */
export function isEncryptionReady() {
  return derivedKey !== null;
}

/**
 * Clear the encryption key from memory
 */
export function clearEncryption() {
  derivedKey = null;
  sessionStorage.removeItem('nlc_encryption_verified');
}

/**
 * Check if a string is encrypted data
 * @param {string} data - Data to check
 * @returns {boolean} True if data is encrypted
 */
export function isEncrypted(data) {
  return typeof data === 'string' && data.startsWith(ENCRYPTED_PREFIX);
}

/**
 * Encrypt data using AES-256-GCM
 * @param {any} data - Data to encrypt (string, object, or array)
 * @returns {Promise<string>} Encrypted data string
 */
export async function encryptData(data) {
  if (!derivedKey) {
    throw new Error('Encryption not initialized. Call initializeEncryption first.');
  }

  try {
    // Convert data to string
    const dataStr = typeof data === 'string' ? data : JSON.stringify(data);
    const encoder = new TextEncoder();
    const dataBytes = encoder.encode(dataStr);

    // Generate random IV
    const iv = crypto.getRandomValues(new Uint8Array(IV_SIZE));

    // Encrypt
    const ciphertext = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: iv },
      derivedKey,
      dataBytes
    );

    // Combine IV + ciphertext
    const combined = new Uint8Array(iv.length + ciphertext.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(ciphertext), iv.length);

    return ENCRYPTED_PREFIX + arrayBufferToBase64(combined.buffer);
  } catch (error) {
    console.error('Encryption failed:', error);
    throw new Error('Encryption failed');
  }
}

/**
 * Decrypt AES-256-GCM encrypted data
 * @param {string} encryptedData - Encrypted data string
 * @param {boolean} parseJson - Whether to parse result as JSON
 * @returns {Promise<any>} Decrypted data
 */
export async function decryptData(encryptedData, parseJson = true) {
  if (!derivedKey) {
    throw new Error('Encryption not initialized. Call initializeEncryption first.');
  }

  if (!isEncrypted(encryptedData)) {
    throw new Error('Data is not encrypted');
  }

  try {
    // Remove prefix and decode
    const encoded = encryptedData.slice(ENCRYPTED_PREFIX.length);
    const combined = new Uint8Array(base64ToArrayBuffer(encoded));

    // Extract IV and ciphertext
    const iv = combined.slice(0, IV_SIZE);
    const ciphertext = combined.slice(IV_SIZE);

    // Decrypt
    const plaintext = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: iv },
      derivedKey,
      ciphertext
    );

    const decoder = new TextDecoder();
    const dataStr = decoder.decode(plaintext);

    // Try to parse as JSON if requested
    if (parseJson) {
      try {
        return JSON.parse(dataStr);
      } catch {
        return dataStr;
      }
    }

    return dataStr;
  } catch (error) {
    console.error('Decryption failed:', error);
    throw new Error('Decryption failed - incorrect key or corrupted data');
  }
}

/**
 * Encrypt an object's sensitive fields
 * @param {Object} obj - Object to process
 * @param {string[]} sensitiveFields - Field names to encrypt
 * @returns {Promise<Object>} Object with encrypted fields
 */
export async function encryptSensitiveFields(obj, sensitiveFields = []) {
  if (!obj || typeof obj !== 'object' || !isEncryptionReady()) {
    return obj;
  }

  const defaultSensitiveFields = [
    'wallet_address',
    'private_key',
    'api_key',
    'password',
    'secret',
    'token',
    'credentials',
    'personal_info',
    'financial_data',
  ];

  const fieldsToEncrypt = [...new Set([...defaultSensitiveFields, ...sensitiveFields])];
  const result = { ...obj };

  for (const key of Object.keys(result)) {
    const keyLower = key.toLowerCase();
    const shouldEncrypt = fieldsToEncrypt.some((field) => keyLower.includes(field.toLowerCase()));

    if (shouldEncrypt && result[key] !== null && !isEncrypted(String(result[key]))) {
      try {
        result[key] = await encryptData(result[key]);
      } catch (error) {
        console.warn(`Failed to encrypt field ${key}:`, error);
      }
    }
  }

  return result;
}

/**
 * Decrypt an object's encrypted fields
 * @param {Object} obj - Object to process
 * @returns {Promise<Object>} Object with decrypted fields
 */
export async function decryptSensitiveFields(obj) {
  if (!obj || typeof obj !== 'object' || !isEncryptionReady()) {
    return obj;
  }

  const result = { ...obj };

  for (const key of Object.keys(result)) {
    if (typeof result[key] === 'string' && isEncrypted(result[key])) {
      try {
        result[key] = await decryptData(result[key]);
      } catch (error) {
        console.warn(`Failed to decrypt field ${key}:`, error);
      }
    }
  }

  return result;
}

/**
 * Create an encrypted localStorage wrapper
 * @param {string} key - localStorage key
 * @param {any} defaultValue - Default value if key doesn't exist
 * @returns {Object} Object with get/set methods
 */
export function createEncryptedStorage(key, defaultValue = null) {
  return {
    async get() {
      try {
        const stored = localStorage.getItem(key);
        if (stored === null) {
          return defaultValue;
        }

        if (isEncrypted(stored) && isEncryptionReady()) {
          return await decryptData(stored);
        }

        // Return raw value if not encrypted or encryption not ready
        try {
          return JSON.parse(stored);
        } catch {
          return stored;
        }
      } catch (error) {
        console.warn(`Failed to get encrypted storage ${key}:`, error);
        return defaultValue;
      }
    },

    async set(value) {
      try {
        if (isEncryptionReady()) {
          const encrypted = await encryptData(value);
          localStorage.setItem(key, encrypted);
        } else {
          // Fall back to unencrypted if encryption not initialized
          localStorage.setItem(key, JSON.stringify(value));
        }
      } catch (error) {
        console.error(`Failed to set encrypted storage ${key}:`, error);
        throw error;
      }
    },

    remove() {
      localStorage.removeItem(key);
    },
  };
}

// Export for use in stores.js
export default {
  generateEncryptionKey,
  initializeEncryption,
  isEncryptionReady,
  clearEncryption,
  isEncrypted,
  encryptData,
  decryptData,
  encryptSensitiveFields,
  decryptSensitiveFields,
  createEncryptedStorage,
};
