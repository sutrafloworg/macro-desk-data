# Macro Futures Desk: cloud data collector

Runs every weekday evening (Mon–Fri) on GitHub Actions once the US futures closes are final (5:20 PM ET), and commits the results to `data/`:

| File | What it holds |
|---|---|
| `data/status.json` | When the run happened, which data source worked, errors |
| `data/latest.json` | Engine output: the ranked **best prediction** candidates, the 33-market forecast board, its out-of-sample validation, setups, macro regime, curves, calendar, headlines |
| `data/desk.json` | The same data shaped for the dashboard |
| `data/prices.json` | Last 160 daily bars per market (used to score past predictions) |
| `data/archive/<date>.json` | One small record per day: best candidates, top of the board, validation |

A Claude scheduled task reads these files at 6:50 PM ET (Mon–Fri), adds research, publishes the dashboard and emails
the trade plan. If the data is late, a 6:50 AM ET run the next morning sends it instead. Nothing runs on a personal computer.

Data: TradingView's public chart feed (continuous back-adjusted futures, front/next contract carry, CFTC
positioning). If that feed refuses the runner, it falls back automatically to Yahoo Finance daily bars, FRED and the
CFTC public API (no carry in that mode).

Research tool, not financial advice. Futures are leveraged.

To publish changes made in this folder: `powershell -ExecutionPolicy Bypass -File update.ps1`
