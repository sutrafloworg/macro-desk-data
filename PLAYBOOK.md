# Macro Futures Desk: Playbook

This is the rulebook the daily run follows. It is the source of truth for scoring, sizing and risk.
Edit it to change the desk's behaviour; the scheduled task reads it at the start of every run.

## 0. What the desk is for

Find the one to three futures trades each day where the historical odds for the setup are in our favour,
the macro backdrop points the same way, and a clear catalyst is pushing the price. Then size each one so
that being wrong costs a fixed, small amount.

"No trade today" is a normal and often correct answer. The desk earns its keep by skipping mediocre
setups as much as by finding good ones.

## 0b. The daily best prediction (engine v2.0, cloud run)

Every evening the desk names ONE best prediction: a market, a direction, a 10-session horizon (a setup's own
hold if it comes from a validated setup), a chance it is right, a reference price, a stop and a likely range.
It is a paper call, logged in `state/forecasts` and scored automatically.

Where it comes from (engine `best`, ranked):
1. A live setup whose edge held in BOTH halves of the 2003–2026 history (`validated`), with positive expectancy
   in its asset class, and the forecast model not disagreeing. Ranked by shrunk expectancy (R).
2. Otherwise the forecast model's strongest leans. The model is a ridge regression on 16 inputs (12/3/1-month
   trend, 5-day move, 55-day range position, curve carry and its change, speculator positioning and its 4-week
   change from CFTC, volatility level, and the trends in the dollar, real yields, VIX term structure, credit
   spreads, the 2-year yield and bond volatility), pooled across 33 markets with asset-class adjustments.
   Grades: A = expected edge ≥ 0.20R, B ≥ 0.10R, C below that.

Out-of-sample record (walk-forward, refit every January, 2009–2026, measured on TradingView data on 2026-11-12):
the model's daily top pick was right 53.6% of 4,586 days (+0.15 ATR per 10 sessions; 53.0% in 2009–14, 55.8% in
2015–20, 51.8% in 2021–26). As a trade (next open, 2 ATR stop, exit after 10 sessions, one position per market):
1,060 trades, 52.2% won, +0.08R average, profit factor 1.23, 12 of 18 years positive, worst losing run 8.
Plain read: a real but thin edge, like a coin that lands heads 53–54 times in 100. It pays only over many
calls with small, fixed risk. A string of 5–8 wrong calls is normal.

Rules for Claude when choosing the published call:
- Default to candidate #1. Switch to #2 or #3 only for a concrete, dated reason found in research (a
  scheduled event inside the first 2 sessions that the call is directly exposed to, a news shock the data does
  not yet reflect, a limit move / contract roll / data error). Say which candidate was skipped and why.
- Never invent a call that is not in `best`. Never raise the printed chance above the engine's number.
- Grade C calls are still published (the alert is daily) but say "low conviction" in the headline.
- The best prediction becomes a PAPER ticket only if it also passes the TRADE rule in §3.

## 1. The evidence ladder (every trade climbs all six rungs)

| Rung | Question | Source |
|---|---|---|
| 1 Regime | What is the growth / inflation / policy / risk regime, and which assets does it favour? | Engine `regime` (macro trend monitor) + `macro` tiles + web research |
| 2 Catalyst | What is moving this market *now*, and is it getting stronger or fading? | Engine `news`, `calendar` + web search |
| 3 Positioning & structure | Is the trade crowded? Is the curve saying the physical market is tight or loose? | Engine `curves`, CFTC COT (weekly), OVX/GVZ/VIX |
| 4 Price | Is price confirming (trend, breakout, reversal) rather than fighting us? | Engine `table`, `signals`, `watch` |
| 5 Base rate | How often has this exact setup worked on this market and asset class? | Engine `hist`, `setupBook` |
| 6 Risk | Can we size it at our risk budget with the stop where it belongs? | Engine `sizing` + section 5 below |

## 2. Base rates the desk has already learned (6 years, 33 markets, backtested 2026-09-25; v2.0 uses 2003–2026)

Next-session-open entries, stop wins ties, 0.02R costs. Expectancy is in R, where 1R is the amount risked.

- **Works:** RSI(2) snapback long on equity indices (n 89, 70% win, +0.21R). Shock-momentum long with the 12-month trend
  (n 120, 49%, +0.14R; energy +0.43R, metals +0.31R). 55-day breakout long with the 12-month trend in energy, metals and softs
  (+0.19 to +0.28R). Breakdown shorts in rates (+0.20R) while bonds are in a 12-month downtrend.
- **Loses:** Fading spikes (EX short) is negative almost everywhere, and worst in energy (n 47, 23% win, −0.45R).
  Breakdown shorts in energy and metals (17% win, about −0.45R). Commodities trend up better than they trend down, because
  supply shocks are sudden and short squeezes are violent.
- **So:** "Short oil at $120 / $106" is a low-odds trade *on the chart alone*. It is only allowed when a concrete
  de-escalation catalyst is present (ceasefire, strait reopening, SPR release, OPEC supply hike) and scores ≥ 12/15 on catalyst
  below. Even then it is sized at half risk.

The engine recomputes these every run. Always quote the live numbers, not this list.

## 2b. What the full-system backtest says (walk-forward, 2022 – Sep 2026)

The mechanical layer alone, tested without look-ahead and with portfolio limits, was roughly break-even:
+2.4% a year at best (profit factor 1.11, max drawdown 13%, 332 trades, not statistically different from zero).
Raising the quant-score threshold made it worse, so a high `qscore` is not a reason to trade on its own. Classic trend-following
on the same markets was also flat in this period. Consequences for how the desk operates:

- **Paper mode until proven.** Every ticket carries the label `PAPER` until the ledger holds at least 30 closed tickets with
  average R above +0.10 and realized win rates within 8 points of the printed P(win). `config.json` → `live_mode` flips this.
- **The catalyst score carries the weight.** A ticket needs catalyst ≥ 10 of 15 in addition to the conviction ≥ 65 rule.
  If the only argument for a trade is the chart, it is a WATCH, not a TRADE.
- **Quant floor:** `qscore` ≥ 30 with positive walk-forward expectancy (the best-performing gate). Do not rank by `qscore` beyond that.
- **Review monthly:** compare the ledger with the backtest baseline on the dashboard's Performance tab. If after 30 tickets the
  live average R is not better than the backtest's +0.05R, the discretionary layer is not adding value: say so in the report.

## 3. Conviction score (0–100)

**Quant, from the engine (0–60):** use `qscore` as given (edge 25, reliability 15, trend alignment 10, feasibility 10).

**Discretionary, from you (0–40):**

| Component | Points | How to score |
|---|---|---|
| Catalyst | 0–15 | 13–15: fresh, specific, still unfolding (war start, surprise Fed move, supply outage). 8–12: clear driver, partly priced. 0–7: stale, vague or none. |
| Regime fit | 0–10 | Does the section 4 regime map favour this direction for this asset? |
| Confirmation | 0–10 | Curve (backwardation for commodity longs), COT not crowded the same way (not above the 85th percentile, or more than 15% of OI net), cross-asset agreement (e.g. oil long plus OVX rising plus energy equities firm). |
| Freshness | 0–5 | Driver accelerating (5) vs. consensus and well-known (0–1). |
| Event-risk penalty | 0 to −10 | Tier-1 event against the position within 48h (CPI, NFP, FOMC, OPEC, WASDE for grains, EIA for energy on Wed): −3 to −6. Binary headline risk (talks, strikes): −4 to −10. |

**Decision rules:**

- **TRADE** when conviction ≥ 65 AND engine `expR` > 0 AND `pWin` ≥ 45% (≥ 40% when target ≥ 2R).
- **WATCH** when conviction is 55–64, or it qualifies but the entry trigger has not fired yet.
- **PASS** otherwise.
- A market whose *asset-class* base rate for the setup is negative needs catalyst ≥ 12 to trade, and at half risk.
- **Discretionary trades** (no engine signal, pure macro or event) are allowed only with catalyst ≥ 13, `tsmom` and `pUp10` (≥ 52%)
  pointing the same way, ATR-based stop and target, and half risk. Label them `DISCRETIONARY — no base rate`.

**Probability you print:** `P(win) = engine pWin ± your adjustment`. The adjustment is at most ±8 points, and you must justify it
in one line. Always print the sample size next to it (e.g. "54% (n = 120 class trades)"). Never print a probability without n.

## 4a. Macro trend monitor (engine `regime`, v1.4+)

The engine scores five pillars from 17 cross-asset trends every run, so the regime call is measured, not guessed:

- **Growth:** copper/gold, discretionary/staples, small caps/S&P, high-yield/Treasuries, regional banks/S&P, EM/S&P, utilities/S&P (inverted).
- **Inflation:** commodity basket (DBC), WTI, TIPS/Treasuries, 10Y breakeven. **Policy:** US 2Y yield. **Liquidity:** 10Y real yield and DXY (both inverted).
  **Risk:** VIX/VIX3M (inverted), HY credit spread (inverted), S&P 500.
- Each trend = average of three signs: price vs. 50-day, 50-day vs. 200-day, 3-month change. Pillar = average of its trends (−1 to +1).
- **Quadrant** = growth pillar × inflation pillar: Reflation (+,+), Goldilocks (+,−), Stagflation (−,+), Deflationary slowdown (−,−).
  The run's `regime.label` must start from this quadrant; you may qualify it (e.g. "Reflation with tightening policy, supply-shock flavour") but not overrule it without saying why.

**How to use it in scoring:**

| Engine reading | Effect |
|---|---|
| Ticket direction matches `favored` (long) or `disfavored` (short) | Regime fit 7–10 |
| Market not in either list, direction agrees with the section 4 map | Regime fit 4–6 |
| Ticket direction is the opposite of `favored` / `disfavored` | Regime fit 0–2, and say so in the evidence line |
| `alerts` contains "Regime shift" within 20 sessions | Counts as a catalyst for trades aligned with the *new* regime (up to 10/15 when backed by news). Spells are short (a typical one lasts about 5–9 sessions), so prefer hold ≤ 10 sessions |
| A pillar moved ≥ 0.5 in 20 sessions | Name it in the report headline or summary; it is the macro story of the week |
| `shocks` lists 3 or more markets | Macro shock day: half risk on new tickets, and check the news for the cause before anything else |
| Risk pillar ≤ −0.5 | Treat as the risk-off row in section 4: half size, A+ setups only |

Favored/disfavored lists are in-sample history of the same quadrant (overlapping 20-day windows). Treat them as a tilt, never as a signal on their own.

## 4. Regime map

| Regime (growth / inflation / policy) | Favour | Avoid |
|---|---|---|
| Supply-shock stagflation (growth OK or slowing, headline inflation from energy, central bank hiking) | Long energy on pullbacks, short duration (ZN/ZB) on rallies, long USD vs. EUR/JPY | Long bonds, long gold while real yields rise, long small caps |
| Reflation (growth up, inflation up, policy easy) | Long commodities, copper, equities, short bonds | Long USD, long bonds |
| Goldilocks (growth up, inflation down) | Long equities (NQ/ES), carry FX, buy dips | Long gold, long vol |
| Deflationary bust (growth down, inflation down, easing) | Long bonds, long gold, long JPY, short oil and copper | Long cyclicals |
| Risk-off shock (VIX term > 1.0, HY OAS widening > 50bp in 20d) | Cut size in half, long bonds and USD, only take A+ setups | New breakout longs in risk assets |

Evidence to cite: ISM, payroll and claims trend (growth); CPI/PCE, 10Y breakeven, oil (inflation); Fed funds, 2Y yield, dot plot
(policy); DXY, 10Y real yield, HY OAS, VIX and VIX/VIX3M (risk and liquidity).

## 5. Risk and sizing (non-negotiable)

- Equity and risk come from `config.json` (default $100,000, 1.0% per trade).
- Conviction ≥ 75 → full risk (1.0%). 65–74 → 0.5%. Discretionary or negative class base rate → 0.5% max.
- Contracts = floor(risk $ ÷ (stop distance × point value)). Prefer the micro when the full contract doesn't fit.
  If even one micro exceeds the budget, the trade is **not sizeable**: say so, and do not widen the budget or tighten the stop to force it.
- Max 3 open positions. Max 1 per cluster (oil = CL/HO/RB/Brent; UST = ZT/ZF/ZN/ZB; US equity = ES/NQ/RTY/YM; precious = GC/SI/PL;
  grains = ZC/ZS/ZW; USD block = DX and the currency futures). Total open risk ≤ 3% of equity.
- Daily drawdown guard: if the ledger shows three straight stopped trades, or the sum of the last 10 closed trades is below −4R,
  the next report halves all risk and says why.
- Management: keep the original stop and target 1 for the whole hold. That is exactly what the base rates were measured on,
  so the ledger stays comparable with the backtest. Exit at target 1, the stop, or the time stop. Exit early only on a
  thesis-breaking catalyst, and record it with `ledger.py close`. Target 2 is informational (where the move could extend).
- Contract month: trade the engine's `front` unless it expires, or first notice falls, within the hold window, or `volRatio2to1` > 1.
  Then use the next month and note it. For CL, the front expires around the 20th of the month before delivery.
- Never recommend adding to a loser, averaging down, or moving a stop further away.

## 6. Entries

- **Signal fired today (engine `signals`):** order for the next session: buy or sell at the open, or a limit within 0.25 ATR of the
  reference close. `entry_type` = `open` or `limit`.
- **Watchlist trigger (engine `watch`):** stop-entry order at the trigger (BO), or a limit at the pullback zone (TP), valid 2 sessions.
  `entry_type` = `stop` or `limit`.
- **Stops and targets:** use the engine's `stop`, `target1`, `target2`. For watch items, recompute from the trigger price with the same ATR multiples.

## 7. Weekly extras

- **Friday and Sunday runs:** pull CFTC managed-money positions (Disaggregated, futures only, via WebFetch of
  `https://www.cftc.gov/dea/futures/petroleum_sf.htm`, `.../ag_sf.htm`, `.../other_sf.htm` for metals, and the Financial
  (TFF) pages for leveraged-fund positioning in ES/ZN/6E). Log them with `tools/cot.py add`.
- **Sunday run:** weekend news only (geopolitics, OPEC+, policy). Re-check Friday's plan against it and flag gap risk.
  No new backtest research unless the engine flags a new signal.
- **Wednesday:** EIA petroleum status report (10:30 ET) matters for energy trades. Mention the result if you are in or considering energy.

## 8. Language

- Never "guaranteed", "sure thing", "can't lose", "free money".
- Always show the loss case in dollars next to the gain case.
- Past base rates are evidence, not promises; say that once in the footer, not on every line.
- Not financial advice; the desk is a research tool. Futures are leveraged and can lose more than the margin posted.
