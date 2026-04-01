"""
Phase 1-5 Component Test Suite
Run: python test_all_phases.py
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.sqlite_handler import SQLiteHandler
from src.engine.signal_engine import SignalEngine
from src.engine.risk_manager import RiskManager
from src.engine.backtester import Backtester
from src.llm.minimax_client import MiniMaxClient


def test_phase1_sqlite():
    print("\n" + "=" * 50)
    print("PHASE 1: SQLite Database")
    print("=" * 50)

    db = SQLiteHandler("data/test_trading_phases.db")

    db.insert_price_snapshot(
        market_id="crypto_test_1",
        market_question="Will BTC reach $100k?",
        price_yes=0.65,
        price_no=0.35,
        btc_price=67000,
        volume=100000,
        liquidity=50000,
        timestamp_ms=int(time.time() * 1000),
    )

    db.insert_btc_feed(67000, int(time.time() * 1000))

    db.insert_latency_event(
        market_id="crypto_test_1",
        btc_price=67000,
        polymarket_price=0.65,
        deviation_pct=0.5,
        btc_timestamp_ms=int(time.time() * 1000),
        polymarket_timestamp_ms=int(time.time() * 1000) - 300,
        latency_ms=300,
        direction="btc_up_polymarket_lagged",
    )

    stats = db.get_latency_stats()
    print(f"[OK] Phase 1 SQLite working!")
    print(f"    Data points: {db.get_data_points_count()}")
    print(f"    Latency events: {stats['count']}")
    return True


def test_phase2_signal_engine():
    print("\n" + "=" * 50)
    print("PHASE 2: Signal Engine")
    print("=" * 50)

    signal_engine = SignalEngine()

    btc_data = {"btc_price": 67000, "timestamp_ms": int(time.time() * 1000)}
    polymarket_data = {"market_id": "crypto_test_1", "price_yes": 0.65}

    llm_result = {
        "recommended_action": "buy_yes",
        "confidence": 0.75,
        "edge": 0.08,
        "reasoning": "Test reasoning",
    }

    signal = signal_engine.check_opportunity(btc_data, polymarket_data, llm_result)

    print(f"[OK] Signal Engine working!")
    print(f"    Priority: {signal['priority']}")
    print(f"    Action: {signal['action']}")
    print(f"    Signals count: {len(signal['signals'])}")

    stats = signal_engine.get_signal_stats()
    print(f"    Total signals: {stats['total']}")
    return True


def test_phase2_risk_manager():
    print("\n" + "=" * 50)
    print("PHASE 2: Risk Manager")
    print("=" * 50)

    rm = RiskManager(initial_capital=10000)

    can_trade = rm.can_trade()
    print(f"    Can trade: {can_trade}")

    size = rm.calculate_position_size(0.75, 0.08)
    print(f"    Position size: ${size:.2f}")

    trade = rm.execute_trade(
        market_id="test_market",
        action="buy_yes",
        price=0.65,
        position_size=size,
        entry_btc_price=67000,
    )
    print(f"    Trade opened: {trade['trade_id'] if trade else 'FAILED'}")

    closed = rm.close_trade(trade["trade_id"], 0.68, reason="test")
    print(f"    Trade closed, P&L: ${closed['pnl']:.2f}")

    metrics = rm.get_metrics()
    print(f"    Current capital: ${metrics['current_capital']:.2f}")
    print(f"    Win rate: {metrics['win_rate']:.1f}%")

    return True


def test_phase3_backtester():
    print("\n" + "=" * 50)
    print("PHASE 3: Backtester")
    print("=" * 50)

    bt = Backtester(initial_capital=10000)

    trades_data = []
    for i in range(100):
        trades_data.append(
            {
                "timestamp": int(time.time() * 1000) + (i * 60000),
                "price_yes": 0.60 + (i * 0.002),
                "btc_price": 67000 + (i * 100),
                "llm_edge": 0.05 if i % 5 == 0 else 0.02,
                "llm_confidence": 0.70 if i % 5 == 0 else 0.55,
                "latency_signal": "buy_yes" if i % 10 == 0 else None,
            }
        )

    result = bt.run_backtest("test_market", trades_data, "combined")

    print(f"[OK] Backtest completed!")
    print(f"    Initial capital: ${result['initial_capital']:.2f}")
    print(f"    Final capital: ${result['final_capital']:.2f}")
    print(f"    Total P&L: ${result['total_pnl']:.2f}")
    print(f"    Win rate: {result['win_rate']:.1f}%")
    print(f"    Total trades: {result['total_trades']}")

    summary = bt.get_summary()
    print(f"    Markets tested: {summary['markets_tested']}")
    print(f"    Best market: {summary['best_market']}")

    return True


def test_phase4_paper_trading():
    print("\n" + "=" * 50)
    print("PHASE 4: Paper Trading (Simulation)")
    print("=" * 50)

    from src.engine.paper_trading_engine import PaperTradingEngine

    paper = PaperTradingEngine(initial_capital=10000)

    print(f"[OK] Paper trading engine created")
    print(f"    Mode: {paper.mode}")
    print(f"    Initial capital: ${paper.risk_manager.initial_capital:.2f}")

    metrics = paper.get_metrics()
    print(f"    Metrics accessible: {metrics['current_capital']:.2f}")

    return True


def test_phase5_pro_trading():
    print("\n" + "=" * 50)
    print("PHASE 5: Pro Trading (Simulation)")
    print("=" * 50)

    from src.engine.pro_trading_engine import ProTradingEngine
    from src.execution.polymarket_executor import PolymarketExecutor

    executor = PolymarketExecutor()

    print(f"[OK] Polymarket executor created")
    print(f"    Mode: {ProTradingEngine.MODE}")

    result = executor.place_order("test_market", "yes", 1.0, 0.65)
    print(f"    Mock order result: {result['status']}")

    pro = ProTradingEngine(initial_capital=10)
    print(f"[OK] Pro trading engine created")
    print(f"    Mode: {pro.MODE}")
    print(f"    Initial capital: ${pro.risk_manager.initial_capital:.2f}")

    return True


def run_all_tests():
    print("\n" + "=" * 60)
    print("POLYMARKET TRADING ENGINE - ALL PHASES TEST")
    print("=" * 60)

    tests = [
        ("Phase 1 - SQLite & Data Collection", test_phase1_sqlite),
        ("Phase 2 - Signal Engine", test_phase2_signal_engine),
        ("Phase 2 - Risk Manager", test_phase2_risk_manager),
        ("Phase 3 - Backtester", test_phase3_backtester),
        ("Phase 4 - Paper Trading", test_phase4_paper_trading),
        ("Phase 5 - Pro Trading", test_phase5_pro_trading),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    failed = len(results) - passed

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")

    print("\n" + "=" * 60)
    print("USAGE GUIDE")
    print("=" * 60)
    print("""
# Set mode in .env or as command line argument:
TRADING_MODE=FREE python main.py    # Data collection only
TRADING_MODE=PAPER python main.py   # Paper trading (simulated)
TRADING_MODE=PRO python main.py    # Live trading (REAL MONEY!)

# Or via command line:
python main.py FREE
python main.py PAPER
python main.py PRO
""")

    return all(r for _, r in results)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
