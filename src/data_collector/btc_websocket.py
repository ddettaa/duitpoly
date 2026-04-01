import websocket
import threading
import time
import json
from config.config import BTC_WS_URL


class BTCWebSocket:
    def __init__(self, callback=None):
        self.ws_url = BTC_WS_URL
        self.callback = callback
        self.running = False
        self.ws = None
        self.thread = None
        self.last_price = None
        self.last_timestamp_ms = None

    def start(self, callback=None):
        self.running = True
        self.callback = callback or self.callback
        self.thread = threading.Thread(target=self._run_ws, daemon=True)
        self.thread.start()
        print("[BTC WS] Started")

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=5)
        print("[BTC WS] Stopped")

    def _run_ws(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self.ws.run_forever(ping_interval=30)
            except Exception as e:
                print(f"[BTC WS] Error: {e}")
                time.sleep(5)

    def _on_open(self, ws):
        print("[BTC WS] Connected")

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get("e") == "trade":
                btc_price = float(data.get("p", 0))
                timestamp_ms = int(data.get("T", time.time() * 1000))

                self.last_price = btc_price
                self.last_timestamp_ms = timestamp_ms

                if self.callback:
                    self.callback(
                        {"btc_price": btc_price, "timestamp_ms": timestamp_ms}
                    )
        except Exception as e:
            print(f"[BTC WS] Parse error: {e}")

    def _on_error(self, ws, error):
        print(f"[BTC WS] WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print(f"[BTC WS] Closed: {close_status_code}")

    def get_last_price(self):
        return self.last_price, self.last_timestamp_ms
