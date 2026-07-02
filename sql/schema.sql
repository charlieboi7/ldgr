-- LDGR database schema (Postgres)

-- 1) Historical transactions parsed from your statement PDFs.
--    Populated once during setup (and re-run when you add statements).
CREATE TABLE IF NOT EXISTS transactions (
  id          SERIAL PRIMARY KEY,
  date        DATE           NOT NULL,
  description TEXT           NOT NULL,
  amount      NUMERIC(12,2)  NOT NULL,   -- positive = money out (a purchase/charge)
  account     TEXT           NOT NULL,   -- which card/account the statement belongs to
  source_file TEXT,                      -- which statement PDF this row came from (audit trail)
  created_at  TIMESTAMPTZ    DEFAULT now()
);
CREATE INDEX IF NOT EXISTS transactions_date_idx ON transactions (date);

-- 2) Daily transactions ingested from bank email alerts (the budget-sync skill).
CREATE TABLE IF NOT EXISTS daily_spend (
  id           SERIAL PRIMARY KEY,
  txn_date     DATE          NOT NULL,
  description  TEXT          NOT NULL,
  amount       NUMERIC(12,2) NOT NULL,
  card         TEXT,
  category     TEXT          NOT NULL,   -- one of the budget categories, or 'Needs Review'
  needs_review BOOLEAN       DEFAULT FALSE,
  source       TEXT,                     -- 'alert' etc.
  gmail_msg_id TEXT,                     -- provenance of the alert email
  created_at   TIMESTAMPTZ   DEFAULT now()
);
CREATE INDEX IF NOT EXISTS daily_spend_month_idx ON daily_spend (txn_date);

-- 3) Durable per-category budgets (survive browser localStorage; the source of
--    truth shared by the dashboard bake, the weekly email, and the sync skill).
CREATE TABLE IF NOT EXISTS budget_goals (
  category TEXT PRIMARY KEY,
  amount   NUMERIC(12,2) NOT NULL
);
