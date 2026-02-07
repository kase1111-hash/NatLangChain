-- NatLangChain Scaling Infrastructure Migration
-- Version: 003
-- Description: Add tables for distributed coordination and caching

-- ============================================================================
-- Instance Registry Table (for multi-instance coordination)
-- ============================================================================
CREATE TABLE IF NOT EXISTS instance_registry (
    instance_id VARCHAR(64) PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL,
    is_leader BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_instance_heartbeat ON instance_registry(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_instance_leader ON instance_registry(is_leader) WHERE is_leader = TRUE;

-- ============================================================================
-- Distributed Locks Table (PostgreSQL-based locking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS distributed_locks (
    lock_name VARCHAR(255) PRIMARY KEY,
    owner_id VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_locks_expires ON distributed_locks(expires_at);
CREATE INDEX IF NOT EXISTS idx_locks_owner ON distributed_locks(owner_id);

-- Function to acquire a distributed lock
CREATE OR REPLACE FUNCTION acquire_lock(
    p_lock_name VARCHAR(255),
    p_owner_id VARCHAR(64),
    p_ttl_seconds INTEGER DEFAULT 30
)
RETURNS BOOLEAN AS $$
DECLARE
    v_acquired BOOLEAN := FALSE;
BEGIN
    -- Clean up expired locks
    DELETE FROM distributed_locks WHERE expires_at < CURRENT_TIMESTAMP;

    -- Try to insert new lock
    BEGIN
        INSERT INTO distributed_locks (lock_name, owner_id, expires_at)
        VALUES (p_lock_name, p_owner_id, CURRENT_TIMESTAMP + (p_ttl_seconds || ' seconds')::INTERVAL);
        v_acquired := TRUE;
    EXCEPTION WHEN unique_violation THEN
        -- Lock already exists, check if we own it
        UPDATE distributed_locks
        SET expires_at = CURRENT_TIMESTAMP + (p_ttl_seconds || ' seconds')::INTERVAL
        WHERE lock_name = p_lock_name AND owner_id = p_owner_id;

        IF FOUND THEN
            v_acquired := TRUE;
        END IF;
    END;

    RETURN v_acquired;
END;
$$ LANGUAGE plpgsql;

-- Function to release a distributed lock
CREATE OR REPLACE FUNCTION release_lock(
    p_lock_name VARCHAR(255),
    p_owner_id VARCHAR(64)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_released BOOLEAN := FALSE;
BEGIN
    DELETE FROM distributed_locks
    WHERE lock_name = p_lock_name AND owner_id = p_owner_id;

    IF FOUND THEN
        v_released := TRUE;
    END IF;

    RETURN v_released;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Cache Table (PostgreSQL-based caching for environments without Redis)
-- ============================================================================
CREATE TABLE IF NOT EXISTS cache_entries (
    cache_key VARCHAR(512) PRIMARY KEY,
    cache_value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at) WHERE expires_at IS NOT NULL;

-- Function to get cached value
CREATE OR REPLACE FUNCTION cache_get(p_key VARCHAR(512))
RETURNS JSONB AS $$
DECLARE
    v_value JSONB;
BEGIN
    SELECT cache_value INTO v_value
    FROM cache_entries
    WHERE cache_key = p_key
      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);

    RETURN v_value;
END;
$$ LANGUAGE plpgsql;

-- Function to set cached value
CREATE OR REPLACE FUNCTION cache_set(
    p_key VARCHAR(512),
    p_value JSONB,
    p_ttl_seconds INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO cache_entries (cache_key, cache_value, expires_at)
    VALUES (
        p_key,
        p_value,
        CASE WHEN p_ttl_seconds IS NOT NULL
             THEN CURRENT_TIMESTAMP + (p_ttl_seconds || ' seconds')::INTERVAL
             ELSE NULL
        END
    )
    ON CONFLICT (cache_key) DO UPDATE
    SET cache_value = EXCLUDED.cache_value,
        expires_at = EXCLUDED.expires_at,
        created_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Function to delete cached value
CREATE OR REPLACE FUNCTION cache_delete(p_key VARCHAR(512))
RETURNS BOOLEAN AS $$
BEGIN
    DELETE FROM cache_entries WHERE cache_key = p_key;
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Metrics Snapshots Table (for historical metrics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id BIGSERIAL PRIMARY KEY,
    instance_id VARCHAR(64),
    metric_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(20) NOT NULL,  -- counter, gauge, histogram
    metric_value DOUBLE PRECISION NOT NULL,
    labels JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Partition by time for efficient cleanup
CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON metrics_snapshots(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics_snapshots(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_instance ON metrics_snapshots(instance_id);

-- ============================================================================
-- Scheduled Jobs Table (for background tasks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name VARCHAR(255) NOT NULL,
    job_type VARCHAR(100) NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed
    priority INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    locked_by VARCHAR(64),
    locked_until TIMESTAMP WITH TIME ZONE,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON scheduled_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON scheduled_jobs(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_jobs_locked ON scheduled_jobs(locked_until) WHERE locked_by IS NOT NULL;

-- Function to claim a job
CREATE OR REPLACE FUNCTION claim_job(
    p_worker_id VARCHAR(64),
    p_job_types VARCHAR(100)[] DEFAULT NULL,
    p_lock_seconds INTEGER DEFAULT 300
)
RETURNS UUID AS $$
DECLARE
    v_job_id UUID;
BEGIN
    UPDATE scheduled_jobs
    SET status = 'running',
        started_at = CURRENT_TIMESTAMP,
        locked_by = p_worker_id,
        locked_until = CURRENT_TIMESTAMP + (p_lock_seconds || ' seconds')::INTERVAL
    WHERE id = (
        SELECT id FROM scheduled_jobs
        WHERE status = 'pending'
          AND scheduled_for <= CURRENT_TIMESTAMP
          AND (p_job_types IS NULL OR job_type = ANY(p_job_types))
          AND (locked_by IS NULL OR locked_until < CURRENT_TIMESTAMP)
        ORDER BY priority DESC, scheduled_for ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id INTO v_job_id;

    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Cleanup Functions
-- ============================================================================

-- Function to clean up expired data
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS TABLE (
    table_name TEXT,
    rows_deleted BIGINT
) AS $$
DECLARE
    v_count BIGINT;
BEGIN
    -- Clean expired locks
    DELETE FROM distributed_locks WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    table_name := 'distributed_locks';
    rows_deleted := v_count;
    RETURN NEXT;

    -- Clean expired cache
    DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    table_name := 'cache_entries';
    rows_deleted := v_count;
    RETURN NEXT;

    -- Clean old metrics (keep 7 days)
    DELETE FROM metrics_snapshots WHERE recorded_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    GET DIAGNOSTICS v_count = ROW_COUNT;
    table_name := 'metrics_snapshots';
    rows_deleted := v_count;
    RETURN NEXT;

    -- Clean stale instances (no heartbeat in 5 minutes)
    DELETE FROM instance_registry WHERE last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '5 minutes';
    GET DIAGNOSTICS v_count = ROW_COUNT;
    table_name := 'instance_registry';
    rows_deleted := v_count;
    RETURN NEXT;

    -- Clean old completed/failed jobs (keep 7 days)
    DELETE FROM scheduled_jobs
    WHERE status IN ('completed', 'failed')
      AND completed_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    GET DIAGNOSTICS v_count = ROW_COUNT;
    table_name := 'scheduled_jobs';
    rows_deleted := v_count;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Record Migration
-- ============================================================================
INSERT INTO schema_migrations (version, name)
VALUES (3, '003_add_scaling_tables')
ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE instance_registry IS 'Registry of active API instances for coordination';
COMMENT ON TABLE distributed_locks IS 'PostgreSQL-based distributed locks';
COMMENT ON TABLE cache_entries IS 'PostgreSQL-based cache for environments without Redis';
COMMENT ON TABLE metrics_snapshots IS 'Historical metrics data for analysis';
COMMENT ON TABLE scheduled_jobs IS 'Background job queue';
COMMENT ON FUNCTION acquire_lock IS 'Acquire a distributed lock with TTL';
COMMENT ON FUNCTION release_lock IS 'Release a distributed lock';
COMMENT ON FUNCTION claim_job IS 'Claim a pending job for processing';
COMMENT ON FUNCTION cleanup_expired_data IS 'Clean up expired locks, cache, metrics, and jobs';
