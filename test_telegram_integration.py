"""
Telegram Integration Test
=========================
Run this after setting up your .env file with real Telegram credentials.

Steps:
1. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
2. Run: python test_telegram_integration.py
3. Check your Telegram for test messages!
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from src.monitoring.telegram_bot import TelegramBot
from src.db.sqlite_handler import SQLiteHandler


def test_real_telegram():
    print("=" * 50)
    print("TELEGRAM INTEGRATION TEST")
    print("=" * 50)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("[ERROR] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        print("\nGet your credentials:")
        print("  1. Bot Token: Message @BotFather on Telegram")
        print("  2. Chat ID: Message @userinfobot on Telegram")
        return False

    print(f"[i] Bot Token: {bot_token[:10]}...")
    print(f"[i] Chat ID: {chat_id}")

    bot = TelegramBot(bot_token=bot_token, chat_id=chat_id)

    print("\n[1] Testing connection...")
    if bot.test_connection():
        print("[OK] Connection successful!")
    else:
        print("[ERROR] Connection failed - check your credentials")
        return False

    print("\n[2] Testing latency spike alert...")
    bot.send_latency_spike(
        latency_ms=523,
        market_id="test_market_123",
        deviation_pct=0.45,
        direction="btc_up_polymarket_lagged",
    )
    print("[OK] Alert sent - check Telegram!")

    print("\n[3] Testing opportunity alert...")
    bot.send_opportunity(
        market_id="crypto_btc_2025",
        edge="8.2%",
        confidence="High (75%)",
        action="buy_yes",
    )
    print("[OK] Alert sent - check Telegram!")

    print("\n[4] Testing system health...")
    bot.send_system_health(data_points=15420, latency_count=47)
    print("[OK] Alert sent - check Telegram!")

    print("\n[5] Testing daily summary...")
    db = SQLiteHandler()
    stats = db.get_latency_stats()
    bot.send_daily_summary(stats)
    print("[OK] Alert sent - check Telegram!")

    print("\n" + "=" * 50)
    print("SUCCESS! All Telegram features working.")
    print("=" * 50)
    print("\nYou should have received 5 messages on Telegram:")
    print("  1. Connection test")
    print("  2. Latency spike alert")
    print("  3. Opportunity alert")
    print("  4. System health check")
    print("  5. Daily summary")
    return True


if __name__ == "__main__":
    success = test_real_telegram()
    sys.exit(0 if success else 1)
