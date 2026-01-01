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

// ============================================================
// Chat Helper Operations (Ollama LLM Assistant)
// ============================================================

export async function getChatStatus() {
  return fetchAPI('/chat/status');
}

export async function sendChatMessage(message, context = {}) {
  return fetchAPI('/chat/message', {
    method: 'POST',
    body: JSON.stringify({ message, context }),
  });
}

export async function getChatSuggestions(content, intent, contractType = '') {
  return fetchAPI('/chat/suggestions', {
    method: 'POST',
    body: JSON.stringify({ content, intent, contract_type: contractType }),
  });
}

export async function getChatQuestions(contractType = '') {
  const params = contractType ? `?contract_type=${contractType}` : '';
  return fetchAPI(`/chat/questions${params}`);
}

export async function explainConcept(concept) {
  return fetchAPI('/chat/explain', {
    method: 'POST',
    body: JSON.stringify({ concept }),
  });
}

export async function getChatHistory() {
  return fetchAPI('/chat/history');
}

export async function clearChatHistory() {
  return fetchAPI('/chat/clear', {
    method: 'POST',
  });
}

// ============================================================
// Boundary Protection Operations
// ============================================================

export async function getBoundaryStatus() {
  return fetchAPI('/boundary/status');
}

export async function getBoundaryStats() {
  return fetchAPI('/boundary/stats');
}

export async function getBoundaryMode() {
  return fetchAPI('/boundary/mode');
}

export async function setBoundaryMode(mode, reason, triggeredBy = null) {
  return fetchAPI('/boundary/mode', {
    method: 'PUT',
    body: JSON.stringify({ mode, reason, triggered_by: triggeredBy }),
  });
}

export async function triggerLockdown(reason) {
  return fetchAPI('/boundary/mode/lockdown', {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export async function getModeHistory(limit = 50) {
  const params = new URLSearchParams({ limit: limit.toString() });
  return fetchAPI(`/boundary/mode/history?${params}`);
}

export async function requestOverride(toMode, reason, requestedBy, validityMinutes = 5) {
  return fetchAPI('/boundary/override/request', {
    method: 'POST',
    body: JSON.stringify({
      to_mode: toMode,
      reason,
      requested_by: requestedBy,
      validity_minutes: validityMinutes,
    }),
  });
}

export async function confirmOverride(requestId, confirmationCode, confirmedBy) {
  return fetchAPI('/boundary/override/confirm', {
    method: 'POST',
    body: JSON.stringify({
      request_id: requestId,
      confirmation_code: confirmationCode,
      confirmed_by: confirmedBy,
    }),
  });
}

export async function checkInput(text, context = 'user_input') {
  return fetchAPI('/boundary/check/input', {
    method: 'POST',
    body: JSON.stringify({ text, context }),
  });
}

export async function checkDocument(content, documentId, source) {
  return fetchAPI('/boundary/check/document', {
    method: 'POST',
    body: JSON.stringify({ content, document_id: documentId, source }),
  });
}

export async function getBoundaryViolations(limit = 100, severity = null) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (severity) params.append('severity', severity);
  return fetchAPI(`/boundary/violations?${params}`);
}

export async function getBoundaryAuditLog(limit = 100, eventType = null) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (eventType) params.append('event_type', eventType);
  return fetchAPI(`/boundary/audit?${params}`);
}

export async function getSiemAlerts(status = null, limit = 100) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (status) params.append('status', status);
  return fetchAPI(`/boundary/siem/alerts?${params}`);
}

export async function acknowledgeSiemAlert(alertId, note = null) {
  return fetchAPI(`/boundary/siem/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  });
}

export async function checkToolAllowed(toolName) {
  return fetchAPI(`/boundary/policy/tool/${toolName}`);
}

export async function checkNetworkAllowed() {
  return fetchAPI('/boundary/policy/network');
}

export async function getEnforcementStatus() {
  return fetchAPI('/boundary/enforcement');
}
