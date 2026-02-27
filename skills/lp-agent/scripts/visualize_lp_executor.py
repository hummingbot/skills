#!/usr/bin/env python3
"""
Generate an interactive HTML dashboard for LP executor performance.

Fetches lp_executor data directly from the Hummingbot REST API (no SQLite needed).
For single-executor view, optionally overlays 5m price candles from KuCoin.

Usage:
    python scripts/visualize_lp_executor.py                                 # all LP executors
    python scripts/visualize_lp_executor.py --pair SOL-USDC                 # filter by pair
    python scripts/visualize_lp_executor.py --id <executor_id>              # single detail view
    python scripts/visualize_lp_executor.py --status TERMINATED             # filter by status
    python scripts/visualize_lp_executor.py --output report.html            # custom output
    python scripts/visualize_lp_executor.py --no-open                       # skip browser open

Examples:
    python scripts/visualize_lp_executor.py --pair SOL-USDC --status TERMINATED
    python scripts/visualize_lp_executor.py --id ryUBCGfuBgmDL5bPggxmVFbQzu7McBE1hXs2yRymiob
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
import webbrowser
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Environment / Auth
# ---------------------------------------------------------------------------

def load_env():
    env_files = [
        Path.home() / "mcp" / ".env",
        Path.home() / ".hummingbot" / ".env",
        Path(".env"),
    ]
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = value
            except Exception:
                pass


def get_api_config():
    load_env()
    base_url = os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000").rstrip("/")
    username = os.environ.get("HUMMINGBOT_USERNAME", "admin")
    password = os.environ.get("HUMMINGBOT_PASSWORD", "admin")
    return base_url, username, password


def make_auth_header(username, password):
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_post(url, payload, auth_header, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


def api_get(url, auth_header, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"Authorization": auth_header},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e


# ---------------------------------------------------------------------------
# Fetch LP executors
# ---------------------------------------------------------------------------

def fetch_lp_executors(base_url, auth_header, trading_pair=None, status=None):
    """POST /executors/search → filter to lp_executor type."""
    url = f"{base_url}/executors/search"
    payload = {"type": "lp_executor"}
    if trading_pair:
        payload["trading_pair"] = trading_pair
    if status:
        payload["status"] = status

    try:
        result = api_post(url, payload, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executors: {e}", file=sys.stderr)
        sys.exit(1)

    items = []
    if isinstance(result, list):
        items = result
    elif isinstance(result, dict):
        for key in ("data", "executors", "items", "results"):
            if key in result and isinstance(result[key], list):
                items = result[key]
                break

    return [
        ex for ex in items
        if ex.get("type") == "lp_executor" or ex.get("executor_type") == "lp_executor"
    ]


def fetch_executor_by_id(base_url, auth_header, executor_id):
    """GET /executors/{id} for single executor detail."""
    url = f"{base_url}/executors/{executor_id}"
    try:
        return api_get(url, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executor {executor_id}: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Candle fetching (KuCoin via Hummingbot market-data endpoint)
# ---------------------------------------------------------------------------

def map_pair_for_kucoin(trading_pair):
    """Swap USDC → USDT for KuCoin (e.g. SOL-USDC → SOL-USDT)."""
    return trading_pair.replace("USDC", "USDT").replace("usdc", "usdt")


def fetch_candles(base_url, auth_header, trading_pair, start_time, end_time, interval="5m"):
    """
    Fetch 5m candles via POST /market-data/historical-candles (KuCoin).
    Returns list of candle dicts or None on any failure.
    Only attempted for pairs that exist on KuCoin (major pairs).
    """
    kucoin_pair = map_pair_for_kucoin(trading_pair)
    # Skip exotic pairs unlikely to be on KuCoin
    base_token = kucoin_pair.split("-")[0]
    if len(base_token) > 10 or base_token.lower().endswith("pump"):
        print(f"  Skipping candle fetch for exotic pair: {kucoin_pair}")
        return None

    url = f"{base_url}/market-data/historical-candles"
    payload = {
        "connector_name": "kucoin",
        "trading_pair": kucoin_pair,
        "interval": interval,
        "start_time": int(start_time),
        "end_time": int(end_time),
    }
    try:
        result = api_post(url, payload, auth_header, timeout=20)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("candles", "data", "ohlcv"):
                if key in result and isinstance(result[key], list):
                    return result[key]
        return None
    except Exception as e:
        print(f"  Warning: Failed to fetch candles for {kucoin_pair}: {e}")
        return None


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _f(v, default=None):
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _s(v, default=""):
    return str(v) if v is not None else default


def parse_ts(iso_str):
    if not iso_str:
        return None
    try:
        clean = str(iso_str).replace("+00:00", "").replace("Z", "")
        if "." in clean:
            parts = clean.split(".")
            clean = parts[0] + "." + parts[1][:6]
        dt = datetime.fromisoformat(clean)
        import calendar
        return calendar.timegm(dt.timetuple()) + dt.microsecond / 1e6
    except Exception:
        return None


def enrich(ex):
    """
    Add computed fields (_created_ts, _close_ts, _duration, _cfg, _ci) to executor in-place.
    These shadow keys start with _ so they don't clash with API fields.
    """
    cfg = ex.get("config") or {}
    ci = ex.get("custom_info") or {}

    created_ts = parse_ts(ex.get("created_at"))
    close_ts = _f(ex.get("close_timestamp"))
    if close_ts is None:
        close_ts = parse_ts(ex.get("closed_at"))

    duration = None
    if created_ts is not None and close_ts is not None and close_ts > created_ts:
        duration = round(close_ts - created_ts, 1)

    ex["_created_ts"] = created_ts
    ex["_close_ts"] = close_ts
    ex["_duration"] = duration
    ex["_cfg"] = cfg
    ex["_ci"] = ci
    return ex


def fmt_dur(s):
    if s is None or s <= 0:
        return "—"
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def fmt_ts(ts):
    if ts is None:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def ex_id(ex):
    return _s(ex.get("executor_id") or ex.get("id"))


# ---------------------------------------------------------------------------
# Common CSS / color constants (inlined into HTML)
# ---------------------------------------------------------------------------

DARK_CSS = """
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0d1117; color: #e8eaed; font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace; font-size: 12px; }
  .container { max-width: 1400px; margin: 0 auto; padding: 24px 20px; }
  h1 { font-size: 22px; font-weight: 700; color: #4ecdc4; margin-bottom: 4px; }
  .subtitle { font-size: 11px; color: #6b7084; margin-bottom: 24px; font-family: monospace; }
  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 24px; }
  .kpi-card { background: #161b27; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 14px 16px; }
  .kpi-label { font-size: 10px; color: #6b7084; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }
  .kpi-value { font-size: 20px; font-weight: 700; }
  .kpi-sub { font-size: 10px; color: #555870; margin-top: 4px; }
  .section-title { font-size: 11px; font-weight: 600; color: #8b8fa3; text-transform: uppercase; letter-spacing: .08em; margin: 24px 0 12px; }
  .chart-wrap { background: #161b27; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; margin-bottom: 20px; }
  .chart-container { position: relative; }
  table { width: 100%; border-collapse: collapse; }
  th { padding: 9px 8px; text-align: left; font-size: 10px; color: #6b7084; border-bottom: 1px solid rgba(255,255,255,0.07); font-weight: 500; white-space: nowrap; }
  td { padding: 8px 8px; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.03); vertical-align: middle; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  tr:last-child td { border-bottom: none; }
  .table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); background: #161b27; }
  .summary-table { background: #161b27; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; overflow: hidden; width: 100%; }
  .summary-table td { padding: 7px 12px; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .footer { font-size: 10px; color: #3a3d50; text-align: center; margin-top: 32px; padding-bottom: 16px; }
  a { color: #7c6df0; text-decoration: none; }
  a:hover { text-decoration: underline; }
"""


def status_color(status):
    return {
        "TERMINATED": "#4ecdc4",
        "COMPLETE": "#4ecdc4",
        "RUNNING": "#f0c644",
        "ACTIVE": "#f0c644",
        "SHUTTING_DOWN": "#f0a644",
        "FAILED": "#e85d75",
    }.get(status, "#8b8fa3")


def pnl_color(v):
    return "#4ecdc4" if (v or 0) >= 0 else "#e85d75"


# ---------------------------------------------------------------------------
# Multi-executor HTML
# ---------------------------------------------------------------------------

def build_multi_html(executors, filters):
    total_pnl = sum(_f(ex.get("net_pnl_quote"), 0) for ex in executors)
    total_fees = sum(_f((ex.get("custom_info") or {}).get("fees_earned_quote"), 0) for ex in executors)
    wins = sum(1 for ex in executors if _f(ex.get("net_pnl_quote"), 0) >= 0)
    losses = len(executors) - wins

    rows_html = ""
    chart_labels = []
    chart_pnl = []
    chart_colors = []

    for idx, ex in enumerate(executors):
        enrich(ex)
        eid = ex_id(ex)
        short_id = eid[:10] + "…" if len(eid) > 12 else eid
        pair = _s(ex.get("trading_pair"))
        status = _s(ex.get("status"))
        pnl = _f(ex.get("net_pnl_quote"), 0)
        pnl_pct = _f(ex.get("net_pnl_pct"), 0)
        ci = ex.get("_ci") or {}
        fees = _f(ci.get("fees_earned_quote"), 0)
        dur = fmt_dur(ex.get("_duration"))
        created = fmt_ts(ex.get("_created_ts"))
        cfg = ex.get("_cfg") or {}
        lower = _f(ci.get("lower_price") or cfg.get("lower_price"))
        upper = _f(ci.get("upper_price") or cfg.get("upper_price"))
        rng = f"{lower:.6g} – {upper:.6g}" if lower is not None and upper is not None else "—"
        state = _s(ci.get("state"))

        sc = status_color(status)
        pc = pnl_color(pnl)

        rows_html += f"""
        <tr>
          <td style="color:#6b7084;">{idx + 1}</td>
          <td style="font-family:monospace;font-size:10px;" title="{eid}">{short_id}</td>
          <td style="color:#e8eaed;font-weight:500;">{pair}</td>
          <td><span style="font-size:9px;padding:2px 8px;border-radius:10px;background:{sc}22;color:{sc};">{status}</span></td>
          <td style="font-size:10px;color:#8b8fa3;">{state}</td>
          <td style="font-size:10px;">{created}</td>
          <td style="font-size:10px;">{dur}</td>
          <td style="color:{pc};font-weight:600;">{pnl:+.6f}</td>
          <td style="color:{pc};">{(pnl_pct * 100):+.3f}%</td>
          <td style="color:#7c6df0;">{fees:.6f}</td>
          <td style="font-size:10px;color:#8b8fa3;">{rng}</td>
        </tr>"""

        if idx < 60:
            chart_labels.append(f"#{idx + 1} {pair}")
            chart_pnl.append(round(pnl, 6))
            chart_colors.append("rgba(78,205,196,0.8)" if pnl >= 0 else "rgba(232,93,117,0.8)")

    # Filters description
    parts = []
    if filters.get("pair"):
        parts.append(f"pair={filters['pair']}")
    if filters.get("status"):
        parts.append(f"status={filters['status']}")
    filter_desc = " · ".join(parts) if parts else "all LP executors"

    pc_total = pnl_color(total_pnl)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>LP Executor Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>{DARK_CSS}</style>
</head>
<body>
<div class="container">
  <h1>LP Executor Dashboard</h1>
  <div class="subtitle">{filter_desc} · {len(executors)} executor(s) · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Executors</div>
      <div class="kpi-value" style="color:#e8eaed;">{len(executors)}</div>
      <div class="kpi-sub">{wins}W · {losses}L</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total PnL</div>
      <div class="kpi-value" style="color:{pc_total};">{total_pnl:+.4f}</div>
      <div class="kpi-sub">net quote</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fees Earned</div>
      <div class="kpi-value" style="color:#7c6df0;">{total_fees:.4f}</div>
      <div class="kpi-sub">quote currency</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value" style="color:#e8eaed;">{wins / len(executors) * 100:.0f}%</div>
      <div class="kpi-sub">{wins} profitable</div>
    </div>
  </div>

  <div class="section-title">Net PnL per Executor</div>
  <div class="chart-wrap">
    <div class="chart-container" style="height:260px;">
      <canvas id="pnlChart"></canvas>
    </div>
  </div>

  <div class="section-title">LP Executor History ({len(executors)} total)</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th><th>ID</th><th>Pair</th><th>Status</th><th>State</th>
          <th>Created</th><th>Duration</th><th>PnL</th><th>PnL%</th>
          <th>Fees</th><th>Price Range</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>

  <div class="footer">Hummingbot LP Executor Dashboard · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</div>
<script>
(function() {{
  const ctx = document.getElementById('pnlChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {json.dumps(chart_labels)},
      datasets: [{{
        label: 'Net PnL (quote)',
        data: {json.dumps(chart_pnl)},
        backgroundColor: {json.dumps(chart_colors)},
        borderColor: {json.dumps(chart_colors)},
        borderWidth: 1,
        borderRadius: 3,
      }}]
    }},
    options: {{
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: (c) => ` PnL: ${{c.parsed.y.toFixed(6)}}` }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color:'#6b7084', font:{{size:9}}, maxRotation:45 }}, grid:{{ color:'rgba(255,255,255,0.04)' }} }},
        y: {{ ticks: {{ color:'#6b7084', font:{{size:10}}, callback:(v)=>v.toFixed(4) }}, grid:{{ color:'rgba(255,255,255,0.06)' }} }}
      }}
    }}
  }});
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Single-executor HTML
# ---------------------------------------------------------------------------

def build_single_html(ex, candles):
    enrich(ex)
    eid = ex_id(ex)
    pair = _s(ex.get("trading_pair"))
    connector = _s(ex.get("connector_name"))
    status = _s(ex.get("status"))
    close_type = _s(ex.get("close_type"))
    pnl = _f(ex.get("net_pnl_quote"), 0)
    pnl_pct = _f(ex.get("net_pnl_pct"), 0)
    filled = _f(ex.get("filled_amount_quote"), 0)
    account = _s(ex.get("account_name"))
    controller = _s(ex.get("controller_id"))
    error_count = ex.get("error_count", 0)

    cfg = ex.get("_cfg") or {}
    ci = ex.get("_ci") or {}
    created_ts = ex.get("_created_ts")
    close_ts = ex.get("_close_ts")
    duration = ex.get("_duration")

    # Config (deployment params)
    pool_address = _s(cfg.get("pool_address"))
    lower_cfg = _f(cfg.get("lower_price"))
    upper_cfg = _f(cfg.get("upper_price"))
    base_amount_cfg = _f(cfg.get("base_amount"))
    quote_amount_cfg = _f(cfg.get("quote_amount"))
    side_val = cfg.get("side")
    pos_offset = _f(cfg.get("position_offset_pct"))
    auto_above = cfg.get("auto_close_above_range_seconds")
    auto_below = cfg.get("auto_close_below_range_seconds")
    keep_pos = cfg.get("keep_position")

    side_map = {0: "0 — BOTH", 1: "1 — BUY (quote-only)", 2: "2 — SELL (base-only)"}
    side_str = side_map.get(side_val, str(side_val) if side_val is not None else "—")

    # custom_info (live / final position state)
    state = _s(ci.get("state"))
    pos_addr = _s(ci.get("position_address"))
    current_price = _f(ci.get("current_price"))
    lower_actual = _f(ci.get("lower_price"))
    upper_actual = _f(ci.get("upper_price"))
    base_current = _f(ci.get("base_amount"))
    quote_current = _f(ci.get("quote_amount"))
    base_fee = _f(ci.get("base_fee"))
    quote_fee = _f(ci.get("quote_fee"))
    fees_earned = _f(ci.get("fees_earned_quote"), 0)
    total_value = _f(ci.get("total_value_quote"))
    unrealized_pnl = _f(ci.get("unrealized_pnl_quote"))
    pos_rent = _f(ci.get("position_rent"))
    rent_refunded = _f(ci.get("position_rent_refunded"))
    tx_fee = _f(ci.get("tx_fee"))
    out_of_range_sec = _f(ci.get("out_of_range_seconds"))
    max_retries = ci.get("max_retries_reached")
    init_base = _f(ci.get("initial_base_amount"))
    init_quote = _f(ci.get("initial_quote_amount"))

    # Display helpers
    sc = status_color(status)
    pc = pnl_color(pnl)
    dur_str = fmt_dur(duration)
    created_str = fmt_ts(created_ts)
    close_str = fmt_ts(close_ts)
    out_range_str = fmt_dur(out_of_range_sec)

    # Solscan links
    solscan_pos = (
        f'<a href="https://solscan.io/account/{pos_addr}" target="_blank" '
        f'style="font-family:monospace;font-size:9px;word-break:break-all;">{pos_addr}</a>'
        if pos_addr else "—"
    )
    pool_link = (
        f'<a href="https://solscan.io/account/{pool_address}" target="_blank" '
        f'style="font-family:monospace;font-size:9px;word-break:break-all;">{pool_address}</a>'
        if pool_address else "—"
    )

    # Use config bounds for chart (deployment range)
    lp_lower = lower_cfg if lower_cfg is not None else lower_actual
    lp_upper = upper_cfg if upper_cfg is not None else upper_actual

    # Build price chart section (if candles available)
    price_chart_section = ""
    price_chart_js = ""

    if candles:
        # Normalize candle formats: [[ts, o, h, l, c, v], ...] or list of dicts
        candle_data = []
        for c in candles:
            if isinstance(c, list) and len(c) >= 5:
                ts_c = _f(c[0])
                close_c = _f(c[4])
                if ts_c and close_c:
                    candle_data.append({"ts": ts_c, "c": close_c})
            elif isinstance(c, dict):
                ts_c = _f(c.get("timestamp") or c.get("ts") or c.get("open_time"))
                close_c = _f(c.get("close") or c.get("c"))
                if ts_c and close_c:
                    candle_data.append({"ts": ts_c, "c": close_c})

        if candle_data:
            candle_data.sort(key=lambda x: x["ts"])
            labels = [datetime.fromtimestamp(d["ts"]).strftime("%H:%M") for d in candle_data]
            closes = [d["c"] for d in candle_data]

            lp_lower_js = round(lp_lower, 8) if lp_lower is not None else "null"
            lp_upper_js = round(lp_upper, 8) if lp_upper is not None else "null"

            # Entry/exit annotations (if we have created/close timestamps)
            open_idx = "null"
            close_idx = "null"
            if created_ts is not None:
                for i, d in enumerate(candle_data):
                    if d["ts"] >= created_ts:
                        open_idx = i
                        break
            if close_ts is not None:
                for i, d in enumerate(reversed(candle_data)):
                    if d["ts"] <= close_ts:
                        close_idx = len(candle_data) - 1 - i
                        break

            price_chart_section = """
  <div class="section-title">Price Chart — 5m Candles (KuCoin) with LP Range</div>
  <div class="chart-wrap">
    <div class="chart-container" style="height:280px;">
      <canvas id="priceChart"></canvas>
    </div>
  </div>"""

            price_chart_js = f"""
(function() {{
  const labels = {json.dumps(labels)};
  const closes = {json.dumps(closes)};
  const lowerPrice = {lp_lower_js};
  const upperPrice = {lp_upper_js};
  const openIdx = {open_idx};
  const closeIdx = {close_idx};

  const datasets = [{{
    label: 'Close Price',
    data: closes,
    borderColor: '#f0c644',
    backgroundColor: 'rgba(240,198,68,0.06)',
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    tension: 0.1,
    order: 1,
  }}];

  if (lowerPrice !== null) {{
    datasets.push({{
      label: 'LP Lower',
      data: closes.map(() => lowerPrice),
      borderColor: 'rgba(78,205,196,0.7)',
      borderWidth: 1.5,
      borderDash: [5, 5],
      pointRadius: 0,
      fill: false,
      order: 2,
    }});
  }}
  if (upperPrice !== null) {{
    datasets.push({{
      label: 'LP Upper',
      data: closes.map(() => upperPrice),
      borderColor: 'rgba(232,93,117,0.7)',
      borderWidth: 1.5,
      borderDash: [5, 5],
      pointRadius: 0,
      fill: false,
      order: 3,
    }});
  }}
  if (lowerPrice !== null && upperPrice !== null) {{
    datasets.push({{
      label: 'LP Range',
      data: closes.map(() => upperPrice),
      borderColor: 'transparent',
      backgroundColor: 'rgba(124,109,240,0.07)',
      fill: 1,
      pointRadius: 0,
      order: 4,
    }});
  }}

  // Open/close point markers
  const openData = closes.map((v, i) => i === openIdx ? v : null);
  const closeData = closes.map((v, i) => i === closeIdx ? v : null);
  if (openIdx !== null) {{
    datasets.push({{
      label: 'Position Open',
      data: openData,
      borderColor: '#4ecdc4',
      backgroundColor: '#4ecdc4',
      pointRadius: closes.map((v, i) => i === openIdx ? 8 : 0),
      pointStyle: 'triangle',
      showLine: false,
      order: 0,
    }});
  }}
  if (closeIdx !== null) {{
    datasets.push({{
      label: 'Position Close',
      data: closeData,
      borderColor: '#e85d75',
      backgroundColor: '#e85d75',
      pointRadius: closes.map((v, i) => i === closeIdx ? 8 : 0),
      pointStyle: 'rectRot',
      showLine: false,
      order: 0,
    }});
  }}

  const ctx = document.getElementById('priceChart').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{ labels, datasets }},
    options: {{
      maintainAspectRatio: false,
      plugins: {{
        legend: {{
          display: true,
          labels: {{ color:'#6b7084', font:{{size:10}}, boxWidth:18,
            filter: (item) => item.text !== 'LP Range'
          }}
        }},
        tooltip: {{
          mode: 'index', intersect: false,
          callbacks: {{
            label: (c) => c.parsed.y !== null ? ` ${{c.dataset.label}}: ${{c.parsed.y.toFixed(6)}}` : null
          }}
        }}
      }},
      scales: {{
        x: {{ ticks:{{color:'#6b7084',font:{{size:9}},maxTicksLimit:12}}, grid:{{color:'rgba(255,255,255,0.04)'}} }},
        y: {{ ticks:{{color:'#6b7084',font:{{size:10}},callback:(v)=>v.toFixed(4)}}, grid:{{color:'rgba(255,255,255,0.06)'}} }}
      }}
    }}
  }});
}})();"""

    # PnL breakdown: fees vs IL vs total
    il_component = pnl - fees_earned
    pnl_bkd_labels = json.dumps(["Fees Earned", "IL / Price Impact", "Net PnL"])
    pnl_bkd_data = json.dumps([round(fees_earned, 8), round(il_component, 8), round(pnl, 8)])
    pnl_bkd_colors = json.dumps([
        "rgba(124,109,240,0.85)",
        "rgba(232,93,117,0.85)" if il_component < 0 else "rgba(78,205,196,0.85)",
        "rgba(78,205,196,0.85)" if pnl >= 0 else "rgba(232,93,117,0.85)",
    ])

    # Balance change bar (initial vs current/final)
    balance_section_js = ""
    if init_base is not None and base_current is not None:
        bal_labels = json.dumps(["Base (initial)", "Base (current)", "Quote (initial)", "Quote (current)"])
        bal_data = json.dumps([
            round(init_base, 6), round(base_current, 6),
            round(init_quote or 0, 6), round(quote_current or 0, 6),
        ])
        balance_section_js = f"""
(function() {{
  const ctx = document.getElementById('balChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {bal_labels},
      datasets: [{{
        label: 'Amount',
        data: {bal_data},
        backgroundColor: ['rgba(78,205,196,0.4)','rgba(78,205,196,0.85)','rgba(124,109,240,0.4)','rgba(124,109,240,0.85)'],
        borderRadius: 4,
      }}]
    }},
    options: {{
      maintainAspectRatio: false,
      plugins: {{ legend:{{display:false}},
        tooltip:{{callbacks:{{label:(c)=>` ${{c.parsed.y.toFixed(6)}}`}}}}
      }},
      scales: {{
        x: {{ticks:{{color:'#6b7084',font:{{size:10}}}},grid:{{color:'rgba(255,255,255,0.04)'}}}},
        y: {{ticks:{{color:'#6b7084',font:{{size:10}}}},grid:{{color:'rgba(255,255,255,0.06)'}}}}
      }}
    }}
  }});
}})();"""
        balance_chart_html = """
  <div class="section-title">Token Balance: Initial vs Current/Final</div>
  <div class="chart-wrap">
    <div class="chart-container" style="height:200px;">
      <canvas id="balChart"></canvas>
    </div>
  </div>"""
    else:
        balance_chart_html = ""

    def row(label, value, color="#e8eaed"):
        return f'<tr><td style="color:#6b7084;font-size:10px;width:48%">{label}</td><td style="text-align:right;color:{color};font-weight:500;">{value}</td></tr>'

    def spacer():
        return '<tr><td colspan="2" style="padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.06);"></td></tr>'

    f_or_dash = lambda v, fmt=".6f": (f"{v:{fmt}}" if v is not None else "—")

    summary_rows = "".join([
        row("Executor ID", f'<span style="font-family:monospace;font-size:9px;">{eid}</span>'),
        row("Account", account),
        row("Controller", controller or "—"),
        row("Connector", connector),
        row("Trading Pair", pair, "#e8eaed"),
        spacer(),
        row("Status", f'<span style="padding:2px 8px;border-radius:8px;background:{sc}22;font-size:9px;">{status}</span>'),
        row("Close Type", close_type or "—"),
        row("State (live)", state or "—"),
        row("Error Count", str(error_count), "#e85d75" if error_count else "#e8eaed"),
        spacer(),
        row("Created At", created_str),
        row("Closed At", close_str),
        row("Duration", dur_str),
        row("Out of Range", out_range_str),
        spacer(),
        row("Net PnL", f"{pnl:+.8f}", pc),
        row("Net PnL %", f"{pnl_pct * 100:+.4f}%", pc),
        row("Fees Earned", f_or_dash(fees_earned), "#7c6df0"),
        row("Base Fee", f_or_dash(base_fee)),
        row("Quote Fee", f_or_dash(quote_fee)),
        row("Total Value", f_or_dash(total_value)),
        row("Unrealized PnL", f_or_dash(unrealized_pnl), pnl_color(unrealized_pnl)),
        row("Filled Amount", f"${filled:.4f}" if filled else "—"),
        spacer(),
        row("Side", side_str),
        row("LP Lower (config)", f_or_dash(lower_cfg, ".8g")),
        row("LP Upper (config)", f_or_dash(upper_cfg, ".8g")),
        row("LP Lower (actual)", f_or_dash(lower_actual, ".8g")),
        row("LP Upper (actual)", f_or_dash(upper_actual, ".8g")),
        row("Current Price", f_or_dash(current_price, ".8g")),
        row("Position Offset %", f"{pos_offset:.4f}%" if pos_offset is not None else "—"),
        spacer(),
        row("Initial Base", f_or_dash(init_base)),
        row("Initial Quote", f_or_dash(init_quote)),
        row("Base (current)", f_or_dash(base_current)),
        row("Quote (current)", f_or_dash(quote_current)),
        spacer(),
        row("Position Rent", f"{pos_rent:.6f} SOL" if pos_rent is not None else "—", "#e85d75"),
        row("Rent Refunded", f"{rent_refunded:.6f} SOL" if rent_refunded is not None else "—", "#4ecdc4"),
        row("TX Fee", f"{tx_fee:.8f} SOL" if tx_fee is not None else "—"),
        row("Max Retries Hit", "yes" if max_retries else ("no" if max_retries is not None else "—"),
            "#e85d75" if max_retries else "#e8eaed"),
        spacer(),
        row("Auto Close Above", f"{auto_above}s" if auto_above is not None else "—"),
        row("Auto Close Below", f"{auto_below}s" if auto_below is not None else "—"),
        row("Keep Position", "yes" if keep_pos else ("no" if keep_pos is not None else "—")),
        spacer(),
        row("Pool Address", pool_link),
        row("Position Address", solscan_pos),
    ])

    # KPI range display
    lower_disp = f"{lower_cfg:.6g}" if lower_cfg is not None else "—"
    upper_disp = f"{upper_cfg:.6g}" if upper_cfg is not None else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>LP Executor — {pair}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
{DARK_CSS}
  .layout {{ display: grid; grid-template-columns: 1fr 340px; gap: 24px; }}
  @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <h1>{pair} — LP Executor</h1>
  <div class="subtitle">ID: {eid} · {connector}</div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Status</div>
      <div class="kpi-value" style="color:{sc};font-size:14px;">{status}</div>
      <div class="kpi-sub">{close_type or state}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Net PnL</div>
      <div class="kpi-value" style="color:{pc};">{pnl:+.6f}</div>
      <div class="kpi-sub">{pnl_pct * 100:+.4f}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fees Earned</div>
      <div class="kpi-value" style="color:#7c6df0;">{fees_earned:.6f}</div>
      <div class="kpi-sub">quote currency</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Duration</div>
      <div class="kpi-value" style="color:#e8eaed;font-size:15px;">{dur_str}</div>
      <div class="kpi-sub">out of range: {out_range_str}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">LP Range</div>
      <div class="kpi-value" style="font-size:12px;color:#e8eaed;">{lower_disp} – {upper_disp}</div>
      <div class="kpi-sub">Side {side_str.split("—")[0].strip()}</div>
    </div>
  </div>

  <div class="layout">
    <div>
      {price_chart_section}

      {balance_chart_html}

      <div class="section-title">PnL Breakdown</div>
      <div class="chart-wrap">
        <div class="chart-container" style="height:190px;">
          <canvas id="pnlChart"></canvas>
        </div>
      </div>
    </div>

    <div>
      <div class="section-title">Position Summary</div>
      <table class="summary-table">
        <tbody>{summary_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="footer">Hummingbot LP Executor Dashboard · {eid[:16]}… · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</div>
<script>
{price_chart_js}

{balance_section_js}

(function() {{
  const ctx = document.getElementById('pnlChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: {pnl_bkd_labels},
      datasets: [{{
        label: 'Quote',
        data: {pnl_bkd_data},
        backgroundColor: {pnl_bkd_colors},
        borderColor: {pnl_bkd_colors},
        borderWidth: 1,
        borderRadius: 4,
      }}]
    }},
    options: {{
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {{
        legend: {{display:false}},
        tooltip: {{callbacks: {{label: (c) => ` ${{c.parsed.x.toFixed(8)}}`}}}}
      }},
      scales: {{
        x: {{ticks:{{color:'#6b7084',font:{{size:10}},callback:(v)=>v.toFixed(6)}},grid:{{color:'rgba(255,255,255,0.06)'}}}},
        y: {{ticks:{{color:'#8b8fa3',font:{{size:11}}}},grid:{{color:'rgba(255,255,255,0.03)'}}}}
      }}
    }}
  }});
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Visualize LP executor performance as an interactive HTML dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pair", "-p", help="Filter by trading pair (e.g., SOL-USDC)")
    parser.add_argument("--id", dest="executor_id", help="Single executor ID for detail view")
    parser.add_argument("--status", "-s", help="Filter by status (e.g., TERMINATED, RUNNING)")
    parser.add_argument("--output", "-o", help="Output HTML path")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    base_url, username, password = get_api_config()
    auth_header = make_auth_header(username, password)

    # Output path
    if args.output:
        output_path = args.output
    else:
        os.makedirs("data", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.executor_id:
            output_path = f"data/lp_executor_{args.executor_id[:10]}_{ts}.html"
        else:
            suffix = f"_{args.pair.replace('-', '_')}" if args.pair else ""
            output_path = f"data/lp_executor_dashboard{suffix}_{ts}.html"

    if args.executor_id:
        # --- Single executor detail ---
        print(f"Fetching executor {args.executor_id} from {base_url} ...")
        ex = fetch_executor_by_id(base_url, auth_header, args.executor_id)

        if not ex:
            print("Executor not found.")
            return 1

        # If returned as a list (some API versions wrap in {"data": [...]})
        if isinstance(ex, list):
            ex = ex[0] if ex else None
        if not ex:
            print("Executor not found.")
            return 1
        if isinstance(ex, dict) and "data" in ex:
            items = ex["data"]
            ex = items[0] if items else None
        if not ex:
            print("Executor not found.")
            return 1

        enrich(ex)
        pair = _s(ex.get("trading_pair"))
        created_ts = ex.get("_created_ts")
        close_ts = ex.get("_close_ts")

        # Fetch candles for price chart (KuCoin supports major pairs only)
        candles = None
        if pair and created_ts is not None:
            import time
            end = close_ts if close_ts else int(time.time()) + 300
            print(f"Fetching 5m candles for {pair} from KuCoin ...")
            candles = fetch_candles(base_url, auth_header, pair,
                                    start_time=created_ts - 300,
                                    end_time=end + 300,
                                    interval="5m")
            if candles:
                print(f"  Loaded {len(candles)} candles.")
            else:
                print("  No candles — price chart skipped.")

        print("Generating single executor dashboard ...")
        html = build_single_html(ex, candles)

    else:
        # --- Multi-executor overview ---
        print(f"Fetching LP executors from {base_url} ...")
        executors = fetch_lp_executors(base_url, auth_header, args.pair, args.status)

        if not executors:
            filters = []
            if args.pair:
                filters.append(f"pair={args.pair}")
            if args.status:
                filters.append(f"status={args.status}")
            suffix = f" ({', '.join(filters)})" if filters else ""
            print(f"No LP executors found{suffix}.")
            return 0

        print(f"Found {len(executors)} LP executor(s).")
        html = build_multi_html(executors, {"pair": args.pair, "status": args.status})

    # Write
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Dashboard written to: {output_path}")

    if not args.no_open:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
        print("Opened in browser.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
