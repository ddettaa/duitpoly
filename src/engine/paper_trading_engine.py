import time
import threading
from datetime import datetime
from src.db.sqlite_handler import db
from src.engine.signal_engine import SignalEngine
from src.engine.risk_manager import RiskManager
from src.llm.minimax_client import MiniMaxClient
from config.config import LLM_ANALYSIS_INTERVAL_MINUTES


class PaperTradingEngine:
    def __init__(
        self,
        initial_capital=10000,
        telegram_bot=None,
        minimax_client=None,
        signal_engine=None,
    ):
        self.mode = "PAPER"
        self.telegram_bot = telegram_bot
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        self.signal_engine = signal_engine or SignalEngine(telegram_bot=telegram_bot)
        self.llm_client = minimax_client
        self.running = False
        self.start_time = time.time()
        self.trade_check_interval = 5
        self.last_analysis_time = 0

    def start(self):
        print("\n" + "=" * 50)
        print("PAPER TRADING ENGINE - FREE MODE")
        print("=" * 50)
        print(f"[Paper] Starting with ${self.risk_manager.initial_capital:.2f}")
        print(f"[Paper] Mode: SIMULATED (no real orders)")
        print("=" * 50)

        self.running = True

        threading.Thread(target=self._trade_monitor_loop, daemon=True).start()
        threading.Thread(target=self._llm_analysis_loop, daemon=True).start()
        threading.Thread(target=self._status_report_loop, daemon=True).start()

        if self.telegram_bot:
            self.telegram_bot.send_message(
                f"[PAPER MODE STARTED]\n"
                f"Initial Capital: ${self.risk_manager.initial_capital:.2f}\n"
                f"Mode: Simulated Trading\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        return self

    def stop(self):
        print("[Paper] Stopping paper trading engine...")
        self.running = False

        metrics = self.risk_manager.get_metrics()
        if self.telegram_bot:
            self.telegram_bot.send_message(
                f"[PAPER MODE STOPPED]\n"
                f"Final Capital: ${metrics['current_capital']:.2f}\n"
                f"Total P&L: ${metrics['total_pnl']:.2f}\n"
                f"Win Rate: {metrics['win_rate']:.1f}%\n"
                f"Total Trades: {metrics['total_trades']}"
            )

    def _trade_monitor_loop(self):
        print("[Paper] Trade monitor started")
        while self.running:
            try:
                open_trades = db.get_open_trades()

                for trade in open_trades:
                    market_id = trade["market_id"]
                    entry_price = trade["entry_price"]
                    current_price = self._get_current_price(market_id)

                    if current_price and current_price > 0:
                        should_exit, reason = self._check_exit_conditions(
                            trade, current_price
                        )

                        if should_exit:
                            closed_trade = self.risk_manager.close_trade(
                                trade_id=trade["trade_id"],
                                exit_price=current_price,
                                reason=reason,
                            )

                            if self.telegram_bot and closed_trade:
                                pnl = closed_trade.get("pnl", 0)
                                emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
                                self.telegram_bot.send_message(
                                    f"{emoji} *[PAPER TRADE CLOSED]*\n\n"
                                    f"`{market_id}`\n"
                                    f"Reason: `{reason}`\n"
                                    f"Entry: `{entry_price:.4f}`\n"
                                    f"Exit: `{current_price:.4f}`\n"
                                    f"*P&L: `${pnl:.2f}`*"
                                )

            except Exception as e:
                print(f"[Paper] Monitor error: {e}")

            time.sleep(self.trade_check_interval)

    def _llm_analysis_loop(self):
        print("[Paper] LLM analysis loop started")
        while self.running:
            try:
                current_time = time.time()
                if (
                    current_time - self.last_analysis_time
                    >= LLM_ANALYSIS_INTERVAL_MINUTES * 60
                ):
                    self.last_analysis_time = current_time

                    if self.llm_client:
                        markets = db.get_pending_markets_for_analysis(limit=5)
                        for market_id, question, price_yes in markets:
                            btc_price, _ = db.get_latest_btc_price()

                            result = self.llm_client.analyze_market(
                                market_question=question,
                                market_price_yes=price_yes,
                                btc_price=btc_price if btc_price > 0 else None,
                            )

                            if result:
                                result["market_id"] = market_id
                                db.insert_llm_analysis(
                                    market_id=market_id,
                                    market_question=question,
                                    market_price_yes=price_yes,
                                    predicted_probability=result[
                                        "predicted_probability"
                                    ],
                                    confidence=result["confidence"],
                                    llm_reasoning=result["reasoning"],
                                    edge=result["edge"],
                                    recommended_action=result["recommended_action"],
                                )

                                self.llm_client.check_and_alert_opportunity(result)

            except Exception as e:
                print(f"[Paper] LLM analysis error: {e}")

            time.sleep(30)

    def _status_report_loop(self):
        print("[Paper] Status report loop started")
        while self.running:
            try:
                time.sleep(3600)
                if self.telegram_bot:
                    metrics = self.risk_manager.get_metrics()
                    stats = db.get_signal_stats()
                    self.telegram_bot.send_message(
                        f"[PAPER STATUS UPDATE]\n"
                        f"Capital: ${metrics['current_capital']:.2f}\n"
                        f"P&L: ${metrics['total_pnl']:.2f}\n"
                        f"Trades: {metrics['total_trades']} (W: {metrics['win_rate']:.0f}%)\n"
                        f"Signals: {stats['total']} (High: {stats['high_priority']})"
                    )
            except Exception as e:
                print(f"[Paper] Status report error: {e}")

    def _get_current_price(self, market_id):
        try:
            markets = db.get_recent_markets(limit=1)
            for m in markets:
                if m[0] == market_id:
                    return m[2]
            return None
        except:
            return None

    def _check_exit_conditions(self, trade, current_price):
        entry_price = trade["entry_price"]
        action = trade["action"]

        if "buy_yes" in action:
            pnl_pct = (current_price - entry_price) / entry_price
            if pnl_pct >= 0.1:
                return True, "take_profit_10pct"
            if pnl_pct <= -0.05:
                return True, "stop_loss_5pct"
        else:
            no_entry = 1 - entry_price
            no_current = 1 - current_price
            pnl_pct = (no_current - no_entry) / no_entry
            if pnl_pct >= 0.1:
                return True, "take_profit_10pct"
            if pnl_pct <= -0.05:
                return True, "stop_loss_5pct"

        hold_time = (time.time() * 1000) - trade["entry_time"]
        if hold_time > 3600000:
            return True, "timeout_1h"

        return False, None

    def get_metrics(self):
        return self.risk_manager.get_metrics()

    def execute_signal(self, signal):
        if signal["action"] == "no_trade":
            return None
        if signal["priority"] not in ("HIGH", "MEDIUM"):
            return None

        market_id = signal["market_id"]
        action = signal["action"]
        confidence = 0.8

        if len(signal.get("signals", [])) > 0:
            for s in signal["signals"]:
                if s.get("type") == "llm":
                    confidence = s.get("confidence", 0.8)
                    break

        position_size = self.risk_manager.calculate_position_size(
            signal_confidence=confidence, edge=signal.get("edge", 0.05)
        )

        if position_size <= 0:
            return None

        price = signal.get("polymarket_price", 0)
        btc_price = signal.get("btc_price", 0)

        trade = self.risk_manager.execute_trade(
            market_id=market_id,
            action=action,
            price=price,
            position_size=position_size,
            entry_btc_price=btc_price,
        )

        if trade and self.telegram_bot:
            self.telegram_bot.send_message(
                f"🟢 *[PAPER TRADE OPENED]*\n\n"
                f"`{market_id}`\n"
                f"Action: *{action.upper()}*\n"
                f"Size: `${position_size:.2f}`\n"
                f"Entry Price: `{price:.4f}`\n"
                f"BTC: `${btc_price:.0f}`"
            )

        return trade
