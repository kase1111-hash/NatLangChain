-- RBAC and API Keys Schema
-- Migration V0003
-- Adds tables for role-based access control

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'readonly',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    use_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_api_keys_role ON api_keys(role);
CREATE INDEX idx_api_keys_enabled ON api_keys(enabled);

-- API Key permissions (additional permissions beyond role)
CREATE TABLE IF NOT EXISTS api_key_permissions (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) REFERENCES api_keys(key_hash) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    granted BOOLEAN NOT NULL DEFAULT TRUE,
    granted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(255),

    UNIQUE(key_hash, permission)
);

-- Audit log for security events
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL,
    actor_key_hash VARCHAR(64),
    actor_ip VARCHAR(45),
    resource VARCHAR(255),
    resource_id VARCHAR(255),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    details JSONB DEFAULT '{}'
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_actor ON audit_log(actor_key_hash);

-- Sessions table (for stateful authentication)
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    key_hash VARCHAR(64) REFERENCES api_keys(key_hash) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sessions_key ON sessions(key_hash);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);


-- @DOWNGRADE
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS api_key_permissions;
DROP TABLE IF EXISTS api_keys;
