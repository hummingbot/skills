#!/usr/bin/env python3
"""
Export LP executor data from SQLite database to CSV.

Usage:
    python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py <controller_id> [--db <database_path>] [--output <output_path>]

Examples:
    python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4
    python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4 --db data/conf_v2_with_controllers_1.sqlite
    python controllers/generic/lp_rebalancer/scripts/export_lp_executors.py lp_rebalancer_4 --output exports/my_export.csv
"""

import argparse
import csv
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def find_latest_db(data_dir: str = "data") -> str:
    """Find the most recently modified .sqlite file in data directory."""
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    sqlite_files = list(data_path.glob("*.sqlite"))
    if not sqlite_files:
        raise FileNotFoundError(f"No .sqlite files found in {data_dir}")

    # Sort by modification time, most recent first
    sqlite_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return str(sqlite_files[0])


def export_executors(controller_id: str, db_path: str, output_path: str) -> int:
    """Export executors for a controller to CSV. Returns number of rows exported."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query all executors for the controller
    cursor.execute("""
        SELECT
            id,
            timestamp,
            type,
            close_type,
            close_timestamp,
            status,
            net_pnl_pct,
            net_pnl_quote,
            cum_fees_quote,
            filled_amount_quote,
            is_active,
            is_trading,
            controller_id,
            config,
            custom_info
        FROM Executors
        WHERE controller_id = ?
        ORDER BY timestamp DESC
    """, (controller_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"No executors found for controller_id: {controller_id}")
        return 0

    # Define status and close_type mappings
    status_map = {0: "NOT_STARTED", 1: "RUNNING", 2: "RUNNING", 3: "SHUTTING_DOWN", 4: "TERMINATED"}
    close_type_map = {None: "", 1: "TIME_LIMIT", 2: "STOP_LOSS", 3: "TAKE_PROFIT",
                      4: "POSITION_HOLD", 5: "EARLY_STOP", 6: "TRAILING_STOP",
                      7: "INSUFFICIENT_BALANCE", 8: "EXPIRED", 9: "FAILED"}

    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        header = [
            # Base columns
            "id", "created_at", "type", "status", "close_type", "close_timestamp",
            "net_pnl_pct", "net_pnl_quote", "cum_fees_quote", "filled_amount_quote",
            "is_active", "is_trading", "controller_id",
            # Config columns
            "cfg_connector", "cfg_trading_pair", "cfg_pool_address",
            "cfg_lower_price", "cfg_upper_price", "cfg_base_amount", "cfg_quote_amount",
            "cfg_side", "cfg_extra_params",
            # Custom info columns
            "ci_state", "ci_position_address", "ci_current_price",
            "ci_lower_price", "ci_upper_price",
            "ci_base_amount", "ci_quote_amount",
            "ci_base_fee", "ci_quote_fee", "ci_fees_earned_quote",
            "ci_initial_base_amount", "ci_initial_quote_amount",
            "ci_total_value_quote", "ci_unrealized_pnl_quote",
            "ci_position_rent", "ci_position_rent_refunded",
            "ci_out_of_range_seconds", "ci_max_retries_reached"
        ]
        writer.writerow(header)

        # Write data rows
        for row in rows:
            (id_, timestamp, type_, close_type, close_timestamp, status,
             net_pnl_pct, net_pnl_quote, cum_fees_quote, filled_amount_quote,
             is_active, is_trading, ctrl_id, config_json, custom_info_json) = row

            # Parse JSON fields
            config = json.loads(config_json) if config_json else {}
            custom_info = json.loads(custom_info_json) if custom_info_json else {}

            # Format timestamps
            created_at = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            close_ts_str = datetime.fromtimestamp(close_timestamp).strftime("%Y-%m-%d %H:%M:%S") if close_timestamp else ""

            # Extract config fields
            market = config.get("market", {})
            cfg_connector = market.get("connector_name", "")
            cfg_trading_pair = market.get("trading_pair", "")
            cfg_pool_address = config.get("pool_address", "")
            cfg_lower_price = config.get("lower_price", "")
            cfg_upper_price = config.get("upper_price", "")
            cfg_base_amount = config.get("base_amount", "")
            cfg_quote_amount = config.get("quote_amount", "")
            cfg_side = config.get("side", "")
            cfg_extra_params = json.dumps(config.get("extra_params", {}))

            # Extract custom_info fields
            ci_state = custom_info.get("state", "")
            ci_position_address = custom_info.get("position_address", "")
            ci_current_price = custom_info.get("current_price", "")
            ci_lower_price = custom_info.get("lower_price", "")
            ci_upper_price = custom_info.get("upper_price", "")
            ci_base_amount = custom_info.get("base_amount", "")
            ci_quote_amount = custom_info.get("quote_amount", "")
            ci_base_fee = custom_info.get("base_fee", "")
            ci_quote_fee = custom_info.get("quote_fee", "")
            ci_fees_earned_quote = custom_info.get("fees_earned_quote", "")
            ci_initial_base_amount = custom_info.get("initial_base_amount", "")
            ci_initial_quote_amount = custom_info.get("initial_quote_amount", "")
            ci_total_value_quote = custom_info.get("total_value_quote", "")
            ci_unrealized_pnl_quote = custom_info.get("unrealized_pnl_quote", "")
            ci_position_rent = custom_info.get("position_rent", "")
            ci_position_rent_refunded = custom_info.get("position_rent_refunded", "")
            ci_out_of_range_seconds = custom_info.get("out_of_range_seconds", "")
            ci_max_retries_reached = custom_info.get("max_retries_reached", "")

            writer.writerow([
                id_, created_at, type_, status_map.get(status, status),
                close_type_map.get(close_type, close_type), close_ts_str,
                net_pnl_pct, net_pnl_quote, cum_fees_quote, filled_amount_quote,
                is_active, is_trading, ctrl_id,
                cfg_connector, cfg_trading_pair, cfg_pool_address,
                cfg_lower_price, cfg_upper_price, cfg_base_amount, cfg_quote_amount,
                cfg_side, cfg_extra_params,
                ci_state, ci_position_address, ci_current_price,
                ci_lower_price, ci_upper_price,
                ci_base_amount, ci_quote_amount,
                ci_base_fee, ci_quote_fee, ci_fees_earned_quote,
                ci_initial_base_amount, ci_initial_quote_amount,
                ci_total_value_quote, ci_unrealized_pnl_quote,
                ci_position_rent, ci_position_rent_refunded,
                ci_out_of_range_seconds, ci_max_retries_reached
            ])

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Export executor data to CSV")
    parser.add_argument("controller_id", help="Controller ID to export (e.g., lp_rebalancer_4)")
    parser.add_argument("--db", help="Path to SQLite database (default: most recent in data/)")
    parser.add_argument("--output", "-o", help="Output CSV path (default: exports/<controller_id>_<timestamp>.csv)")

    args = parser.parse_args()

    # Determine database path
    if args.db:
        db_path = args.db
    else:
        db_path = find_latest_db()
        print(f"Using database: {db_path}")

    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}")
        return 1

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/{args.controller_id}_{timestamp}.csv"

    # Export
    count = export_executors(args.controller_id, db_path, output_path)

    if count > 0:
        print(f"Exported {count} executors to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
