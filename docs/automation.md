# 6 · Automation (scheduled runs)

Two jobs keep LDGR alive with zero manual effort:

| job | when | what runs |
|---|---|---|
| budget-sync | daily 9 AM | headless Claude Code executes the budget-sync skill (reads alert emails → DB → re-bakes dashboard) |
| weekly-report | Friday 9 AM | plain Python emails the Budget Brief (no Claude involved) |

## macOS: use launchd, not cron

cron on macOS misses runs when the machine is asleep at the scheduled minute and
needs Full Disk Access wrangling. **launchd** runs jobs in your login session and
catches up a missed run on wake. Templates ship in `automation/`:

```bash
# 1. copy the skills into place first (see the skill SETUP.md files)
# 2. fill in the plists
sed "s|REPLACE_WITH_HOME|$HOME|g" automation/com.ldgr.budget-sync.plist   > ~/Library/LaunchAgents/com.ldgr.budget-sync.plist
sed "s|REPLACE_WITH_HOME|$HOME|g" automation/com.ldgr.weekly-report.plist > ~/Library/LaunchAgents/com.ldgr.weekly-report.plist
# 3. load them (they also auto-load at every login)
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ldgr.budget-sync.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ldgr.weekly-report.plist
```

On Linux, plain cron is fine:
```
0 9 * * * $HOME/.claude/skills/budget-sync/run_budget_sync.sh
0 9 * * 5 $HOME/.claude/skills/weekly-budget-report/run_weekly_report.sh
```

## Headless Claude Code — read this before enabling

The daily sync runs `claude --print "Run the budget-sync skill in ingest mode"
--dangerously-skip-permissions`. Two things make that work unattended:

1. The workspace (your home directory or wherever the dashboard lives) must be
   **trusted** — open Claude Code there once interactively and accept the trust
   prompt.
2. `--dangerously-skip-permissions` is exactly what it says: the headless agent
   can use any tool without asking. Without it, the run stalls on the first
   un-preapproved tool; with it, you're trusting the skill you installed.
   Read `skills/budget-sync/SKILL.md` so you know precisely what it does, and
   check `sync.log` for the first few days.

Also run `/budget-sync` once **interactively** first, approving the Gmail and
Bash permissions, and confirm the Gmail integration is connected to the inbox
that receives your bank alerts.

## The data feed: bank alert emails

Every major issuer can email you on every transaction (set the alert threshold
to $0/$1). Turn this on for **each** card and your checking account, pointed at
the connected Gmail. Alert emails typically arrive within seconds of a purchase,
so the 9 AM run captures yesterday completely.

**Known limitation:** transactions that only exist as SMS (some banks) can't be
auto-ingested by forwarding screenshots — the Gmail integration can't download
attachments for vision reading. Prefer email alerts; anything else can be added
in a `/budget-sync resolve` session by hand.

## Logs

- Daily sync: `~/.claude/skills/budget-sync/sync.log` (+ `launchd.*.log`)
- Weekly report: `~/.claude/skills/weekly-budget-report/report.log`
