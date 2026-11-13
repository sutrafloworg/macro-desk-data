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
from datetime import date, timedelta

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
alts = [{"name": b["name"], "dir": b["dir"], "prob": prob_of(b), "grade": b.get("grade"), "basis": b.get("basis")} for b in best if not pick or b["sym"] != pick["sym"]][:3]

meta = L.get("meta") or {}
data = {
    "session_label": session, "session_date": nxt.isoformat(), "asof_label": "Closes of " + asof + " · data via " + str(L.get("source") or ST.get("source")),
    "run_mode": "FULL", "data_note": "Cloud run · " + ("TradingView data" if "tradingview" in str(ST.get("source")) else "public data (Yahoo/FRED/CFTC)"),
    "engine": {"version": meta.get("engine"), "secs": meta.get("secs"), "errors": (meta.get("errors") or [])[:12]},
    "verdict": {"stance": "WATCH", "headline": "TODO", "summary": "TODO", "no_trade_reason": ""},
    "best_prediction": bp, "alternatives": alts,
    "forecast_board": DS.get("forecast_board") or [], "forecast_validation": DS.get("forecast_validation"),
    "forecast_record": REC, "trades": [], "positions": [],
    "regime": {"label": (L.get("regime") or {}).get("quadrant"), "asof": (L.get("regime") or {}).get("asof"), "narrative": "TODO"},
    "macro_tiles": DS.get("macro_tiles") or [], "macro_trend": DS.get("macro_trend") or {}, "scanner": DS.get("scanner") or [],
    "base_rates": DS.get("base_rates") or {}, "curves": (DS.get("curves") or [])[:12], "events": (DS.get("events") or [])[:15],
    "watch": (DS.get("watch") or [])[:10], "news": [{"t": n.get("t"), "title": n.get("title"), "take": ""} for n in (DS.get("news") or [])[:8]],
    "sources": [],
}
json.dump(data, open(a.out, "w", encoding="utf-8"), indent=1)
print(json.dumps({"session": session, "session_date": nxt.isoformat(), "asof": asof, "best": bp.get("name"), "dir": bp.get("dir"), "prob": bp.get("prob"), "grade": bp.get("grade"),
                  "candidates": [f'{b["rank"]}. {b["name"]} {b["dir"]} ({b.get("kind")}, grade {b.get("grade")}, chance {prob_of(b)}%)' for b in best]}))
