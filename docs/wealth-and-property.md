# 5 · Optional: wealth & property (Net Worth + Growth tabs)

The dashboard's **Net Worth** and **Growth** tabs are optional — the budget
system works without them. If you want them, gather these inputs (your Claude
agent should interview you for each):

## Inputs

| input | where to get it |
|---|---|
| Investment balances (401k/IRA/brokerage) | account statements, or your advisor app's screenshots |
| Cash savings | bank balances |
| Property market values | Zillow/Redfin estimate, a recent appraisal, or your own number |
| Mortgage balances, rates, and monthly P&I | mortgage servicer statement |
| Other debt (cards, loans) | statements |
| Monthly investing amount | from your savings-rate work (see averages-methodology.md) |

Decisions to make explicitly:
- **What's excluded.** For example, kids' 529 accounts can be excluded from both
  savings and net worth if you think of them as the kids' money, not yours.
- **One loan is one loan.** If a mortgage was transferred between servicers,
  it appears under two names across statements — model it once.

## What the tabs do

- **Net Worth** — assets (investments + cash + real estate) minus liabilities
  (mortgages + other debt), with a home-equity card per property, and a
  projection: homes appreciate at an adjustable rate, mortgages amortize using
  the real monthly P&I, investments compound with your monthly contribution.
- **Growth** — pure compound-interest explorer for your monthly savings: preset
  buttons for "current savings rate" and "savings + surplus", milestone cards at
  5/10/20/30 years, contributions vs growth chart.

All of it is plain JS `const`s near the top of the dashboard's script block
(`NW = {...}`, the growth slider defaults) — your agent fills them in from your
answers and the dashboard recomputes live. No external data, no APIs; update the
balances whenever you feel like it (quarterly is plenty).

## Keeping it honest

Where a figure is an estimate (property values especially), label it in the UI
text. The projection sliders are for exploring scenarios, not predictions —
the defaults (3.5% home appreciation, 7% market return) are long-run averages,
and the note under each slider says so.
