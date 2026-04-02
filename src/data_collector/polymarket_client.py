import requests
import json
import time
import threading
from datetime import datetime, timezone
from config.config import POLYMARKET_POLL_INTERVAL_MS

POLYMARKET_API = "https://polymarket.com/api/crypto/markets"
CLOBB_API = "https://clob.polymarket.com"

CRYPTO_KEYWORDS = [
    "btc",
    "bitcoin",
    "eth",
    "ethereum",
    "crypto",
    "defi",
    "sol",
    "solana",
    "xrp",
    "ripple",
    "dogecoin",
    "cardano",
    "polkadot",
    "avalanche",
    "matic",
    "binance",
    "bnb",
    "shiba",
    "doge",
    "dot",
    "ada",
    "link",
    "megaeth",
]


class PolymarketClient:
    def __init__(self, callback=None):
        self.poll_interval = POLYMARKET_POLL_INTERVAL_MS / 1000.0
        self.callback = callback
        self.running = False
        self.thread = None
        self.last_prices = {}
        self.error_count = 0
        self.max_errors = 5
        self._btc_price = 0
        self._btc_timestamp = 0

    def _fetch_crypto_markets(self, limit=50, offset=0):
        try:
            url = POLYMARKET_API
            params = {
                "_c": "crypto",
                "_s": "volume_24hr",
                "_sts": "active",
                "_l": limit,
                "_offset": offset,
            }
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            return {"events": [], "hasMore": False, "totalCount": 0}
        except Exception as e:
            print(f"[Polymarket] API error: {e}")
            return {"events": [], "hasMore": False, "totalCount": 0}

    def _parse_markets_from_events(self, events):
        markets = []
        for event in events:
            nested_markets = event.get("markets", []) or []
            for m in nested_markets:
                try:
                    outcome_prices = m.get("outcomePrices", [])
                    if not outcome_prices or len(outcome_prices) < 2:
                        continue

                    price_yes = float(outcome_prices[0])
                    price_no = (
                        float(outcome_prices[1])
                        if len(outcome_prices) > 1
                        else (1 - price_yes)
                    )

                    if price_yes <= 0:
                        continue

                    market_id = m.get("conditionId", "") or m.get("id", "")
                    if not market_id:
                        continue

                    question = m.get("question", "") or ""
                    end_date_str = m.get("endDate", "") or ""

                    end_date = None
                    if end_date_str:
                        try:
                            end_date = datetime.fromisoformat(
                                end_date_str.replace("Z", "+00:00")
                            )
                        except:
                            pass

                    markets.append(
                        {
                            "id": market_id,
                            "question": question,
                            "price_yes": price_yes,
                            "price_no": price_no,
                            "volume": float(m.get("liquidity", 0) or 0),
                            "liquidity": float(m.get("liquidity", 0) or 0),
                            "active": m.get("active", True),
                            "closed": m.get("closed", False),
                            "end_date": end_date,
                        }
                    )
                except Exception as e:
                    continue
        return markets

    def get_crypto_markets(self, limit=100):
        all_markets = []
        offset = 0
        page_size = 50

        while len(all_markets) < limit:
            data = self._fetch_crypto_markets(limit=page_size, offset=offset)
            events = data.get("events", []) or []

            if not events:
                break

            markets = self._parse_markets_from_events(events)
            all_markets.extend(markets)

            has_more = data.get("hasMore", False)
            if not has_more:
                break

            offset += page_size
            time.sleep(0.1)

        print(f"[Polymarket] Fetched {len(all_markets)} crypto markets from Polymarket")
        return all_markets[:limit]

    def get_market_price(self, market_id):
        markets = self.get_crypto_markets(limit=500)
        for m in markets:
            if m["id"] == market_id:
                return {
                    "price_yes": m["price_yes"],
                    "price_no": m["price_no"],
                    "volume": m["volume"],
                    "liquidity": m["liquidity"],
                }
        return None

    def start_polling(self, callback=None):
        self.running = True
        self.callback = callback or self.callback
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print("[Polymarket] Started polling (Polymarket API)")

    def stop_polling(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Polymarket] Stopped polling")

    def _poll_loop(self):
        consecutive_errors = 0
        max_errors = 5

        while self.running:
            try:
                markets = self.get_crypto_markets(limit=100)
                consecutive_errors = 0

                for market in markets:
                    if not market:
                        continue

                    market_id = market.get("id", "")
                    price_yes = market.get("price_yes", 0)
                    price_no = market.get("price_no", 0)
                    volume = market.get("volume", 0)
                    liquidity = market.get("liquidity", 0)
                    question = market.get("question", "")

                    if price_yes > 0:
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
                consecutive_errors += 1
                if consecutive_errors <= max_errors:
                    print(f"[Polymarket] Polling error: {e}")
                elif consecutive_errors == max_errors + 1:
                    print(f"[Polymarket] Continuing error suppression...")

            time.sleep(self.poll_interval)

    def get_last_price(self, market_id):
        return self.last_prices.get(market_id)
