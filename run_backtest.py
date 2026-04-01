"""
Backtest Runner
Run historical backtests on collected data.

Usage:
    python run_backtest.py                    # Backtest all markets
    python run_backtest.py --market ID        # Backtest specific market
    python run_backtest.py --days 7           # Last 7 days of data
    python run_backtest.py --export           # Export to JSON
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.sqlite_handler import SQLiteHandler
from src.engine.backtester import Backtester


def get_market_data(db, market_id=None, days=7):
    conn = db._get_connection()
    cursor = conn.cursor()

    if market_id:
        cursor.execute(
            """
            SELECT market_id, price_yes, btc_price, timestamp_ms
            FROM price_snapshots
            WHERE market_id = ?
            AND created_at > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp_ms ASC
        """,
            (market_id, days),
        )
    else:
        cursor.execute(
            """
            SELECT market_id, price_yes, btc_price, timestamp_ms
            FROM price_snapshots
            WHERE created_at > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp_ms ASC
        """,
            (days,),
        )

    results = cursor.fetchall()
    conn.close()

    market_data = {}
    for row in results:
        mid, price_yes, btc_price, ts = row
        if mid not in market_data:
            market_data[mid] = []
        market_data[mid].append(
            {
                "timestamp": ts,
                "price_yes": price_yes,
                "btc_price": btc_price,
                "llm_edge": 0.03,
                "llm_confidence": 0.6,
                "latency_signal": None,
            }
        )

    return market_data


def run_backtests(market_id=None, days=7, export=False):
    print("\n" + "=" * 60)
    print("POLYMARKET BACKTEST RUNNER")
    print("=" * 60)
    print(f"Market: {market_id or 'ALL'}")
    print(f"Days: {days}")
    print(f"Export: {export}")
    print("=" * 60)

    db = SQLiteHandler()
    market_data = get_market_data(db, market_id, days)

    if not market_data:
        print("No data found for specified criteria")
        return

    print(
        f"\nFound {len(market_data)} markets with {sum(len(v) for v in market_data.values())} total data points"
    )

    bt = Backtester(initial_capital=10000)
    all_results = []

    for mid, data in market_data.items():
        if len(data) < 10:
            print(f"\nSkipping {mid}: insufficient data ({len(data)} points)")
            continue

        print(f"\n--- Backtesting {mid} ({len(data)} points) ---")

        result = bt.run_backtest(mid, data, "combined")
        all_results.append(result)

        print(f"    Initial: ${result['initial_capital']:.2f}")
        print(f"    Final: ${result['final_capital']:.2f}")
        print(f"    P&L: ${result['total_pnl']:.2f} ({result['total_pnl_pct']:.2f}%)")
        print(f"    Trades: {result['total_trades']}")
        print(f"    Win Rate: {result['win_rate']:.1f}%")

        if result["total_trades"] > 0:
            print(f"    Avg Win: ${result['avg_win']:.2f}")
            print(f"    Avg Loss: ${result['avg_loss']:.2f}")
            print(f"    Profit Factor: {result['profit_factor']:.2f}")
            print(f"    Max Drawdown: {result['max_drawdown']:.2f}%")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if all_results:
        total_pnl = sum(r["total_pnl"] for r in all_results)
        avg_win_rate = sum(r["win_rate"] for r in all_results) / len(all_results)
        total_trades = sum(r["total_trades"] for r in all_results)
        profitable = sum(1 for r in all_results if r["total_pnl"] > 0)

        print(f"Markets tested: {len(all_results)}")
        print(f"Profitable: {profitable} ({profitable / len(all_results) * 100:.1f}%)")
        print(f"Total trades: {total_trades}")
        print(f"Average win rate: {avg_win_rate:.1f}%")
        print(f"Total P&L: ${total_pnl:.2f}")

        best = max(all_results, key=lambda x: x["total_pnl"])
        worst = min(all_results, key=lambda x: x["total_pnl"])

        print(f"\nBest: {best['market_id']} (${best['total_pnl']:.2f})")
        print(f"Worst: {worst['market_id']} (${worst['total_pnl']:.2f})")

        if export:
            report = bt.save_report("backtest_report.json")
            print(f"\nReport exported to backtest_report.json")

    return all_results


def main():
    parser = argparse.ArgumentParser(description="Run backtests on Polymarket data")
    parser.add_argument("--market", type=str, help="Specific market ID to backtest")
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days of data to use"
    )
    parser.add_argument("--export", action="store_true", help="Export results to JSON")

    args = parser.parse_args()

    results = run_backtests(market_id=args.market, days=args.days, export=args.export)


if __name__ == "__main__":
    main()
