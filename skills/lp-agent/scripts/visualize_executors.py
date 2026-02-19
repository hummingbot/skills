#!/usr/bin/env python3
"""
Export executor data from SQLite and generate an interactive HTML dashboard.

Usage:
    python visualize_executors.py <controller_id> [--db <path>] [--csv <path>] [--output <path>] [--no-open]

Examples:
    python visualize_executors.py lp_rebalancer_4                          # DB -> HTML, opens browser
    python visualize_executors.py lp_rebalancer_4 --db data/my.sqlite      # specific DB
    python visualize_executors.py --csv exports/lp_rebalancer_4.csv        # CSV -> HTML
    python visualize_executors.py lp_rebalancer_4 --output report.html     # custom output path
    python visualize_executors.py lp_rebalancer_4 --no-open                # don't open browser
"""

import argparse
import csv
import json
import os
import sqlite3
import webbrowser
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# DB helpers (adapted from export_executors.py)
# ---------------------------------------------------------------------------

STATUS_MAP = {0: "NOT_STARTED", 1: "RUNNING", 2: "RUNNING", 3: "SHUTTING_DOWN", 4: "TERMINATED"}
CLOSE_TYPE_MAP = {
    None: "", 1: "TIME_LIMIT", 2: "STOP_LOSS", 3: "TAKE_PROFIT",
    4: "POSITION_HOLD", 5: "EARLY_STOP", 6: "TRAILING_STOP",
    7: "INSUFFICIENT_BALANCE", 8: "EXPIRED", 9: "FAILED",
}


def find_latest_db(data_dir: str = "data") -> str:
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    sqlite_files = list(data_path.glob("*.sqlite"))
    if not sqlite_files:
        raise FileNotFoundError(f"No .sqlite files found in {data_dir}")
    sqlite_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return str(sqlite_files[0])


def query_executors(controller_id: str, db_path: str) -> list[dict]:
    """Query executors from SQLite and return list of dicts (same shape as CSV rows)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, type, close_type, close_timestamp, status,
               net_pnl_pct, net_pnl_quote, cum_fees_quote, filled_amount_quote,
               is_active, is_trading, controller_id, config, custom_info
        FROM Executors
        WHERE controller_id = ?
        ORDER BY timestamp ASC
    """, (controller_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        raise ValueError(f"No executors found for controller_id: {controller_id}")

    result = []
    for row in rows:
        (id_, timestamp, type_, close_type, close_timestamp, status,
         net_pnl_pct, net_pnl_quote, cum_fees_quote, filled_amount_quote,
         is_active, is_trading, ctrl_id, config_json, custom_info_json) = row

        config = json.loads(config_json) if config_json else {}
        custom_info = json.loads(custom_info_json) if custom_info_json else {}
        market = config.get("market", {})

        result.append({
            "id": id_,
            "created_at": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "type": type_,
            "status": STATUS_MAP.get(status, str(status)),
            "close_type": CLOSE_TYPE_MAP.get(close_type, str(close_type)),
            "close_timestamp": (
                datetime.fromtimestamp(close_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                if close_timestamp else ""
            ),
            "net_pnl_pct": _float(net_pnl_pct),
            "net_pnl_quote": _float(net_pnl_quote),
            "cum_fees_quote": _float(cum_fees_quote),
            "filled_amount_quote": _float(filled_amount_quote),
            "is_active": is_active,
            "is_trading": is_trading,
            "controller_id": ctrl_id,
            "cfg_connector": market.get("connector_name", ""),
            "cfg_trading_pair": market.get("trading_pair", ""),
            "cfg_pool_address": config.get("pool_address", ""),
            "cfg_lower_price": _float(config.get("lower_price")),
            "cfg_upper_price": _float(config.get("upper_price")),
            "cfg_base_amount": _float(config.get("base_amount")),
            "cfg_quote_amount": _float(config.get("quote_amount")),
            "cfg_side": config.get("side", ""),
            "ci_state": custom_info.get("state", ""),
            "ci_current_price": _float(custom_info.get("current_price")),
            "ci_lower_price": _float(custom_info.get("lower_price")),
            "ci_upper_price": _float(custom_info.get("upper_price")),
            "ci_base_amount": _float(custom_info.get("base_amount")),
            "ci_quote_amount": _float(custom_info.get("quote_amount")),
            "ci_base_fee": _float(custom_info.get("base_fee")),
            "ci_quote_fee": _float(custom_info.get("quote_fee")),
            "ci_fees_earned_quote": _float(custom_info.get("fees_earned_quote")),
            "ci_initial_base_amount": _float(custom_info.get("initial_base_amount")),
            "ci_initial_quote_amount": _float(custom_info.get("initial_quote_amount")),
            "ci_total_value_quote": _float(custom_info.get("total_value_quote")),
            "ci_unrealized_pnl_quote": _float(custom_info.get("unrealized_pnl_quote")),
            "ci_position_rent": _float(custom_info.get("position_rent")),
            "ci_position_rent_refunded": _float(custom_info.get("position_rent_refunded")),
            "ci_out_of_range_seconds": _int(custom_info.get("out_of_range_seconds")),
            "ci_max_retries_reached": custom_info.get("max_retries_reached", False),
        })

    return result


def load_csv(csv_path: str) -> list[dict]:
    """Load executor data from CSV file."""
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            # Coerce numeric fields
            for key in row:
                if key.startswith(("net_pnl", "cum_fees", "filled_amount", "cfg_lower",
                                   "cfg_upper", "cfg_base", "cfg_quote", "ci_")):
                    row[key] = _float(row[key])
                if key in ("is_active", "is_trading", "cfg_side"):
                    row[key] = _int(row[key])
            rows.append(row)
    # Ensure chronological order
    rows.sort(key=lambda r: r.get("created_at", ""))
    return rows


# ---------------------------------------------------------------------------
# Transform rows -> chart-ready JSON
# ---------------------------------------------------------------------------

def rows_to_chart_data(rows: list[dict]) -> list[dict]:
    """Convert executor rows into the compact JSON the dashboard expects."""
    cum_pnl = 0.0
    cum_fees = 0.0
    records = []

    for idx, r in enumerate(rows):
        pnl = _float(r.get("net_pnl_quote"))
        fees = _float(r.get("ci_fees_earned_quote"))
        cum_pnl += pnl
        cum_fees += fees

        ts = r.get("created_at", "")
        close_ts = r.get("close_timestamp", "")
        dur = _duration_seconds(ts, close_ts)

        records.append({
            # Core identifiers
            "idx": idx,
            "id": r.get("id", ""),
            "ts": ts.replace(" ", "T"),
            "close_ts": close_ts.replace(" ", "T"),
            "status": r.get("status", ""),
            "close_type": r.get("close_type", ""),

            # PnL metrics
            "pnl": round(pnl, 6),
            "pnl_pct": round(_float(r.get("net_pnl_pct")), 6),
            "cum_pnl": round(cum_pnl, 6),
            "fees": round(fees, 6),
            "cum_fees": round(cum_fees, 6),
            "cum_fees_quote": round(_float(r.get("cum_fees_quote")), 6),

            # Config fields
            "cfg_connector": r.get("cfg_connector", ""),
            "cfg_trading_pair": r.get("cfg_trading_pair", ""),
            "cfg_pool_address": r.get("cfg_pool_address", ""),
            "cfg_lower": round(_float(r.get("cfg_lower_price")), 6),
            "cfg_upper": round(_float(r.get("cfg_upper_price")), 6),
            "cfg_base_amount": round(_float(r.get("cfg_base_amount")), 6),
            "cfg_quote_amount": round(_float(r.get("cfg_quote_amount")), 6),
            "side": _int(r.get("cfg_side")),

            # Custom info - current state
            "ci_state": r.get("ci_state", ""),
            "price": round(_float(r.get("ci_current_price")), 6),
            "lower": round(_float(r.get("ci_lower_price")), 6),
            "upper": round(_float(r.get("ci_upper_price")), 6),

            # Custom info - amounts
            "ci_base_amount": round(_float(r.get("ci_base_amount")), 6),
            "ci_quote_amount": round(_float(r.get("ci_quote_amount")), 6),
            "ci_initial_base_amount": round(_float(r.get("ci_initial_base_amount")), 6),
            "ci_initial_quote_amount": round(_float(r.get("ci_initial_quote_amount")), 6),

            # Custom info - fees & value
            "ci_base_fee": round(_float(r.get("ci_base_fee")), 6),
            "ci_quote_fee": round(_float(r.get("ci_quote_fee")), 6),
            "ci_fees_earned_quote": round(_float(r.get("ci_fees_earned_quote")), 6),
            "ci_total_value_quote": round(_float(r.get("ci_total_value_quote")), 6),
            "ci_unrealized_pnl_quote": round(_float(r.get("ci_unrealized_pnl_quote")), 6),

            # Custom info - rent & timing
            "rent": round(_float(r.get("ci_position_rent")), 6),
            "ci_position_rent_refunded": round(_float(r.get("ci_position_rent_refunded")), 6),
            "oor": _int(r.get("ci_out_of_range_seconds")),
            "ci_max_retries_reached": r.get("ci_max_retries_reached", False),

            # Computed
            "filled": round(_float(r.get("filled_amount_quote")), 2),
            "dur": dur,
        })

    return records


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(chart_data: list[dict], meta: dict) -> str:
    """Build a self-contained HTML file with the dashboard."""
    data_json = json.dumps(chart_data)
    meta_json = json.dumps(meta)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>LP Dashboard — {meta.get("controller_id", "")}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0f1019; color: #e8eaed; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace; }}
  #root {{ min-height: 100vh; }}
</style>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prop-types/15.8.1/prop-types.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/recharts/2.12.7/Recharts.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.9/babel.min.js"></script>
</head>
<body>
<div id="root"></div>
<script>
  window.__LP_DATA__ = {data_json};
  window.__LP_META__ = {meta_json};
</script>
<script type="text/babel">
{DASHBOARD_JSX}
</script>
</body>
</html>"""


# The dashboard component — written as a single JSX blob that gets transpiled
# by Babel standalone in the browser. Zero build step required.
DASHBOARD_JSX = r"""
const {
  LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
  ScatterChart, Scatter, ComposedChart,
} = Recharts;

const DATA = window.__LP_DATA__;
const META = window.__LP_META__;

const fmt = (n, d = 4) => n?.toFixed(d) ?? "—";
const fmtTime = (iso) => {
  if (!iso) return "";
  const parts = iso.split("T");
  if (parts.length < 2) return iso;
  return parts[1].substring(0, 5);
};
const fmtDateTime = (iso) => iso ? iso.replace("T", " ") : "—";
const fmtDuration = (s) => {
  if (!s) return "0s";
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`;
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
};

function StatCard({ label, value, sub, accent }) {
  return React.createElement("div", {
    style: {
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 10, padding: "14px 18px", minWidth: 0,
    }
  },
    React.createElement("div", {
      style: { fontSize: 11, color: "#8b8fa3", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 6 }
    }, label),
    React.createElement("div", {
      style: { fontSize: 22, fontWeight: 600, color: accent || "#e8eaed" }
    }, value),
    sub && React.createElement("div", { style: { fontSize: 11, color: "#6b7084", marginTop: 4 } }, sub)
  );
}

function CustomTooltip({ active, payload, labelKey }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return React.createElement("div", {
    style: {
      background: "#1a1c2e", border: "1px solid rgba(255,255,255,0.1)",
      borderRadius: 8, padding: "10px 14px", fontSize: 11, color: "#c8cad4", lineHeight: 1.7,
    }
  },
    labelKey && d?.[labelKey] && React.createElement("div", { style: { color: "#8b8fa3" } }, fmtTime(d[labelKey])),
    ...payload.map((p, i) =>
      React.createElement("div", { key: i, style: { color: p.color || "#e8eaed" } },
        p.name, ": ", React.createElement("span", { style: { fontWeight: 600 } },
          typeof p.value === "number" ? fmt(p.value, 6) : p.value
        )
      )
    )
  );
}

function SectionTitle({ children }) {
  return React.createElement("h3", {
    style: {
      fontSize: 13, fontWeight: 600, color: "#8b8fa3", textTransform: "uppercase",
      letterSpacing: "0.08em", margin: "32px 0 14px",
    }
  }, children);
}

function ChartWrap({ children }) {
  return React.createElement("div", {
    style: {
      background: "rgba(255,255,255,0.02)", borderRadius: 10,
      border: "1px solid rgba(255,255,255,0.05)", padding: "16px 8px 8px",
    }
  }, children);
}

// Detail row component for executor detail panel
function DetailRow({ label, value, color }) {
  const e = React.createElement;
  return e("div", { style: { display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" } },
    e("span", { style: { color: "#6b7084", fontSize: 11 } }, label),
    e("span", { style: { color: color || "#e8eaed", fontSize: 11, fontWeight: 500, fontFamily: "monospace" } }, value)
  );
}

// Executor detail panel
function ExecutorDetail({ executor, onClose }) {
  const e = React.createElement;
  if (!executor) return null;

  const d = executor;
  const pnlColor = d.pnl >= 0 ? "#4ecdc4" : "#e85d75";
  const sideLabel = d.side === 1 ? "Quote (Buy)" : d.side === 2 ? "Base (Sell)" : "Unknown";

  return e("div", {
    style: {
      position: "fixed", top: 0, right: 0, width: 420, height: "100vh",
      background: "#12141f", borderLeft: "1px solid rgba(255,255,255,0.08)",
      overflowY: "auto", zIndex: 1000, boxShadow: "-4px 0 20px rgba(0,0,0,0.3)",
    }
  },
    // Header
    e("div", { style: { padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, background: "#12141f", zIndex: 1 } },
      e("div", null,
        e("div", { style: { fontSize: 14, fontWeight: 600, color: "#e8eaed" } }, `Executor #${d.idx + 1}`),
        e("div", { style: { fontSize: 10, color: "#555870", marginTop: 2, fontFamily: "monospace" } }, d.id.substring(0, 20) + "...")
      ),
      e("button", {
        onClick: onClose,
        style: { background: "none", border: "none", color: "#6b7084", fontSize: 20, cursor: "pointer", padding: "4px 8px" }
      }, "×")
    ),

    // Content
    e("div", { style: { padding: "16px 20px" } },
      // Status badges
      e("div", { style: { display: "flex", gap: 8, marginBottom: 16 } },
        e("span", { style: { fontSize: 10, padding: "3px 10px", borderRadius: 12, background: "rgba(78,205,196,0.1)", color: "#4ecdc4" } }, d.status),
        d.close_type && e("span", { style: { fontSize: 10, padding: "3px 10px", borderRadius: 12, background: "rgba(240,198,68,0.1)", color: "#f0c644" } }, d.close_type),
        e("span", { style: { fontSize: 10, padding: "3px 10px", borderRadius: 12, background: d.side === 1 ? "rgba(240,198,68,0.1)" : "rgba(78,205,196,0.1)", color: d.side === 1 ? "#f0c644" : "#4ecdc4" } }, `Side ${d.side} (${sideLabel})`)
      ),

      // PnL highlight
      e("div", { style: { background: "rgba(255,255,255,0.02)", borderRadius: 10, padding: "16px", marginBottom: 16, textAlign: "center" } },
        e("div", { style: { fontSize: 11, color: "#6b7084", marginBottom: 4 } }, "Net PnL"),
        e("div", { style: { fontSize: 28, fontWeight: 700, color: pnlColor } }, `$${fmt(d.pnl, 6)}`),
        e("div", { style: { fontSize: 12, color: pnlColor, marginTop: 4 } }, `${fmt(d.pnl_pct, 4)}%`)
      ),

      // Timing section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 16 } }, "TIMING"),
      e(DetailRow, { label: "Created", value: fmtDateTime(d.ts) }),
      e(DetailRow, { label: "Closed", value: fmtDateTime(d.close_ts) }),
      e(DetailRow, { label: "Duration", value: fmtDuration(d.dur) }),
      e(DetailRow, { label: "Out of Range", value: fmtDuration(d.oor), color: d.oor > 0 ? "#f0c644" : "#4ecdc4" }),

      // Config section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "CONFIG"),
      e(DetailRow, { label: "Connector", value: d.cfg_connector }),
      e(DetailRow, { label: "Trading Pair", value: d.cfg_trading_pair }),
      e(DetailRow, { label: "Config Lower", value: fmt(d.cfg_lower, 6) }),
      e(DetailRow, { label: "Config Upper", value: fmt(d.cfg_upper, 6) }),
      e(DetailRow, { label: "Config Base Amount", value: fmt(d.cfg_base_amount, 6) }),
      e(DetailRow, { label: "Config Quote Amount", value: fmt(d.cfg_quote_amount, 6) }),

      // Position state section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "POSITION STATE"),
      e(DetailRow, { label: "State", value: d.ci_state || "—" }),
      e(DetailRow, { label: "Current Price", value: fmt(d.price, 6) }),
      e(DetailRow, { label: "Lower Price", value: fmt(d.lower, 6) }),
      e(DetailRow, { label: "Upper Price", value: fmt(d.upper, 6) }),

      // Amounts section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "AMOUNTS"),
      e(DetailRow, { label: "Initial Base", value: fmt(d.ci_initial_base_amount, 6) }),
      e(DetailRow, { label: "Initial Quote", value: fmt(d.ci_initial_quote_amount, 6) }),
      e(DetailRow, { label: "Current Base", value: fmt(d.ci_base_amount, 6) }),
      e(DetailRow, { label: "Current Quote", value: fmt(d.ci_quote_amount, 6) }),
      e(DetailRow, { label: "Filled (Quote)", value: `$${fmt(d.filled, 2)}` }),

      // Fees & value section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "FEES & VALUE"),
      e(DetailRow, { label: "Base Fee", value: fmt(d.ci_base_fee, 6) }),
      e(DetailRow, { label: "Quote Fee", value: fmt(d.ci_quote_fee, 6) }),
      e(DetailRow, { label: "Fees Earned (Quote)", value: `$${fmt(d.ci_fees_earned_quote, 6)}`, color: "#7c6df0" }),
      e(DetailRow, { label: "Total Value (Quote)", value: `$${fmt(d.ci_total_value_quote, 6)}` }),
      e(DetailRow, { label: "Unrealized PnL", value: `$${fmt(d.ci_unrealized_pnl_quote, 6)}`, color: d.ci_unrealized_pnl_quote >= 0 ? "#4ecdc4" : "#e85d75" }),

      // Rent section
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "RENT"),
      e(DetailRow, { label: "Position Rent", value: `$${fmt(d.rent, 6)}`, color: "#e85d75" }),
      e(DetailRow, { label: "Rent Refunded", value: `$${fmt(d.ci_position_rent_refunded, 6)}`, color: "#4ecdc4" }),

      // Cumulative at close
      e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8, marginTop: 20 } }, "CUMULATIVE AT CLOSE"),
      e(DetailRow, { label: "Cumulative PnL", value: `$${fmt(d.cum_pnl, 6)}`, color: d.cum_pnl >= 0 ? "#4ecdc4" : "#e85d75" }),
      e(DetailRow, { label: "Cumulative Fees", value: `$${fmt(d.cum_fees, 6)}`, color: "#7c6df0" }),

      // Flags
      d.ci_max_retries_reached && e("div", { style: { marginTop: 16, padding: "8px 12px", background: "rgba(232,93,117,0.1)", borderRadius: 6, fontSize: 11, color: "#e85d75" } }, "⚠ Max retries reached"),

      // Pool address (if present)
      d.cfg_pool_address && e("div", { style: { marginTop: 20 } },
        e("div", { style: { fontSize: 11, fontWeight: 600, color: "#8b8fa3", marginBottom: 8 } }, "POOL ADDRESS"),
        e("div", { style: { fontSize: 10, color: "#555870", fontFamily: "monospace", wordBreak: "break-all" } }, d.cfg_pool_address)
      ),
    )
  );
}

// Executor table component
function ExecutorTable({ data, selectedIdx, onSelect }) {
  const e = React.createElement;
  const [sortKey, setSortKey] = React.useState("idx");
  const [sortDir, setSortDir] = React.useState(1);
  const [filterSide, setFilterSide] = React.useState("all");
  const [filterPnl, setFilterPnl] = React.useState("all");

  const filtered = React.useMemo(() => {
    let result = [...data];
    if (filterSide !== "all") result = result.filter(d => d.side === Number(filterSide));
    if (filterPnl === "positive") result = result.filter(d => d.pnl > 0);
    if (filterPnl === "negative") result = result.filter(d => d.pnl < 0);
    if (filterPnl === "zero") result = result.filter(d => d.pnl === 0);
    result.sort((a, b) => (a[sortKey] > b[sortKey] ? 1 : -1) * sortDir);
    return result;
  }, [data, filterSide, filterPnl, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(-sortDir);
    else { setSortKey(key); setSortDir(1); }
  };

  const thStyle = { padding: "8px 6px", textAlign: "left", fontSize: 10, color: "#6b7084", cursor: "pointer", userSelect: "none", borderBottom: "1px solid rgba(255,255,255,0.06)" };
  const tdStyle = { padding: "8px 6px", fontSize: 11, borderBottom: "1px solid rgba(255,255,255,0.03)" };

  const sortIcon = (key) => sortKey === key ? (sortDir === 1 ? " ↑" : " ↓") : "";

  const filterBtn = (value, label, currentFilter, setFilter) => e("button", {
    onClick: () => setFilter(value),
    style: {
      fontSize: 9, padding: "3px 8px", borderRadius: 10, cursor: "pointer", fontFamily: "inherit",
      border: `1px solid ${currentFilter === value ? "#4ecdc4" : "rgba(255,255,255,0.08)"}`,
      background: currentFilter === value ? "rgba(78,205,196,0.12)" : "transparent",
      color: currentFilter === value ? "#4ecdc4" : "#6b7084", marginRight: 4,
    }
  }, label);

  return e("div", null,
    // Filters
    e("div", { style: { display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap" } },
      e("div", { style: { display: "flex", alignItems: "center", gap: 4 } },
        e("span", { style: { fontSize: 10, color: "#555870", marginRight: 4 } }, "Side:"),
        filterBtn("all", "All", filterSide, setFilterSide),
        filterBtn("1", "Quote", filterSide, setFilterSide),
        filterBtn("2", "Base", filterSide, setFilterSide),
      ),
      e("div", { style: { display: "flex", alignItems: "center", gap: 4 } },
        e("span", { style: { fontSize: 10, color: "#555870", marginRight: 4 } }, "PnL:"),
        filterBtn("all", "All", filterPnl, setFilterPnl),
        filterBtn("positive", "Profit", filterPnl, setFilterPnl),
        filterBtn("negative", "Loss", filterPnl, setFilterPnl),
        filterBtn("zero", "Zero", filterPnl, setFilterPnl),
      ),
      e("span", { style: { fontSize: 10, color: "#555870", marginLeft: "auto" } }, `${filtered.length} executors`)
    ),

    // Table
    e("div", { style: { overflowX: "auto", background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.05)" } },
      e("table", { style: { width: "100%", borderCollapse: "collapse", minWidth: 700 } },
        e("thead", null,
          e("tr", null,
            e("th", { style: thStyle, onClick: () => handleSort("idx") }, "#" + sortIcon("idx")),
            e("th", { style: thStyle, onClick: () => handleSort("ts") }, "Created" + sortIcon("ts")),
            e("th", { style: thStyle, onClick: () => handleSort("dur") }, "Duration" + sortIcon("dur")),
            e("th", { style: thStyle, onClick: () => handleSort("side") }, "Side" + sortIcon("side")),
            e("th", { style: thStyle, onClick: () => handleSort("pnl") }, "PnL" + sortIcon("pnl")),
            e("th", { style: thStyle, onClick: () => handleSort("pnl_pct") }, "PnL %" + sortIcon("pnl_pct")),
            e("th", { style: thStyle, onClick: () => handleSort("fees") }, "Fees" + sortIcon("fees")),
            e("th", { style: thStyle, onClick: () => handleSort("filled") }, "Volume" + sortIcon("filled")),
            e("th", { style: thStyle, onClick: () => handleSort("oor") }, "OOR" + sortIcon("oor")),
            e("th", { style: thStyle }, "Status"),
          )
        ),
        e("tbody", null,
          ...filtered.map(d => e("tr", {
            key: d.idx,
            onClick: () => onSelect(d.idx),
            style: {
              cursor: "pointer",
              background: selectedIdx === d.idx ? "rgba(78,205,196,0.08)" : "transparent",
              transition: "background 0.15s",
            },
            onMouseEnter: (ev) => ev.currentTarget.style.background = selectedIdx === d.idx ? "rgba(78,205,196,0.12)" : "rgba(255,255,255,0.02)",
            onMouseLeave: (ev) => ev.currentTarget.style.background = selectedIdx === d.idx ? "rgba(78,205,196,0.08)" : "transparent",
          },
            e("td", { style: { ...tdStyle, color: "#8b8fa3" } }, d.idx + 1),
            e("td", { style: { ...tdStyle, fontFamily: "monospace", fontSize: 10 } }, fmtDateTime(d.ts)),
            e("td", { style: tdStyle }, fmtDuration(d.dur)),
            e("td", { style: { ...tdStyle, color: d.side === 1 ? "#f0c644" : "#4ecdc4" } }, d.side === 1 ? "Quote" : "Base"),
            e("td", { style: { ...tdStyle, color: d.pnl >= 0 ? "#4ecdc4" : "#e85d75", fontWeight: 500 } }, `$${fmt(d.pnl, 4)}`),
            e("td", { style: { ...tdStyle, color: d.pnl_pct >= 0 ? "#4ecdc4" : "#e85d75" } }, `${fmt(d.pnl_pct, 3)}%`),
            e("td", { style: { ...tdStyle, color: "#7c6df0" } }, `$${fmt(d.fees, 4)}`),
            e("td", { style: tdStyle }, `$${fmt(d.filled, 0)}`),
            e("td", { style: { ...tdStyle, color: d.oor > 0 ? "#f0c644" : "#555870" } }, d.oor > 0 ? fmtDuration(d.oor) : "—"),
            e("td", { style: tdStyle },
              e("span", { style: { fontSize: 9, padding: "2px 6px", borderRadius: 8, background: "rgba(78,205,196,0.1)", color: "#4ecdc4" } }, d.close_type || d.status)
            ),
          ))
        )
      )
    )
  );
}

// Custom chart component for position ranges with price line
function PositionRangeChart({ data, onSelectPosition, tradingPair }) {
  const e = React.createElement;
  const containerRef = React.useRef(null);
  const [dimensions, setDimensions] = React.useState({ width: 0, height: 400 });

  React.useEffect(() => {
    if (containerRef.current) {
      const resizeObserver = new ResizeObserver(entries => {
        for (let entry of entries) {
          setDimensions({ width: entry.contentRect.width, height: 400 });
        }
      });
      resizeObserver.observe(containerRef.current);
      return () => resizeObserver.disconnect();
    }
  }, []);

  const { width, height } = dimensions;
  const margin = { top: 20, right: 60, bottom: 40, left: 70 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Compute time and price domains
  const { minTime, maxTime, minPrice, maxPrice, pricePoints } = React.useMemo(() => {
    if (!data.length) return { minTime: 0, maxTime: 1, minPrice: 0, maxPrice: 1, pricePoints: [] };

    let minT = Infinity, maxT = -Infinity;
    let minP = Infinity, maxP = -Infinity;
    const points = [];

    data.forEach(d => {
      const addTs = new Date(d.ts).getTime();
      const removeTs = d.close_ts ? new Date(d.close_ts).getTime() : Date.now();

      minT = Math.min(minT, addTs);
      maxT = Math.max(maxT, removeTs);
      minP = Math.min(minP, d.lower, d.price);
      maxP = Math.max(maxP, d.upper, d.price);

      // Add price points for the line
      points.push({ time: addTs, price: d.price });
      if (d.close_ts) {
        points.push({ time: removeTs, price: d.price });
      }
    });

    // Sort price points by time
    points.sort((a, b) => a.time - b.time);

    // Add padding to price range
    const priceRange = maxP - minP;
    minP -= priceRange * 0.05;
    maxP += priceRange * 0.05;

    return { minTime: minT, maxTime: maxT, minPrice: minP, maxPrice: maxP, pricePoints: points };
  }, [data]);

  // Scale functions
  const xScale = (t) => margin.left + ((t - minTime) / (maxTime - minTime)) * innerWidth;
  const yScale = (p) => margin.top + innerHeight - ((p - minPrice) / (maxPrice - minPrice)) * innerHeight;

  // Generate Y axis ticks
  const yTicks = React.useMemo(() => {
    const ticks = [];
    const range = maxPrice - minPrice;
    const step = range / 5;
    for (let i = 0; i <= 5; i++) {
      ticks.push(minPrice + step * i);
    }
    return ticks;
  }, [minPrice, maxPrice]);

  // Generate X axis ticks
  const xTicks = React.useMemo(() => {
    const ticks = [];
    const range = maxTime - minTime;
    const step = range / 6;
    for (let i = 0; i <= 6; i++) {
      ticks.push(minTime + step * i);
    }
    return ticks;
  }, [minTime, maxTime]);

  // Build price line path
  const pricePath = React.useMemo(() => {
    if (pricePoints.length < 2) return "";
    return pricePoints.map((p, i) =>
      `${i === 0 ? "M" : "L"} ${xScale(p.time)} ${yScale(p.price)}`
    ).join(" ");
  }, [pricePoints, xScale, yScale]);

  if (width === 0) {
    return e("div", { ref: containerRef, style: { width: "100%", height: 400 } });
  }

  // Map side: 1 = Quote (Buy), 2 = Base (Sell)
  const getSideLabel = (side) => side === 1 ? "BUY" : "SELL";

  return e("div", { ref: containerRef, style: { width: "100%", height: 400, background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.05)" } },
    e("svg", { width, height, style: { display: "block" } },
      // Grid lines
      ...yTicks.map((tick, i) => e("line", {
        key: `y-${i}`,
        x1: margin.left,
        y1: yScale(tick),
        x2: width - margin.right,
        y2: yScale(tick),
        stroke: "rgba(255,255,255,0.04)",
        strokeDasharray: "3,3"
      })),
      ...xTicks.map((tick, i) => e("line", {
        key: `x-${i}`,
        x1: xScale(tick),
        y1: margin.top,
        x2: xScale(tick),
        y2: height - margin.bottom,
        stroke: "rgba(255,255,255,0.04)",
        strokeDasharray: "3,3"
      })),

      // Position range bars
      ...data.map((d, i) => {
        const addTs = new Date(d.ts).getTime();
        const removeTs = d.close_ts ? new Date(d.close_ts).getTime() : Date.now();
        const x1 = xScale(addTs);
        const x2 = xScale(removeTs);
        const y1 = yScale(d.upper);
        const y2 = yScale(d.lower);
        // Side 1 = Quote (Buy) = green, Side 2 = Base (Sell) = red
        const fillColor = d.side === 1 ? "rgba(78,205,196,0.25)" : "rgba(232,93,117,0.25)";
        const strokeColor = d.side === 1 ? "#4ecdc4" : "#e85d75";

        return e("rect", {
          key: `pos-${i}`,
          x: x1,
          y: y1,
          width: Math.max(x2 - x1, 2),
          height: Math.max(y2 - y1, 1),
          fill: fillColor,
          stroke: strokeColor,
          strokeWidth: 1,
          strokeOpacity: 0.5,
          cursor: "pointer",
          onClick: () => onSelectPosition(d.idx),
        });
      }),

      // Price line
      e("path", {
        d: pricePath,
        fill: "none",
        stroke: "#f0c644",
        strokeWidth: 2,
        strokeLinejoin: "round",
        strokeLinecap: "round",
      }),

      // Price dots at position open/close
      ...pricePoints.map((p, i) => e("circle", {
        key: `dot-${i}`,
        cx: xScale(p.time),
        cy: yScale(p.price),
        r: 3,
        fill: "#f0c644",
      })),

      // Y axis
      e("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, stroke: "rgba(255,255,255,0.1)" }),
      ...yTicks.map((tick, i) => e("text", {
        key: `yl-${i}`,
        x: margin.left - 8,
        y: yScale(tick),
        fill: "#555870",
        fontSize: 10,
        textAnchor: "end",
        dominantBaseline: "middle",
      }, tick.toFixed(tick > 100 ? 0 : tick > 1 ? 2 : 4))),

      // X axis
      e("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, stroke: "rgba(255,255,255,0.1)" }),
      ...xTicks.map((tick, i) => e("text", {
        key: `xl-${i}`,
        x: xScale(tick),
        y: height - margin.bottom + 16,
        fill: "#555870",
        fontSize: 10,
        textAnchor: "middle",
      }, fmtTime(tick))),

      // Y axis label
      e("text", {
        x: 14,
        y: height / 2,
        fill: "#6b7084",
        fontSize: 11,
        textAnchor: "middle",
        transform: `rotate(-90, 14, ${height / 2})`,
      }, `${tradingPair} Price`),

      // Legend
      e("line", { x1: width - margin.right - 200, y1: margin.top + 6, x2: width - margin.right - 180, y2: margin.top + 6, stroke: "#f0c644", strokeWidth: 2 }),
      e("text", { x: width - margin.right - 175, y: margin.top + 9, fill: "#8b8fa3", fontSize: 10 }, `${tradingPair} Price`),
      e("rect", { x: width - margin.right - 95, y: margin.top, width: 12, height: 12, fill: "rgba(78,205,196,0.25)", stroke: "#4ecdc4", strokeWidth: 1 }),
      e("text", { x: width - margin.right - 78, y: margin.top + 9, fill: "#8b8fa3", fontSize: 10 }, "Buy"),
      e("rect", { x: width - margin.right - 40, y: margin.top, width: 12, height: 12, fill: "rgba(232,93,117,0.25)", stroke: "#e85d75", strokeWidth: 1 }),
      e("text", { x: width - margin.right - 23, y: margin.top + 9, fill: "#8b8fa3", fontSize: 10 }, "Sell"),
    )
  );
}

function App() {
  const [sideFilter, setSideFilter] = React.useState("all");
  const [selectedIdx, setSelectedIdx] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState("overview");

  const filtered = React.useMemo(() => {
    if (sideFilter === "all") return DATA;
    return DATA.filter(d => d.side === Number(sideFilter));
  }, [sideFilter]);

  const stats = React.useMemo(() => {
    const last = DATA[DATA.length - 1];
    const totalPnl = last.cum_pnl;
    const totalFees = last.cum_fees;
    const totalFilled = DATA.reduce((s, d) => s + d.filled, 0);
    const profitable = DATA.filter(d => d.pnl > 0).length;
    const losing = DATA.filter(d => d.pnl < 0).length;
    const zero = DATA.filter(d => d.pnl === 0).length;
    const totalRent = DATA.reduce((s, d) => s + d.rent, 0);
    const maxPnl = Math.max(...DATA.map(d => d.pnl));
    const minPnl = Math.min(...DATA.map(d => d.pnl));
    return { totalPnl, totalFees, totalFilled, profitable, losing, zero, totalRent, maxPnl, minPnl };
  }, []);

  const priceData = React.useMemo(() =>
    DATA.map(d => ({ ...d, time: fmtTime(d.ts) })), []);

  const pnlBars = React.useMemo(() =>
    filtered.filter(d => d.pnl !== 0).map((d, i) => ({ ...d, barIdx: i, time: fmtTime(d.ts) })),
  [filtered]);

  const pair = META.trading_pair || "?";
  const connector = META.connector || "?";

  const selectedExecutor = selectedIdx !== null ? DATA[selectedIdx] : null;

  // ---- render helpers ----
  const e = React.createElement;

  const sideBtn = (v, label) => e("button", {
    key: v, onClick: () => setSideFilter(v),
    style: {
      fontSize: 10, padding: "4px 12px", borderRadius: 16, cursor: "pointer", fontFamily: "inherit",
      border: `1px solid ${sideFilter === v ? "#4ecdc4" : "rgba(255,255,255,0.08)"}`,
      background: sideFilter === v ? "rgba(78,205,196,0.12)" : "transparent",
      color: sideFilter === v ? "#4ecdc4" : "#6b7084",
    }
  }, label);

  const tabBtn = (v, label) => e("button", {
    key: v, onClick: () => setActiveTab(v),
    style: {
      fontSize: 11, padding: "8px 20px", cursor: "pointer", fontFamily: "inherit",
      border: "none", borderBottom: activeTab === v ? "2px solid #4ecdc4" : "2px solid transparent",
      background: "transparent",
      color: activeTab === v ? "#e8eaed" : "#6b7084",
      fontWeight: activeTab === v ? 600 : 400,
    }
  }, label);

  // PnL % histogram bins
  const histBins = React.useMemo(() => {
    const bins = [
      { range: "< 0", count: 0 }, { range: "0-0.1", count: 0 },
      { range: "0.1-0.2", count: 0 }, { range: "0.2-0.3", count: 0 },
      { range: "0.3-0.5", count: 0 }, { range: "0.5-0.7", count: 0 },
      { range: "> 0.7", count: 0 },
    ];
    DATA.filter(d => d.pnl_pct !== 0).forEach(d => {
      const p = d.pnl_pct;
      if (p < 0) bins[0].count++;
      else if (p < 0.1) bins[1].count++;
      else if (p < 0.2) bins[2].count++;
      else if (p < 0.3) bins[3].count++;
      else if (p < 0.5) bins[4].count++;
      else if (p < 0.7) bins[5].count++;
      else bins[6].count++;
    });
    return bins;
  }, []);

  const firstTs = DATA[0]?.ts?.replace("T", " ").substring(0, 16) || "";
  const lastClose = DATA[DATA.length - 1]?.close_ts?.replace("T", " ").substring(0, 16) || "";

  return e("div", { style: { paddingRight: selectedExecutor ? 420 : 0, transition: "padding-right 0.2s" } },
    e("div", { style: { padding: "28px 24px", maxWidth: 1100, margin: "0 auto" } },
      // Header
      e("div", { style: { display: "flex", alignItems: "baseline", gap: 16, marginBottom: 6 } },
        e("h1", { style: { fontSize: 20, fontWeight: 700, margin: 0 } }, META.controller_id || "LP Dashboard"),
        e("span", { style: { fontSize: 12, color: "#4ecdc4", background: "rgba(78,205,196,0.1)", padding: "3px 10px", borderRadius: 20, fontWeight: 500 } }, pair),
        e("span", { style: { fontSize: 11, color: "#6b7084" } }, connector),
      ),
      e("div", { style: { fontSize: 11, color: "#555870", marginBottom: 16 } },
        `${firstTs} → ${lastClose} UTC · ${DATA.length} executors`
      ),

      // Tab navigation
      e("div", { style: { display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.06)", marginBottom: 24 } },
        tabBtn("overview", "Overview"),
        tabBtn("executors", "Executors"),
        tabBtn("chart", "Range Chart"),
      ),

      // Overview tab
      activeTab === "overview" && e("div", null,
        // KPI cards
        e("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: 10, marginBottom: 8 } },
          e(StatCard, { label: "Total PnL", value: `$${fmt(stats.totalPnl, 4)}`, sub: `${fmt(stats.totalPnl / stats.totalFilled * 100, 2)}% of volume`, accent: "#4ecdc4" }),
          e(StatCard, { label: "Fees Earned", value: `$${fmt(stats.totalFees, 4)}`, sub: `${fmt(stats.totalFees / stats.totalFilled * 10000, 1)} bps`, accent: "#7c6df0" }),
          e(StatCard, { label: "Volume", value: `$${fmt(stats.totalFilled, 0)}`, sub: `~$${fmt(stats.totalFilled / DATA.length, 1)} avg` }),
          e(StatCard, { label: "Win / Loss / Zero", value: `${stats.profitable}/${stats.losing}/${stats.zero}`, sub: `${fmt(stats.profitable / Math.max(stats.profitable + stats.losing, 1) * 100, 0)}% win rate`, accent: "#f0c644" }),
          e(StatCard, { label: "Best / Worst", value: `${fmt(stats.maxPnl, 4)}`, sub: `worst: ${fmt(stats.minPnl, 4)}`, accent: "#4ecdc4" }),
          e(StatCard, { label: "Rent Cost", value: `$${fmt(stats.totalRent, 3)}`, sub: stats.totalPnl > 0 ? `${fmt(stats.totalRent / stats.totalPnl * 100, 1)}% of PnL` : "", accent: "#e85d75" }),
        ),

        // Cumulative PnL
        e(SectionTitle, null, "Cumulative PnL & Fees"),
        e(ChartWrap, null,
          e(ResponsiveContainer, { width: "100%", height: 220 },
            e(AreaChart, { data: priceData, margin: { top: 5, right: 20, bottom: 5, left: 5 } },
              e("defs", null,
                e("linearGradient", { id: "pnlGrad", x1: 0, y1: 0, x2: 0, y2: 1 },
                  e("stop", { offset: "5%", stopColor: "#4ecdc4", stopOpacity: 0.3 }),
                  e("stop", { offset: "95%", stopColor: "#4ecdc4", stopOpacity: 0 }),
                ),
                e("linearGradient", { id: "feeGrad", x1: 0, y1: 0, x2: 0, y2: 1 },
                  e("stop", { offset: "5%", stopColor: "#7c6df0", stopOpacity: 0.25 }),
                  e("stop", { offset: "95%", stopColor: "#7c6df0", stopOpacity: 0 }),
                ),
              ),
              e(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" }),
              e(XAxis, { dataKey: "time", tick: { fontSize: 10, fill: "#555870" }, interval: "preserveStartEnd" }),
              e(YAxis, { tick: { fontSize: 10, fill: "#555870" }, width: 50 }),
              e(Tooltip, { content: e(CustomTooltip, { labelKey: "ts" }) }),
              e(Area, { type: "monotone", dataKey: "cum_pnl", stroke: "#4ecdc4", fill: "url(#pnlGrad)", strokeWidth: 2, name: "Cum PnL", dot: false }),
              e(Area, { type: "monotone", dataKey: "cum_fees", stroke: "#7c6df0", fill: "url(#feeGrad)", strokeWidth: 1.5, name: "Cum Fees", dot: false, strokeDasharray: "4 2" }),
            )
          )
        ),

        // Price chart
        e(SectionTitle, null, "Price & LP Range"),
        e(ChartWrap, null,
          e(ResponsiveContainer, { width: "100%", height: 220 },
            e(ComposedChart, { data: priceData, margin: { top: 5, right: 20, bottom: 5, left: 5 } },
              e(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" }),
              e(XAxis, { dataKey: "time", tick: { fontSize: 10, fill: "#555870" }, interval: "preserveStartEnd" }),
              e(YAxis, { domain: ["dataMin - 0.1", "dataMax + 0.1"], tick: { fontSize: 10, fill: "#555870" }, width: 50 }),
              e(Tooltip, { content: e(CustomTooltip, { labelKey: "ts" }) }),
              e(Area, { type: "stepAfter", dataKey: "upper", stroke: "none", fill: "rgba(78,205,196,0.08)", name: "Upper" }),
              e(Area, { type: "stepAfter", dataKey: "lower", stroke: "none", fill: "#0f1019", name: "Lower" }),
              e(Line, { type: "monotone", dataKey: "price", stroke: "#f0c644", strokeWidth: 1.5, dot: false, name: "Price" }),
              e(Line, { type: "stepAfter", dataKey: "upper", stroke: "rgba(78,205,196,0.3)", strokeWidth: 1, dot: false, name: "Range Upper", strokeDasharray: "3 3" }),
              e(Line, { type: "stepAfter", dataKey: "lower", stroke: "rgba(78,205,196,0.3)", strokeWidth: 1, dot: false, name: "Range Lower", strokeDasharray: "3 3" }),
            )
          )
        ),

        // Per-executor PnL
        e("div", { style: { display: "flex", alignItems: "center", gap: 16, marginTop: 32, marginBottom: 14 } },
          e(SectionTitle, null, "Per-Executor PnL"),
          e("div", { style: { display: "flex", gap: 6, marginLeft: "auto" } },
            sideBtn("all", "All"),
            sideBtn("1", "Side 1 (Quote)"),
            sideBtn("2", "Side 2 (Base)"),
          ),
        ),
        e(ChartWrap, null,
          e(ResponsiveContainer, { width: "100%", height: 200 },
            e(BarChart, { data: pnlBars, margin: { top: 5, right: 20, bottom: 5, left: 5 } },
              e(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" }),
              e(XAxis, { dataKey: "time", tick: { fontSize: 9, fill: "#555870" }, interval: "preserveStartEnd" }),
              e(YAxis, { tick: { fontSize: 10, fill: "#555870" }, width: 50 }),
              e(Tooltip, { content: e(CustomTooltip, { labelKey: "ts" }) }),
              e(ReferenceLine, { y: 0, stroke: "rgba(255,255,255,0.1)" }),
              e(Bar, { dataKey: "pnl", name: "PnL", radius: [2, 2, 0, 0], onClick: (data) => { if (data?.idx !== undefined) setSelectedIdx(data.idx); } },
                ...pnlBars.map((d, i) => e(Cell, { key: i, fill: d.pnl >= 0 ? "#4ecdc4" : "#e85d75", fillOpacity: 0.8, cursor: "pointer" }))
              ),
            )
          )
        ),

        // PnL % histogram
        e(SectionTitle, null, "PnL % Distribution (non-zero)"),
        e(ChartWrap, null,
          e(ResponsiveContainer, { width: "100%", height: 180 },
            e(BarChart, { data: histBins, margin: { top: 5, right: 20, bottom: 5, left: 5 } },
              e(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" }),
              e(XAxis, { dataKey: "range", tick: { fontSize: 10, fill: "#555870" } }),
              e(YAxis, { tick: { fontSize: 10, fill: "#555870" }, width: 30 }),
              e(Tooltip, { content: e(CustomTooltip, {}) }),
              e(Bar, { dataKey: "count", name: "Executors", radius: [3, 3, 0, 0] },
                ...histBins.map((d, i) => e(Cell, { key: i, fill: i === 0 ? "#e85d75" : "#7c6df0", fillOpacity: 0.75 }))
              ),
            )
          )
        ),

        // Duration vs PnL
        e(SectionTitle, null, "Duration vs PnL (non-zero)"),
        e(ChartWrap, null,
          e(ResponsiveContainer, { width: "100%", height: 200 },
            e(ScatterChart, { margin: { top: 5, right: 20, bottom: 5, left: 5 } },
              e(CartesianGrid, { strokeDasharray: "3 3", stroke: "rgba(255,255,255,0.04)" }),
              e(XAxis, { dataKey: "dur", name: "Duration (s)", tick: { fontSize: 10, fill: "#555870" }, type: "number" }),
              e(YAxis, { dataKey: "pnl", name: "PnL", tick: { fontSize: 10, fill: "#555870" }, width: 55 }),
              e(Tooltip, { content: e(CustomTooltip, {}) }),
              e(Scatter, { data: DATA.filter(d => d.pnl !== 0), fill: "#f0c644", fillOpacity: 0.7, onClick: (data) => { if (data?.idx !== undefined) setSelectedIdx(data.idx); }, cursor: "pointer" }),
            )
          )
        ),

        // Side breakdown
        e(SectionTitle, null, "Side Breakdown"),
        e("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 } },
          ...[1, 2].map(side => {
            const s = DATA.filter(d => d.side === side);
            const pnl = s.reduce((a, d) => a + d.pnl, 0);
            const prof = s.filter(d => d.pnl > 0).length;
            const fees = s.reduce((a, d) => a + d.fees, 0);
            const avgDur = s.length ? s.reduce((a, d) => a + d.dur, 0) / s.length : 0;
            return e("div", {
              key: side,
              style: { background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.05)", padding: "16px 18px" }
            },
              e("div", { style: { fontSize: 12, fontWeight: 600, color: side === 1 ? "#f0c644" : "#4ecdc4", marginBottom: 10 } },
                `Side ${side} — ${side === 1 ? "Quote (Buy)" : "Base (Sell)"}  (${s.length})`
              ),
              e("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 11, color: "#8b8fa3" } },
                e("div", null, "PnL", e("br"), e("span", { style: { color: pnl >= 0 ? "#4ecdc4" : "#e85d75", fontWeight: 600, fontSize: 14 } }, `$${fmt(pnl, 4)}`)),
                e("div", null, "Fees", e("br"), e("span", { style: { color: "#7c6df0", fontWeight: 600, fontSize: 14 } }, `$${fmt(fees, 4)}`)),
                e("div", null, "Profitable", e("br"), e("span", { style: { color: "#e8eaed", fontWeight: 600, fontSize: 14 } }, `${prof} / ${s.length}`)),
                e("div", null, "Avg Duration", e("br"), e("span", { style: { color: "#e8eaed", fontWeight: 600, fontSize: 14 } }, `${fmt(avgDur, 0)}s`)),
              ),
            );
          })
        ),
      ),

      // Executors tab
      activeTab === "executors" && e("div", null,
        e(SectionTitle, null, "All Executors"),
        e(ExecutorTable, { data: DATA, selectedIdx, onSelect: setSelectedIdx }),
      ),

      // Range Chart tab
      activeTab === "chart" && e("div", null,
        e(SectionTitle, null, "Position Ranges & Price"),
        e(PositionRangeChart, { data: DATA, onSelectPosition: setSelectedIdx, tradingPair: pair }),
      ),

      e("div", { style: { fontSize: 10, color: "#3a3d50", textAlign: "center", marginTop: 32, paddingBottom: 16 } },
        `${META.controller_id} · ${DATA.length} executors · ${connector}`
      ),
    ),

    // Detail panel
    selectedExecutor && e(ExecutorDetail, { executor: selectedExecutor, onClose: () => setSelectedIdx(null) }),
  );
}

ReactDOM.render(React.createElement(App), document.getElementById("root"));
"""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _float(v) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _int(v) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return 0


def _duration_seconds(start: str, end: str) -> int:
    """Compute duration in seconds between two datetime strings."""
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        s = datetime.strptime(start, fmt)
        e = datetime.strptime(end, fmt)
        return max(int((e - s).total_seconds()), 0)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Visualize Hummingbot LP executor data as an interactive HTML dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("controller_id", nargs="?", help="Controller ID to query from DB (e.g. lp_rebalancer_4)")
    parser.add_argument("--db", help="Path to SQLite database (default: most recent in data/)")
    parser.add_argument("--csv", help="Path to CSV file (skip DB, use exported CSV directly)")
    parser.add_argument("--output", "-o", help="Output HTML path (default: data/<controller_id>_dashboard.html)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open in browser")

    args = parser.parse_args()

    if not args.controller_id and not args.csv:
        parser.error("Provide a controller_id or --csv <path>")

    # Load data
    if args.csv:
        print(f"Loading CSV: {args.csv}")
        rows = load_csv(args.csv)
        controller_id = args.controller_id or Path(args.csv).stem
    else:
        db_path = args.db or find_latest_db()
        print(f"Using database: {db_path}")
        rows = query_executors(args.controller_id, db_path)
        controller_id = args.controller_id

    print(f"Loaded {len(rows)} executors")

    # Extract metadata from first row
    first = rows[0] if rows else {}
    meta = {
        "controller_id": controller_id,
        "trading_pair": first.get("cfg_trading_pair", ""),
        "connector": first.get("cfg_connector", ""),
    }

    # Transform and generate
    chart_data = rows_to_chart_data(rows)
    html = generate_html(chart_data, meta)

    # Write output
    if args.output:
        output_path = args.output
    else:
        os.makedirs("data", exist_ok=True)
        output_path = f"data/{controller_id}_dashboard.html"

    with open(output_path, "w") as f:
        f.write(html)

    print(f"Dashboard written to: {output_path}")

    if not args.no_open:
        abs_path = os.path.abspath(output_path)
        webbrowser.open(f"file://{abs_path}")
        print("Opened in browser")

    return 0


if __name__ == "__main__":
    exit(main())
