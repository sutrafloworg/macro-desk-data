// Macro Futures Desk — cloud collector. Runs the desk engine (engine/mfd_engine.min.js) headless and
// writes everything the daily alert needs into data/. Designed for GitHub Actions; no laptop involved.
//
//   node runner/run_node.mjs --engine engine/mfd_engine.min.js --outdir data [--equity 100000 --risk 1]
//
// Data path 1: TradingView's public chart websocket (same feed the browser engine uses; carry + COT included).
// Data path 2 (automatic fallback): Yahoo Finance daily bars, FRED and the CFTC public API, served to the
// engine through the same websocket protocol so the engine code is identical either way.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import WS from "ws";

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const enginePath = arg("engine", "engine/mfd_engine.min.js"), outdir = arg("outdir", "data");
const equity = +arg("equity", 100000), riskPct = +arg("risk", 1), force = arg("source", "auto");
const ORIGIN = "https://www.tradingview.com", UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";
fs.mkdirSync(path.join(outdir, "archive"), { recursive: true });
const log = (...a) => console.log(new Date().toISOString(), ...a);
const fetchT = async (url, init = {}, ms = 30000) => { const c = new AbortController(); const t = setTimeout(() => c.abort(), ms); try { return await fetch(url, { ...init, signal: c.signal }); } finally { clearTimeout(t); } };

// ---------- path 1: TradingView websocket with the Origin header it expects ----------
class TVSocket {
  constructor(url) {
    this._ws = new WS(url, { headers: { Origin: ORIGIN, "User-Agent": UA } });
    this._ws.on("open", () => this.onopen && this.onopen());
    this._ws.on("message", (d) => this.onmessage && this.onmessage({ data: d.toString() }));
    this._ws.on("error", (e) => { TVSocket.lastError = String((e && e.message) || e); this.onerror && this.onerror(e); });
    this._ws.on("close", () => this.onclose && this.onclose());
  }
  send(s) { if (this._ws.readyState === 1) this._ws.send(s); }
  close() { try { this._ws.close(); } catch (e) {} }
}
const tvFetch = (url, init = {}) => fetchT(url, { ...init, headers: { Origin: ORIGIN, Referer: ORIGIN + "/", "User-Agent": UA, ...(init.headers || {}) } });

// ---------- path 2: public sources behind the same protocol ----------
const YF = { "NYMEX:CL1!": "CL=F", "NYMEX:HO1!": "HO=F", "NYMEX:RB1!": "RB=F", "NYMEX:NG1!": "NG=F", "COMEX:GC1!": "GC=F", "COMEX:SI1!": "SI=F", "NYMEX:PL1!": "PL=F", "COMEX:HG1!": "HG=F",
  "CME_MINI:ES1!": "ES=F", "CME_MINI:NQ1!": "NQ=F", "CME_MINI:RTY1!": "RTY=F", "CBOT_MINI:YM1!": "YM=F", "CBOT:ZT1!": "ZT=F", "CBOT:ZF1!": "ZF=F", "CBOT:ZN1!": "ZN=F", "CBOT:ZB1!": "ZB=F",
  "ICEUS:DX1!": "DX=F", "CME:6E1!": "6E=F", "CME:6J1!": "6J=F", "CME:6B1!": "6B=F", "CME:6A1!": "6A=F", "CME:6C1!": "6C=F", "CBOT:ZC1!": "ZC=F", "CBOT:ZS1!": "ZS=F", "CBOT:ZW1!": "ZW=F",
  "CME:LE1!": "LE=F", "CME:HE1!": "HE=F", "ICEUS:KC1!": "KC=F", "ICEUS:SB1!": "SB=F", "ICEUS:CC1!": "CC=F", "ICEUS:CT1!": "CT=F", "CME:BTC1!": "BTC=F", "CME:ETH1!": "ETH=F",
  "ICEEUR:BRN1!": "BZ=F", "NYMEX:BZ1!": "BZ=F", "TVC:DXY": "DX-Y.NYB", "CBOE:VIX": "^VIX", "CBOE:VIX3M": "^VIX3M", "CBOE:OVX": "^OVX", "CBOE:GVZ": "^GVZ", "TVC:MOVE": "^MOVE" };
const FRED = { "TVC:US02Y": "DGS2", "TVC:US10Y": "DGS10", "TVC:US30Y": "DGS30", "ECONOMICS:USINTR": "DFEDTARU", "ECONOMICS:USUR": "UNRATE" };
const cache = new Map();
async function yahoo(t) {
  for (const host of ["query1", "query2"]) {
    try {
      const r = await fetchT("https://" + host + ".finance.yahoo.com/v8/finance/chart/" + encodeURIComponent(t) + "?range=max&interval=1d&includePrePost=false", { headers: { "User-Agent": UA, Accept: "application/json" } });
      if (!r.ok) { if (r.status === 429) await new Promise((z) => setTimeout(z, 1500)); continue; }
      const j = await r.json(), x = j.chart && j.chart.result && j.chart.result[0]; if (!x || !x.timestamp) continue;
      const q = x.indicators.quote[0], out = [];
      for (let i = 0; i < x.timestamp.length; i++) { const o = q.open[i], h = q.high[i], l = q.low[i], c = q.close[i]; if (c == null || o == null || h == null || l == null) continue; out.push([x.timestamp[i], o, h, l, c, q.volume ? q.volume[i] || 0 : 0]); }
      return out;
    } catch (e) {}
  }
  return null;
}
async function fred(id) {
  try {
    const r = await fetchT("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + id, { headers: { "User-Agent": UA } }); if (!r.ok) return null;
    const out = []; for (const line of (await r.text()).split("\n").slice(1)) { const [d, v] = line.trim().split(","); const x = parseFloat(v); if (!d || !isFinite(x)) continue; const t = Date.parse(d + "T00:00:00Z") / 1000; out.push([t, x, x, x, x, 0]); }
    return out;
  } catch (e) { return null; }
}
async function cot(code) {
  try {
    const u = "https://publicreporting.cftc.gov/resource/6dca-aqww.json?$select=report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all&$where=cftc_contract_market_code='" + code + "'&$order=report_date_as_yyyy_mm_dd&$limit=5000";
    const r = await fetchT(u, { headers: { "User-Agent": UA, Accept: "application/json" } }); if (!r.ok) return null;
    return (await r.json()).map((x) => { const v = (+x.noncomm_positions_long_all - +x.noncomm_positions_short_all) / +x.open_interest_all; const t = Date.parse(x.report_date_as_yyyy_mm_dd.slice(0, 10) + "T00:00:00Z") / 1000; return [t, v, v, v, v, 0]; }).filter((b) => isFinite(b[1]));
  } catch (e) { return null; }
}
async function publicBars(sym) {
  if (cache.has(sym)) return cache.get(sym);
  const p = (async () => {
    const m = sym.match(/^\(COT:([0-9A-Z]+)_F_NCP_L-COT:\1_F_NCP_S\)\/COT:\1_F_OI$/); if (m) return cot(m[1]);
    if (sym.includes("/") || /2!$/.test(sym) || sym.startsWith("COT")) return null;          // carry ratios / 2nd contracts: not available here
    if (YF[sym]) return yahoo(YF[sym]);
    if (FRED[sym]) return fred(FRED[sym]);
    if (sym.startsWith("FRED:")) return fred(sym.slice(5));
    if (/^(AMEX|NASDAQ|NYSE|ARCA|BATS):/.test(sym)) return yahoo(sym.split(":")[1]);
    return null;
  })();
  cache.set(sym, p); return p;
}
class PublicSocket {
  constructor() { setTimeout(() => this.onopen && this.onopen(), 0); }
  send(msg) {
    for (const part of msg.split(/~m~\d+~m~/).filter(Boolean)) {
      let j; try { j = JSON.parse(part); } catch (e) { continue; }
      if (j.m === "resolve_symbol") this.sym = JSON.parse(j.p[2].slice(1)).symbol;
      if (j.m === "create_series") {
        const n = j.p[5];
        publicBars(this.sym).then((bars) => {
          const pk = (o) => { const s = JSON.stringify(o); return "~m~" + s.length + "~m~" + s; };
          if (!bars || !bars.length) return this.onmessage && this.onmessage({ data: pk({ m: "symbol_error", p: [0, "sds_sym_1", "no public source"] }) });
          const b = bars.slice(-n);
          this.onmessage && this.onmessage({ data: pk({ m: "symbol_resolved", p: [0, "sds_sym_1", { front_contract: null }] }) + pk({ m: "timescale_update", p: [0, { sds_1: { s: b.map((v) => ({ v })) } }] }) + pk({ m: "series_completed", p: [0, "sds_1"] }) });
        });
      }
    }
  }
  close() {}
}

async function probeTV() {
  if (force === "public") return "forced public";
  try { const r = await tvFetch("https://news-headlines.tradingview.com/v2/headlines?client=web&lang=en&category=futures"); if (!r.ok) return "headlines HTTP " + r.status; } catch (e) { return "headlines " + String(e.message || e); }
  // a real bar request decides it
  const ctx = vm.createContext({ WebSocket: TVSocket, fetch: tvFetch, console, setTimeout, clearTimeout, Date, Math, JSON, Promise, Array, Object, Set, Map, String, Number, isNaN, isFinite, parseFloat, Float32Array, Float64Array, URL });
  vm.runInContext(fs.readFileSync(enginePath, "utf8") + "\n;globalThis.MFD = MFD;", ctx);
  const r = await ctx.MFD.getBars("NYMEX:CL1!", 50, true);
  return r && r.bars && r.bars.length >= 40 ? null : "bars " + (r && r.err) + " " + (TVSocket.lastError || "");
}

const status = { generated_utc: new Date().toISOString(), ok: false, source: null, tv_probe: null, engine: null, markets: 0, errors: [] };
const writeJSON = (f, o) => fs.writeFileSync(path.join(outdir, f), JSON.stringify(o));
try {
  const why = await probeTV();
  status.tv_probe = why || "ok";
  const useTV = !why;
  status.source = useTV ? "tradingview" : "public (yahoo/fred/cftc)";
  log("data source:", status.source, why || "");
  const ctx = vm.createContext({ WebSocket: useTV ? TVSocket : PublicSocket, fetch: useTV ? tvFetch : (u, i) => fetchT(u, i), console, setTimeout, clearTimeout, Date, Math, JSON, Promise, Array, Object, Set, Map, String, Number, isNaN, isFinite, parseFloat, Float32Array, Float64Array, URL });
  vm.runInContext(fs.readFileSync(enginePath, "utf8") + "\n;globalThis.MFD = MFD;", ctx);
  const t0 = Date.now();
  const o = await ctx.MFD.run({ equity, riskPct, conc: useTV ? 6 : 4 });
  log("engine done in", Math.round((Date.now() - t0) / 1000), "s; markets", o.meta.markets);
  status.engine = o.meta.engine; status.markets = o.meta.markets; status.errors = (o.meta.errors || []).slice(0, 80);
  if (o.meta.markets < 20) throw new Error("only " + o.meta.markets + " markets loaded");
  const desk = ctx.MFD.deskSections(o);
  // prices for scoring forecasts: last 160 sessions per market
  const prices = {};
  for (const r of o.table) {
    const b = await ctx.MFD.getBars(r.sym, 170, true); if (!b || !b.bars) continue;
    const rows = b.bars.filter((x) => x && x[4] != null).map((x) => [new Date((new Date(x[0] * 1000).getUTCHours() >= 16 ? x[0] + 43200 : x[0]) * 1000).toISOString().slice(0, 10), ...[1, 2, 3, 4].map((k) => +(+x[k]).toPrecision(7))]);
    prices[r.sym] = { name: r.name, front: r.front, atr: r.atr, bars: rows.slice(-160) };
  }
  const asof = o.forecast && o.forecast.asof || (o.table[0] && o.table[0].asof);
  const lean = { meta: o.meta, source: status.source, asof, best: o.best, forecast: o.forecast, signals: o.signals, watch: o.watch, macro: o.macro, regime: o.regime, curves: o.curves, calendar: o.calendar, news: o.news, setupBook: o.setupBook };
  writeJSON("latest.json", lean);
  writeJSON("desk.json", desk);
  writeJSON("prices.json", { asof, prices });
  writeJSON("archive/" + asof + ".json", { asof, generated_utc: status.generated_utc, source: status.source, best: o.best, board: (o.forecast.board || []).slice(0, 12), validation: o.forecast.validation });
  status.ok = true; status.asof = asof; status.best = o.best && o.best[0] ? o.best[0].name + " " + o.best[0].dir : null;
} catch (e) {
  status.errors.unshift("fatal: " + String((e && e.stack) || e).slice(0, 600));
  log("FAILED", e);
}
writeJSON("status.json", status);
log(JSON.stringify({ ok: status.ok, source: status.source, markets: status.markets, best: status.best }));
process.exit(status.ok ? 0 : 1);
