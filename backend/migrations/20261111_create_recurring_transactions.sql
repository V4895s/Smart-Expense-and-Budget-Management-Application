-- SEA-F-016: recurring income and expenses.
-- Apply once to Supabase if the table is not created automatically by create_all on startup.

CREATE TABLE IF NOT EXISTS recurring_transactions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(10) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    category_id VARCHAR(36) NOT NULL REFERENCES categories(id),
    description VARCHAR(200) NOT NULL DEFAULT '',
    frequency VARCHAR(10) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    next_run_date DATE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_recurring_user_id ON recurring_transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_recurring_next_run ON recurring_transactions(next_run_date);
