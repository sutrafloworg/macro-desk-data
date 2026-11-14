#!/usr/bin/env python3
"""Render the nightly Macro Futures Desk email (v3) from the report JSON.

  python3 email_report.py DATA.json OUT_DIR [--dashboard URL]

Writes OUT_DIR/subject.txt, OUT_DIR/email.html and OUT_DIR/email.txt.

Layout rules (learned the hard way): Gmail strips every background colour from this email, so nothing here
depends on one. All text is dark or strongly coloured on white, labels are outlined not filled, and every
block is a simple label / value row that reads the same on a phone and a laptop. The exact trade comes first.
"""
import html, json, os, sys

args = sys.argv[1:]
if len(args) < 2:
    sys.exit(__doc__)
data_path, out_dir = args[0], args[1]
dash = "https://claude.ai/artifact/4tCfHkU55uKquwJ7vNvD4N"
if "--dashboard" in args:
    dash = args[args.index("--dashboard") + 1]

D = json.load(open(data_path, encoding="utf-8"))
if "data" in D and "verdict" not in D:
    D = D["data"]
os.makedirs(out_dir, exist_ok=True)

e = lambda s: html.escape("" if s is None else str(s))
V = D.get("verdict") or {}
BP = D.get("best_prediction") or {}
TR = D.get("trade") or {}
ALT = D.get("alternatives") or []
REC = D.get("forecast_record") or {}
VAL = D.get("forecast_validation") or {}
MT = D.get("macro_trend") or {}
RG = D.get("regime") or {}
E = D.get("events") or []
N = D.get("news") or []
mode = str(D.get("run_mode") or "").upper()
eng = D.get("engine") or {}
session = (D.get("session_label") or "").split(" (")[0].replace("Report for the ", "").replace(" session", "")

INK, INK2, MUTED, RULE = "#12202B", "#34454F", "#5E6E7B", "#D3DAE1"
LONG, SHORT, WARN, ACC = "#0B7A5A", "#B2372F", "#9A5B00", "#2952B8"
F = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
M = "font-family:Consolas,'SFMono-Regular',Menlo,'Liberation Mono',monospace"


def clip(s, n):
    s = "" if s is None else str(s).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def sentences(s, n=2, limit=320):
    s = "" if s is None else str(s).strip().replace("\n", " ")
    out = []
    for p in s.split(". "):
        out.append(p.rstrip("."))
        if len(out) >= n:
            break
    txt = ". ".join(out).strip()
    return clip(txt + ("." if txt and not txt.endswith((".", "!", "?")) else ""), limit)


def num(x):
    if x is None or x == "":
        return "-"
    if isinstance(x, (int, float)):
        s = f"{x:,.0f}" if abs(x) >= 1000 else f"{x:,}"
        return s[:-2] if s.endswith(".0") else s
    return str(x)


def money(x):
    return "-" if x in (None, "") else "$" + f"{x:,.0f}"


def real(s):
    return s and str(s).strip() and str(s).strip().upper() != "TODO"


def tag(text, col):
    return f'<span style="{F};font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:{col};border:1px solid {col};border-radius:4px;padding:2px 7px">{e(text)}</span>'


def h2(title):
    return f'<div style="{F};font-size:13px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:{INK2};border-bottom:2px solid {INK};padding-bottom:6px;margin:0 0 10px">{e(title)}</div>'


def block(title, inner):
    return f'<tr><td style="padding:26px 20px 0">{h2(title)}{inner}</td></tr>'


def kv(rows, big=False):
    """Label / value rows. rows = [(label, value_html, note_text)]."""
    out = ""
    for lab, val, note in rows:
        out += (f'<tr><td width="34%" style="{F};font-size:13px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:{MUTED};padding:11px 10px 11px 0;border-top:1px solid {RULE};vertical-align:top">{e(lab)}</td>'
                f'<td style="{F};font-size:{"17" if big else "15"}px;line-height:1.45;color:{INK};padding:10px 0;border-top:1px solid {RULE};vertical-align:top">{val}'
                + (f'<div style="{F};font-size:13px;line-height:1.45;color:{MUTED};margin-top:3px">{e(note)}</div>' if note else "") + '</td></tr>')
    return f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">{out}</table>'


def bullets(items, col=INK2):
    li = "".join(f'<li style="margin:0 0 6px">{e(x)}</li>' for x in items if real(x))
    return f'<ul style="{F};font-size:15px;line-height:1.5;color:{col};margin:6px 0 0;padding-left:20px">{li}</ul>' if li else ""


parts = []
# ---------- header ----------
stale = mode == "DEGRADED"
parts.append(
    f'<tr><td style="padding:20px 20px 0"><div style="{F};font-size:12px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:{MUTED}">Claude · Macro Futures Desk</div>'
    f'<div style="{F};font-size:22px;font-weight:700;color:{INK};margin-top:4px">Trade plan for {e(session or "the next session")}</div>'
    + (f'<div style="{F};font-size:14px;line-height:1.45;color:{WARN};border:1px solid {WARN};border-radius:6px;padding:8px 10px;margin-top:10px"><b>Older data tonight.</b> {e(sentences(D.get("data_note"), 1, 200))} Check the price before acting.</div>' if stale else "")
    + '</td></tr>')

# ---------- the trade ----------
if TR.get("action") and BP.get("name"):
    is_long = TR["action"].upper().startswith("BUY")
    col = LONG if is_long else SHORT
    contract = TR.get("contract_override") if real(TR.get("contract_override")) else TR.get("contract")
    qty = TR.get("qty")
    conv = TR.get("conviction") or "Low"
    conv_col = {"High": LONG, "Medium": ACC}.get(conv, WARN)
    size_val = (f'<b>{qty} × {e(contract)}</b>' if qty else '<b>Paper only</b>')
    size_note = (f'{TR.get("product")}. ' if TR.get("product") else "") + (TR.get("note") or "")
    loss = TR.get("max_loss_usd")
    risk_val = f'<b style="color:{SHORT}">{money(loss)}</b> if the stop is hit' if loss else "-"
    risk_note = (f'{TR.get("risk_pct_equity")}% of the account. ' if TR.get("risk_pct_equity") else "") + (f'Gain at the target: about {money(TR.get("gain_at_target_usd"))}.' if TR.get("gain_at_target_usd") else "")
    stop_pct = TR.get("stop_pct")
    rows = [
        ("Entry", f'<b>{e(TR.get("entry_when"))}</b>', TR.get("entry_rule")),
        ("Stop loss", f'<b style="{M};font-size:18px;color:{SHORT}">{num(TR.get("stop"))}</b>', f'{TR.get("stop_order", "Stop")} order, placed as soon as you are in' + (f' ({"+" if stop_pct > 0 else ""}{stop_pct}% from the last close).' if stop_pct is not None else ".")),
        ("Exit", (f'<b style="{M};font-size:18px;color:{LONG}">{num(TR.get("target"))}</b> take profit' if TR.get("target") is not None else f'<b>Close on {e(TR.get("exit_label"))}</b>'), TR.get("exit_rule")),
        ("Size", size_val, size_note.strip()),
        ("Risk", risk_val, risk_note.strip()),
        ("Chance it works", f'<b>{num(TR.get("chance"))}%</b> &nbsp;{tag(conv + " conviction", conv_col)}', "Grade " + str(TR.get("grade") or "-") + ". " + ("Wrong almost half the time: keep the size small." if (TR.get("chance") or 0) < 58 else "")),
    ]
    why = BP.get("why") if real(BP.get("why")) else V.get("summary")
    box = (f'<table width="100%" cellpadding="0" cellspacing="0" style="border:3px solid {col};border-radius:10px"><tr><td style="padding:16px 16px 6px">'
           f'<div style="{F};font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:{col}">Tonight\'s trade{" · paper" if TR.get("paper") else ""}</div>'
           f'<div style="{F};font-size:30px;line-height:1.15;font-weight:800;color:{col};margin-top:6px">{e(TR["action"])}</div>'
           f'<div style="{F};font-size:24px;line-height:1.2;font-weight:800;color:{INK};margin-top:2px">{e(BP.get("name"))}</div>'
           f'<div style="{M};font-size:14px;color:{MUTED};margin:6px 0 12px">{e(contract)} · {e(BP.get("basis") or "")}</div>'
           + kv(rows, big=True)
           + (f'<div style="{F};font-size:15px;line-height:1.5;color:{INK2};border-top:1px solid {RULE};padding:12px 0 10px"><b style="color:{INK}">Why:</b> {e(sentences(why, 3, 480))}</div>' if real(why) else "")
           + '</td></tr></table>')
    parts.append(f'<tr><td style="padding:16px 12px 0">{box}</td></tr>')

    extra = ""
    if real(BP.get("invalidation")):
        extra += f'<div style="{F};font-size:15px;line-height:1.5;color:{INK2};margin:0 0 10px"><b style="color:{SHORT}">Get out early if:</b> {e(clip(BP.get("invalidation"), 300))}</div>'
    drv = bullets((BP.get("drivers") or [])[:4])
    if drv:
        extra += f'<div style="{F};font-size:14px;font-weight:700;color:{INK};margin-top:4px">What the model sees</div>{drv}'
    rk = bullets((BP.get("risks") or [])[:3])
    if rk:
        extra += f'<div style="{F};font-size:14px;font-weight:700;color:{INK};margin-top:12px">What could go wrong</div>{rk}'
    if extra:
        parts.append(block("Behind the trade", extra))
elif real(V.get("headline")):
    parts.append(f'<tr><td style="padding:16px 20px 0"><div style="{F};font-size:18px;font-weight:700;color:{INK}">{e(V.get("headline"))}</div><div style="{F};font-size:15px;line-height:1.5;color:{INK2};margin-top:6px">{e(sentences(V.get("summary"), 3, 420))}</div></td></tr>')

# ---------- runners-up ----------
if ALT:
    rows = [(a.get("name"), f'<b style="color:{LONG if a.get("dir") == "LONG" else SHORT}">{"BUY" if a.get("dir") == "LONG" else "SELL SHORT"}</b> &nbsp;{num(a.get("prob"))}% · grade {e(a.get("grade") or "-")}', clip(a.get("basis"), 80)) for a in ALT[:3]]
    parts.append(block("Next best ideas (not tonight's trade)", kv(rows)))

# ---------- track record and odds ----------
rec_rows = []
if REC.get("calls"):
    closed = REC.get("closed") or 0
    rec_rows.append(("Live record", f'<b>{REC.get("calls")}</b> trades logged, <b>{closed}</b> closed' + (f', {REC.get("win_pct")}% won, average {REC.get("avgR")}R' if closed else ""), "R = result as a multiple of the amount risked. Each trade runs about 10 sessions." if not closed else ""))
    for r in (REC.get("recent") or [])[:4]:
        res = r.get("R") if r.get("R") is not None else r.get("R_now")
        rec_rows.append((f'{r.get("date")}', f'{e(r.get("name"))} <b style="color:{LONG if r.get("dir") == "LONG" else SHORT}">{"BUY" if r.get("dir") == "LONG" else "SELL"}</b> &nbsp;{e(r.get("exit") or r.get("status") or "")}' + (f' &nbsp;<b style="{M}">{"+" if res > 0 else ""}{res}R</b>' if isinstance(res, (int, float)) else ""), ""))
tp, tpl = VAL.get("topPick") or {}, VAL.get("tradePlan") or {}
if tp.get("n"):
    rec_rows.append(("History test", f'Right <b>{tp.get("hit")}%</b> of {num(tp.get("n"))} days', f'{VAL.get("span", "")}, on data the model had not seen. As a trade with this stop and exit: {tpl.get("win")}% won, {"+" if (tpl.get("expR") or 0) > 0 else ""}{tpl.get("expR")}R average, worst losing streak {tpl.get("maxLossRun")}.'))
if rec_rows:
    parts.append(block("Track record", kv(rec_rows)))

# ---------- regime ----------
if MT.get("quadrant"):
    names = [("growth", "Growth"), ("inflation", "Inflation"), ("policy", "Fed policy"), ("liquidity", "Liquidity"), ("risk", "Risk appetite")]
    rows = []
    for k, lab in names:
        p = (MT.get("pillars") or {}).get(k) or {}
        s = p.get("score")
        if s is None:
            continue
        c = LONG if s > 0.2 else SHORT if s < -0.2 else MUTED
        d20 = p.get("d20")
        rows.append((lab, f'<b style="color:{c}">{e(p.get("label", "-"))}</b> &nbsp;<span style="{M};font-size:14px;color:{MUTED}">{"+" if s > 0 else ""}{s}</span>', (f'Moved {"+" if d20 > 0 else ""}{d20} in 20 sessions.' if d20 and abs(d20) >= 0.5 else "")))
    fav = ", ".join(x["name"] for x in (MT.get("favored") or [])[:4])
    dis = ", ".join(x["name"] for x in (MT.get("disfavored") or [])[:4])
    if fav:
        rows.append(("Tends to rise", e(fav), ""))
        rows.append(("Tends to fall", e(dis), ""))
    head = (f'<div style="{F};font-size:20px;font-weight:800;color:{INK}">{e(MT.get("quadrant"))} <span style="font-size:14px;font-weight:400;color:{MUTED}">day {e(MT.get("ageSessions"))}</span></div>'
            + (f'<div style="{F};font-size:15px;line-height:1.5;color:{INK2};margin:6px 0 8px">{e(sentences(RG.get("narrative"), 2, 320))}</div>' if real(RG.get("narrative")) else '<div style="margin-bottom:8px"></div>'))
    parts.append(block("Macro backdrop", head + kv(rows)))

# ---------- events ----------
hi = [x for x in E if str(x.get("imp", "")).lower() == "high"] or E
if hi:
    rows = [(f'{x.get("day", "")} {x.get("time", "")}'.strip(), e(clip(x.get("what"), 90)), "") for x in hi[:6]]
    parts.append(block("Events to watch (ET)", kv(rows)))

# ---------- news ----------
news = [n for n in N if real(n.get("title"))][:4]
if news:
    items = "".join(
        '<li style="margin:0 0 10px">' + (f'<a href="{e(n.get("url"))}" style="color:{ACC}">{e(n.get("title"))}</a>' if n.get("url") else e(n.get("title")))
        + (f'<div style="font-size:14px;color:{MUTED};margin-top:2px">{e(clip(n.get("take"), 170))}</div>' if real(n.get("take")) else "") + '</li>' for n in news)
    parts.append(block("What moved markets", f'<ul style="{F};font-size:15px;line-height:1.45;margin:0;padding-left:20px;color:{INK}">{items}</ul>'))

# ---------- footer ----------
parts.append(
    f'<tr><td style="padding:26px 20px 0"><a href="{e(dash)}" style="{F};font-size:16px;font-weight:700;color:{ACC}">Open the live dashboard →</a>'
    f'<div style="{F};font-size:13px;color:{MUTED};margin-top:4px">Forecasts for all 33 markets, the full track record and past reports. Engine {e(eng.get("version", "-"))} · {e(mode.title() or "Full")} run.</div></td></tr>'
    f'<tr><td style="padding:18px 20px 24px;{F};font-size:12px;line-height:1.5;color:{MUTED}">Sent by Claude (scheduled cloud task). This is the output of a rules-based model, written up as a paper trade and scored automatically. It is research, not financial advice, and Claude is not a licensed advisor. Futures are leveraged and can lose more than the margin posted. A 53–58% chance means it is wrong almost half the time.</td></tr>')

html_doc = ('<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:8px 4px">'
            '<table width="620" cellpadding="0" cellspacing="0" style="width:100%;max-width:620px;border:1px solid ' + RULE + ';border-radius:10px">'
            + "".join(parts) + '</table></td></tr></table>')

# ---------- plain text ----------
L = [f"CLAUDE · MACRO FUTURES DESK · trade plan for {session}", ""]
if stale:
    L += ["OLDER DATA TONIGHT: " + sentences(D.get("data_note"), 1, 200) + " Check the price before acting.", ""]
if TR.get("action") and BP.get("name"):
    contract = TR.get("contract_override") if real(TR.get("contract_override")) else TR.get("contract")
    L += [f"TONIGHT'S TRADE{' (paper)' if TR.get('paper') else ''}: {TR['action']} {BP.get('name')}  [{contract}]",
          f"  ENTRY:      {TR.get('entry_when')} {TR.get('entry_rule')}",
          f"  STOP LOSS:  {num(TR.get('stop'))} ({TR.get('stop_order', 'stop')} order)",
          f"  EXIT:       {TR.get('exit_rule')}",
          f"  SIZE:       {str(TR.get('qty')) + ' x ' + str(contract) if TR.get('qty') else 'paper only'} ({TR.get('product')})",
          f"  RISK:       {money(TR.get('max_loss_usd'))} if the stop is hit",
          f"  CHANCE:     {num(TR.get('chance'))}% · {TR.get('conviction')} conviction (grade {TR.get('grade')})"]
    why = BP.get("why") if real(BP.get("why")) else V.get("summary")
    if real(why):
        L += ["", "WHY: " + sentences(why, 3, 480)]
    if real(BP.get("invalidation")):
        L.append("GET OUT EARLY IF: " + clip(BP.get("invalidation"), 300))
    if ALT:
        L += ["", "NEXT BEST: " + "; ".join(f"{a.get('name')} {'BUY' if a.get('dir') == 'LONG' else 'SELL'} {a.get('prob')}%" for a in ALT[:3])]
else:
    L += [str(V.get("headline") or ""), sentences(V.get("summary"), 3, 420)]
if REC.get("calls"):
    L += ["", f"TRACK RECORD: {REC.get('calls')} trades logged, {REC.get('closed')} closed" + (f", {REC.get('win_pct')}% won, avg {REC.get('avgR')}R" if REC.get("closed") else "")]
if MT.get("quadrant"):
    L += ["", f"MACRO: {MT['quadrant']} (day {MT.get('ageSessions')})"]
if hi:
    L += ["", "EVENTS"] + [f"- {x.get('day')} {x.get('time')}: {clip(x.get('what'), 90)}" for x in hi[:6]]
L += ["", f"Dashboard: {dash}", "Rules-based model output, paper trade. Research, not financial advice."]

# ---------- subject ----------
if TR.get("action") and BP.get("name"):
    short_action = "BUY" if TR["action"].upper().startswith("BUY") else "SELL"
    contract = TR.get("contract_override") if real(TR.get("contract_override")) else TR.get("contract")
    subj = f"[Claude] {short_action} {str(BP.get('name')).split(' (')[0]} ({contract}) · stop {num(TR.get('stop'))} · {num(TR.get('chance'))}% {str(TR.get('conviction') or '').lower()} conviction · {session}"
else:
    subj = f"[Claude] Macro Desk · {session} — {clip(V.get('headline'), 70)}"
if stale:
    subj += " · older data"
if D.get("subject_prefix"):
    subj = subj.replace("[Claude] ", "[Claude] " + str(D["subject_prefix"]).strip() + " ", 1)
open(os.path.join(out_dir, "subject.txt"), "w", encoding="utf-8").write(subj)
open(os.path.join(out_dir, "email.html"), "w", encoding="utf-8").write(html_doc)
open(os.path.join(out_dir, "email.txt"), "w", encoding="utf-8").write("\n".join(L))
print(json.dumps({"subject": subj, "html_bytes": len(html_doc), "text_lines": len(L)}))
