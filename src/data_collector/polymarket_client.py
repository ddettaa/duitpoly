import requests
import time
import threading
from config.config import (
    POLYMARKET_API_URL,
    POLYMARKET_POLL_INTERVAL_MS,
    CRYPTO_ONLY_TAGS,
)


class PolymarketClient:
    def __init__(self, callback=None):
        self.api_url = POLYMARKET_API_URL
        self.poll_interval = POLYMARKET_POLL_INTERVAL_MS / 1000.0
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_prices = {}

    def get_markets(self, limit=20):
        try:
            url = f"{self.api_url}/markets"
            params = {"limit": limit, "closed": "false"}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"[Polymarket] Error fetching markets: {e}")
            return []

    def get_crypto_markets(self, limit=50):
        all_markets = self.get_markets(limit=limit)
        crypto_markets = []

        for market in all_markets:
            tags = market.get("tags", []) or []
            question = market.get("question", "").lower()

            is_crypto = any(
                tag.lower() in CRYPTO_ONLY_TAGS
                or any(
                    crypto in question
                    for crypto in [
                        "btc",
                        "bitcoin",
                        "eth",
                        "ethereum",
                        "crypto",
                        "defi",
                    ]
                )
                for tag in tags
            )

            if is_crypto:
                crypto_markets.append(market)

        return crypto_markets

    def get_market_price(self, market_id):
        try:
            url = f"{self.api_url}/markets/{market_id}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "price_yes": float(data.get("yes_price", 0)),
                    "price_no": float(data.get("no_price", 0)),
                    "volume": float(data.get("volume", 0)),
                    "liquidity": float(data.get("liquidity", 0)),
                }
            return None
        except Exception as e:
            print(f"[Polymarket] Error fetching market {market_id}: {e}")
            return None

    def start_polling(self, callback=None):
        self.running = True
        self.callback = callback or self.callback
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print("[Polymarket] Started polling")

    def stop_polling(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Polymarket] Stopped polling")

    def _poll_loop(self):
        while self.running:
            try:
                markets = self.get_crypto_markets(limit=30)
                for market in markets:
                    market_id = market.get("id", "")
                    price_yes = float(market.get("yes_price", 0))
                    price_no = float(market.get("no_price", 0))
                    volume = float(market.get("volume", 0))
                    liquidity = float(market.get("liquidity", 0))
                    question = market.get("question", "")

                    if price_yes > 0 and price_no > 0:
                        timestamp_ms = int(time.time() * 1000)

                        if self.callback:
                            self.callback(
                                {
                                    "market_id": market_id,
                                    "market_question": question,
                                    "price_yes": price_yes,
                                    "price_no": price_no,
                                    "volume": volume,
                                    "liquidity": liquidity,
                                    "timestamp_ms": timestamp_ms,
                                }
                            )

                        self.last_prices[market_id] = {
                            "price_yes": price_yes,
                            "price_no": price_no,
                            "timestamp_ms": timestamp_ms,
                        }

            except Exception as e:
                print(f"[Polymarket] Polling error: {e}")

            time.sleep(self.poll_interval)

    def get_last_price(self, market_id):
        return self.last_prices.get(market_id)
