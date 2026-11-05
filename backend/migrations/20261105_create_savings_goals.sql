-- SEA-F-014 / SEA-NF-003: persistent, per-user savings goals.
-- Apply once to the Supabase PostgreSQL database if the table is not created
-- automatically by the application's SQLAlchemy create_all startup routine.

CREATE TABLE IF NOT EXISTS savings_goals (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    target_amount NUMERIC(12, 2) NOT NULL CHECK (target_amount > 0),
    current_amount NUMERIC(12, 2) NOT NULL DEFAULT 0
        CHECK (current_amount >= 0 AND current_amount <= target_amount),
    target_date DATE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_savings_goals_user_id
    ON savings_goals(user_id);