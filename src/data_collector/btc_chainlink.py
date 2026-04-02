import requests
import time
import threading
from datetime import datetime


CHAINLINK_CANDLES_URL = "https://polymarket.com/api/chainlink-candles"


class BTCCollector:
    def __init__(self, interval_seconds=60, callback=None):
        self.interval = interval_seconds
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_price = None
        self.last_timestamp_ms = None
        self.price_history = []

    def start(self, callback=None):
        self.running = True
        self.callback = callback or self.callback
        self.thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self.thread.start()
        print("[BTC Collector] Started (Polymarket Chainlink)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[BTC Collector] Stopped")

    def _fetch_loop(self):
        while self.running:
            try:
                self._fetch_candles()
            except Exception as e:
                print(f"[BTC Collector] Error: {e}")
            time.sleep(self.interval)

    def _fetch_candles(self):
        try:
            url = f"{CHAINLINK_CANDLES_URL}?symbol=BTC&interval=5m&limit=30"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                candles = data.get("candles", [])
                if candles:
                    latest = candles[-1]
                    btc_price = latest.get("close", 0)
                    timestamp_ms = int(latest.get("time", time.time()) * 1000)

                    self.last_price = btc_price
                    self.last_timestamp_ms = timestamp_ms
                    self.price_history.append(
                        {
                            "price": btc_price,
                            "timestamp_ms": timestamp_ms,
                            "open": latest.get("open"),
                            "high": latest.get("high"),
                            "low": latest.get("low"),
                        }
                    )

                    if len(self.price_history) > 100:
                        self.price_history = self.price_history[-100:]

                    if self.callback:
                        self.callback(
                            {
                                "btc_price": btc_price,
                                "timestamp_ms": timestamp_ms,
                                "open": latest.get("open"),
                                "high": latest.get("high"),
                                "low": latest.get("low"),
                                "interval": "5m",
                            }
                        )
        except Exception as e:
            print(f"[BTC Collector] Fetch error: {e}")

    def get_last_price(self):
        return self.last_price, self.last_timestamp_ms

    def get_price_history(self, limit=30):
        return self.price_history[-limit:] if self.price_history else []

    def get_trend(self, periods=4):
        if len(self.price_history) < periods:
            return "neutral"
        recent = self.price_history[-periods:]
        if all(
            recent[i]["price"] < recent[i + 1]["price"] for i in range(len(recent) - 1)
        ):
            return "up"
        elif all(
            recent[i]["price"] > recent[i + 1]["price"] for i in range(len(recent) - 1)
        ):
            return "down"
        return "neutral"
