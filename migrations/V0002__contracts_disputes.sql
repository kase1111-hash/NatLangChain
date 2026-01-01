-- Contracts and Disputes Schema
-- Migration V0002
-- Adds tables for smart contracts and dispute resolution

-- Contracts table
CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    contract_id VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    parties JSONB NOT NULL DEFAULT '[]',
    terms TEXT NOT NULL,
    parsed_clauses JSONB DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_parties ON contracts USING gin(parties);
CREATE INDEX idx_contracts_created ON contracts(created_at);

-- Contract signatures
CREATE TABLE IF NOT EXISTS contract_signatures (
    id SERIAL PRIMARY KEY,
    contract_id VARCHAR(64) REFERENCES contracts(contract_id) ON DELETE CASCADE,
    party_id VARCHAR(255) NOT NULL,
    signature TEXT NOT NULL,
    signed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verification_method VARCHAR(50),
    metadata JSONB DEFAULT '{}',

    UNIQUE(contract_id, party_id)
);

-- Disputes table
CREATE TABLE IF NOT EXISTS disputes (
    id SERIAL PRIMARY KEY,
    dispute_id VARCHAR(64) NOT NULL UNIQUE,
    contract_id VARCHAR(64) REFERENCES contracts(contract_id),
    complainant_id VARCHAR(255) NOT NULL,
    respondent_id VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    evidence JSONB DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'filed',
    resolution TEXT,
    mediator_id VARCHAR(255),
    filed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_disputes_status ON disputes(status);
CREATE INDEX idx_disputes_contract ON disputes(contract_id);
CREATE INDEX idx_disputes_parties ON disputes(complainant_id, respondent_id);

-- Dispute votes (for community resolution)
CREATE TABLE IF NOT EXISTS dispute_votes (
    id SERIAL PRIMARY KEY,
    dispute_id VARCHAR(64) REFERENCES disputes(dispute_id) ON DELETE CASCADE,
    voter_id VARCHAR(255) NOT NULL,
    vote VARCHAR(50) NOT NULL,
    reasoning TEXT,
    voted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    weight DECIMAL(10, 4) DEFAULT 1.0,

    UNIQUE(dispute_id, voter_id)
);


-- @DOWNGRADE
DROP TABLE IF EXISTS dispute_votes;
DROP TABLE IF EXISTS disputes;
DROP TABLE IF EXISTS contract_signatures;
DROP TABLE IF EXISTS contracts;
