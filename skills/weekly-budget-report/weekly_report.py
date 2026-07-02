#!/usr/bin/env python3
"""
weekly-budget-report — emails a newsletter-style "Budget Brief" of the current month's
meters with computed insights (run-rate pace, watch list, top categories, projection) to
the recipient via Gmail SMTP. Pure/deterministic (no LLM). Schedule: Fridays 9 AM.
  --dry-run   write preview to /tmp, don't send
  --sample    render with synthetic mid-month numbers (for previewing the design)

Configuration (env vars):
  BUDGET_DB          required — Postgres connection string
  BUDGET_START       optional YYYY-MM-DD floor for the first tracked month
  REPORT_SENDER      Gmail address the report is sent FROM (needs the app password)
  REPORT_TO          recipient address
  SMTP_APP_PASSWORD  Gmail app password, or put it in .smtp_secret next to this
                     script (chmod 600). NEVER commit that file.
"""
import os, sys, ssl, smtplib, datetime, argparse, calendar
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import psycopg2

CONN = os.environ.get("BUDGET_DB")
START_DATE = os.environ.get("BUDGET_START", "")
SENDER    = os.environ.get("REPORT_SENDER", "")
RECIPIENT = os.environ.get("REPORT_TO", "")
SECRET    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".smtp_secret")
APP_PW    = os.environ.get("SMTP_APP_PASSWORD") or (open(SECRET).read().strip() if os.path.exists(SECRET) else None)

# Fallback budgets when a category isn't in budget_goals. Your Claude agent regenerates
# this to match YOUR categories/amounts (must mirror the dashboard's budgetCats).
DEFAULTS = {
  "Mortgage / rent":2400,"Childcare":1500,"School tuition":900,"Car payment":420,"Internet":90,
  "Student loan":150,"Insurance (life/pet/home)":180,"Auto insurance":120,"Phone":140,
  "Financial advisor":250,"Groceries":850,"Electric":220,"Water / trash":100,"Restaurants":450,
  "Amazon":300,"Target":200,"Misc / discretionary":700,"Church / giving":200,"Housekeeping":160,
  "Pet care":110,"Lawn care":60,"Subscriptions":95,"Kids' activities":120,"Tolls":40,
}
INK="#eef1f7"; INK2="#9aa6bd"; MUTED="#5e6b86"; PAPER="#0b0e16"; CARD="#10141e"; LINE="#222838"
PANEL="#161b27"; GOLD="#c8a96a"; ICE="#74c8d8"; RED="#d4806e"; GREEN="#5cc6a0"

def money(n): return "$"+format(int(round(n)),",")

def month_days(month):
    y,m = map(int,month.split("-")); return calendar.monthrange(y,m)[1]

def elapsed_days(month):
    y,m = map(int,month.split("-")); dim=calendar.monthrange(y,m)[1]
    now=datetime.date.today(); start=datetime.date(y,m,1)
    end=(datetime.date(y,m,dim))
    if now<start: return 0
    if now>end: return dim
    return now.day

def data():
    if not CONN:
        raise SystemExit("BUDGET_DB is not set — export your Postgres connection string first")
    month = datetime.date.today().strftime("%Y-%m")
    if START_DATE: month = max(month, START_DATE[:7])
    budgets=dict(DEFAULTS); spent={c:0.0 for c in DEFAULTS}; review={"count":0,"amount":0.0}
    with psycopg2.connect(CONN) as cx, cx.cursor() as cur:
        cur.execute("SELECT category,amount FROM budget_goals")
        for c,a in cur.fetchall():
            if c in budgets: budgets[c]=float(a)
        cur.execute("SELECT category,COALESCE(SUM(amount),0) FROM daily_spend "
                    "WHERE to_char(txn_date,'YYYY-MM')=%s AND needs_review=false GROUP BY category",(month,))
        for c,t in cur.fetchall():
            if c in spent: spent[c]=float(t)
        cur.execute("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM daily_spend "
                    "WHERE to_char(txn_date,'YYYY-MM')=%s AND needs_review=true",(month,))
        n,a=cur.fetchone(); review={"count":int(n),"amount":float(a)}
    return month, budgets, spent, review, elapsed_days(month)

def sample_data():
    month=datetime.date.today().strftime("%Y-%m")
    budgets=dict(DEFAULTS); spent={c:0.0 for c in DEFAULTS}
    spent.update({"Mortgage / rent":2400,"Childcare":860,"Groceries":512,"Restaurants":296,"Amazon":188,
      "Target":105,"Electric":134,"Misc / discretionary":340,"Church / giving":100,"Pet care":49,
      "Subscriptions":38,"Water / trash":61,"Car payment":420,"Lawn care":60,"Tolls":20})
    return month, budgets, spent, {"count":2,"amount":63.74}, 18

def tile(lab,val,col=INK):
    return (f'<td style="padding:0 6px"><div style="background:{PANEL};border:1px solid {LINE};border-radius:10px;padding:12px 14px">'
            f'<div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};font-weight:700">{lab}</div>'
            f'<div style="font-size:20px;font-weight:700;color:{col};margin-top:4px">{val}</div></div></td>')

def section(title, inner):
    return (f'<tr><td style="padding:22px 26px 0"><div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;'
            f'color:{GOLD};font-weight:700;border-bottom:1px solid {LINE};padding-bottom:8px;margin-bottom:12px">{title}</div>{inner}</td></tr>')

def meter_row(c,b,s):
    pct=(s/b*100) if b else 0; col=RED if pct>100 else (GOLD if pct>=80 else ICE); w=min(100,round(pct)); rem=100-w
    over=f' <span style="color:{RED};font-weight:700">OVER</span>' if pct>100 else ''
    bar=(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {LINE};border-radius:3px;background:{PAPER}"><tr>'
         f'<td height="11" width="{w}%" style="background:{col};border-radius:3px;font-size:0;line-height:0">&nbsp;</td>'
         f'<td width="{rem}%" style="font-size:0;line-height:0">&nbsp;</td></tr></table>')
    return (f'<tr><td style="padding:6px 10px 6px 0;font-size:12.5px;color:{INK};white-space:nowrap">{c}</td>'
            f'<td style="padding:6px 12px;width:42%">{bar}</td>'
            f'<td align="right" style="padding:6px 0;font-size:11.5px;color:{INK2};white-space:nowrap">{money(s)} / {money(b)} · {round(pct)}%{over}</td></tr>')

def build_html(month, budgets, spent, review, elapsed):
    label=datetime.datetime.strptime(month+"-01","%Y-%m-%d").strftime("%B %Y")
    today=datetime.date.today().strftime("%b %d, %Y"); dim=month_days(month)
    totB=sum(budgets.values()); totS=sum(spent.values()); usedPct=round(totS/totB*100) if totB else 0
    frac=elapsed/dim if dim else 0; projected=(totS/frac) if frac>0 else 0; remaining=totB-totS
    early = elapsed==0 or totS<=0

    # ---- insights ----
    over=[]; pace=[]
    for c in budgets:
        b=budgets[c]; s=spent[c]
        if b and s>b: over.append((c,s-b))
        elif b and frac>0 and s>0 and s/frac>b*1.03: pace.append((c,s/frac-b))
    over.sort(key=lambda x:-x[1]); pace.sort(key=lambda x:-x[1])
    top=sorted([(c,spent[c]) for c in budgets if spent[c]>0],key=lambda x:-x[1])[:5]

    if early:
        headline=(f"{label} is just getting underway — nothing's been logged yet. The meters below are your "
                  f"targets; insights kick in as transactions roll in this week.")
        vlab,vcol="Fresh month",ICE; proj_txt="—"
    else:
        diff=totB-projected
        headline=(f"You're <b style='color:#fff'>{round(frac*100)}%</b> through {label} and have spent "
                  f"<b style='color:#fff'>{money(totS)}</b> of your {money(totB)} budget ({usedPct}%). At this run-rate "
                  f"you're trending toward <b style='color:#fff'>{money(projected)}</b> by month-end — "
                  f"<b style='color:{GREEN if diff>=0 else RED}'>{money(abs(diff))} {'under' if diff>=0 else 'over'}</b>.")
        vlab,vcol=("On track",GREEN) if diff>=0 else ("Trending over",RED); proj_txt=money(projected)

    # KPI tiles
    kpis=(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 -6px"><tr>'
          + tile("Spent", money(totS)) + tile("Remaining", money(remaining), GREEN if remaining>=0 else RED)
          + tile("Used", f"{usedPct}%", GOLD) + tile("Projected", proj_txt) + '</tr></table>')

    # Pace verdict pill
    pace_pill=(f'<div style="display:inline-block;background:{PANEL};border:1px solid {vcol};color:{vcol};'
               f'border-radius:20px;padding:5px 14px;font-size:12px;font-weight:700;margin-top:6px">{vlab}</div>')

    # ---- Pacing: calendar elapsed vs budget used ----
    cal=round(frac*100); expected=totB*frac; pdelta=totS-expected
    if early:
        pacing=(f'<div style="font-size:13px;color:{INK2};line-height:1.6">The month is {cal}% elapsed and nothing\'s '
                f'logged yet — pacing turns on with your first transactions. On an even pace you\'d spend about '
                f'<b style="color:#fff">{money(totB/dim)}/day</b> ({money(totB)} ÷ {dim}).</div>')
    else:
        ahead=pdelta>0; pcol=RED if usedPct>cal+3 else (GREEN if usedPct<cal-3 else GOLD)
        sw=min(100,usedPct); cw=min(100,cal)
        pacing=(f'<div style="font-size:13px;color:{INK2};line-height:1.6">You\'re <b style="color:#fff">{cal}%</b> through '
                f'the month but have used <b style="color:#fff">{usedPct}%</b> of budget — '
                f'<b style="color:{RED if ahead else GREEN}">{money(abs(pdelta))} {"ahead of" if ahead else "behind"}</b> '
                f'an even pace (you\'d be at {money(expected)} today on steady spending). Daily run-rate '
                f'<b style="color:#fff">{money(totS/max(elapsed,1))}/day</b> vs a {money(totB/dim)}/day budget.</div>'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {LINE};'
                f'border-radius:4px;background:{PAPER};margin-top:11px"><tr>'
                f'<td height="14" width="{sw}%" style="background:{pcol};border-radius:4px;font-size:0;line-height:0">&nbsp;</td>'
                f'<td width="{100-sw}%" style="font-size:0;line-height:0">&nbsp;</td></tr></table>'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:3px"><tr>'
                f'<td width="{cw}%" style="font-size:0;line-height:0">&nbsp;</td>'
                f'<td align="left" style="font-size:10px;color:{MUTED};white-space:nowrap">▲ on-pace mark ({cal}%)</td></tr></table>')

    # Watch list
    if over or pace:
        items=""
        for c,amt in over[:4]:
            items+=f'<li style="margin:5px 0;color:{INK}"><b style="color:{RED}">{c}</b> — over budget by <b>{money(amt)}</b></li>'
        for c,amt in pace[:4]:
            items+=f'<li style="margin:5px 0;color:{INK}"><b style="color:{GOLD}">{c}</b> — on pace to exceed by ~<b>{money(amt)}</b></li>'
        watch=f'<ul style="margin:4px 0 0;padding-left:18px;font-size:13px;line-height:1.5">{items}</ul>'
    elif early:
        watch=f'<div style="font-size:13px;color:{INK2}">Nothing to flag yet — check back once spending starts.</div>'
    else:
        watch=f'<div style="font-size:13px;color:{GREEN}">✓ Nothing over budget or on pace to break it. Clean month so far.</div>'

    # Top categories
    if top:
        tr=""
        for c,s in top:
            b=budgets[c]; p=round(s/b*100) if b else 0
            tr+=(f'<tr><td style="padding:5px 0;font-size:13px;color:{INK}">{c}</td>'
                 f'<td align="right" style="padding:5px 0;font-size:13px;color:#fff;font-weight:600">{money(s)} '
                 f'<span style="color:{MUTED};font-weight:400">· {p}% of budget</span></td></tr>')
        topsec=f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{tr}</table>'
    else:
        topsec=f'<div style="font-size:13px;color:{INK2}">No spending logged yet this month.</div>'

    meters="".join(meter_row(c,budgets[c],spent[c]) for c in
                   sorted(budgets,key=lambda c:-((spent[c]/budgets[c]) if budgets[c] else 0)))
    rev=(f'<div style="background:#2e1512;border:1px solid {RED};border-radius:8px;padding:10px 14px;font-size:12.5px;color:{INK};margin-top:6px">'
         f'⚠ {review["count"]} transaction(s) need a category ({money(review["amount"])} unassigned) — open the dashboard ▸ Budget to resolve.</div>') if review["count"]>0 else ''

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:{PAPER}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};padding:24px 0">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:{CARD};border:1px solid {LINE};border-radius:14px;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;overflow:hidden">
  <tr><td style="padding:24px 26px 18px;border-bottom:1px solid {LINE}">
    <div style="font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:{GOLD};font-weight:700">◆ LDGR · The Budget Brief</div>
    <div style="font-size:24px;font-weight:600;color:#fff;margin-top:8px">{label}</div>
    <div style="font-size:12px;color:{MUTED};margin-top:3px">Weekly edition · {today} · day {elapsed} of {dim}</div>
  </td></tr>
  <tr><td style="padding:20px 26px 4px">
    <div style="font-size:14px;line-height:1.6;color:{INK2}">{headline}</div>
    <div>{pace_pill}</div>
  </td></tr>
  <tr><td style="padding:16px 20px 0">{kpis}</td></tr>
  {section("Pacing", pacing)}
  {section("Watch list", watch)}
  {section("Top categories this month", topsec)}
  {section("All meters", f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{meters}</table>{rev}')}
  <tr><td style="padding:18px 26px 24px">
    <div style="font-size:10.5px;color:{MUTED};border-top:1px solid {LINE};padding-top:12px;line-height:1.6">
      Ice = under budget · gold = ≥80% · red = over. "Projected" = current run-rate extended to month-end.
      Auto-sent every Friday at 9 AM by LDGR. Reply to adjust what you'd like to see.</div>
  </td></tr>
</table>
</td></tr></table></body></html>"""

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--dry-run",action="store_true"); ap.add_argument("--sample",action="store_true")
    a=ap.parse_args()
    month,budgets,spent,review,elapsed = sample_data() if a.sample else data()
    html=build_html(month,budgets,spent,review,elapsed)
    subj=f"The Budget Brief — {datetime.datetime.strptime(month+'-01','%Y-%m-%d').strftime('%B %Y')} ({money(sum(spent.values()))} spent)"
    if a.dry_run or a.sample or not APP_PW:
        out="/tmp/weekly_report_preview.html"; open(out,"w").write(html)
        tag="SAMPLE" if a.sample else ("DRY-RUN" if a.dry_run else "NO APP PASSWORD — not sent")
        print(f"{tag}: preview written to {out}")
        if not APP_PW and not (a.dry_run or a.sample): sys.exit(2)
        return
    if not SENDER or not RECIPIENT:
        raise SystemExit("REPORT_SENDER / REPORT_TO are not set")
    msg=MIMEMultipart("alternative"); msg["Subject"]=subj; msg["From"]=SENDER; msg["To"]=RECIPIENT
    msg.attach(MIMEText("Your weekly LDGR Budget Brief (view in an HTML-capable client).","plain"))
    msg.attach(MIMEText(html,"html"))
    with smtplib.SMTP("smtp.gmail.com",587) as s:
        s.starttls(context=ssl.create_default_context()); s.login(SENDER,APP_PW)
        s.sendmail(SENDER,[RECIPIENT],msg.as_string())
    print(f"Sent to {RECIPIENT}: {subj}")

if __name__=="__main__": main()
