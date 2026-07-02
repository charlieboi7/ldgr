# 2 · Ingest your statements

The foundation of LDGR is 4–6 months of real statement history. From it your
Claude agent derives the expense categories, the monthly averages behind the
dashboard, and the suggested budgets.

## Gather the statements

1. Download PDF statements for **every** account money flows through: checking,
   every credit card, and any savings account with automatic transfers.
2. Cover the **same window for all accounts** — 5–6 recent months is the sweet
   spot (enough to average, recent enough to reflect current life).
3. Put them somewhere Claude can read: a local folder, or a Google Drive folder
   if your Claude has the Drive integration connected. Name them so the account
   and month are obvious (`chase-checking-2026-03.pdf`).

## Parse into the `transactions` table

Have Claude read each PDF and extract one row per transaction:

| column | meaning |
|---|---|
| `date` | transaction date (not posting date, when both are shown) |
| `description` | merchant/payee line, lightly cleaned |
| `amount` | positive number = money out |
| `account` | which card/account, consistent label per account |
| `source_file` | the PDF filename — the audit trail |

Rules that matter (learned the hard way):

- **Skip payments and internal transfers.** A credit-card payment from checking
  shows up on both statements — count the underlying purchases once, on the card
  statement, and skip the payment row and the checking-side transfer. Otherwise
  everything double-counts.
- **Verify outliers against the PDF.** PDF text extraction sometimes grabs the
  wrong number — e.g. a statement's "Eligible Purchases: $X" summary line can get
  captured as a transaction amount, turning an $82 pizza into $850. After parsing,
  have Claude list the largest transactions per account and eyeball them against
  the actual PDFs before trusting any averages.
- **One account at a time, then reconcile.** After each statement, compare the
  parsed total against the statement's own "total purchases" figure. If they
  don't tie out, find out why before moving on.
- Keep the row count honest — a normal household lands in the hundreds of rows
  for 6 months, not tens of thousands. Wild counts mean the parse went wrong.

## From transactions to categories

Once the table is loaded, Claude should:

1. Group by merchant and propose **20–30 categories** that match how *you* think
   about money (see the sample list in `skills/budget-sync/category_map.json`).
   Split fixed bills (mortgage, tuition, insurance) from variable spend
   (groceries, dining, Amazon).
2. Ask you to confirm the category set and which merchants belong where — this
   becomes your personalized `category_map.json`.
3. Ask what to **exclude entirely** (see `averages-methodology.md`) before
   computing any averages.
