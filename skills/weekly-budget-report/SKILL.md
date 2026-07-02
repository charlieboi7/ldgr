---
name: weekly-budget-report
description: Send (or preview) the LDGR weekly budget report email. Use when the user runs /weekly-budget-report, or asks to email/preview the current month's budget meters. Runs automatically every Friday 9 AM via the scheduler.
---

# weekly-budget-report

Emails a themed HTML report of the current month's budget meters (per-category spent-vs-budget) to the configured recipient, from the configured Gmail via SMTP. Fully deterministic — it's just a Python script reading the `daily_spend` + `budget_goals` tables.

## To send now
```
python3 ~/.claude/skills/weekly-budget-report/weekly_report.py
```

## To preview without sending (writes /tmp/weekly_report_preview.html)
```
python3 ~/.claude/skills/weekly-budget-report/weekly_report.py --dry-run
```
Use `--sample` to preview the design with synthetic mid-month numbers.

## Notes
- Needs `BUDGET_DB` plus `REPORT_SENDER` / `REPORT_TO` in the environment, and the Gmail **app password** at `.smtp_secret` (chmod 600) or env `SMTP_APP_PASSWORD` — see SETUP.md. Without the password, the script writes a preview and exits.
- Budgets come from the `budget_goals` table, falling back to the `DEFAULTS` dict in the script when a category isn't set there. Keep `DEFAULTS` in sync with the dashboard's categories.
