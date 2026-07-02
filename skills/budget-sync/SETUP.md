# budget-sync — setup

## What it does
Daily, reads transaction-alert emails from your banks/cards, logs them to the
`daily_spend` table, and re-bakes the Budget meters in the dashboard HTML.
Ambiguous ones are flagged for one-tap review (`/budget-sync resolve`).

## Pieces
- `SKILL.md` — the procedure (ingest + resolve).
- `budget_sync.py` — DB + file engine (insert / aggregate / pending / set-category).
- `category_map.json` — merchant → category rules (edit to teach it new merchants).
- `run_budget_sync.sh` — scheduler entrypoint (launchd/cron).

## One-time setup

1. **Install the skill** — copy this directory to `~/.claude/skills/budget-sync/` and:
   ```
   chmod +x ~/.claude/skills/budget-sync/run_budget_sync.sh
   ```

2. **Enable transaction alerts at every bank/card.** In each card's app or site,
   turn on email alerts for **every transaction** (set the threshold to $0 or $1).
   Point them at the Gmail account your Claude Code is connected to. This is the
   data feed — without it, ingest finds nothing.

3. **Python deps**: `pip3 install psycopg2-binary`

4. **Environment** — the helper reads `BUDGET_DB` (Postgres connection string) and
   optionally `BUDGET_DASH` (dashboard path) and `BUDGET_START` (YYYY-MM-DD floor for
   your first clean tracking month). Put them in the runner script or your shell profile.

5. **Gmail access for headless runs** — the scheduled run uses Claude Code
   non-interactively, so the Gmail (and Bash) tools must be pre-authorized. Run the
   skill once *interactively* first (`/budget-sync`) and approve the Gmail/Bash
   permissions so they're remembered. Confirm the Gmail integration is connected to
   the inbox that receives the alerts.

6. **Schedule it for 9 AM daily** — see `docs/automation.md` in the LDGR repo.
   On macOS prefer **launchd** over cron (catches up missed runs after sleep; a
   template plist ships in the repo's `automation/` directory). cron works on Linux.

## Manual use
- Ingest now:        `/budget-sync`
- Resolve reviews:   `/budget-sync resolve`
- Inspect helper:    `python3 ~/.claude/skills/budget-sync/budget_sync.py pending`

## Notes
- Runs find nothing until real alerts start arriving — enable them first.
- Tune `category_map.json` as new merchants show up.
- Dedup keys on date + amount + merchant (not card), so the same charge alerted
  twice with different card labels won't double-count.
