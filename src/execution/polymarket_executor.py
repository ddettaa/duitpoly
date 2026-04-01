import os
import time
import threading
import requests
from datetime import datetime
from src.db.sqlite_handler import db
from src.engine.risk_manager import RiskManager
from src.engine.signal_engine import SignalEngine
from config.config import POLYMARKET_API_URL


class PolymarketExecutor:
    def __init__(self, api_key=None, api_secret=None, telegram_bot=None):
        self.api_key = api_key or os.getenv("POLYMARKET_API_KEY", "")
        self.api_secret = api_secret or os.getenv("POLYMARKET_API_SECRET", "")
        self.base_url = POLYMARKET_API_URL
        self.telegram_bot = telegram_bot

    def place_order(self, market_id, side, size, price):
        if not self.api_key:
            print(f"[Executor] No API key - would place order: {side} {size} @ {price}")
            return self._mock_order_response(market_id, side, size, price)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "market_id": market_id,
                "side": side,
                "size": size,
                "price": price,
            }

            response = requests.post(
                f"{self.base_url}/orders", headers=headers, json=payload, timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(
                    f"[Executor] Order failed: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            print(f"[Executor] Order error: {e}")
            return None

    def _mock_order_response(self, market_id, side, size, price):
        return {
            "order_id": f"mock_order_{int(time.time() * 1000)}",
            "market_id": market_id,
            "side": side,
            "size": size,
            "price": price,
            "status": "filled",
            "filled_at": int(time.time() * 1000),
        }

    def cancel_order(self, order_id):
        if not self.api_key:
            print(f"[Executor] No API key - would cancel order: {order_id}")
            return True

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.delete(
                f"{self.base_url}/orders/{order_id}", headers=headers, timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[Executor] Cancel error: {e}")
            return False

    def get_order_status(self, order_id):
        if not self.api_key:
            return {"status": "filled", "filled_size": "mock"}

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                f"{self.base_url}/orders/{order_id}", headers=headers, timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"[Executor] Status check error: {e}")

        return None

    def get_balance(self):
        if not self.api_key:
            return 10.00

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                f"{self.base_url}/balance", headers=headers, timeout=10
            )
            if response.status_code == 200:
                return float(response.json().get("balance", 0))
        except Exception as e:
            print(f"[Executor] Balance check error: {e}")

        return 0
