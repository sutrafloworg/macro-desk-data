#!/usr/bin/env python3
"""Render the nightly Macro Futures Desk email from the report JSON.

  python3 email_report.py DATA.json OUT_DIR [--dashboard URL]

Writes OUT_DIR/subject.txt, OUT_DIR/email.html and OUT_DIR/email.txt.
The layout is fixed here so every email looks the same; the run only supplies data.
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


def clip(s, n):
    s = "" if s is None else str(s).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def first_sentences(s, n=2, limit=320):
    s = "" if s is None else str(s).strip()
    parts, out = s.replace("\n", " ").split(". "), []
    for p in parts:
        out.append(p.rstrip("."))
        if len(out) >= n:
            break
    txt = ". ".join(out).strip()
    return clip(txt + ("." if txt and not txt.endswith((".", "!", "?")) else ""), limit)


V = D.get("verdict") or {}
stance = str(V.get("stance") or "STAND ASIDE").upper()
headline = V.get("headline") or ""
T = D.get("trades") or []
MT = D.get("macro_trend") or {}
W = D.get("watch") or []
P = D.get("positions") or []
E = D.get("events") or []
N = D.get("news") or []
mode = D.get("run_mode") or ""
eng = D.get("engine") or {}
session = (D.get("session_label") or "").split(" (")[0]
BP = D.get("best_prediction") or {}
ALT = D.get("alternatives") or []
REC = D.get("forecast_record") or {}
VAL = D.get("forecast_validation") or {}

C = {"ink": "#12202B", "ink2": "#34454F", "muted": "#5E6E7B", "rule": "#E4E9EE", "bg": "#EDF0F3", "card": "#FFFFFF",
     "long": "#0B7A5A", "longbg": "#DDF2EA", "short": "#B2372F", "shortbg": "#F8E1DE", "warn": "#A8690C", "warnbg": "#FBEFD9",
     "acc": "#2952B8", "accbg": "#E3EAFA", "flat": "#6A7885", "flatbg": "#E8ECEF"}
stance_col = C["long"] if stance.startswith("TRADE") else C["warn"] if stance.startswith("WATCH") else C["flat"]
FONT = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "font-family:SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace"


def chip(text, fg, bg):
    return f'<span style="display:inline-block;padding:3px 8px;border-radius:4px;background:{bg};color:{fg};font:700 11px/1.2 Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase">{e(text)}</span>'


def side_chip(d):
    d = str(d or "").upper()
    return chip(d or "-", C["long"] if d == "LONG" else C["short"] if d == "SHORT" else C["flat"],
                C["longbg"] if d == "LONG" else C["shortbg"] if d == "SHORT" else C["flatbg"])


def section(title, inner, sub=""):
    s = f'<div style="{FONT};font-size:13px;color:{C["muted"]};margin:2px 0 10px">{e(sub)}</div>' if sub else ""
    return (f'<tr><td style="padding:22px 24px 4px"><div style="{FONT};font-size:12px;font-weight:700;letter-spacing:.1em;'
            f'text-transform:uppercase;color:{C["ink2"]};border-bottom:2px solid {C["ink"]};padding-bottom:6px;margin-bottom:10px">{e(title)}</div>{s}{inner}</td></tr>')


def table(headers, rows, aligns=None):
    aligns = aligns or ["left"] * len(headers)
    th = "".join(f'<th align="{a}" style="{FONT};font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{C["muted"]};padding:6px 8px;border-bottom:1px solid {C["rule"]}">{e(h)}</th>' for h, a in zip(headers, aligns))
    trs = ""
    for r in rows:
        trs += "<tr>" + "".join(f'<td align="{a}" style="{FONT};font-size:14px;color:{C["ink"]};padding:8px;border-bottom:1px solid {C["rule"]};vertical-align:top">{c}</td>' for c, a in zip(r, aligns)) + "</tr>"
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">{"<tr>" + th + "</tr>"}{trs}</table>'


# ---------- header ----------
parts = []
parts.append(
    f'<tr><td style="background:{C["ink"]};padding:18px 24px">'
    f'<div style="{FONT};font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#AFC0CC">Claude · Macro Futures Desk</div>'
    f'<div style="{FONT};font-size:20px;font-weight:700;color:#FFFFFF;margin-top:4px">{e(session or "Nightly report")}</div>'
    f'</td></tr>')
parts.append(
    f'<tr><td style="padding:20px 24px 6px">'
    f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
    f'<td style="background:{stance_col};color:#fff;{FONT};font-weight:700;font-size:14px;letter-spacing:.1em;padding:8px 12px;border-radius:5px">{e(stance)}</td>'
    f'<td style="padding-left:12px;{FONT};font-size:12px;color:{C["muted"]}">{e(mode.title())} run · engine {e(eng.get("version", "-"))}</td></tr></table>'
    f'<div style="{FONT};font-size:18px;line-height:1.35;font-weight:700;color:{C["ink"]};margin-top:12px">{e(headline)}</div>'
    f'<div style="{FONT};font-size:14px;line-height:1.55;color:{C["ink2"]};margin-top:8px">{e(first_sentences(V.get("summary"), 3, 420))}</div>'
    f'</td></tr>')
if mode.upper() == "DEGRADED":
    parts.append(f'<tr><td style="padding:10px 24px 0"><div style="background:{C["warnbg"]};color:{C["warn"]};{FONT};font-size:13px;padding:10px 12px;border-radius:6px"><b>Degraded run:</b> {e(first_sentences(D.get("data_note"), 1, 220))}</div></td></tr>')

# ---------- best prediction ----------
def fmt(x):
    return "-" if x in (None, "") else str(x)


if BP.get("name"):
    d = str(BP.get("dir", "")).upper()
    col, bg = (C["long"], C["longbg"]) if d == "LONG" else (C["short"], C["shortbg"])
    verb = "UP" if d == "LONG" else "DOWN"
    grade = str(BP.get("grade") or "")
    gcol = {"A": C["long"], "B": C["acc"]}.get(grade, C["flat"])
    band = BP.get("band") or []
    cells = [("Chance it's right", f'{BP.get("prob")}%' if BP.get("prob") is not None else None),
             ("Expected move", BP.get("exp_move")), ("Horizon", f'{BP.get("hold")} sessions' if BP.get("hold") else None),
             ("Reference", BP.get("ref")), ("Stop", BP.get("stop")), ("Target", BP.get("target") or "time exit"),
             ("Likely range (80%)", f'{band[0]} – {band[1]}' if len(band) == 2 else None), ("Size (paper)", BP.get("size")), ("Risk at stop", BP.get("risk_usd"))]
    grid = ""
    for i, (k, v) in enumerate(cells):
        grid += (f'<td width="33%" style="padding:8px 10px;border-top:1px solid {C["rule"]};vertical-align:top"><div style="{FONT};font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:{C["muted"]}">{k}</div>'
                 f'<div style="{MONO};font-size:14px;font-weight:700;color:{C["ink"]};margin-top:2px">{e(fmt(v))}</div></td>') + ("</tr><tr>" if i in (2, 5) else "")
    drv = "".join(f'<li style="margin:2px 0">{e(x)}</li>' for x in (BP.get("drivers") or [])[:4])
    rk = "".join(f'<li style="margin:2px 0">{e(x)}</li>' for x in (BP.get("risks") or [])[:3])
    card = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:2px solid {col};border-radius:8px">'
            f'<tr><td colspan="3" style="padding:12px 14px;background:{bg}">'
            f'<div style="{FONT};font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:{col};font-weight:700">Best prediction · next {e(BP.get("hold") or 10)} sessions</div>'
            f'<div style="{FONT};font-size:22px;font-weight:800;color:{C["ink"]};margin-top:4px">{e(BP.get("name"))} {chip(verb, "#fff", col)} {chip("Grade " + grade, "#fff", gcol) if grade else ""}</div>'
            f'<div style="{MONO};font-size:12px;color:{C["muted"]};margin-top:4px">{e(BP.get("instrument") or "")}{" · " if BP.get("instrument") else ""}{e(BP.get("basis") or "")}</div></td></tr>'
            f'<tr>{grid}</tr>'
            f'<tr><td colspan="3" style="padding:10px 14px;border-top:1px solid {C["rule"]};{FONT};font-size:14px;line-height:1.55;color:{C["ink2"]}">{e(first_sentences(BP.get("why"), 3, 460))}'
            + (f'<div style="margin-top:8px;font-size:13px"><b style="color:{C["ink"]}">Why the model leans this way</b><ul style="margin:4px 0 0;padding-left:18px">{drv}</ul></div>' if drv else "")
            + (f'<div style="margin-top:8px;font-size:13px"><b style="color:{C["short"]}">What could break it</b><ul style="margin:4px 0 0;padding-left:18px">{rk}</ul></div>' if rk else "")
            + (f'<div style="margin-top:6px;font-size:13px"><b style="color:{C["short"]}">Wrong if:</b> {e(clip(BP.get("invalidation"), 200))}</div>' if BP.get("invalidation") else "")
            + (f'<div style="margin-top:8px;font-size:12px;color:{C["muted"]}">{e(clip(BP.get("history"), 260))}</div>' if BP.get("history") else "")
            + '</td></tr></table>')
    if ALT:
        rows = [[f'<b>{e(a.get("name"))}</b>', side_chip(a.get("dir")), f'<span style="{MONO}">{e(fmt(a.get("prob")))}%</span>', f'<span style="font-size:12px;color:{C["muted"]}">{e(clip(a.get("basis"), 60))}</span>'] for a in ALT[:3]]
        card += f'<div style="{FONT};font-size:12px;font-weight:700;color:{C["ink2"]};margin:14px 0 4px">Runners-up</div>' + table(["Market", "Call", "Chance", "Basis"], rows)
    sub = "Paper call, scored automatically after the horizon."
    if VAL.get("topPick"):
        tp = VAL["topPick"]; tr = VAL.get("tradePlan") or {}
        sub = (f"Model's daily top pick, tested {VAL.get('span', '')} on data it had not seen: right {tp.get('hit')}% of {tp.get('n')} days"
               + (f"; as a stop + 10-day exit plan {tr.get('win')}% won, average {'+' if (tr.get('expR') or 0) > 0 else ''}{tr.get('expR')}R." if tr.get("n") else "."))
    parts.append(section("Today's best prediction", card, sub))
    if REC.get("calls"):
        rec = (f'<div style="{FONT};font-size:14px;color:{C["ink2"]}">{REC.get("calls")} calls so far · {REC.get("closed")} closed'
               + (f' · {REC.get("win_pct")}% won · average {REC.get("avgR")}R · total {REC.get("sumR")}R' if REC.get("closed") else "")
               + (f' · direction right {REC.get("dir_right_pct")}% of {REC.get("judged")}' if REC.get("judged") else "") + '</div>')
        rr = [[e(r.get("date")), f'<b>{e(r.get("name"))}</b>', side_chip(r.get("dir")), e(r.get("exit") or r.get("status")),
               f'<span style="{MONO}">{e(r.get("R") if r.get("R") is not None else r.get("R_now"))}R</span>'] for r in (REC.get("recent") or [])[:5]]
        parts.append(section("Prediction track record", rec + (table(["Date", "Market", "Call", "Status", "R"], rr, ["left", "left", "left", "left", "right"]) if rr else "")))

# ---------- tickets ----------
if T:
    cards = ""
    for t in T:
        d = str(t.get("dir", "")).upper()
        verb = "BUY" if d == "LONG" else "SELL"
        col, bg = (C["long"], C["longbg"]) if d == "LONG" else (C["short"], C["shortbg"])
        cells = [("Entry", t.get("entry")), ("Stop", t.get("stop")), ("Target 1", t.get("target1")),
                 ("Size", t.get("size")), ("P(win)", f'{t.get("pwin")}%' if t.get("pwin") is not None else None), ("Conviction", f'{t.get("conviction")}/100' if t.get("conviction") is not None else None)]
        grid = "".join(
            f'<td width="33%" style="padding:8px 10px;border-top:1px solid {C["rule"]};vertical-align:top"><div style="{FONT};font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:{C["muted"]}">{k}</div>'
            f'<div style="{MONO};font-size:14px;font-weight:700;color:{C["ink"]};margin-top:2px">{e(v if v not in (None, "") else "-")}</div></td>'
            + ("</tr><tr>" if i == 2 else "") for i, (k, v) in enumerate(cells))
        cards += (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid {C["rule"]};border-left:4px solid {col};border-radius:6px;margin-bottom:12px">'
                  f'<tr><td colspan="3" style="padding:10px 12px">{chip(verb, "#fff", col)} <span style="{FONT};font-size:16px;font-weight:700;color:{C["ink"]}">{e(t.get("name"))}</span>'
                  f'<div style="{MONO};font-size:12px;color:{C["muted"]};margin-top:4px">{e(t.get("instrument"))} · {e(t.get("setup_name"))}</div></td></tr>'
                  f'<tr>{grid}</tr>'
                  f'<tr><td colspan="3" style="padding:10px 12px;border-top:1px solid {C["rule"]};{FONT};font-size:13px;line-height:1.5;color:{C["ink2"]}">'
                  f'{e(first_sentences(t.get("thesis"), 2, 300))}'
                  + (f'<div style="margin-top:6px"><b style="color:{C["short"]}">Invalidated if:</b> {e(clip(t.get("invalidation"), 200))}</div>' if t.get("invalidation") else "")
                  + (f'<div style="margin-top:6px;color:{C["muted"]};font-size:12px">{e(clip(t.get("risk_note"), 160))}</div>' if t.get("risk_note") else "")
                  + '</td></tr></table>')
    parts.append(section(f"Trade tickets ({len(T)})", cards, "Orders for the next session. PAPER until the ledger proves the edge."))
else:
    reason = V.get("no_trade_reason") or ""
    parts.append(section("Trade tickets", f'<div style="background:{C["flatbg"]};border-radius:6px;padding:12px 14px;{FONT};font-size:14px;color:{C["ink2"]}"><b style="color:{C["ink"]}">No trade today.</b> Nothing cleared the bar (conviction ≥ 65, qscore ≥ 30, positive expectancy).'
                         + (f'<div style="margin-top:6px;font-size:12px;color:{C["muted"]}">{e(clip(reason, 240))}</div>' if reason else "") + '</div>'))

# ---------- regime ----------
if MT.get("quadrant"):
    names = [("growth", "Growth"), ("inflation", "Inflation"), ("policy", "Policy"), ("liquidity", "Liquidity"), ("risk", "Risk appetite")]
    rows = ""
    for k, lab in names:
        p = (MT.get("pillars") or {}).get(k) or {}
        s = p.get("score")
        v = 0 if s is None else max(-1, min(1, float(s)))
        w = int(round(abs(v) * 50))
        left = 50 - w if v < 0 else 50
        barcol = C["warn"] if v < 0 else C["acc"]
        d20 = p.get("d20")
        d20s = "" if d20 in (None, 0) else f' <span style="color:{C["warn"] if abs(d20) >= .5 else C["muted"]}">({"+" if d20 > 0 else ""}{d20} in 20d)</span>'
        bar = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="height:8px"><tr>'
               + (f'<td width="{left}%" style="background:{C["rule"]};font-size:0;line-height:0">&nbsp;</td>' if left else "")
               + (f'<td width="{w}%" style="background:{barcol};font-size:0;line-height:0">&nbsp;</td>' if w else "")
               + (f'<td style="background:{C["rule"]};font-size:0;line-height:0">&nbsp;</td>' if left + w < 100 else "")
               + '</tr></table>')
        rows += (f'<tr><td style="{FONT};font-size:13px;color:{C["ink2"]};padding:8px 0 3px">{lab}</td>'
                 f'<td align="right" style="{FONT};font-size:13px;color:{C["ink"]};padding:8px 0 3px"><b>{e(p.get("label", "-"))}</b> <span style="{MONO};color:{C["muted"]}">{e(s)}</span>{d20s}</td></tr>'
                 f'<tr><td colspan="2" style="padding:0 0 4px">{bar}</td></tr>')
    quad = MT.get("quadrant")
    qcol = {"Reflation": C["long"], "Goldilocks": C["acc"], "Stagflation": C["warn"], "Deflationary slowdown": C["short"]}.get(quad, C["ink"])
    alerts = [a for a in (MT.get("alerts") or []) if any(x in a for x in ("Regime shift", "pillar moved", "shock"))][:3]
    al = "".join(f'<li style="margin:3px 0">{e(a)}</li>' for a in alerts)
    fav = ", ".join(f'{x["name"]}' for x in (MT.get("favored") or [])[:4])
    dis = ", ".join(f'{x["name"]}' for x in (MT.get("disfavored") or [])[:4])
    inner = (f'<div style="{FONT};font-size:22px;font-weight:700;color:{qcol}">{e(quad)} <span style="font-size:13px;color:{C["muted"]};font-weight:400">day {e(MT.get("ageSessions"))} · was {e(MT.get("prior20"))} 20 sessions ago</span></div>'
             f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px">{rows}</table>'
             + (f'<ul style="{FONT};font-size:13px;color:{C["warn"]};margin:10px 0 0;padding-left:18px">{al}</ul>' if al else "")
             + (f'<div style="{FONT};font-size:13px;color:{C["ink2"]};margin-top:10px"><b style="color:{C["long"]}">Tends to rise now:</b> {e(fav)}<br><b style="color:{C["short"]}">Tends to fall now:</b> {e(dis)}</div>' if fav else ""))
    parts.append(section("Macro regime", inner))

# ---------- watchlist ----------
if W:
    rows = [[f'<b>{e(w.get("name"))}</b>', side_chip(w.get("dir")), f'<span style="{MONO}">{e(w.get("trigger"))}</span>', f'<span style="{MONO};font-size:12px;color:{C["muted"]}">{e(w.get("base"))}</span>'] for w in W[:6]]
    parts.append(section("Watchlist", table(["Market", "Side", "Trigger", "Base rate"], rows), "Closest setups to triggering. Base rate = trades · win rate · average R."))

# ---------- positions ----------
if P:
    rows = [[f'<b>{e(p.get("name"))}</b><div style="{MONO};font-size:11px;color:{C["muted"]}">{e(p.get("instrument"))}</div>', side_chip(p.get("dir")), e(p.get("status")),
             f'<span style="{MONO}">{e(p.get("R"))}R</span>'] for p in P]
    parts.append(section("Open positions", table(["Market", "Side", "Status", "R"], rows, ["left", "left", "left", "right"])))
else:
    parts.append(section("Open positions", f'<div style="{FONT};font-size:14px;color:{C["muted"]}">None.</div>'))

# ---------- week ahead ----------
hi = [x for x in E if str(x.get("imp", "")).lower() == "high"] or E
if hi:
    rows = [[f'<span style="{MONO};font-size:12px;color:{C["muted"]}">{e(x.get("day"))} {e(x.get("time"))}</span>', e(clip(x.get("what"), 70)),
             f'<span style="{MONO};font-size:12px;color:{C["muted"]}">{e(x.get("markets"))}</span>'] for x in hi[:6]]
    parts.append(section("Key events", table(["When (ET)", "Event", "Moves"], rows)))

# ---------- news ----------
if N:
    items = "".join(
        f'<li style="margin:0 0 8px">' + (f'<a href="{e(n.get("url"))}" style="color:{C["acc"]};text-decoration:none">{e(n.get("title"))}</a>' if n.get("url") else e(n.get("title")))
        + (f'<div style="color:{C["muted"]};font-size:12px;margin-top:2px">{e(clip(n.get("take"), 160))}</div>' if n.get("take") else "") + '</li>'
        for n in N[:4])
    parts.append(section("What moved markets", f'<ul style="{FONT};font-size:14px;line-height:1.4;margin:0;padding-left:18px;color:{C["ink"]}">{items}</ul>'))

# ---------- footer ----------
parts.append(
    f'<tr><td style="padding:22px 24px 8px" align="center"><a href="{e(dash)}" style="display:inline-block;background:{C["acc"]};color:#fff;{FONT};font-weight:700;font-size:14px;text-decoration:none;padding:12px 22px;border-radius:6px">Open the live dashboard</a></td></tr>'
    f'<tr><td style="padding:12px 24px 22px;{FONT};font-size:11px;line-height:1.5;color:{C["muted"]}">Sent by Claude (scheduled cloud task). Predictions and tickets are PAPER and scored automatically. A 53–58% chance means it is wrong almost half the time; size so a string of losses is survivable. Base rates are history, not promises. Futures are leveraged and can lose more than the margin posted. Research tool, not financial advice.</td></tr>')

html_doc = (f'<!doctype html><html><body style="margin:0;padding:0;background:{C["bg"]}">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C["bg"]}"><tr><td align="center" style="padding:16px 8px">'
            f'<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="width:100%;max-width:640px;background:{C["card"]};border-radius:8px;overflow:hidden">'
            + "".join(parts) + '</table></td></tr></table></body></html>')

# ---------- plain text ----------
L = [f"CLAUDE · MACRO FUTURES DESK — {session}", ""]
if BP.get("name"):
    L += [f"BEST PREDICTION ({BP.get('hold') or 10} sessions): {BP.get('name')} {'UP' if str(BP.get('dir')).upper() == 'LONG' else 'DOWN'} · chance {BP.get('prob')}% · grade {BP.get('grade')}",
          f"  ref {BP.get('ref')}, stop {BP.get('stop')}, target {BP.get('target') or 'time exit'}, expected move {BP.get('exp_move')}, size {BP.get('size')} (risk {BP.get('risk_usd')})",
          "  " + first_sentences(BP.get("why"), 3, 460)]
    L += [f"  - {x}" for x in (BP.get("drivers") or [])[:4]]
    if BP.get("invalidation"):
        L.append(f"  Wrong if: {clip(BP.get('invalidation'), 200)}")
    if ALT:
        L.append("  Runners-up: " + "; ".join(f"{a.get('name')} {a.get('dir')} {a.get('prob')}%" for a in ALT[:3]))
    if REC.get("calls"):
        L.append(f"  Track record: {REC.get('calls')} calls, {REC.get('closed')} closed, avg {REC.get('avgR')}R, direction right {REC.get('dir_right_pct')}%")
    L.append("")
L += [f"{stance}: {headline}", first_sentences(V.get("summary"), 3, 420), ""]
if T:
    L.append("TRADE TICKETS")
    for t in T:
        L.append(f"- {'BUY' if str(t.get('dir')).upper() == 'LONG' else 'SELL'} {t.get('instrument')} ({t.get('name')}): entry {t.get('entry')}, stop {t.get('stop')}, target {t.get('target1')}, size {t.get('size')}, P(win) {t.get('pwin')}%, conviction {t.get('conviction')}/100")
else:
    L.append("TRADE TICKETS: none today.")
if MT.get("quadrant"):
    pl = MT.get("pillars") or {}
    L += ["", f"REGIME: {MT['quadrant']} (day {MT.get('ageSessions')})",
          "  " + " | ".join(f"{k.title()} {(pl.get(k) or {}).get('score')}" for k in ["growth", "inflation", "policy", "liquidity", "risk"])]
if W:
    L += ["", "WATCHLIST"] + [f"- {w.get('name')} {w.get('dir')}: {w.get('trigger')} (base {w.get('base')})" for w in W[:6]]
L += ["", "OPEN POSITIONS: " + ("none" if not P else "; ".join(f"{p.get('name')} {p.get('dir')} {p.get('R')}R" for p in P))]
if hi:
    L += ["", "KEY EVENTS"] + [f"- {x.get('day')} {x.get('time')}: {clip(x.get('what'), 70)}" for x in hi[:7]]
L += ["", f"Dashboard: {dash}", "Research tool, not financial advice."]

short_hl = headline.replace(";", ".").split(". ")[0].rstrip(".")
sess = session.replace('Report for the ', '').replace(' session', '')
if BP.get("name"):
    subj = f"[Claude] Best prediction · {sess} · {BP.get('name')} {'UP' if str(BP.get('dir')).upper() == 'LONG' else 'DOWN'} ({BP.get('prob')}%, grade {BP.get('grade')}) — {clip(short_hl, 60)}"
else:
    subj = f"[Claude] Macro Desk · {sess} · {stance} — {clip(short_hl, 70)}"
open(os.path.join(out_dir, "subject.txt"), "w", encoding="utf-8").write(subj)
open(os.path.join(out_dir, "email.html"), "w", encoding="utf-8").write(html_doc)
open(os.path.join(out_dir, "email.txt"), "w", encoding="utf-8").write("\n".join(L))
print(json.dumps({"subject": subj, "html_bytes": len(html_doc), "text_lines": len(L)}))
