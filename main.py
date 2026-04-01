import os
import sys
import time
import threading
import signal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import LATENCY_THRESHOLD_PCT, LLM_ANALYSIS_INTERVAL_MINUTES, DB_PATH
from config.telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.db.sqlite_handler import SQLiteHandler
from src.data_collector.polymarket_client import PolymarketClient
from src.data_collector.btc_websocket import BTCWebSocket
from src.latency_detector.latency_analyzer import LatencyDetector
from src.llm.minimax_client import MiniMaxClient
from src.monitoring.telegram_bot import TelegramBot


class TradingEngine:
    def __init__(self):
        self.db = SQLiteHandler(DB_PATH)
        self.telegram_bot = None
        self.polymarket_client = None
        self.btc_ws = None
        self.latency_detector = None
        self.llm_client = None
        self.running = False
        self.start_time = time.time()

        self._init_components()
        self._register_signal_handlers()

    def _init_components(self):
        print("[Engine] Initializing components...")

        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            self.telegram_bot = TelegramBot()
            print("[Engine] Telegram bot initialized")
        else:
            print(
                "[Engine] WARNING: Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)"
            )

        self.polymarket_client = PolymarketClient()
        print("[Engine] Polymarket client ready")

        self.btc_ws = BTCWebSocket()
        print("[Engine] BTC WebSocket ready")

        self.latency_detector = LatencyDetector(telegram_bot=self.telegram_bot)
        print("[Engine] Latency detector ready")

        minimax_key = os.getenv("MINIMAX_API_KEY", "")
        if minimax_key:
            self.llm_client = MiniMaxClient(
                api_key=minimax_key, telegram_bot=self.telegram_bot
            )
            print("[Engine] MiniMax client ready")
        else:
            print("[Engine] WARNING: MiniMax not configured (set MINIMAX_API_KEY)")

        print("[Engine] All components initialized")

    def _register_signal_handlers(self):
        def signal_handler(sig, frame):
            print("\n[Engine] Shutdown signal received")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _on_polymarket_data(self, data):
        try:
            self.db.insert_price_snapshot(
                market_id=data["market_id"],
                market_question=data["market_question"],
                price_yes=data["price_yes"],
                price_no=data["price_no"],
                btc_price=0,
                volume=data.get("volume", 0),
                liquidity=data.get("liquidity", 0),
                timestamp_ms=data["timestamp_ms"],
                source="polymarket",
            )

            btc_price, btc_ts = self.btc_ws.get_last_price()
            if btc_price:
                data_with_btc = data.copy()
                data_with_btc["btc_price"] = btc_price
                self.latency_detector.check_deviation(
                    {"btc_price": btc_price, "timestamp_ms": btc_ts}, data
                )

        except Exception as e:
            print(f"[Engine] Error processing polymarket data: {e}")

    def _on_btc_data(self, data):
        try:
            self.db.insert_btc_feed(
                btc_price=data["btc_price"], timestamp_ms=data["timestamp_ms"]
            )

        except Exception as e:
            print(f"[Engine] Error processing BTC data: {e}")

    def _slow_analysis_loop(self):
        print("[Engine] Slow analysis loop started")
        while self.running:
            try:
                time.sleep(LLM_ANALYSIS_INTERVAL_MINUTES * 60)

                if not self.llm_client:
                    continue

                markets = self.db.get_pending_markets_for_analysis(limit=10)
                if not markets:
                    continue

                print(f"[Engine] Analyzing {len(markets)} markets...")

                for market in markets:
                    if not self.running:
                        break

                    market_id, question, price_yes = market
                    btc_price, _ = self.db.get_latest_btc_price()

                    result = self.llm_client.analyze_market(
                        market_question=question,
                        market_price_yes=price_yes,
                        btc_price=btc_price if btc_price > 0 else None,
                    )

                    if result:
                        result["market_id"] = market_id
                        self.db.insert_llm_analysis(
                            market_id=market_id,
                            market_question=question,
                            market_price_yes=price_yes,
                            predicted_probability=result["predicted_probability"],
                            confidence=result["confidence"],
                            llm_reasoning=result["reasoning"],
                            edge=result["edge"],
                            recommended_action=result["recommended_action"],
                        )

                        self.llm_client.check_and_alert_opportunity(result)
                        print(
                            f"[Engine] Analyzed {market_id}: edge={result['edge']:.2%}, action={result['recommended_action']}"
                        )

                    time.sleep(2)

            except Exception as e:
                print(f"[Engine] Slow analysis error: {e}")

    def _daily_summary_loop(self):
        print("[Engine] Daily summary loop started")
        while self.running:
            try:
                while True:
                    now = datetime.now()
                    if now.hour == 18 and now.minute == 0:
                        break
                    time.sleep(60)

                if self.running and self.telegram_bot:
                    stats = self.db.get_latency_stats()
                    self.telegram_bot.send_daily_summary(stats)
                    print("[Engine] Daily summary sent")

                time.sleep(60)

            except Exception as e:
                print(f"[Engine] Daily summary error: {e}")

    def start(self):
        print("\n" + "=" * 50)
        print("POLYMARKET TRADING ENGINE - PHASE 1")
        print("=" * 50)
        print(f"[Engine] Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.running = True

        self.polymarket_client.start_polling(callback=self._on_polymarket_data)

        self.btc_ws.start(callback=self._on_btc_data)

        if self.telegram_bot:
            self.telegram_bot.send_startup_message()
            self.telegram_bot.start_health_checker(
                interval_minutes=60,
                data_points_func=self.db.get_data_points_count,
                latency_count_func=self.db.get_latency_events_today,
            )

        threading.Thread(target=self._slow_analysis_loop, daemon=True).start()
        threading.Thread(target=self._daily_summary_loop, daemon=True).start()

        print("[Engine] All systems started!")
        print("[Engine] Press Ctrl+C to stop")
        print("=" * 50 + "\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\n[Engine] Stopping...")
        self.running = False

        self.polymarket_client.stop_polling()
        self.btc_ws.stop()

        if self.telegram_bot:
            self.telegram_bot.stop_health_checker()

        print("[Engine] Stopped")

    def get_status(self):
        uptime = time.time() - self.start_time
        data_points = self.db.get_data_points_count()
        latency_stats = self.db.get_latency_stats()

        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "data_points": data_points,
            "latency_stats": latency_stats,
        }


def main():
    engine = TradingEngine()
    engine.start()


if __name__ == "__main__":
    main()
