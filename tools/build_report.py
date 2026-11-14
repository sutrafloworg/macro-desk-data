#!/usr/bin/env python3
"""Build the nightly report skeleton (data.json) from the cloud collector's output.

  python3 build_report.py --latest latest.json --desk desk.json --status status.json \
      --record record.json --config config.json [--pick N] --out data.json

Fills every number deterministically: best prediction (candidate N, default 1), runners-up, forecast board,
validation, track record, regime monitor, tiles, scanner, curves, events, watchlist and headlines.
Claude then adds only the words: verdict, best_prediction.why / risks / invalidation, regime narrative,
news takes, and any ticket. Fields left for Claude are marked "TODO".
"""
import argparse, json
from datetime import date, datetime, time, timedelta
try:
    from zoneinfo import ZoneInfo
    NOW = datetime.now(ZoneInfo("America/New_York")).replace(tzinfo=None)
except Exception:
    NOW = datetime.utcnow() - timedelta(hours=5)

ap = argparse.ArgumentParser()
for k in ("latest", "desk", "status", "record", "config", "out"):
    ap.add_argument("--" + k)
ap.add_argument("--pick", type=int, default=1)
a = ap.parse_args()
J = lambda p, d=None: json.load(open(p, encoding="utf-8")) if p else (d if d is not None else {})
L, DS, ST = J(a.latest), J(a.desk), J(a.status, {})
REC = J(a.record, {}) if a.record else {}
CFG = J(a.config, {}) if a.config else {}

asof = L.get("asof") or ""
nxt = date.fromisoformat(asof) + timedelta(days=1) if asof else date.today()
while nxt.weekday() >= 5:
    nxt += timedelta(days=1)
session = nxt.strftime("%A, %b ") + str(nxt.day) + nxt.strftime(", %Y")

best = L.get("best") or []
pick = best[a.pick - 1] if 0 < a.pick <= len(best) else (best[0] if best else None)


def prob_of(b):
    if not b:
        return None
    if b.get("kind") == "setup" and b.get("pWin") is not None:
        return b["pWin"]
    pu = b.get("pUp")
    if pu is None:
        return None
    return round(pu if b.get("dir") == "LONG" else 100 - pu, 1)


def exp_move(b):
    board = {x["sym"]: x for x in (L.get("forecast") or {}).get("board", [])}
    x = board.get(b["sym"])
    if not x:
        return None
    pct = x.get("expPct")
    return None if pct is None else ("+" if pct > 0 else "") + str(pct) + "%"


bp = {}
if pick:
    pl = pick.get("plan") or {}
    drivers = []
    for d in pick.get("drivers") or []:
        drivers.append(f'{d["f"][0].upper() + d["f"][1:]} is {d["state"]}: pushes {d["effect"]}')
    if pick.get("kind") == "setup":
        drivers.insert(0, f'{pick.get("basis")} fired on the latest close')
    bp = {
        "name": pick["name"], "sym": pick["sym"], "dir": pick["dir"], "kind": pick.get("kind"), "grade": pick.get("grade"),
        "instrument": ("PAPER · " if not CFG.get("live_mode") else "") + (pick.get("front") or pick["sym"].split(":")[1].replace("1!", "")),
        "basis": pick.get("basis"), "prob": prob_of(pick), "pUp": pick.get("pUp"), "exp_move": exp_move(pick),
        "ref": pl.get("ref"), "stop": pl.get("stop"), "target": pl.get("target"), "hold": pl.get("hold"), "atr": pl.get("atr"),
        "size": pl.get("size"), "risk_usd": ("$" + format(pl["riskUSD"], ",")) if pl.get("riskUSD") else None,
        "band": pick.get("band"), "history": pick.get("history"), "drivers": drivers[:4], "model": pick.get("model"),
        "why": "TODO", "risks": ["TODO"], "invalidation": "TODO", "asof": asof,
    }

# ---------- the exact trade plan (all numbers come from the engine's plan) ----------
MICRO = {"MCL": "Micro WTI Crude Oil", "MNG": "Micro Henry Hub Natural Gas", "MGC": "Micro Gold", "SIL": "Micro Silver (1,000 oz)", "MHG": "Micro Copper",
         "MES": "Micro E-mini S&P 500", "MNQ": "Micro E-mini Nasdaq-100", "M2K": "Micro E-mini Russell 2000", "MYM": "Micro E-mini Dow", "M6E": "Micro EUR/USD",
         "MJY": "Micro JPY/USD", "M6B": "Micro GBP/USD", "M6A": "Micro AUD/USD", "MCD": "Micro CAD/USD", "XC": "Mini Corn", "YK": "Mini Soybeans", "XW": "Mini Wheat",
         "MBT": "Micro Bitcoin", "MET": "Micro Ether"}
# session open (ET) by market root; evening opens belong to the next day's session
OPEN = {"ZC": (20, 0, -1), "ZS": (20, 0, -1), "ZW": (20, 0, -1), "LE": (9, 30, 0), "HE": (9, 30, 0), "KC": (4, 15, 0), "SB": (3, 30, 0), "CC": (4, 45, 0), "CT": (21, 0, -1)}


def num(x):
    if x is None:
        return "-"
    s = (f"{x:,.0f}" if abs(x) >= 1000 else f"{x:,}") if isinstance(x, (int, float)) else str(x)
    return s[:-2] if s.endswith(".0") else s


def bday_add(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def dlabel(d):
    return d.strftime("%a %b ") + str(d.day)


trade = {}
if pick:
    pl = pick.get("plan") or {}
    root = pick["sym"].split(":")[1].replace("1!", "")
    front = pick.get("front") or ""
    month = front[len(root):] if front.startswith(root) else ""
    size = str(pl.get("size") or "")
    sizeable = " x" in size and not size.upper().startswith("NOT")
    tok = size.split(" x")[0].replace("(mini)", "").strip() if sizeable else root
    qty = int(size.split(" x")[1].split()[0]) if sizeable else None
    long_ = pick["dir"] == "LONG"
    ref, stop, tgt, atr, hold = pl.get("ref"), pl.get("stop"), pl.get("target"), pl.get("atr") or 0, int(pl.get("hold") or 10)
    lo, hi = (ref - 0.5 * atr, ref + 0.5 * atr) if ref is not None else (None, None)
    rnd = lambda v: None if v is None else float(f"{v:.6g}")
    h, m, off = OPEN.get(root, (18, 0, -1))
    open_dt = datetime.combine(nxt + timedelta(days=off), time(h, m))
    if off < 0 and nxt.weekday() == 0:
        open_dt = datetime.combine(nxt - timedelta(days=1), time(h, m))  # Monday's session opens Sunday evening
    t12 = open_dt.strftime("%I:%M %p").lstrip("0")
    verb = "Buy" if long_ else "Sell"
    if NOW >= open_dt:
        when = f"{verb} at market when you read this. The {nxt.strftime('%A')} session opened {dlabel(open_dt.date())}, {t12} ET."
    else:
        when = f"{verb} at market at the open: {dlabel(open_dt.date())}, {t12} ET."
    exit_d = bday_add(date.fromisoformat(asof), hold)
    risk = abs(ref - stop) if ref is not None and stop is not None else None
    rr = round(abs(tgt - ref) / risk, 1) if tgt is not None and risk else None
    g = pick.get("grade")
    trade = {
        "action": "BUY" if long_ else "SELL SHORT", "market": pick["name"], "product": MICRO.get(tok, pick["name"] + " futures"),
        "contract": tok + month, "front": front, "qty": qty, "sizeable": sizeable, "paper": not CFG.get("live_mode"),
        "entry_when": when, "entry_lo": rnd(lo), "entry_hi": rnd(hi), "ref": ref,
        "entry_rule": f"Only if the price is between {num(rnd(lo))} and {num(rnd(hi))} (last close {num(ref)}). Outside that range, skip the trade.",
        "stop": stop, "stop_pct": round(100 * (stop - ref) / abs(ref), 1) if ref else None, "stop_order": ("Sell" if long_ else "Buy") + " stop",
        "target": tgt, "reward_risk": rr, "exit_date": exit_d.isoformat(), "exit_label": dlabel(exit_d), "hold": hold,
        "exit_rule": (f"Take profit at {num(tgt)} ({rr}x the risk). " if tgt is not None else "No fixed target. ") + f"If neither stop nor target is hit, close at the settlement on {dlabel(exit_d)} (session {hold}).",
        "max_loss_usd": pl.get("riskUSD"), "gain_at_target_usd": round(pl["riskUSD"] * rr) if pl.get("riskUSD") and rr else None,
        "risk_pct_equity": round(100 * pl["riskUSD"] / CFG.get("equity_usd", 100000), 2) if pl.get("riskUSD") else None,
        "chance": prob_of(pick), "grade": g, "conviction": {"A": "High", "B": "Medium"}.get(g, "Low"),
        "contract_override": "",  # Claude: put the next contract symbol here (e.g. MBTZ2026) if the front one expires or hits first notice before exit_date
        "note": "" if sizeable else "One contract risks more than the per-trade budget, so this one is paper-only: track it, do not size it.",
    }

alts = [{"name": b["name"], "dir": b["dir"], "prob": prob_of(b), "grade": b.get("grade"), "basis": b.get("basis")} for b in best if not pick or b["sym"] != pick["sym"]][:3]

meta = L.get("meta") or {}
data = {
    "session_label": session, "session_date": nxt.isoformat(), "asof_label": "Closes of " + asof + " · data via " + str(L.get("source") or ST.get("source")),
    "run_mode": "FULL", "data_note": "Cloud run · " + ("TradingView data" if "tradingview" in str(ST.get("source")) else "public data (Yahoo/FRED/CFTC)"),
    "engine": {"version": meta.get("engine"), "secs": meta.get("secs"), "errors": (meta.get("errors") or [])[:12]},
    "verdict": {"stance": "WATCH", "headline": "TODO", "summary": "TODO", "no_trade_reason": ""},
    "best_prediction": bp, "trade": trade, "alternatives": alts,
    "forecast_board": DS.get("forecast_board") or [], "forecast_validation": DS.get("forecast_validation"),
    "forecast_record": REC, "trades": [], "positions": [],
    "regime": {"label": (L.get("regime") or {}).get("quadrant"), "asof": (L.get("regime") or {}).get("asof"), "narrative": "TODO"},
    "macro_tiles": DS.get("macro_tiles") or [], "macro_trend": DS.get("macro_trend") or {}, "scanner": DS.get("scanner") or [],
    "base_rates": DS.get("base_rates") or {}, "curves": (DS.get("curves") or [])[:12], "events": (DS.get("events") or [])[:15],
    "watch": (DS.get("watch") or [])[:10], "news": [{"t": n.get("t"), "title": n.get("title"), "take": ""} for n in (DS.get("news") or [])[:8]],
    "sources": [],
}
json.dump(data, open(a.out, "w", encoding="utf-8"), indent=1)
print(json.dumps({"session": session, "session_date": nxt.isoformat(), "asof": asof, "best": bp.get("name"), "dir": bp.get("dir"), "prob": bp.get("prob"), "grade": bp.get("grade"), "trade": {k: trade.get(k) for k in ("action", "contract", "qty", "entry_when", "entry_rule", "stop", "exit_rule", "max_loss_usd")},
                  "candidates": [f'{b["rank"]}. {b["name"]} {b["dir"]} ({b.get("kind")}, grade {b.get("grade")}, chance {prob_of(b)}%)' for b in best]}))
