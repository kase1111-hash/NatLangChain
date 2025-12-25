/**
 * NatLangChain API Client
 * Handles all communication with the Flask backend
 */

// In development, Vite proxies /api to localhost:5000
// In production (Tauri), we need to call the Flask server directly
const isDev = import.meta.env.DEV;
const API_BASE = isDev ? '/api' : 'http://localhost:5000';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || `HTTP error ${response.status}`);
    }

    return data;
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// ============================================================
// Chain Operations
// ============================================================

export async function getChainInfo() {
  return fetchAPI('/chain');
}

export async function getBlock(index) {
  return fetchAPI(`/block/${index}`);
}

export async function getLatestBlock() {
  return fetchAPI('/block/latest');
}

export async function validateChain() {
  return fetchAPI('/validate/chain');
}

// ============================================================
// Entry Operations
// ============================================================

export async function submitEntry(content, author, intent, metadata = {}) {
  return fetchAPI('/entry', {
    method: 'POST',
    body: JSON.stringify({ content, author, intent, metadata }),
  });
}

export async function getPendingEntries() {
  return fetchAPI('/pending');
}

export async function validateEntry(content, intent, author) {
  return fetchAPI('/entry/validate', {
    method: 'POST',
    body: JSON.stringify({ content, intent, author }),
  });
}

// ============================================================
// Mining Operations
// ============================================================

export async function mineBlock(minerId = 'web-miner') {
  return fetchAPI('/mine', {
    method: 'POST',
    body: JSON.stringify({ miner_id: minerId }),
  });
}

// ============================================================
// Search Operations
// ============================================================

export async function searchEntries(query, limit = 10) {
  const params = new URLSearchParams({ intent: query, limit: limit.toString() });
  return fetchAPI(`/entries/search?${params}`);
}

export async function semanticSearch(query, limit = 10) {
  return fetchAPI('/search/semantic', {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  });
}

// ============================================================
// Contract Operations
// ============================================================

export async function parseContract(content) {
  return fetchAPI('/contract/parse', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

export async function findContractMatches(pendingEntries, minerId) {
  return fetchAPI('/contract/match', {
    method: 'POST',
    body: JSON.stringify({ pending_entries: pendingEntries, miner_id: minerId }),
  });
}

export async function getOpenContracts() {
  return fetchAPI('/contract/list');
}

// ============================================================
// Dispute Operations
// ============================================================

export async function getDisputes() {
  return fetchAPI('/dispute/list');
}

export async function createDispute(disputeType, relatedEntries, description, filedBy) {
  return fetchAPI('/dispute/file', {
    method: 'POST',
    body: JSON.stringify({
      dispute_type: disputeType,
      related_entries: relatedEntries,
      description,
      filed_by: filedBy,
    }),
  });
}

// ============================================================
// Oracle Operations
// ============================================================

export async function verifyEvent(condition, intent, event, eventData = {}) {
  return fetchAPI('/oracle/verify', {
    method: 'POST',
    body: JSON.stringify({
      contract_condition: condition,
      contract_intent: intent,
      event_description: event,
      event_data: eventData,
    }),
  });
}

// ============================================================
// Statistics
// ============================================================

export async function getStats() {
  return fetchAPI('/stats');
}
