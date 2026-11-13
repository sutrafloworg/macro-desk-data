#!/usr/bin/env python3
"""Track record of the daily "best prediction" (paper only).

  python3 forecast_ledger.py --json STATE.json add '<JSON list of rows>'
  python3 forecast_ledger.py --json STATE.json score PRICES.json
  python3 forecast_ledger.py --json STATE.json stats

STATE.json is {"rows": [...]} (the dashboard doc state/forecasts). PRICES.json is data/prices.json from the
collector: {"prices": {sym: {"bars": [[date, o, h, l, c], ...]}}}.

A row: {id, date (signal session), sym, name, dir LONG|SHORT, ref (close), atr, stop, target (or null), hold,
prob (model %), grade, kind, basis}. Scoring: enter at the next session's open, stop first if a bar touches both,
target if set, otherwise exit at the close of session `hold`. R = move / (entry-to-stop distance), minus 0.02R costs.
"Direction right" = close after `hold` sessions vs the signal close, in the called direction.
"""
import json, sys
from datetime import datetime, timezone

COST = 0.02


def load(p):
    try:
        d = json.load(open(p, encoding="utf-8"))
    except FileNotFoundError:
        d = {}
    if "data" in d and "rows" not in d:
        d = d["data"]
    d.setdefault("rows", [])
    return d


def save(p, d):
    d["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1)


def add(d, rows):
    n = len(d["rows"])
    out = []
    for r in rows:
        dup = [x for x in d["rows"] if x.get("date") == r.get("date") and x.get("sym") == r.get("sym") and x.get("dir") == r.get("dir")]
        if dup:
            out.append(dup[0]["id"])
            continue
        n += 1
        r = dict(r)
        r["id"] = r.get("id") or "F%03d" % n
        r["status"] = "OPEN"
        r.setdefault("hold", 10)
        d["rows"].append(r)
        out.append(r["id"])
    return out


def score_row(r, bars):
    dates = [b[0] for b in bars]
    if r["date"] not in dates:
        later = [i for i, x in enumerate(dates) if x > r["date"]]
        if not later:
            return {"status": "OPEN", "note": "no session since signal"}
        i = later[0] - 1
        if i < 0:
            return {"status": "OPEN", "note": "signal date older than price history"}
    else:
        i = dates.index(r["date"])
    if i + 1 >= len(bars):
        return {"status": "OPEN", "note": "enters at the next open"}
    d = 1 if r["dir"] == "LONG" else -1
    entry = bars[i + 1][1]
    stop = float(r["stop"])
    risk = abs(entry - stop) or float(r.get("atr") or 1)
    tgt = r.get("target")
    tgt = float(tgt) if tgt not in (None, "") else None
    hold = int(r.get("hold") or 10)
    last_i = len(bars) - 1
    res = None
    for j in range(i + 1, min(last_i, i + hold) + 1):
        o, h, l, c = bars[j][1:5]
        if j > i + 1 and ((d > 0 and o <= stop) or (d < 0 and o >= stop)):
            res = ("STOP", (o - entry) * d / risk - COST, j); break
        hit_s = l <= stop if d > 0 else h >= stop
        hit_t = tgt is not None and (h >= tgt if d > 0 else l <= tgt)
        if hit_s:
            res = ("STOP", -1 - COST, j); break
        if hit_t:
            res = ("TARGET", abs(tgt - entry) / risk - COST, j); break
    done = i + hold <= last_i
    if res is None and done:
        j = i + hold
        res = ("TIME", (bars[j][4] - entry) * d / risk - COST, j)
    jj = min(last_i, i + hold)
    move = (bars[jj][4] - bars[i][4]) * d
    out = {"entry": round(entry, 6), "sessions": last_i - i, "last": bars[-1][4], "R_now": round((bars[-1][4] - entry) * d / risk, 2)}
    if res:
        out.update({"status": "CLOSED", "exit": res[0], "exit_date": bars[res[2]][0], "R": round(res[1], 2)})
    else:
        out["status"] = "OPEN"
    if done:
        out["dir_right"] = move > 0
        out["move_atr"] = round(move / float(r.get("atr") or risk / 2), 2)
    return out


def score(d, prices):
    P = prices.get("prices", prices)
    for r in d["rows"]:
        if r.get("status") == "CLOSED" and "dir_right" in r:
            continue
        p = P.get(r["sym"])
        if not p:
            r["note"] = "no prices for " + r["sym"]
            continue
        r.update(score_row(r, p["bars"]))


def stats(d):
    rows = d["rows"]
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    judged = [r for r in rows if "dir_right" in r]
    Rs = [r["R"] for r in closed if r.get("R") is not None]
    curve, s = [], 0.0
    for r in sorted(closed, key=lambda x: x.get("exit_date") or ""):
        s += r["R"]; curve.append(round(s, 2))
    return {
        "calls": len(rows), "closed": len(closed), "open": len(rows) - len(closed),
        "win_pct": round(100 * sum(1 for x in Rs if x > 0) / len(Rs), 1) if Rs else None,
        "avgR": round(sum(Rs) / len(Rs), 2) if Rs else None, "sumR": round(sum(Rs), 2) if Rs else 0,
        "dir_right_pct": round(100 * sum(1 for r in judged if r["dir_right"]) / len(judged), 1) if judged else None,
        "judged": len(judged), "curve": curve,
        "recent": [{k: r.get(k) for k in ("id", "date", "name", "dir", "grade", "status", "exit", "R", "R_now", "dir_right")} for r in rows[-12:]][::-1],
    }


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 3 or a[0] != "--json":
        sys.exit(__doc__)
    path, cmd = a[1], a[2]
    d = load(path)
    if cmd == "add":
        rows = json.loads(a[3] if len(a) > 3 else sys.stdin.read())
        print(json.dumps(add(d, rows if isinstance(rows, list) else [rows])))
        save(path, d)
    elif cmd == "score":
        score(d, json.load(open(a[3], encoding="utf-8")))
        save(path, d)
        print(json.dumps(stats(d)))
    elif cmd == "stats":
        print(json.dumps(stats(d)))
    else:
        sys.exit(__doc__)
