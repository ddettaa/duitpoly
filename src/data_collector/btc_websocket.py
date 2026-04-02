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
        reconnect_delay = 1
        max_reconnect_delay = 30
        consecutive_errors = 0

        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)

                if self.running:
                    consecutive_errors += 1
                    if consecutive_errors <= 3:
                        print(
                            f"[BTC WS] Disconnected, retrying in {reconnect_delay}s..."
                        )
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)
                else:
                    break

            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    print(f"[BTC WS] Error: {e}, retrying...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_reconnect_delay)

        print("[BTC WS] Stopped")

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
        if self.running:
            error_str = str(error)
            if "10060" in error_str or "WSAEWOULDBLOCK" in error_str:
                pass
            else:
                print(f"[BTC WS] Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        if self.running and close_status_code != 1000:
            print(f"[BTC WS] Connection closed (code: {close_status_code})")

    def get_last_price(self):
        return self.last_price, self.last_timestamp_ms
