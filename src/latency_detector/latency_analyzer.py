import time
from config.config import LATENCY_THRESHOLD_PCT, LATENCY_ALERT_THRESHOLD_MS
from src.db.sqlite_handler import db


class LatencyDetector:
    def __init__(self, telegram_bot=None):
        self.threshold_pct = LATENCY_THRESHOLD_PCT
        self.alert_threshold_ms = LATENCY_ALERT_THRESHOLD_MS
        self.telegram_bot = telegram_bot
        self.btc_price_history = []
        self.polymarket_price_history = {}
        self.last_btc_move = None
        self.last_polymarket_move = {}

    def check_latency(self, btc_data, polymarket_data):
        btc_price = btc_data["btc_price"]
        btc_timestamp_ms = btc_data["timestamp_ms"]
        market_id = polymarket_data["market_id"]
        polymarket_price = polymarket_data["price_yes"]
        polymarket_timestamp_ms = polymarket_data["timestamp_ms"]

        btc_direction = self._get_price_direction(self.last_btc_move, btc_price)
        polymarket_direction = self._get_price_direction(
            self.last_polymarket_move.get(market_id), polymarket_price
        )

        self.last_btc_move = btc_price
        self.last_polymarket_move[market_id] = polymarket_price

        if btc_direction == 0:
            return None

        latency_ms = btc_timestamp_ms - polymarket_timestamp_ms

        if abs(latency_ms) > self.alert_threshold_ms and latency_ms > 0:
            direction = self._determine_direction(btc_direction, polymarket_direction)

            if direction:
                deviation_pct = abs(btc_price - polymarket_price) / btc_price * 100

                db.insert_latency_event(
                    market_id=market_id,
                    btc_price=btc_price,
                    polymarket_price=polymarket_price,
                    deviation_pct=deviation_pct,
                    btc_timestamp_ms=btc_timestamp_ms,
                    polymarket_timestamp_ms=polymarket_timestamp_ms,
                    latency_ms=latency_ms,
                    direction=direction,
                )

                if self.telegram_bot and latency_ms > self.alert_threshold_ms:
                    self.telegram_bot.send_alert(
                        alert_type="latency_spike",
                        data={
                            "latency_ms": latency_ms,
                            "market_id": market_id,
                            "deviation_pct": deviation_pct,
                            "direction": direction,
                        },
                    )

                return {
                    "market_id": market_id,
                    "latency_ms": latency_ms,
                    "direction": direction,
                    "deviation_pct": deviation_pct,
                }

        return None

    def check_deviation(self, btc_data, polymarket_data):
        btc_price = btc_data["btc_price"]
        market_id = polymarket_data["market_id"]
        polymarket_price = polymarket_data["price_yes"]

        btc_pct_change = 0
        if self.last_btc_move:
            btc_pct_change = (
                (btc_price - self.last_btc_move) / self.last_btc_move
            ) * 100

        polymarket_pct_change = 0
        last_poly = self.last_polymarket_move.get(market_id)
        if last_poly:
            polymarket_pct_change = ((polymarket_price - last_poly) / last_poly) * 100

        deviation = abs(btc_pct_change - polymarket_pct_change)

        if deviation > self.threshold_pct * 100:
            direction = self._determine_direction(
                1 if btc_pct_change > 0 else -1, 1 if polymarket_pct_change > 0 else -1
            )

            if direction:
                db.insert_latency_event(
                    market_id=market_id,
                    btc_price=btc_price,
                    polymarket_price=polymarket_price,
                    deviation_pct=deviation,
                    btc_timestamp_ms=btc_data["timestamp_ms"],
                    polymarket_timestamp_ms=polymarket_data["timestamp_ms"],
                    latency_ms=0,
                    direction=direction,
                )

                if self.telegram_bot and deviation > 0.5:
                    self.telegram_bot.send_alert(
                        alert_type="high_deviation",
                        data={"deviation_pct": deviation, "market_id": market_id},
                    )

        return deviation

    def _get_price_direction(self, last_price, current_price):
        if last_price is None:
            return 0
        if current_price > last_price:
            return 1
        elif current_price < last_price:
            return -1
        return 0

    def _determine_direction(self, btc_direction, polymarket_direction):
        if btc_direction == 1 and polymarket_direction <= 0:
            return "btc_up_polymarket_lagged"
        elif btc_direction == -1 and polymarket_direction >= 0:
            return "btc_down_polymarket_lagged"
        return None

    def get_stats(self):
        return db.get_latency_stats()
