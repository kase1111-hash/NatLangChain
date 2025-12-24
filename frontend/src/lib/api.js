/**
 * NatLangChain API Client
 * Handles all communication with the Flask backend
 */

const API_BASE = '/api';

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
  return fetchAPI('/chain/validate');
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
  return fetchAPI('/entries/pending');
}

export async function validateEntry(content, intent, author) {
  return fetchAPI('/validate', {
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
  return fetchAPI('/search', {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  });
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
  return fetchAPI('/contracts/open');
}

// ============================================================
// Dispute Operations
// ============================================================

export async function getDisputes() {
  return fetchAPI('/disputes');
}

export async function createDispute(disputeType, relatedEntries, description, filedBy) {
  return fetchAPI('/dispute', {
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
