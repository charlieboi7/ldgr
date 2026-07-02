---
name: budget-sync
description: Sync daily bank/card transactions into the LDGR budget dashboard. Use when the user runs /budget-sync, or daily via a scheduler, to read transaction-alert emails, log them to the daily_spend DB table, and re-bake the dashboard meters. Two modes - "ingest" (default, automated) and "resolve" (interactive, clear the needs-review queue).
---

# budget-sync

Keeps the **Budget** tab of the LDGR dashboard current. The deterministic DB + file work is done by the helper `budget_sync.py` in this skill's directory — your job is the reading/extraction/categorization and the interactive review.

Helper dir: `~/.claude/skills/budget-sync/`. Run helper with `python3 ~/.claude/skills/budget-sync/budget_sync.py <cmd>`. The helper needs `BUDGET_DB` (Postgres connection string) in the environment; `BUDGET_DASH` points at the dashboard HTML if it isn't at `~/finance_dashboard.html`.

## Mode
- Args contain **`resolve`** → run **RESOLVE**.
- Otherwise → run **INGEST**.

## INGEST (automated, default — used by the daily 9 AM scheduled run)

1. **Find new emails** in the connected Gmail inbox. Use Gmail `search_threads`, then `get_thread` (FULL_CONTENT) for matches:
   - Bank/card alerts: `(from:chase.com OR from:americanexpress.com OR from:capitalone.com OR from:citi.com OR from:citibank.com OR from:discover.com OR from:bankofamerica.com OR from:wellsfargo.com) newer_than:2d -in:sent`
   - Adjust the sender list to the user's actual banks (see SETUP.md).
   (Use a 2-day window; dedup makes overlap safe. Skip anything clearly not a transaction — statements-ready notices, balance summaries, marketing.)

2. **Extract** one record per transaction from the alert bodies:
   `{ "date":"YYYY-MM-DD", "description":"<merchant>", "amount":<number>, "card":"<card/account>", "source":"alert", "gmail_msg_id":"<message id>" }`
   - `amount` = the purchase amount (positive). `card` = which card — infer from sender/body, and **use a consistent short label per card** (dedup ignores card, but consistency keeps reports clean).
   - If a date isn't shown, use the email date.

3. **Categorize** with `category_map.json` (load it). Uppercase the description and match against the `rules` substrings (most specific first). On a match, set `"category"` to that value. **No match, or the merchant is one of the user's excluded types (see the map's `note`) → set `"category":"NEEDS_REVIEW"`.**

4. **Insert** — write the records to a temp file and run:
   `python3 ~/.claude/skills/budget-sync/budget_sync.py insert --file /tmp/budget_txns.json`
   (It dedups by content key — date + amount + merchant — so re-runs never double-count. It returns `{inserted, skipped, needs_review}`.)

5. **Re-bake the dashboard**:
   `python3 ~/.claude/skills/budget-sync/budget_sync.py aggregate`
   (Rewrites the actuals + budgets + review marker blocks for the current month.)

6. **Notify if needed** — if `insert` reported `needs_review > 0`, send a push notification summarizing the unassigned transactions ("3 transactions need a category — run /budget-sync resolve"). If push is unavailable, create a Gmail draft to self via `create_draft`.

7. **Report** a one-line summary: counts inserted/skipped, total spent this month, and any needs-review count.

If no new transactions are found, do nothing and say so.

## RESOLVE (interactive — clear the needs-review queue)

1. `python3 ~/.claude/skills/budget-sync/budget_sync.py pending` → JSON list of rows needing a category.
2. For each row, **ask the user** (AskUserQuestion) which budget category it belongs to (offer the most likely 3-4 from the merchant, plus "Misc / discretionary"; "Other" lets them pick any). The valid categories are in `category_map.json` → `categories`.
3. Apply each answer: `python3 ~/.claude/skills/budget-sync/budget_sync.py set-category --id <N> --category "<Category>"`.
4. Re-bake: `python3 ~/.claude/skills/budget-sync/budget_sync.py aggregate`.
5. Report what was categorized. The dashboard's "Needs Review" banner clears automatically.

## Notes
- Never edit the dashboard HTML by hand — only the helper's `aggregate` touches it (marker blocks only).
- The valid category list MUST match the dashboard's budget categories (see `category_map.json`). If the user adds/renames a category, update `category_map.json`, `budget_sync.py`'s `CATEGORIES`, the dashboard's `budgetCats` + marker blocks, and `weekly_report.py`'s `DEFAULTS` together.
- When you meet a new recurring merchant, add a rule to `category_map.json` so it auto-categorizes next time.
- Known limitation: forwarded SMS-screenshot emails can't be ingested — the Gmail integration has no attachment-download tool, so images can't be vision-read headlessly. Rely on the banks' **email** alerts instead (every major card issuer can email every transaction).
