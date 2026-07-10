# 3 · How the averages are computed

This is the most important doc in the repo. The dashboard is only as trustworthy
as the monthly figures baked into it, and naive averaging produces numbers that
feel wrong immediately. These are the conventions LDGR uses — your Claude agent
should walk you through each decision rather than assume.

## Exclude outliers — don't let one big month lie to you

A plain 6-month mean gets skewed by single events: one $2,000 TV purchase turns
"Misc" into a scary number; one reimbursed work trip inflates "Travel" forever.

- For each category, look at the per-month totals **and the largest individual
  transactions** before averaging.
- Drop clearly one-time purchases from the average (big electronics, furniture,
  an appliance replacement, a security deposit). They're real spending, but
  they're not a *monthly rate*, and the dashboard models monthly rates.
- When a category is spiky but genuinely recurring (kids' clothes, home goods),
  keep it — that's what "Misc / discretionary" is for — but note in the dashboard
  that it's spiky rather than pretending it's a fixed bill.

## Only amortize genuinely recurring bills

Turning a 6-month insurance premium of $540 into $90/mo is honest — it recurs
on a fixed schedule. Turning one sporadic $90 charge into "$15/mo" is not; it
makes a one-off look like a subscription. The test: **would you bet it happens
again next cycle?** If yes, amortize; if no, exclude it or leave it in Misc.

## Agree an exclusion list up front

Some spending is real but doesn't belong in a monthly planning view. Decide
*before* averaging what's out. Common exclusions (pick your own): travel,
medical, one-time purchases, work-reimbursed expenses, categories you track
elsewhere. Excluded merchants should **not** get category rules in
`category_map.json` — the daily sync flags them `needs_review` so you decide
each time instead of silently counting them.

## Income conventions

- **Net income = what actually reaches checking.** If a paycheck auto-splits
  some amount straight to savings before it ever hits checking, that money is
  *savings*, not income available to spend — exclude it from net income and the
  spending pie, and count it in the savings rate instead.
- **Savings rate is measured against gross**, and includes: 401(k) contributions
  (yours and a partner's), employer match, and after-tax auto-saves. The
  dashboard KPI shows the breakdown on hover.
- **The 50/30/20 view uses total after-tax income** (checking + the auto-save)
  as its base, with toggles to sweep the surplus into savings and to include
  pre-tax 401(k) on a gross basis. Keep the bases labeled — mixing gross and
  after-tax silently is how dashboards lose trust.

## Reconcile after every change

Every time a figure is edited, the totals must tie out again: category amounts
sum to total expenses, needs + wants + surplus equals net income, the pie and
the flow bar agree with the KPI strip. The agent should recompute with a quick
script and confirm before delivering — never eyeball it.

## Document the caveats in the dashboard itself

The footer of the dashboard states the basis: which months, that outliers were
removed, and what was excluded. Future-you will thank present-you.
