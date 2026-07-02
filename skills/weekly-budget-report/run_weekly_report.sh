#!/bin/bash
# Weekly budget report — scheduler entrypoint (Fridays 9 AM). Pure Python, no Claude needed.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/opt/libpq/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# --- your config ---
export BUDGET_DB="${BUDGET_DB:-}"          # Postgres connection string (or set it here)
export REPORT_SENDER="${REPORT_SENDER:-}"  # sending Gmail address
export REPORT_TO="${REPORT_TO:-}"          # recipient address

LOG="$HOME/.claude/skills/weekly-budget-report/report.log"
echo "=== weekly-report $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"
/usr/bin/python3 "$HOME/.claude/skills/weekly-budget-report/weekly_report.py" >> "$LOG" 2>&1
echo "--- exit $? ---" >> "$LOG"
