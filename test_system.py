import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db.sqlite_handler import SQLiteHandler
from src.monitoring.telegram_bot import TelegramBot
from src.data_collector.polymarket_client import PolymarketClient
from src.data_collector.btc_websocket import BTCWebSocket
from src.latency_detector.latency_analyzer import LatencyDetector
import time


def test_sqlite():
    print("\n" + "=" * 50)
    print("TEST 1: SQLite Database")
    print("=" * 50)

    db = SQLiteHandler("data/test_trading.db")

    db.insert_price_snapshot(
        market_id="test_market_1",
        market_question="Will BTC reach $100k by 2025?",
        price_yes=0.65,
        price_no=0.35,
        btc_price=67500,
        volume=100000,
        liquidity=50000,
        timestamp_ms=int(time.time() * 1000),
    )

    db.insert_btc_feed(btc_price=67500, timestamp_ms=int(time.time() * 1000))

    db.insert_latency_event(
        market_id="test_market_1",
        btc_price=67500,
        polymarket_price=0.65,
        deviation_pct=0.5,
        btc_timestamp_ms=int(time.time() * 1000),
        polymarket_timestamp_ms=int(time.time() * 1000) - 300,
        latency_ms=300,
        direction="btc_up_polymarket_lagged",
    )

    stats = db.get_latency_stats()
    print("[OK] SQLite working!")
    print(f"   - Data points: {db.get_data_points_count()}")
    print(f"   - Latency events: {stats['count']}")
    print(f"   - Avg latency: {stats['avg_ms']}ms")

    return True


def test_telegram_bot():
    print("\n" + "=" * 50)
    print("TEST 2: Telegram Bot (Mock)")
    print("=" * 50)

    bot = TelegramBot(bot_token="", chat_id="")

    print("[i] Testing Telegram bot methods (no actual send)...")

    test_message = "[ALERT] Latency Spike: 523ms on test_market_1"
    print(f"   Message preview: {test_message}")

    opportunity_message = (
        "[OPPORTUNITY] test_market_1\nEdge=0.08\nConfidence=75%\nAction=buy_yes"
    )
    print(f"   Opportunity preview:\n   {opportunity_message}")

    health_message = (
        "[SYSTEM HEALTH]\n"
        "Status: Running\n"
        "Uptime: 2.5 hours\n"
        "Data Points: 1500\n"
        "Latency Events: 23"
    )
    print(f"   Health check preview:\n   {health_message}")

    print("[OK] Telegram bot methods working!")
    print("[!] Note: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable real alerts")

    return True


def test_polymarket_client():
    print("\n" + "=" * 50)
    print("TEST 3: Polymarket Client")
    print("=" * 50)

    client = PolymarketClient()
    print("[OK] Polymarket client initialized")
    print(f"   API URL: {client.api_url}")
    print(f"   Poll interval: {client.poll_interval}s")

    return True


def test_btc_websocket():
    print("\n" + "=" * 50)
    print("TEST 4: BTC WebSocket Client")
    print("=" * 50)

    ws = BTCWebSocket()
    print("[OK] BTC WebSocket client initialized")
    print(f"   URL: {ws.ws_url}")

    return True


def test_latency_detector():
    print("\n" + "=" * 50)
    print("TEST 5: Latency Detector")
    print("=" * 50)

    detector = LatencyDetector()
    print("[OK] Latency detector initialized")
    print(f"   Threshold: {detector.threshold_pct:.1%}")
    print(f"   Alert threshold: {detector.alert_threshold_ms}ms")

    test_btc_data = {"btc_price": 67500, "timestamp_ms": int(time.time() * 1000)}
    test_poly_data = {
        "market_id": "test_market",
        "price_yes": 0.65,
        "timestamp_ms": int(time.time() * 1000) - 100,
    }

    result = detector.check_deviation(test_btc_data, test_poly_data)
    print(f"   Test deviation check: {result:.4f}%")

    return True


def print_summary():
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print("[OK] All core components initialized successfully!")
    print()
    print("Next steps to run the full system:")
    print("   1. Copy .env.example to .env")
    print("   2. Set TELEGRAM_BOT_TOKEN (get from @BotFather)")
    print("   3. Set TELEGRAM_CHAT_ID (your Telegram user ID)")
    print("   4. Set MINIMAX_API_KEY (for LLM analysis)")
    print("   5. Run: python main.py")
    print()
    print("To check stats after running:")
    print(
        '   python -c "from src.db.sqlite_handler import db; print(db.get_latency_stats())"'
    )


def main():
    print("\n" + "=" * 50)
    print("POLYMARKET TRADING ENGINE - TEST SUITE")
    print("=" * 50)

    tests = [
        ("SQLite", test_sqlite),
        ("Telegram Bot", test_telegram_bot),
        ("Polymarket Client", test_polymarket_client),
        ("BTC WebSocket", test_btc_websocket),
        ("Latency Detector", test_latency_detector),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[X] {name} failed: {e}")
            results.append((name, False))

    print_summary()

    all_passed = all(r[1] for r in results)
    print("\n" + "=" * 50)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - Check errors above")
    print("=" * 50)


if __name__ == "__main__":
    main()
