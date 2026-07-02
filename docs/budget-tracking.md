# 4 · Daily budget tracking

Once the dashboard exists, the **Budget** tab tracks the current month live:
editable per-category budgets with horizontal meters that fill as transactions
are logged (ice = under, gold = ≥80%, red = OVER).

## The data flow

```
bank/card email alerts ──▶ Claude (budget-sync skill, daily 9 AM)
                             │  extract {date, merchant, amount, card}
                             │  categorize via category_map.json
                             ▼
                        daily_spend table  ──▶ budget_sync.py aggregate
                                                 │  rewrites 3 marker blocks
                                                 ▼
                                          finance_dashboard.html (Budget tab)
```

## The three marker blocks

The dashboard HTML contains three comment-fenced blocks that the helper rewrites
— **never edit them by hand**, and never let any other tool touch the file's
markers:

- `BUDGET_ACTUALS` — the displayed month + per-category month-to-date spend.
- `BUDGET_GOALS` — budgets baked from the `budget_goals` table, so your numbers
  survive a fresh browser or a regenerated file.
- `BUDGET_REVIEW` — the "N transactions need a category" banner.

Budget resolution order in the browser: your localStorage edit → DB-baked
`savedBudgets` → the hardcoded default suggestion. Export/Import buttons move
budgets between browser and JSON; to make them durable, sync them into
`budget_goals` (ask your Claude to do it, or `INSERT ... ON CONFLICT` via psql).

## Needs-review queue

Transactions that match no rule in `category_map.json` — or that hit your
excluded categories — are stored with `needs_review = true`. They're counted
nowhere until resolved. Run `/budget-sync resolve` and Claude walks you through
each one with a category picker, then re-bakes the meters.

## Dedup

Inserts dedup on **date + amount + normalized merchant** (deliberately *not*
card — the same charge can arrive in two alerts labeled "Chase" and "Chase
Rewards Visa" and would otherwise double-count). Re-running ingest over an
overlapping email window is always safe.

## A clean first month

Set `BUDGET_START` (e.g. `2026-08-01`) so pre-launch stragglers in the alert
feed don't pollute your first tracked month: `insert` skips anything earlier,
and `aggregate` won't display an earlier month.

## Category discipline

One category list rules everything. If you add or rename a category, update all
four together (your Claude agent should do this as one operation):
`category_map.json` → `categories`, `budget_sync.py` → `CATEGORIES`, the
dashboard's `budgetCats` + marker blocks, and `weekly_report.py` → `DEFAULTS`.
