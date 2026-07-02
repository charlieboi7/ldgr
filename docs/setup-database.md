# 1 · Set up the database

LDGR keeps all durable data in a small Postgres database with three tables
(`sql/schema.sql`): `transactions` (parsed statement history), `daily_spend`
(ongoing transactions from bank email alerts), and `budget_goals` (your budgets).

Any Postgres works. Two easy paths:

## Option A — Ghost (what LDGR was built on)

[Ghost](https://ghost.build) is a CLI that provisions hosted Postgres databases
(free tier available, metered compute) — nice because your Claude agent can drive
it entirely from the terminal.

```bash
# install the ghost CLI (see ghost.build for the current install command)
ghost login                      # GitHub OAuth
ghost create my-finances         # provision a database
ghost connect my-finances        # prints the postgresql://... connection string
ghost list                       # see your databases
```

Export the connection string wherever LDGR components run:

```bash
export BUDGET_DB="$(ghost connect my-finances)"
```

Notes:
- The connection string contains a password — treat it like one. Don't commit it,
  don't paste it into issues/chats. It can be rotated from Ghost if leaked.
- Free-tier databases share a compute pool and auto-pause at the limit; LDGR's
  once-a-day usage fits comfortably.

## Option B — any other Postgres

Neon, Supabase, Timescale Cloud, RDS, or a local `brew install postgresql` all
work identically — LDGR only needs a connection string in `BUDGET_DB`.

## Create the schema

```bash
psql "$BUDGET_DB" -f sql/schema.sql
```

macOS note: if `psql` isn't on your PATH, `brew install libpq` puts it at
`/opt/homebrew/opt/libpq/bin/psql`.

## Python driver

The skills use `psycopg2`:

```bash
pip3 install psycopg2-binary
```

## Where the connection string lives

- **Never in the repo or any committed file.** LDGR's scripts read it from the
  `BUDGET_DB` environment variable only.
- For scheduled runs, set it inside your local copies of `run_budget_sync.sh` /
  `run_weekly_report.sh` (which live under `~/.claude/skills/`, outside the repo)
  or in a `chmod 600` env file they source.
