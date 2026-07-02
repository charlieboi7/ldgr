# weekly-budget-report — setup

Emails the current month's budget meters to your chosen recipient every **Friday 9 AM**,
from your Gmail via SMTP. Pure Python (no Claude/headless needed).

## One-time: the Gmail app password (required to actually send)
SMTP from Gmail needs an **app password** (not your normal password):
1. On the sending Gmail account, enable **2-Step Verification** (myaccount.google.com → Security).
2. Go to **myaccount.google.com/apppasswords**, create one (name it "LDGR report"), copy the 16-char code.
3. Save it locally with tight perms:
   ```
   printf 'XXXXXXXXXXXXXXXX' > ~/.claude/skills/weekly-budget-report/.smtp_secret
   chmod 600 ~/.claude/skills/weekly-budget-report/.smtp_secret
   ```
   (Or set env `SMTP_APP_PASSWORD`.) Revoke anytime from the same Google page.
   **Never commit `.smtp_secret`** — it's in this repo's `.gitignore` for a reason.

## Configuration (env vars, e.g. in `run_weekly_report.sh`)
```
BUDGET_DB       Postgres connection string
REPORT_SENDER   the Gmail address sending the report
REPORT_TO       who receives it (can be the same address, or a partner)
```

## Schedule (Fridays 9 AM)
```
chmod +x ~/.claude/skills/weekly-budget-report/run_weekly_report.sh
```
Then schedule `run_weekly_report.sh` — on macOS use the launchd template in the LDGR
repo's `automation/` directory (weekday 5); on Linux, cron: `0 9 * * 5 <path>/run_weekly_report.sh`.

## Manual use
- Send now:     `python3 ~/.claude/skills/weekly-budget-report/weekly_report.py`
- Preview only: `python3 ~/.claude/skills/weekly-budget-report/weekly_report.py --dry-run`  → /tmp/weekly_report_preview.html
- Logs:         `~/.claude/skills/weekly-budget-report/report.log`

## Notes
- Without `.smtp_secret`, the script just writes a preview and exits (no send).
- Budgets read from the `budget_goals` table; categories not set there use the script's
  `DEFAULTS` (so until you sync your custom budgets to the DB, totals reflect defaults).
