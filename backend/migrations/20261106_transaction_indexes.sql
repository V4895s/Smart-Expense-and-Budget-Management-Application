-- SEA-NF-001: composite indexes for per-user transaction list, filter and report queries.
-- Safe to re-run. Run in the Supabase SQL editor.
CREATE INDEX IF NOT EXISTS ix_transactions_user_date
    ON transactions (user_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_user_type_date
    ON transactions (user_id, type, transaction_date DESC);
CREATE INDEX IF NOT EXISTS ix_transactions_user_category
    ON transactions (user_id, category_id);
