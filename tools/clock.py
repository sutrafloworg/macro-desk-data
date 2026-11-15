#!/usr/bin/env python3
"""Desk clock: which closes are final, and is data/status.json fresh enough to use?

  python3 tools/clock.py [status.json]          -> JSON {now_et, run, cutoff_et, fresh, asof, generated_et, session_date}
  python3 tools/clock.py --gate [status.json]   -> "skip=true|false" for the GitHub workflow

US futures sessions end at 5 PM ET; with the data feed's 10-minute delay, closes are final from 5:20 PM ET.
The cutoff is the latest weekday 5:20 PM ET at or before now. Data is fresh when it was generated after the cutoff.
"""
import json, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
a = [x for x in sys.argv[1:] if not x.startswith("--")]
path = a[0] if a else "data/status.json"
now = datetime.now(ET)
cut = now.replace(hour=17, minute=20, second=0, microsecond=0)
if now < cut:
    cut -= timedelta(days=1)
while cut.weekday() >= 5:
    cut -= timedelta(days=1)
try:
    s = json.load(open(path, encoding="utf-8"))
    gen = datetime.fromisoformat(s["generated_utc"].replace("Z", "+00:00")).astimezone(ET)
    fresh = bool(s.get("ok")) and gen >= cut
except Exception:
    s, gen, fresh = {}, None, False
nxt = cut.date() + timedelta(days=1)
while nxt.weekday() >= 5:
    nxt += timedelta(days=1)
if "--gate" in sys.argv:
    print("skip=" + ("true" if fresh else "false"))
else:
    print(json.dumps({"now_et": now.strftime("%a %Y-%m-%d %H:%M"), "run": "evening" if now.hour >= 12 else "morning",
                      "cutoff_et": cut.strftime("%a %Y-%m-%d %H:%M"), "fresh": fresh, "asof": s.get("asof"),
                      "expected_asof": cut.date().isoformat(), "session_date": nxt.isoformat(),
                      "generated_et": gen.strftime("%a %Y-%m-%d %H:%M") if gen else None}))
