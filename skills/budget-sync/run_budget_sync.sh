#!/bin/bash
# Daily budget-sync runner (invoked by launchd/cron at 9 AM). Runs Claude Code headlessly
# to execute the budget-sync skill in ingest mode, then logs the result.
set -euo pipefail

# Full PATH incl. ~/.local/bin (where `claude` may live) and homebrew — schedulers have a bare PATH.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/opt/libpq/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "$HOME"

# --- your config ---
export BUDGET_DB="${BUDGET_DB:-}"          # Postgres connection string (or set it here)
# export BUDGET_DASH="$HOME/finance_dashboard.html"
# export BUDGET_START="2026-07-01"

CLAUDE_BIN="$(command -v claude)"
LOG="$HOME/.claude/skills/budget-sync/sync.log"
echo "=== budget-sync $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG"

# Headless Claude Code. --print runs non-interactively.
# --dangerously-skip-permissions: for a trusted, unattended personal automation; without it the
# headless run stalls on any tool that isn't pre-approved. Requires the workspace to be trusted.
# Understand the risk before enabling this — it lets the headless agent use any tool unprompted.
# Timeout guard so a stuck run can never hang forever.
if command -v timeout >/dev/null 2>&1; then TO="timeout 300"; else TO=""; fi
$TO "$CLAUDE_BIN" --print "Run the budget-sync skill in ingest mode" \
  --dangerously-skip-permissions \
  >> "$LOG" 2>&1

echo "--- done $(date '+%H:%M:%S') (exit $?) ---" >> "$LOG"
