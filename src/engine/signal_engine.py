from src.db.sqlite_handler import db
from src.llm.minimax_client import MiniMaxClient
from config.config import LLM_MIN_CONFIDENCE, LLM_EDGE_THRESHOLD


class SignalEngine:
    def __init__(self, llm_client=None, latency_detector=None, telegram_bot=None):
        self.llm_client = llm_client
        self.latency_detector = latency_detector
        self.telegram_bot = telegram_bot
        self.signal_history = []

    def check_opportunity(self, btc_data, polymarket_data, llm_result=None):
        signals = []
        priority = "LOW"
        primary_signal = None
        action = "no_trade"

        if self.latency_detector:
            latency_signal = self._check_latency_signal(btc_data, polymarket_data)
            if latency_signal:
                signals.append(latency_signal)
                priority = "HIGH"
                primary_signal = latency_signal

        if llm_result and llm_result.get("recommended_action") != "no_trade":
            llm_signal = self._check_llm_signal(llm_result)
            if llm_signal:
                signals.append(llm_signal)
                if priority != "HIGH":
                    priority = "MEDIUM"
                    primary_signal = llm_signal

        if len(signals) >= 2:
            if signals[0]["direction"] == signals[1]["direction"]:
                priority = "HIGH"
                action = signals[0]["action"]
            elif primary_signal:
                action = primary_signal["action"]
        elif primary_signal:
            action = primary_signal["action"]

        combined_signal = {
            "priority": priority,
            "signals": signals,
            "action": action,
            "btc_price": btc_data.get("btc_price"),
            "market_id": polymarket_data.get("market_id"),
            "polymarket_price": polymarket_data.get("price_yes"),
        }

        self._log_signal(combined_signal)

        if priority == "HIGH" and self.telegram_bot:
            self._send_signal_alert(combined_signal)

        return combined_signal

    def _check_latency_signal(self, btc_data, polymarket_data):
        if not self.latency_detector:
            return None

        result = self.latency_detector.check_deviation(btc_data, polymarket_data)

        if result and result > 0.003:
            direction = None
            action = None

            if "btc_up_polymarket_lagged" in str(result):
                direction = "up"
                action = "buy_yes"
            elif "btc_down_polymarket_lagged" in str(result):
                direction = "down"
                action = "buy_no"

            if direction:
                return {
                    "type": "latency",
                    "direction": direction,
                    "action": action,
                    "confidence": 0.8,
                    "edge": result / 100,
                }

        return None

    def _check_llm_signal(self, llm_result):
        if not llm_result:
            return None

        edge = llm_result.get("edge", 0)
        confidence = llm_result.get("confidence", 0)
        action = llm_result.get("recommended_action", "no_trade")

        if abs(edge) >= LLM_EDGE_THRESHOLD and confidence >= LLM_MIN_CONFIDENCE:
            return {
                "type": "llm",
                "direction": "up" if edge > 0 else "down",
                "action": action,
                "confidence": confidence,
                "edge": edge,
                "reasoning": llm_result.get("reasoning", ""),
            }

        return None

    def _log_signal(self, signal):
        self.signal_history.append(signal)
        if len(self.signal_history) > 1000:
            self.signal_history = self.signal_history[-500:]

    def _send_signal_alert(self, signal):
        if not self.telegram_bot:
            return

        priority_emoji = "🔴" if signal["priority"] == "HIGH" else "🟡"
        action_emoji = (
            "🟢"
            if signal["action"] == "buy_yes"
            else "🔴"
            if "buy_no" in str(signal["action"])
            else "⚪"
        )

        message = (
            f"{priority_emoji} *SIGNAL: {signal['priority']} PRIORITY*\n\n"
            f"{action_emoji} Action: *{signal['action']}*\n"
            f"Market: `{signal['market_id']}`\n"
            f"Price: {signal['polymarket_price']}\n"
            f"BTC: ${signal['btc_price']}\n"
            f"Signals: {len(signal['signals'])}"
        )

        self.telegram_bot.send_message(message)

    def get_signal_stats(self):
        if not self.signal_history:
            return {
                "total": 0,
                "high_priority": 0,
                "buy_yes": 0,
                "buy_no": 0,
                "no_trade": 0,
            }

        stats = {
            "total": len(self.signal_history),
            "high_priority": sum(
                1 for s in self.signal_history if s["priority"] == "HIGH"
            ),
            "medium_priority": sum(
                1 for s in self.signal_history if s["priority"] == "MEDIUM"
            ),
            "low_priority": sum(
                1 for s in self.signal_history if s["priority"] == "LOW"
            ),
            "buy_yes": sum(
                1 for s in self.signal_history if "buy_yes" in str(s["action"])
            ),
            "buy_no": sum(
                1 for s in self.signal_history if "buy_no" in str(s["action"])
            ),
            "no_trade": sum(
                1 for s in self.signal_history if s["action"] == "no_trade"
            ),
        }

        return stats
