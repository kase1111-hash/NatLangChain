-- NatLangChain Semantic Search Migration
-- Version: 002
-- Description: Add vector storage for semantic search capabilities

-- Enable pgvector extension (requires installation on the database server)
-- See: https://github.com/pgvector/pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Entry Embeddings Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS entry_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    embedding vector(384),  -- Sentence transformer default dimension
    model_name VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(entry_id, model_name)
);

-- Create HNSW index for fast similarity search
-- Parameters tuned for quality over speed (m=16, ef_construction=64)
CREATE INDEX IF NOT EXISTS idx_entry_embeddings_vector
ON entry_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_entry_embeddings_entry ON entry_embeddings(entry_id);
CREATE INDEX IF NOT EXISTS idx_entry_embeddings_model ON entry_embeddings(model_name);

-- ============================================================================
-- Contract Embeddings Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS contract_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    section VARCHAR(100),  -- 'full', 'terms', 'parties', etc.
    embedding vector(384),
    model_name VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(contract_id, section, model_name)
);

CREATE INDEX IF NOT EXISTS idx_contract_embeddings_vector
ON contract_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_contract_embeddings_contract ON contract_embeddings(contract_id);

-- ============================================================================
-- Semantic Search Functions
-- ============================================================================

-- Function to find similar entries
CREATE OR REPLACE FUNCTION search_similar_entries(
    query_embedding vector(384),
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    entry_id UUID,
    content TEXT,
    author VARCHAR(255),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id as entry_id,
        e.content,
        e.author,
        1 - (ee.embedding <=> query_embedding) as similarity
    FROM entry_embeddings ee
    JOIN entries e ON e.id = ee.entry_id
    WHERE 1 - (ee.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY ee.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar contracts
CREATE OR REPLACE FUNCTION search_similar_contracts(
    query_embedding vector(384),
    limit_count INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
    contract_id UUID,
    title VARCHAR(500),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id as contract_id,
        c.title,
        1 - (ce.embedding <=> query_embedding) as similarity
    FROM contract_embeddings ce
    JOIN contracts c ON c.id = ce.contract_id
    WHERE ce.section = 'full'
      AND 1 - (ce.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Record Migration
-- ============================================================================
INSERT INTO schema_migrations (version, name)
VALUES (2, '002_add_semantic_search')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE entry_embeddings IS 'Vector embeddings for semantic entry search';
COMMENT ON TABLE contract_embeddings IS 'Vector embeddings for semantic contract search';
COMMENT ON FUNCTION search_similar_entries IS 'Find entries similar to a query vector';
COMMENT ON FUNCTION search_similar_contracts IS 'Find contracts similar to a query vector';
