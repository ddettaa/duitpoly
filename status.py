"""
System Status Checker
View current system status and metrics.

Usage:
    python status.py
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.sqlite_handler import SQLiteHandler


def print_status():
    db = SQLiteHandler()

    latency_stats = db.get_latency_stats()
    data_points = db.get_data_points_count()
    trade_stats = db.get_trade_stats()
    signal_stats = db.get_signal_stats()

    print("\n" + "=" * 60)
    print("POLYMARKET TRADING ENGINE - STATUS")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("DATA COLLECTION")
    print("-" * 40)
    print(f"  Total data points: {data_points}")
    print(f"  Latency events: {latency_stats['count']}")
    print(f"  Avg latency: {latency_stats['avg_ms']}ms")
    print(f"  Max latency: {latency_stats['max_ms']}ms")
    print(f"  Avg deviation: {latency_stats['avg_deviation']:.3f}%")
    print(f"  Max deviation: {latency_stats['max_deviation']:.3f}%")
    print()

    print("TRADING SIGNALS")
    print("-" * 40)
    print(f"  Total signals: {signal_stats['total']}")
    print(f"  High priority: {signal_stats['high_priority']}")
    print(f"  BUY_YES signals: {signal_stats['buy_yes']}")
    print(f"  BUY_NO signals: {signal_stats['buy_no']}")
    print()

    print("TRADE HISTORY")
    print("-" * 40)
    print(f"  Total closed trades: {trade_stats['total']}")
    print(f"  Wins: {trade_stats['wins']}")
    print(f"  Losses: {trade_stats['losses']}")
    if trade_stats["total"] > 0:
        win_rate = trade_stats["wins"] / trade_stats["total"] * 100
        print(f"  Win rate: {win_rate:.1f}%")
    else:
        print(f"  Win rate: N/A")
    print(f"  Total P&L: ${trade_stats['total_pnl']:.2f}")
    print(f"  Avg P&L per trade: ${trade_stats['avg_pnl']:.2f}")
    print()

    recent_markets = db.get_recent_markets(limit=5)
    if recent_markets:
        print("RECENT MARKETS")
        print("-" * 40)
        for market_id, question, price, created_at in recent_markets:
            question_short = question[:50] + "..." if len(question) > 50 else question
            print(f"  {market_id}")
            print(f"    Q: {question_short}")
            print(f"    Price: {price:.2%}")
            print(f"    Time: {created_at}")
            print()

    print("=" * 60)

    if latency_stats["count"] < 100:
        print("\n[INFO] Need more data for analysis. Keep running for 7-14 days.")
    elif latency_stats["avg_ms"] < 200:
        print("\n[INFO] Latency looks good. Consider testing paper trading.")
    else:
        print(f"\n[INFO] Avg latency {latency_stats['avg_ms']}ms detected.")

    if trade_stats["total"] > 0:
        if trade_stats["total_pnl"] > 0:
            print("[INFO] Profitable trades so far. Consider paper trading.")
        else:
            print("[INFO] Still learning. Continue data collection.")

    print()


if __name__ == "__main__":
    print_status()
