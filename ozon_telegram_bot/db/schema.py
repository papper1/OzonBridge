from __future__ import annotations

from db.session import Database


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS shops (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL,
    poll_interval_seconds INTEGER NOT NULL DEFAULT 180,
    next_poll_at TIMESTAMPTZ NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shop_credentials (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    client_id TEXT NOT NULL,
    api_key TEXT NOT NULL,
    extra_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_shop_credentials_active_provider
ON shop_credentials (shop_id, provider)
WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS shop_channels (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    channel_type TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    target TEXT NOT NULL,
    secret TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS poll_jobs (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retry INTEGER NOT NULL DEFAULT 3,
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ NULL,
    locked_by TEXT NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_poll_jobs_ready
ON poll_jobs (status, next_run_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_poll_jobs_single_active
ON poll_jobs (shop_id, job_type)
WHERE status IN ('queued', 'running');

CREATE TABLE IF NOT EXISTS order_state (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    posting_number TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    last_status TEXT NOT NULL,
    last_notified_status TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(shop_id, posting_number)
);

CREATE INDEX IF NOT EXISTS idx_order_state_shop_updated
ON order_state (shop_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS return_state (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    return_number TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    last_status TEXT NOT NULL,
    last_notified_status TEXT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(shop_id, return_number)
);

CREATE INDEX IF NOT EXISTS idx_return_state_shop_updated
ON return_state (shop_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS notification_log (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    channel_type TEXT NOT NULL,
    event_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS command_log (
    id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT NULL REFERENCES shops(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    command_text TEXT NOT NULL,
    command_type TEXT NOT NULL,
    status TEXT NOT NULL,
    response_summary TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def create_schema(database: Database) -> None:
    with database.connection() as conn:
        conn.execute(SCHEMA_SQL)
        conn.commit()
