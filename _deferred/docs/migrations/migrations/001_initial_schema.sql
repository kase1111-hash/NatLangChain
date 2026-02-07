-- NatLangChain Initial Schema Migration
-- Version: 001
-- Description: Create core blockchain tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- Blockchain Entries Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id VARCHAR(64) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    intent VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    signature TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Indexing for common queries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for entries
CREATE INDEX IF NOT EXISTS idx_entries_author ON entries(author);
CREATE INDEX IF NOT EXISTS idx_entries_intent ON entries(intent);
CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_entries_metadata ON entries USING gin(metadata);

-- ============================================================================
-- Blocks Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    block_index INTEGER UNIQUE NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) UNIQUE NOT NULL,
    nonce INTEGER DEFAULT 0,
    difficulty INTEGER DEFAULT 4,

    -- Block metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for blocks
CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index);
CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);
CREATE INDEX IF NOT EXISTS idx_blocks_previous_hash ON blocks(previous_hash);

-- ============================================================================
-- Block Entries Junction Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS block_entries (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,

    UNIQUE(block_id, entry_id),
    UNIQUE(block_id, position)
);

CREATE INDEX IF NOT EXISTS idx_block_entries_block ON block_entries(block_id);
CREATE INDEX IF NOT EXISTS idx_block_entries_entry ON block_entries(entry_id);

-- ============================================================================
-- Validation Results Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS validation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    validator_type VARCHAR(50) NOT NULL,  -- 'pou', 'hybrid', 'rule'
    is_valid BOOLEAN NOT NULL,
    confidence DECIMAL(5, 4),  -- 0.0000 to 1.0000
    reasoning TEXT,
    validator_metadata JSONB DEFAULT '{}'::jsonb,
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_validation_entry ON validation_results(entry_id);
CREATE INDEX IF NOT EXISTS idx_validation_type ON validation_results(validator_type);
CREATE INDEX IF NOT EXISTS idx_validation_valid ON validation_results(is_valid);

-- ============================================================================
-- Chain State Table (for distributed coordination)
-- ============================================================================
CREATE TABLE IF NOT EXISTS chain_state (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- Singleton row
    chain_id VARCHAR(64) NOT NULL,
    last_block_hash VARCHAR(64),
    block_count INTEGER DEFAULT 0,
    entry_count INTEGER DEFAULT 0,
    difficulty INTEGER DEFAULT 4,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial chain state
INSERT INTO chain_state (chain_id, block_count, entry_count)
VALUES (encode(gen_random_bytes(16), 'hex'), 0, 0)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- Contracts Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    parties JSONB DEFAULT '[]'::jsonb,
    terms JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, completed, disputed, cancelled
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_contracts_created_by ON contracts(created_by);
CREATE INDEX IF NOT EXISTS idx_contracts_parties ON contracts USING gin(parties);

-- ============================================================================
-- Disputes Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_id VARCHAR(64) UNIQUE NOT NULL,
    contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL,
    entry_id UUID REFERENCES entries(id) ON DELETE SET NULL,
    claimant VARCHAR(255) NOT NULL,
    respondent VARCHAR(255),
    claim TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',  -- open, under_review, resolved, escalated
    resolution TEXT,
    resolved_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX IF NOT EXISTS idx_disputes_claimant ON disputes(claimant);
CREATE INDEX IF NOT EXISTS idx_disputes_contract ON disputes(contract_id);

-- ============================================================================
-- Audit Log Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- entry, block, contract, dispute
    entity_id VARCHAR(64) NOT NULL,
    actor VARCHAR(255),
    action VARCHAR(50) NOT NULL,  -- create, update, delete, validate
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);

-- ============================================================================
-- Schema Version Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Record this migration
INSERT INTO schema_migrations (version, name)
VALUES (1, '001_initial_schema')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
CREATE TRIGGER update_entries_updated_at
    BEFORE UPDATE ON entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at
    BEFORE UPDATE ON contracts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chain_state_updated_at
    BEFORE UPDATE ON chain_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE entries IS 'Natural language blockchain entries';
COMMENT ON TABLE blocks IS 'Blockchain blocks containing grouped entries';
COMMENT ON TABLE block_entries IS 'Junction table linking blocks to entries';
COMMENT ON TABLE validation_results IS 'LLM and rule-based validation results';
COMMENT ON TABLE chain_state IS 'Singleton table for chain coordination';
COMMENT ON TABLE contracts IS 'Natural language smart contracts';
COMMENT ON TABLE disputes IS 'Dispute resolution records';
COMMENT ON TABLE audit_log IS 'Audit trail for all operations';
COMMENT ON TABLE schema_migrations IS 'Database migration version tracking';
