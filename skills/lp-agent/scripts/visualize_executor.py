#!/usr/bin/env python3
"""
Generate an interactive HTML dashboard for executor performance from the Hummingbot REST API.

Works directly from the API — no SQLite database required. For single executor view,
fetches real price candles from KuCoin to overlay the LP range on a price chart.

Usage:
    python scripts/visualize_executor.py                                 # all executors
    python scripts/visualize_executor.py --pair SOL-USDC                # filter by pair
    python scripts/visualize_executor.py --id <executor_id>             # single executor detail
    python scripts/visualize_executor.py --connector meteora/clmm       # filter by connector
    python scripts/visualize_executor.py --status TERMINATED            # filter by status
    python scripts/visualize_executor.py --output report.html           # custom output path
    python scripts/visualize_executor.py --no-open                      # don't auto-open browser

Examples:
    python scripts/visualize_executor.py --pair SOL-USDC
    python scripts/visualize_executor.py --id abc123 --output my_executor.html
    python scripts/visualize_executor.py --connector meteora/clmm --status TERMINATED
"""

import argparse
import base64
import json
import math
import os
import sys
import urllib.request
import urllib.error
import webbrowser
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Environment / Auth (mirrors export_executor.py)
# ---------------------------------------------------------------------------

def load_env():
    """Load environment variables from .env files. Priority: ~/mcp/.env, ~/.hummingbot/.env, .env"""
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
    """Get API base URL and auth credentials from environment."""
    load_env()
    base_url = os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000").rstrip("/")
    username = os.environ.get("HUMMINGBOT_USERNAME", "admin")
    password = os.environ.get("HUMMINGBOT_PASSWORD", "admin")
    return base_url, username, password


def make_auth_header(username, password):
    """Build Basic Auth header value."""
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_post(url, payload, auth_header, timeout=30):
    """POST JSON to API endpoint, return parsed response dict."""
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
    """GET from API endpoint, return parsed response dict."""
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
# Executor fetching
# ---------------------------------------------------------------------------

def fetch_executors(base_url, auth_header, trading_pair=None, connector_name=None, status=None):
    """Fetch executors via POST /executors/search with optional filters."""
    url = f"{base_url}/executors/search"
    payload = {}
    if trading_pair:
        payload["trading_pair"] = trading_pair
    if connector_name:
        payload["connector_name"] = connector_name
    if status:
        payload["status"] = status

    try:
        result = api_post(url, payload, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executors: {e}")
        sys.exit(1)

    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ("executors", "data", "items", "results"):
            if key in result and isinstance(result[key], list):
                return result[key]
    return []


def fetch_executor_by_id(base_url, auth_header, executor_id):
    """Fetch a single executor by ID via GET /executors/{id}."""
    url = f"{base_url}/executors/{executor_id}"
    try:
        return api_get(url, auth_header)
    except RuntimeError as e:
        print(f"Error fetching executor {executor_id}: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Candle fetching
# ---------------------------------------------------------------------------

def map_pair_for_kucoin(trading_pair):
    """Map trading pair to KuCoin equivalent (e.g. SOL-USDC -> SOL-USDT)."""
    return trading_pair.replace("USDC", "USDT").replace("usdc", "usdt")


def fetch_candles(base_url, auth_header, trading_pair, start_time, end_time, interval="5m"):
    """
    Fetch OHLCV candles from KuCoin via POST /market-data/historical-candles.
    Returns list of candle dicts or None on failure.
    """
    kucoin_pair = map_pair_for_kucoin(trading_pair)
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
        # Result may be a list of candles or wrapped in a key
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

def _float(v, default=None):
    """Safe float conversion."""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _str(v, default=""):
    if v is None:
        return default
    return str(v)


def parse_created_at_ts(created_at_str):
    """Parse ISO timestamp string to unix timestamp float."""
    if not created_at_str:
        return None
    try:
        clean = created_at_str.replace("+00:00", "").replace("Z", "")
        # Remove sub-microsecond precision
        if "." in clean:
            parts = clean.split(".")
            clean = parts[0] + "." + parts[1][:6]
        dt = datetime.fromisoformat(clean)
        # Convert to UTC unix timestamp (assume UTC if no tz)
        import calendar
        return calendar.timegm(dt.timetuple()) + dt.microsecond / 1e6
    except Exception:
        return None


def enrich_executor(executor):
    """Add computed fields to an executor dict (in-place). Returns executor."""
    config = executor.get("config") or {}
    custom = executor.get("custom_info") or {}

    created_at_str = _str(executor.get("created_at"))
    created_at_ts = parse_created_at_ts(created_at_str)
    close_ts = _float(executor.get("close_timestamp"))

    duration_seconds = None
    if created_at_ts is not None and close_ts is not None and close_ts > created_at_ts:
        duration_seconds = round(close_ts - created_at_ts, 1)

    executor["_created_at_ts"] = created_at_ts
    executor["_close_ts"] = close_ts
    executor["_duration_seconds"] = duration_seconds
    executor["_config"] = config
    executor["_custom"] = custom
    return executor


def fmt_duration(seconds):
    """Format seconds as human-readable duration."""
    if seconds is None or seconds <= 0:
        return "—"
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"


def fmt_ts(ts):
    """Format unix timestamp as local datetime string."""
    if ts is None:
        return "—"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


# ---------------------------------------------------------------------------
# HTML generation — multi-executor view
# ---------------------------------------------------------------------------

def build_multi_executor_html(executors, filters):
    """Generate the HTML dashboard for multiple executors."""
    # Compute KPIs
    total_pnl = sum(_float(ex.get("net_pnl_quote"), 0) for ex in executors)
    total_fees = sum(_float(ex.get("cum_fees_quote"), 0) for ex in executors)
    wins = sum(1 for ex in executors if _float(ex.get("net_pnl_quote"), 0) >= 0)
    losses = len(executors) - wins

    # Build table rows and chart data
    table_rows_html = ""
    chart_labels = []
    chart_pnl_values = []
    chart_colors = []

    for idx, ex in enumerate(executors):
        enrich_executor(ex)
        eid = _str(ex.get("executor_id"))
        short_id = eid[:8] + "..." if len(eid) > 12 else eid
        pair = _str(ex.get("trading_pair"))
        connector = _str(ex.get("connector_name"))
        status = _str(ex.get("status"))
        close_type = _str(ex.get("close_type"))
        pnl = _float(ex.get("net_pnl_quote"), 0)
        pnl_pct = _float(ex.get("net_pnl_pct"), 0)
        fees = _float(ex.get("cum_fees_quote"), 0)
        filled = _float(ex.get("filled_amount_quote"), 0)
        custom = ex.get("_custom") or {}
        duration = ex.get("_duration_seconds")
        created_at_ts = ex.get("_created_at_ts")
        close_ts = ex.get("_close_ts")

        pnl_color = "#4ecdc4" if pnl >= 0 else "#e85d75"
        status_color = {
            "TERMINATED": "#4ecdc4",
            "ACTIVE": "#f0c644",
            "FAILED": "#e85d75",
        }.get(status, "#8b8fa3")

        created_str = fmt_ts(created_at_ts) if created_at_ts else _str(ex.get("created_at"))[:19]
        dur_str = fmt_duration(duration)

        lower = _float(custom.get("lower_price"))
        upper = _float(custom.get("upper_price"))
        range_str = f"{lower:.4f} – {upper:.4f}" if lower is not None and upper is not None else "—"

        table_rows_html += f"""
        <tr onclick="window.location.hash='#ex-{eid}'" style="cursor:pointer;">
          <td style="color:#6b7084;font-size:10px;">{idx + 1}</td>
          <td style="font-family:monospace;font-size:10px;" title="{eid}">{short_id}</td>
          <td style="color:#e8eaed;font-weight:500;">{pair}</td>
          <td style="font-size:10px;color:#8b8fa3;">{connector.split("/")[0] if "/" in connector else connector}</td>
          <td style="font-size:10px;">{created_str}</td>
          <td style="font-size:10px;">{dur_str}</td>
          <td style="color:#e8eaed;">${filled:.2f}</td>
          <td style="color:{pnl_color};font-weight:600;">${pnl:.4f}</td>
          <td style="color:{pnl_color};">{pnl_pct * 100:.2f}%</td>
          <td style="color:#7c6df0;">${fees:.4f}</td>
          <td style="font-size:10px;">{range_str}</td>
          <td><span style="font-size:9px;padding:2px 8px;border-radius:10px;background:{status_color}22;color:{status_color};">{status}</span></td>
          <td style="font-size:10px;color:#6b7084;">{close_type}</td>
        </tr>"""

        # Chart data (show last 30 to keep readable)
        if idx < 50:
            chart_labels.append(f"#{idx + 1} {pair}")
            chart_pnl_values.append(round(pnl, 6))
            chart_colors.append("rgba(78,205,196,0.8)" if pnl >= 0 else "rgba(232,93,117,0.8)")

    chart_labels_json = json.dumps(chart_labels)
    chart_pnl_json = json.dumps(chart_pnl_values)
    chart_colors_json = json.dumps(chart_colors)

    filter_parts = []
    if filters.get("pair"):
        filter_parts.append(f"pair={filters['pair']}")
    if filters.get("connector"):
        filter_parts.append(f"connector={filters['connector']}")
    if filters.get("status"):
        filter_parts.append(f"status={filters['status']}")
    filter_str = " · ".join(filter_parts) if filter_parts else "all executors"

    pnl_color_class = "#4ecdc4" if total_pnl >= 0 else "#e85d75"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Executor Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0d1117; color: #e8eaed; font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace; font-size: 12px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 20px; }}
  h1 {{ font-size: 24px; font-weight: 700; color: #4ecdc4; margin-bottom: 4px; }}
  .subtitle {{ font-size: 11px; color: #6b7084; margin-bottom: 24px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 28px; }}
  .kpi-card {{ background: #161b27; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 16px 18px; }}
  .kpi-label {{ font-size: 10px; color: #6b7084; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
  .kpi-value {{ font-size: 22px; font-weight: 700; }}
  .kpi-sub {{ font-size: 10px; color: #555870; margin-top: 4px; }}
  .section-title {{ font-size: 11px; font-weight: 600; color: #8b8fa3; text-transform: uppercase; letter-spacing: 0.08em; margin: 28px 0 14px; }}
  .chart-wrap {{ background: #161b27; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 20px; margin-bottom: 28px; }}
  .chart-container {{ height: 280px; position: relative; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b27; border-radius: 10px; overflow: hidden; }}
  th {{ padding: 10px 8px; text-align: left; font-size: 10px; color: #6b7084; border-bottom: 1px solid rgba(255,255,255,0.07); font-weight: 500; white-space: nowrap; }}
  td {{ padding: 9px 8px; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.03); vertical-align: middle; }}
  tr:hover td {{ background: rgba(255,255,255,0.02); }}
  tr:last-child td {{ border-bottom: none; }}
  .table-wrap {{ overflow-x: auto; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); }}
  .footer {{ font-size: 10px; color: #3a3d50; text-align: center; margin-top: 32px; padding-bottom: 16px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Executor Dashboard</h1>
  <div class="subtitle">{filter_str} · {len(executors)} executor(s) · generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Executors</div>
      <div class="kpi-value" style="color:#e8eaed;">{len(executors)}</div>
      <div class="kpi-sub">{wins} wins · {losses} losses</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total PnL</div>
      <div class="kpi-value" style="color:{pnl_color_class};">${total_pnl:.4f}</div>
      <div class="kpi-sub">net quote currency</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Fees</div>
      <div class="kpi-value" style="color:#7c6df0;">${total_fees:.4f}</div>
      <div class="kpi-sub">fees earned</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value" style="color:#e8eaed;">{(wins / len(executors) * 100):.0f}%</div>
      <div class="kpi-sub">{wins} profitable</div>
    </div>
  </div>

  <!-- PnL Bar Chart -->
  <div class="section-title">PnL per Executor</div>
  <div class="chart-wrap">
    <div class="chart-container">
      <canvas id="pnlChart"></canvas>
    </div>
  </div>

  <!-- Executor Table -->
  <div class="section-title">Executor History ({len(executors)} total)</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>ID</th>
          <th>Pair</th>
          <th>Connector</th>
          <th>Created</th>
          <th>Duration</th>
          <th>Filled $</th>
          <th>PnL $</th>
          <th>PnL %</th>
          <th>Fees $</th>
          <th>Price Range</th>
          <th>Status</th>
          <th>Close Type</th>
        </tr>
      </thead>
      <tbody>
        {table_rows_html}
      </tbody>
    </table>
  </div>

  <div class="footer">Hummingbot Executor Dashboard · {len(executors)} executors · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</div>

<script>
(function() {{
  const labels = {chart_labels_json};
  const pnlValues = {chart_pnl_json};
  const colors = {chart_colors_json};

  const ctx = document.getElementById('pnlChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [{{
        label: 'Net PnL (quote)',
        data: pnlValues,
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 3,
      }}]
    }},
    options: {{
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ` PnL: ${{ctx.parsed.y.toFixed(6)}}`
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{ color: '#6b7084', font: {{ size: 9 }}, maxRotation: 45 }},
          grid: {{ color: 'rgba(255,255,255,0.04)' }},
        }},
        y: {{
          ticks: {{ color: '#6b7084', font: {{ size: 10 }}, callback: (v) => '$' + v.toFixed(4) }},
          grid: {{ color: 'rgba(255,255,255,0.06)' }},
        }}
      }}
    }}
  }});
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTML generation — single executor view
# ---------------------------------------------------------------------------

def build_single_executor_html(executor, candles):
    """Generate detailed HTML dashboard for a single executor."""
    enrich_executor(executor)

    eid = _str(executor.get("executor_id"))
    pair = _str(executor.get("trading_pair"))
    connector = _str(executor.get("connector_name"))
    status = _str(executor.get("status"))
    close_type = _str(executor.get("close_type"))
    pnl = _float(executor.get("net_pnl_quote"), 0)
    pnl_pct = _float(executor.get("net_pnl_pct"), 0)
    fees = _float(executor.get("cum_fees_quote"), 0)
    filled = _float(executor.get("filled_amount_quote"), 0)

    config = executor.get("_config") or {}
    custom = executor.get("_custom") or {}
    created_at_ts = executor.get("_created_at_ts")
    close_ts = executor.get("_close_ts")
    duration = executor.get("_duration_seconds")

    # Price bounds
    lower_price = _float(custom.get("lower_price")) or _float(config.get("lower_price"))
    upper_price = _float(custom.get("upper_price")) or _float(config.get("upper_price"))
    current_price = _float(custom.get("current_price"))
    initial_base = _float(custom.get("initial_base_amount")) or _float(config.get("base_amount"))
    initial_quote = _float(custom.get("initial_quote_amount")) or _float(config.get("quote_amount"))
    base_final = _float(custom.get("base_amount"))
    quote_final = _float(custom.get("quote_amount"))
    fees_earned = _float(custom.get("fees_earned_quote"), 0)
    position_rent = _float(custom.get("position_rent"))
    rent_refunded = _float(custom.get("position_rent_refunded"))
    tx_fee = _float(custom.get("tx_fee"))
    out_of_range_sec = _float(custom.get("out_of_range_seconds"))
    pool_address = _str(config.get("pool_address"))
    position_address = _str(custom.get("position_address"))
    auto_close_above = config.get("auto_close_above_range_seconds")
    auto_close_below = config.get("auto_close_below_range_seconds")
    side_val = config.get("side")

    side_map = {0: "BOTH", 1: "BUY (quote-only)", 2: "SELL (base-only)"}
    side_str = side_map.get(side_val, str(side_val)) if side_val is not None else "—"

    pnl_color = "#4ecdc4" if pnl >= 0 else "#e85d75"
    status_color = {
        "TERMINATED": "#4ecdc4",
        "ACTIVE": "#f0c644",
        "FAILED": "#e85d75",
    }.get(status, "#8b8fa3")

    created_str = fmt_ts(created_at_ts)
    close_str = fmt_ts(close_ts)
    dur_str = fmt_duration(duration)
    out_range_str = fmt_duration(out_of_range_sec)

    # Build candle chart data (if available)
    candle_chart_js = "null"
    candle_chart_section = ""

    if candles:
        # Normalize candles — may be list of lists [ts, o, h, l, c, v] or list of dicts
        candle_data = []
        for c in candles:
            if isinstance(c, list) and len(c) >= 5:
                ts, o, h, l, close_c = float(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4])
                candle_data.append({"ts": ts, "o": o, "h": h, "l": l, "c": close_c})
            elif isinstance(c, dict):
                ts = _float(c.get("timestamp") or c.get("ts") or c.get("open_time"), 0)
                o = _float(c.get("open") or c.get("o"), 0)
                h = _float(c.get("high") or c.get("h"), 0)
                l = _float(c.get("low") or c.get("l"), 0)
                close_c = _float(c.get("close") or c.get("c"), 0)
                if ts and close_c:
                    candle_data.append({"ts": ts, "o": o, "h": h, "l": l, "c": close_c})

        if candle_data:
            candle_data.sort(key=lambda x: x["ts"])
            candle_labels = [datetime.fromtimestamp(d["ts"]).strftime("%H:%M") for d in candle_data]
            candle_closes = [d["c"] for d in candle_data]
            candle_labels_json = json.dumps(candle_labels)
            candle_closes_json = json.dumps(candle_closes)
            lp = round(lower_price, 6) if lower_price is not None else "null"
            up = round(upper_price, 6) if upper_price is not None else "null"

            candle_chart_section = """
  <div class="section-title">Price Chart with LP Range (5m candles from KuCoin)</div>
  <div class="chart-wrap">
    <div class="chart-container" style="height:280px;">
      <canvas id="priceChart"></canvas>
    </div>
  </div>"""
            candle_chart_js = f"""
(function() {{
  const labels = {candle_labels_json};
  const closes = {candle_closes_json};
  const lowerPrice = {lp};
  const upperPrice = {up};

  const datasets = [{{
    label: 'Close Price',
    data: closes,
    borderColor: '#f0c644',
    backgroundColor: 'rgba(240,198,68,0.06)',
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    tension: 0.1,
  }}];

  if (lowerPrice !== null) {{
    datasets.push({{
      label: 'Lower Range',
      data: closes.map(() => lowerPrice),
      borderColor: 'rgba(78,205,196,0.6)',
      borderWidth: 1,
      borderDash: [4, 4],
      pointRadius: 0,
      fill: false,
    }});
  }}
  if (upperPrice !== null) {{
    datasets.push({{
      label: 'Upper Range',
      data: closes.map(() => upperPrice),
      borderColor: 'rgba(232,93,117,0.6)',
      borderWidth: 1,
      borderDash: [4, 4],
      pointRadius: 0,
      fill: false,
    }});
  }}
  if (lowerPrice !== null && upperPrice !== null) {{
    datasets.push({{
      label: 'LP Range Fill',
      data: closes.map(() => upperPrice),
      borderColor: 'transparent',
      backgroundColor: 'rgba(124,109,240,0.08)',
      fill: datasets.findIndex(d => d.label === 'Lower Range'),
      pointRadius: 0,
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
          labels: {{ color: '#6b7084', font: {{ size: 10 }}, boxWidth: 20 }},
          filter: (item) => item.text !== 'LP Range Fill',
        }},
        tooltip: {{
          mode: 'index',
          intersect: false,
          callbacks: {{
            label: (ctx) => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(4)}}`
          }}
        }},
      }},
      scales: {{
        x: {{
          ticks: {{ color: '#6b7084', font: {{ size: 9 }}, maxTicksLimit: 12 }},
          grid: {{ color: 'rgba(255,255,255,0.04)' }},
        }},
        y: {{
          ticks: {{ color: '#6b7084', font: {{ size: 10 }}, callback: (v) => v.toFixed(2) }},
          grid: {{ color: 'rgba(255,255,255,0.06)' }},
        }}
      }}
    }}
  }});
}})();"""

    # PnL breakdown chart
    pnl_breakdown_labels = json.dumps(["Fees Earned", "IL / Value Change", "Net PnL"])
    il_component = pnl - fees_earned  # Net PnL = IL + fees
    pnl_breakdown_data = json.dumps([round(fees_earned, 6), round(il_component, 6), round(pnl, 6)])
    pnl_breakdown_colors = json.dumps([
        "rgba(124,109,240,0.8)",
        "rgba(232,93,117,0.8)" if il_component < 0 else "rgba(78,205,196,0.8)",
        "rgba(78,205,196,0.8)" if pnl >= 0 else "rgba(232,93,117,0.8)",
    ])

    def def_row(label, value, color="#e8eaed"):
        return f'<tr><td style="color:#6b7084;font-size:10px;">{label}</td><td style="text-align:right;color:{color};font-weight:500;">{value}</td></tr>'

    summary_rows = "".join([
        def_row("Executor ID", f'<span style="font-family:monospace;font-size:10px;">{eid}</span>'),
        def_row("Trading Pair", pair, "#e8eaed"),
        def_row("Connector", connector),
        def_row("Status", f'<span style="padding:2px 8px;border-radius:8px;background:{status_color}22;font-size:9px;">{status}</span>'),
        def_row("Close Type", close_type),
        def_row("Created At", created_str),
        def_row("Closed At", close_str),
        def_row("Duration", dur_str),
        def_row("Side", side_str),
        def_row("", ""),  # spacer
        def_row("Filled Amount", f"${filled:.4f}"),
        def_row("Net PnL", f"${pnl:.6f}", pnl_color),
        def_row("Net PnL %", f"{pnl_pct * 100:.4f}%", pnl_color),
        def_row("Fees Earned", f"${fees_earned:.6f}", "#7c6df0"),
        def_row("", ""),
        def_row("Lower Price", f"{lower_price:.6f}" if lower_price is not None else "—"),
        def_row("Upper Price", f"{upper_price:.6f}" if upper_price is not None else "—"),
        def_row("Current Price", f"{current_price:.6f}" if current_price is not None else "—"),
        def_row("", ""),
        def_row("Initial Base", f"{initial_base:.6f}" if initial_base is not None else "—"),
        def_row("Initial Quote", f"{initial_quote:.6f}" if initial_quote is not None else "—"),
        def_row("Final Base", f"{base_final:.6f}" if base_final is not None else "—"),
        def_row("Final Quote", f"{quote_final:.6f}" if quote_final is not None else "—"),
        def_row("", ""),
        def_row("Position Rent", f"{position_rent:.6f} SOL" if position_rent is not None else "—", "#e85d75"),
        def_row("Rent Refunded", f"{rent_refunded:.6f} SOL" if rent_refunded is not None else "—", "#4ecdc4"),
        def_row("TX Fee", f"{tx_fee:.8f} SOL" if tx_fee is not None else "—"),
        def_row("Out of Range", out_range_str),
        def_row("Auto Close Above", f"{auto_close_above}s" if auto_close_above is not None else "—"),
        def_row("Auto Close Below", f"{auto_close_below}s" if auto_close_below is not None else "—"),
        def_row("", ""),
        def_row("Pool Address", f'<span style="font-family:monospace;font-size:9px;word-break:break-all;">{pool_address or "—"}</span>'),
        def_row("Position Address", f'<span style="font-family:monospace;font-size:9px;word-break:break-all;">{position_address or "—"}</span>'),
    ])

    lower_price_str = "{:.2f}".format(lower_price) if lower_price is not None else "—"
    upper_price_str = "{:.2f}".format(upper_price) if upper_price is not None else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Executor {eid[:12]}... — {pair}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0d1117; color: #e8eaed; font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace; font-size: 12px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 20px; }}
  h1 {{ font-size: 22px; font-weight: 700; color: #4ecdc4; margin-bottom: 2px; }}
  .subtitle {{ font-size: 11px; color: #6b7084; margin-bottom: 24px; font-family: monospace; }}
  .layout {{ display: grid; grid-template-columns: 1fr 340px; gap: 24px; }}
  @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  .main-col {{ min-width: 0; }}
  .side-col {{ min-width: 0; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 24px; }}
  .kpi-card {{ background: #161b27; border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 14px 16px; }}
  .kpi-label {{ font-size: 10px; color: #6b7084; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
  .kpi-value {{ font-size: 20px; font-weight: 700; }}
  .kpi-sub {{ font-size: 10px; color: #555870; margin-top: 4px; }}
  .section-title {{ font-size: 11px; font-weight: 600; color: #8b8fa3; text-transform: uppercase; letter-spacing: 0.08em; margin: 24px 0 12px; }}
  .chart-wrap {{ background: #161b27; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px; margin-bottom: 20px; }}
  .chart-container {{ position: relative; }}
  .summary-table {{ background: #161b27; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; overflow: hidden; width: 100%; }}
  .summary-table td {{ padding: 7px 12px; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.03); }}
  .summary-table tr:last-child td {{ border-bottom: none; }}
  .summary-table tr:hover td {{ background: rgba(255,255,255,0.02); }}
  .footer {{ font-size: 10px; color: #3a3d50; text-align: center; margin-top: 32px; padding-bottom: 16px; }}
</style>
</head>
<body>
<div class="container">
  <h1>{pair} — Executor Detail</h1>
  <div class="subtitle">ID: {eid}</div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Status</div>
      <div class="kpi-value" style="color:{status_color};font-size:14px;">{status}</div>
      <div class="kpi-sub">{close_type}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Net PnL</div>
      <div class="kpi-value" style="color:{pnl_color};">${pnl:.4f}</div>
      <div class="kpi-sub">{pnl_pct * 100:.4f}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fees Earned</div>
      <div class="kpi-value" style="color:#7c6df0;">${fees_earned:.4f}</div>
      <div class="kpi-sub">quote currency</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Filled Size</div>
      <div class="kpi-value" style="color:#e8eaed;">${filled:.2f}</div>
      <div class="kpi-sub">{dur_str} duration</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Price Range</div>
      <div class="kpi-value" style="font-size:13px;color:#e8eaed;">{lower_price_str} – {upper_price_str}</div>
      <div class="kpi-sub">LP bounds</div>
    </div>
  </div>

  <div class="layout">
    <div class="main-col">
      {candle_chart_section}

      <!-- PnL Breakdown Chart -->
      <div class="section-title">PnL Breakdown</div>
      <div class="chart-wrap">
        <div class="chart-container" style="height:200px;">
          <canvas id="pnlBreakdownChart"></canvas>
        </div>
      </div>
    </div>

    <div class="side-col">
      <!-- Summary Table -->
      <div class="section-title">Position Summary</div>
      <table class="summary-table">
        <tbody>
          {summary_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">Hummingbot Executor Dashboard · {eid} · {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
</div>

<script>
{candle_chart_js if candles else "// No candle data available"}

(function() {{
  const labels = {pnl_breakdown_labels};
  const data = {pnl_breakdown_data};
  const colors = {pnl_breakdown_colors};

  const ctx = document.getElementById('pnlBreakdownChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [{{
        label: 'Amount (quote)',
        data: data,
        backgroundColor: colors,
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 4,
      }}]
    }},
    options: {{
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ` ${{ctx.parsed.x.toFixed(6)}}`
          }}
        }}
      }},
      scales: {{
        x: {{
          ticks: {{ color: '#6b7084', font: {{ size: 10 }}, callback: (v) => '$' + v.toFixed(4) }},
          grid: {{ color: 'rgba(255,255,255,0.06)' }},
        }},
        y: {{
          ticks: {{ color: '#8b8fa3', font: {{ size: 11 }} }},
          grid: {{ color: 'rgba(255,255,255,0.03)' }},
        }}
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
        description="Visualize executor performance as an interactive HTML dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--pair", "-p", help="Filter by trading pair (e.g., SOL-USDC)")
    parser.add_argument("--id", dest="executor_id", help="Single executor ID for detail view")
    parser.add_argument("--connector", "-c", help="Filter by connector (e.g., meteora/clmm)")
    parser.add_argument("--status", "-s", help="Filter by status (e.g., TERMINATED)")
    parser.add_argument("--output", "-o", help="Output HTML path (default: data/executor_dashboard_<timestamp>.html)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")

    args = parser.parse_args()

    base_url, username, password = get_api_config()
    auth_header = make_auth_header(username, password)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        os.makedirs("data", exist_ok=True)
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{args.pair.replace('-', '_')}" if args.pair else ""
        if args.executor_id:
            suffix = f"_{args.executor_id[:8]}"
        output_path = f"data/executor_dashboard{suffix}_{ts}.html"

    if args.executor_id:
        # Single executor detail view
        print(f"Fetching executor {args.executor_id} from {base_url} ...")
        executor = fetch_executor_by_id(base_url, auth_header, args.executor_id)

        if not executor:
            print(f"Executor not found: {args.executor_id}")
            return 1

        enrich_executor(executor)
        pair = _str(executor.get("trading_pair"))
        created_at_ts = executor.get("_created_at_ts")
        close_ts = executor.get("_close_ts")

        # Fetch candles if we have timing data
        candles = None
        if pair and created_at_ts is not None and close_ts is not None:
            print(f"Fetching 5m candles for {pair} from KuCoin ...")
            candles = fetch_candles(
                base_url, auth_header,
                pair,
                start_time=created_at_ts - 300,
                end_time=close_ts + 300,
                interval="5m",
            )
            if candles:
                print(f"  Loaded {len(candles)} candles.")
            else:
                print("  No candles fetched — price chart will be skipped.")
        elif pair and created_at_ts is not None:
            # Still open — use current time as end
            import time
            print(f"Fetching 5m candles for {pair} from KuCoin (executor still open) ...")
            candles = fetch_candles(
                base_url, auth_header,
                pair,
                start_time=created_at_ts - 300,
                end_time=int(time.time()) + 300,
                interval="5m",
            )

        print(f"Generating single executor dashboard ...")
        html = build_single_executor_html(executor, candles)

    else:
        # Multi-executor view
        print(f"Fetching executors from {base_url} ...")
        executors = fetch_executors(base_url, auth_header, args.pair, args.connector, args.status)

        if not executors:
            filters = []
            if args.pair:
                filters.append(f"pair={args.pair}")
            if args.connector:
                filters.append(f"connector={args.connector}")
            if args.status:
                filters.append(f"status={args.status}")
            filter_str = f" ({', '.join(filters)})" if filters else ""
            print(f"No executors found{filter_str}.")
            return 0

        print(f"Found {len(executors)} executor(s).")
        filters = {
            "pair": args.pair,
            "connector": args.connector,
            "status": args.status,
        }
        html = build_multi_executor_html(executors, filters)

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard written to: {output_path}")

    if not args.no_open:
        abs_path = os.path.abspath(output_path)
        webbrowser.open(f"file://{abs_path}")
        print("Opened in browser.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
