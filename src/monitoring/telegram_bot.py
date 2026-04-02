import os
import time
import threading
import requests
from datetime import datetime
from config.telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ALERT_CONFIG


class TelegramBot:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.running = False
        self.health_thread = None
        self.start_time = time.time()

    def send_message(self, text, parse_mode="Markdown"):
        if not self.bot_token or not self.chat_id:
            print(f"[Telegram] Bot not configured.")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode}
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            if not result.get("ok"):
                print(f"[Telegram] API error: {result}")
            return result.get("ok", False)
        except Exception as e:
            print(f"[Telegram] Send error: {e}")
            return False

    def send_alert(self, alert_type, data):
        config = ALERT_CONFIG.get(alert_type)
        if not config:
            return

        message = config["message"].format(**data)
        self.send_message(message)

    def send_latency_spike(self, latency_ms, market_id, deviation_pct, direction):
        message = f"🔴 *Latency Spike Detected*\n\n"
        message += f"Market: `{market_id}`\n"
        message += f"Latency: *{latency_ms}ms*\n"
        message += f"Deviation: {deviation_pct:.3f}%\n"
        message += f"Direction: {direction}"
        self.send_message(message)

    def send_opportunity(self, market_id, edge, confidence, action):
        emoji = "🟢" if action == "buy_yes" else "🔴" if action == "buy_no" else "⚪"
        message = f"{emoji} *Trading Opportunity*\n\n"
        message += f"Market: `{market_id}`\n"
        message += f"Edge: *{edge}*\n"
        message += f"Confidence: {confidence}\n"
        message += f"Action: *{action}*"
        self.send_message(message)

    def send_daily_summary(self, latency_stats):
        message = f"📊 *Daily Summary*\n\n"
        message += f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        message += f"---\n"
        message += f"📈 *Latency Events:* {latency_stats['count']}\n"
        message += f"⏱️ Avg Latency: {latency_stats['avg_ms']}ms\n"
        message += f"⚡ Max Latency: {latency_stats['max_ms']}ms\n"
        message += f"📉 Avg Deviation: {latency_stats['avg_deviation']:.3f}%\n"
        message += f"📉 Max Deviation: {latency_stats['max_deviation']:.3f}%"
        self.send_message(message)

    def send_system_health(self, data_points, latency_count):
        uptime_hours = (time.time() - self.start_time) / 3600
        message = f"✅ *System Health*\n\n"
        message += f"🟢 Status: Running\n"
        message += f"⏱️ Uptime: {uptime_hours:.1f} hours\n"
        message += f"📊 Data Points: {data_points}\n"
        message += f"⚡ Latency Events: {latency_count}"
        self.send_message(message)

    def start_health_checker(
        self,
        interval_minutes=60,
        latency_stats_func=None,
        data_points_func=None,
        latency_count_func=None,
    ):
        self.running = True
        self.latency_stats_func = latency_stats_func
        self.data_points_func = data_points_func
        self.latency_count_func = latency_count_func

        self.health_thread = threading.Thread(
            target=self._health_loop, args=(interval_minutes,), daemon=True
        )
        self.health_thread.start()
        print("[Telegram] Health checker started")

    def stop_health_checker(self):
        self.running = False
        if self.health_thread:
            self.health_thread.join(timeout=5)
        print("[Telegram] Health checker stopped")

    def _health_loop(self, interval_minutes):
        while self.running:
            try:
                data_points = self.data_points_func() if self.data_points_func else 0
                latency_count = (
                    self.latency_count_func() if self.latency_count_func else 0
                )
                self.send_system_health(data_points, latency_count)
            except Exception as e:
                print(f"[Telegram] Health check error: {e}")

            time.sleep(interval_minutes * 60)

    def test_connection(self):
        message = f"🧪 *Bot Test*\n\n"
        message += f"✅ Polymarket Trading Bot connected!\n"
        message += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(message)

    def send_startup_message(self):
        message = f"🚀 *System Started*\n\n"
        message += f"✅ Polymarket Trading Engine Online\n"
        message += f"🟢 Latency Detector: Active\n"
        message += f"🟢 LLM Analyzer: Ready\n"
        message += f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_message(message)
