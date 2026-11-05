-- SEA-F-015: persistent in-app budget alerts.

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,

    user_id VARCHAR(36) NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    budget_id VARCHAR(36) NULL
        REFERENCES budgets(id)
        ON DELETE CASCADE,

    dedupe_key VARCHAR(255) NOT NULL UNIQUE,

    title VARCHAR(120) NOT NULL,

    message TEXT NOT NULL,

    level VARCHAR(20) NOT NULL
        CHECK (level IN ('warning', 'danger')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    read_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id
    ON notifications(user_id);