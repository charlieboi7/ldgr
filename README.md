# LDGR

**A local-first household finance dashboard, built and maintained for you by a
Claude agent.** Your statements go into a small Postgres database, a single
self-contained HTML file becomes your dashboard, bank alert emails keep the
budget meters current every day, and a Budget Brief email lands every Friday.

No SaaS, no account aggregators, no analytics — your financial data lives in
your database and one HTML file on your machine.

## What you get

- **`finance_dashboard.html`** — one file, zero external dependencies (all
  charts are pure CSS/SVG, deliberately, so financial data never leaves the
  file). Seven tabs:
  - **Overview** — income → expenses → surplus flow, category bars, needs/wants donut
  - **Optimize** — toggle/drag categories and watch the what-if surplus recompute
  - **Misc** — the spiky one-off bucket, explained instead of hidden
  - **50/30/20** — needs/wants/savings vs targets, with honest basis toggles
  - **Growth** — compound-growth explorer for your savings rate
  - **Net Worth** — assets/liabilities, home equity, amortizing projection *(optional)*
  - **Budget** — live month-to-date meters, fed automatically every morning
- **budget-sync skill** — daily headless Claude run: reads your banks' transaction
  alert emails, categorizes, dedups, logs to Postgres, re-bakes the meters, and
  flags anything ambiguous for one-tap review.
- **weekly-budget-report skill** — Friday email with pacing, watch list, top
  categories, and every meter. Pure Python; no LLM in the loop.

## Quick start (the intended way)

1. Install [Claude Code](https://claude.com/claude-code) and connect its Gmail
   integration to the inbox that will receive your bank alerts.
2. Clone this repo and open Claude Code in it.
3. Say:

   > Read CLAUDE.md and set up LDGR for me.

   The agent interviews you (income, accounts, what to exclude), walks you
   through database setup and statement parsing, computes your real averages,
   generates your personalized dashboard from the template, and schedules the
   daily/weekly automations.

Prefer doing it by hand? The docs walk through the same steps:

1. [Set up the database](docs/setup-database.md)
2. [Ingest your statements](docs/statement-ingestion.md)
3. [How the averages are computed](docs/averages-methodology.md) ← read this one regardless
4. [Daily budget tracking](docs/budget-tracking.md)
5. [Wealth & property (optional)](docs/wealth-and-property.md)
6. [Automation](docs/automation.md)

## Repo layout

```
CLAUDE.md                     the agent playbook — how Claude sets everything up
dashboard/finance_dashboard.html   the dashboard template (sample data; yours replaces it)
docs/                         step-by-step guides (also the agent's reference)
skills/budget-sync/           daily ingest skill (SKILL.md + helper + category map)
skills/weekly-budget-report/  Friday email skill (SKILL.md + report script)
sql/schema.sql                the three tables
automation/                   launchd templates for the schedules
```

The dashboard in this repo is populated with a **fictional sample household**
so you can open it in a browser right now and click around.

## Security & privacy notes

- Nothing in this repo phones home. The only outbound calls are the ones you
  configure: your Postgres connection and Gmail SMTP.
- Secrets (DB connection string, Gmail app password) live in environment
  variables and a `chmod 600` file outside the repo — never commit them.
  `.gitignore` guards the obvious ones.
- The daily sync runs headless Claude with `--dangerously-skip-permissions`.
  That's a real trade-off; read [docs/automation.md](docs/automation.md) before
  enabling it.
- If you fork this and bake in your own numbers, **keep your fork private** —
  your dashboard file will contain your entire financial life.

## License

MIT — see [LICENSE](LICENSE).
