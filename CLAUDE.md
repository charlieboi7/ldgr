# CLAUDE.md — the LDGR setup playbook

You are setting up LDGR, a personal finance dashboard system, for the user.
The end state: a personalized `~/finance_dashboard.html` built from their real
statement data, a Postgres database feeding it, a daily budget-sync automation,
and a weekly email report. Work through the phases below in order, and read the
matching doc in `docs/` before each phase — the docs are the source of truth on
methodology; this file is the itinerary.

General conduct:

- **Interview before assuming.** Income structure, exclusions, categories, and
  budgets are the user's decisions. Present a proposal, get confirmation.
- **Reconcile after every data change.** Totals must tie out (categories sum to
  total expenses; needs + wants + surplus = net income). Verify with a quick
  script, not by eye, before showing the user.
- **Never commit or echo secrets.** The DB connection string and Gmail app
  password go in env vars / chmod-600 files outside the repo. If the user's
  repo fork is public, warn them before writing any real figures into files
  inside it — the personalized dashboard belongs at `~/finance_dashboard.html`,
  not in the repo.
- One category list rules everything. Whenever categories change, update
  `category_map.json`, `budget_sync.py` CATEGORIES, the dashboard `budgetCats` +
  marker blocks, and `weekly_report.py` DEFAULTS together.

## Phase 0 — Intake interview

Ask (AskUserQuestion works well; batch sensibly):
1. Household shape: single or partner? Kids? Rental income or other side income?
2. Accounts: which checking, credit cards, savings. Which months of statements
   they can download (aim for 5–6 recent months, same window across accounts).
3. Income mechanics: take-home per paycheck, any auto-splits to savings before
   checking, 401(k) contributions and employer match (theirs and partner's),
   gross salaries (for the savings-rate KPI).
4. Exclusions: what should NOT count in monthly averages (common: travel,
   medical, one-time purchases). See `docs/averages-methodology.md`.
5. Optional modules: do they want Net Worth/Growth tabs? If yes, collect the
   inputs listed in `docs/wealth-and-property.md`.
6. Email: which Gmail receives bank alerts (must be the connected one), who gets
   the Friday report.

## Phase 1 — Database (`docs/setup-database.md`)

1. Help them provision Postgres (Ghost CLI or any provider) and export
   `BUDGET_DB`.
2. `psql "$BUDGET_DB" -f sql/schema.sql`
3. `pip3 install psycopg2-binary`. Verify with a trivial connect.

## Phase 2 — Statements → transactions (`docs/statement-ingestion.md`)

1. Get the statement PDFs (local folder or Drive).
2. Parse each into `transactions` rows. Skip card payments and internal
   transfers. Reconcile each statement's parsed total against its own summary
   figure before moving on.
3. Hunt outliers: list each account's largest transactions and confirm them
   against the PDFs (watch for summary lines like "Eligible Purchases: $X"
   parsed as amounts).

## Phase 3 — Categories & averages (`docs/averages-methodology.md`)

1. Group merchants, propose 20–30 categories (fixed vs variable), confirm with
   the user, and write their personalized `category_map.json`.
2. Apply the exclusion list. Compute per-category monthly averages with
   outliers removed; amortize only genuinely recurring bills.
3. Confirm the income conventions (net income = reaches checking; savings rate
   vs gross; 50/30/20 basis) and compute those figures.
4. Show the user the full table; iterate until they sign off.

## Phase 4 — Generate the dashboard

1. Copy `dashboard/finance_dashboard.html` to `~/finance_dashboard.html`.
2. Replace the sample data: the `income`/`savings`/`grossIncome`/
   `savingsBreakdown` consts, the `expenses` array, `peaks`, the growth preset
   buttons/sliders, and (if opted in) the `NW` object. Update the three budget
   marker blocks and `budgetCats` to their categories, with their averages as
   the default suggestions.
3. Sync their confirmed budgets into `budget_goals`, then run
   `budget_sync.py aggregate` once so DB, dashboard, and email agree.
4. Reconcile everything; open the file in a browser together.

## Phase 5 — Skills & automation (`docs/budget-tracking.md`, `docs/automation.md`)

1. Copy `skills/budget-sync/` and `skills/weekly-budget-report/` to
   `~/.claude/skills/`, chmod +x the runners, and edit the runner scripts'
   config lines (BUDGET_DB, BUDGET_START = first of next month, REPORT_SENDER,
   REPORT_TO). Adjust the alert-sender query in the budget-sync SKILL.md to
   their actual banks.
2. Have the user enable per-transaction **email alerts** at every bank/card.
3. Set up the Gmail app password for the weekly report (`.smtp_secret`,
   chmod 600). Preview with `--sample`, then `--dry-run`, then a live send.
4. Run `/budget-sync` once interactively to grant permissions; then install the
   launchd plists (or cron on Linux). Explain the
   `--dangerously-skip-permissions` trade-off before enabling it — this is the
   user's call.

## Phase 6 — Handoff

Tell the user: how to read the meters, how `/budget-sync resolve` works, how to
edit budgets (Budget tab, Tab-to-accept; export/import), where the logs are, and
that adding a new recurring merchant means adding one rule to
`category_map.json`. Suggest a memory/note so future Claude sessions know the
dashboard's conventions and that the marker blocks are machine-owned.
