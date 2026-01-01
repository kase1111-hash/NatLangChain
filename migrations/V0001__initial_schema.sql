-- Initial NatLangChain Schema
-- Migration V0001
-- Creates core tables for blockchain storage

-- Blocks table
CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    block_index INTEGER NOT NULL UNIQUE,
    timestamp TIMESTAMP NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) NOT NULL UNIQUE,
    nonce INTEGER NOT NULL DEFAULT 0,
    proof_of_understanding JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_blocks_hash ON blocks(hash);
CREATE INDEX idx_blocks_timestamp ON blocks(timestamp);

-- Entries table (natural language entries within blocks)
CREATE TABLE IF NOT EXISTS entries (
    id SERIAL PRIMARY KEY,
    block_id INTEGER REFERENCES blocks(id) ON DELETE CASCADE,
    entry_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    intent VARCHAR(100),
    semantic_hash VARCHAR(64),
    signature TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(block_id, entry_index)
);

CREATE INDEX idx_entries_agent ON entries(agent_id);
CREATE INDEX idx_entries_timestamp ON entries(timestamp);
CREATE INDEX idx_entries_intent ON entries(intent);
CREATE INDEX idx_entries_content_trgm ON entries USING gin(content gin_trgm_ops);

-- Pending entries (not yet mined into blocks)
CREATE TABLE IF NOT EXISTS pending_entries (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    intent VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pending_timestamp ON pending_entries(timestamp);

-- Chain metadata
CREATE TABLE IF NOT EXISTS chain_metadata (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- @DOWNGRADE
DROP TABLE IF EXISTS chain_metadata;
DROP TABLE IF EXISTS pending_entries;
DROP TABLE IF EXISTS entries;
DROP TABLE IF EXISTS blocks;
