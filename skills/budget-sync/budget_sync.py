#!/usr/bin/env python3
"""
budget_sync helper — deterministic DB + dashboard-file engine for the budget-sync skill.
The skill (Claude) extracts transactions from Gmail; this script handles data integrity:
dedup + insert, month aggregation, and the exact rewrite of the dashboard's marker blocks.

Subcommands:
  insert       --file txns.json     dedup + insert transactions; prints summary JSON
  aggregate   [--month YYYY-MM]      recompute month-to-date totals + rewrite dashboard blocks
  pending                            list needs_review rows as JSON
  set-category --id N --category X   assign a category to a reviewed row (clears needs_review)

txns.json schema: [{ "date":"YYYY-MM-DD", "description":str, "amount":num, "card":str,
                     "category":str|"NEEDS_REVIEW", "source":"alert"|"screenshot",
                     "gmail_msg_id":str }]

Configuration (env vars):
  BUDGET_DB     required — Postgres connection string (e.g. from `ghost connect <db>`)
  BUDGET_DASH   path to the dashboard HTML (default ~/finance_dashboard.html)
  BUDGET_START  optional YYYY-MM-DD floor; transactions before it are skipped on insert,
                and `aggregate` never displays a month earlier than it. Set this to the
                first day of your first clean tracking month.
"""
import os, sys, json, re, argparse, datetime
import psycopg2

CONN = os.environ.get("BUDGET_DB")
DASH = os.environ.get("BUDGET_DASH", os.path.expanduser("~/finance_dashboard.html"))
START_DATE = os.environ.get("BUDGET_START", "")

# IMPORTANT: this list must exactly match the dashboard's budgetCats names AND
# category_map.json's "categories". Your Claude agent regenerates all three together.
CATEGORIES = [
    "Mortgage / rent","Childcare","School tuition","Car payment","Internet","Student loan",
    "Insurance (life/pet/home)","Auto insurance","Phone","Financial advisor",
    "Groceries","Electric","Water / trash","Restaurants","Amazon","Target",
    "Misc / discretionary","Church / giving","Housekeeping","Pet care","Lawn care",
    "Subscriptions","Kids' activities","Tolls",
]

def db():
    if not CONN:
        raise SystemExit("BUDGET_DB is not set — export your Postgres connection string first "
                         "(e.g. BUDGET_DB=\"$(ghost connect my-finances)\")")
    return psycopg2.connect(CONN)

def content_key(t):
    # Dedup on date + amount + normalized merchant only (NOT card) — the same charge can be
    # labeled with different card strings across alerts, which would otherwise double-count.
    return (str(t["date"]), round(float(t["amount"]),2),
            " ".join(str(t["description"]).upper().split()))

def cmd_insert(args):
    txns = json.load(open(args.file)) if args.file else json.load(sys.stdin)
    inserted = skipped = review = skipped_old = 0
    with db() as cx, cx.cursor() as cur:
        # existing content keys (recent window) to dedup against
        cur.execute("SELECT txn_date, amount, upper(description) "
                    "FROM daily_spend WHERE txn_date >= %s",
                    (datetime.date.today()-datetime.timedelta(days=45),))
        seen = set()
        for d,a,desc in cur.fetchall():
            seen.add((d.isoformat(), round(float(a),2), " ".join(desc.split())))
        for t in txns:
            if START_DATE and str(t["date"]) < START_DATE:
                skipped_old += 1; continue
            k = content_key(t)
            if k in seen:
                skipped += 1; continue
            nr = (t.get("category","NEEDS_REVIEW") == "NEEDS_REVIEW") or bool(t.get("needs_review"))
            cat = "Needs Review" if nr else t["category"]
            cur.execute(
                "INSERT INTO daily_spend (txn_date, description, amount, card, category, "
                "needs_review, source, gmail_msg_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (t["date"], t["description"], t["amount"], t["card"], cat, nr,
                 t.get("source"), t.get("gmail_msg_id")))
            seen.add(k); inserted += 1; review += 1 if nr else 0
    print(json.dumps({"inserted":inserted,"skipped":skipped,"skipped_before_start":skipped_old,"needs_review":review}))

def _replace_block(html, start_tok, end_tok, new_inner):
    pat = re.compile(re.escape(start_tok)+r".*?"+re.escape(end_tok), re.S)
    if not pat.search(html):
        raise SystemExit(f"marker {start_tok!r} not found in {DASH}")
    return pat.sub(lambda m: new_inner, html, count=1)

def cmd_aggregate(args):
    # Track the current calendar month, but never earlier than the START_DATE month.
    month = args.month or datetime.date.today().strftime("%Y-%m")
    if START_DATE:
        month = max(month, START_DATE[:7])
    actuals = {c:0.0 for c in CATEGORIES}
    review = {"count":0,"amount":0.0}
    budgets = {}
    with db() as cx, cx.cursor() as cur:
        cur.execute("SELECT category, COALESCE(SUM(amount),0) FROM daily_spend "
                    "WHERE to_char(txn_date,'YYYY-MM')=%s AND needs_review=false GROUP BY category",(month,))
        for cat,total in cur.fetchall():
            if cat in actuals: actuals[cat]=float(total)
        cur.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM daily_spend "
                    "WHERE to_char(txn_date,'YYYY-MM')=%s AND needs_review=true",(month,))
        c,a = cur.fetchone(); review={"count":int(c),"amount":float(a)}
        cur.execute("SELECT category, amount FROM budget_goals")
        for cat,amt in cur.fetchall(): budgets[cat]=float(amt)

    def jsobj(d): return "{\n"+",\n".join(f'  {json.dumps(k)}:{round(v,2)}' for k,v in d.items())+"\n}"
    html = open(DASH).read()
    html = _replace_block(html,"/* BUDGET_ACTUALS_START","/* BUDGET_ACTUALS_END */",
        "/* BUDGET_ACTUALS_START — the daily email-alert skill rewrites this block (month + per-category MTD spend) */\n"
        f'const actualsMonth = "{month}";\n'
        f"const actuals = {jsobj(actuals)};\n/* BUDGET_ACTUALS_END */")
    html = _replace_block(html,"/* BUDGET_GOALS_START","/* BUDGET_GOALS_END */",
        "/* BUDGET_GOALS_START — the skill bakes your saved budgets here (from the budget_goals table) so they survive a fresh file/browser */\n"
        f"const savedBudgets = {jsobj(budgets) if budgets else '{}'};\n/* BUDGET_GOALS_END */")
    html = _replace_block(html,"/* BUDGET_REVIEW_START","/* BUDGET_REVIEW_END */",
        "/* BUDGET_REVIEW_START — skill sets the needs-review banner */\n"
        f'const needsReview = {{count:{review["count"]}, amount:{round(review["amount"],2)}}};\n/* BUDGET_REVIEW_END */')
    open(DASH,"w").write(html)
    print(json.dumps({"month":month,"categories_with_spend":sum(1 for v in actuals.values() if v>0),
                      "total_spent":round(sum(actuals.values()),2),"needs_review":review}))

def cmd_pending(args):
    with db() as cx, cx.cursor() as cur:
        cur.execute("SELECT id, txn_date, description, amount, card FROM daily_spend "
                    "WHERE needs_review=true ORDER BY txn_date, id")
        rows=[{"id":r[0],"date":r[1].isoformat(),"description":r[2],
               "amount":float(r[3]),"card":r[4]} for r in cur.fetchall()]
    print(json.dumps(rows, indent=2))

def cmd_set_category(args):
    with db() as cx, cx.cursor() as cur:
        cur.execute("UPDATE daily_spend SET category=%s, needs_review=false WHERE id=%s",
                    (args.category, args.id))
        n=cur.rowcount
    print(json.dumps({"updated":n,"id":args.id,"category":args.category}))

if __name__=="__main__":
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("insert"); s.add_argument("--file"); s.set_defaults(fn=cmd_insert)
    s=sub.add_parser("aggregate"); s.add_argument("--month"); s.set_defaults(fn=cmd_aggregate)
    s=sub.add_parser("pending"); s.set_defaults(fn=cmd_pending)
    s=sub.add_parser("set-category"); s.add_argument("--id",type=int,required=True); s.add_argument("--category",required=True); s.set_defaults(fn=cmd_set_category)
    a=p.parse_args(); a.fn(a)
