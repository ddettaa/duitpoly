import time
import threading
from datetime import datetime
from src.db.sqlite_handler import db
from src.engine.risk_manager import RiskManager
from src.engine.signal_engine import SignalEngine
from src.execution.polymarket_executor import PolymarketExecutor
from src.llm.minimax_client import MiniMaxClient


class ProTradingEngine:
    MODE = "PRO"

    def __init__(
        self,
        initial_capital=10,
        telegram_bot=None,
        minimax_client=None,
        api_key=None,
        api_secret=None,
    ):
        self.telegram_bot = telegram_bot
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        self.signal_engine = SignalEngine(telegram_bot=telegram_bot)
        self.executor = PolymarketExecutor(
            api_key=api_key, api_secret=api_secret, telegram_bot=telegram_bot
        )
        self.llm_client = minimax_client
        self.running = False
        self.start_time = time.time()
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3

    def start(self):
        print("\n" + "=" * 50)
        print("PRO TRADING ENGINE - LIVE MODE")
        print("=" * 50)
        print(f"[PRO] WARNING: Real money at stake!")
        print(f"[PRO] Starting with ${self.risk_manager.initial_capital:.2f}")
        print(f"[PRO] Mode: LIVE TRADING")
        print("=" * 50)

        self.running = True

        balance = self.executor.get_balance()
        print(f"[PRO] Connected wallet balance: ${balance:.2f}")

        if self.telegram_bot:
            self.telegram_bot.send_message(
                f"[PRO MODE STARTED]\n"
                f"⚠️ LIVE TRADING - REAL MONEY\n"
                f"Initial Capital: ${self.risk_manager.initial_capital:.2f}\n"
                f"Wallet Balance: ${balance:.2f}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

        threading.Thread(target=self._trade_execution_loop, daemon=True).start()
        threading.Thread(target=self._monitor_open_positions, daemon=True).start()
        threading.Thread(target=self._health_monitor, daemon=True).start()

        return self

    def stop(self):
        print("[PRO] Stopping pro trading engine...")
        self.running = False

        closed = self.risk_manager.force_stop(reason="manual_stop")

        if self.telegram_bot:
            metrics = self.risk_manager.get_metrics()
            self.telegram_bot.send_message(
                f"[PRO MODE STOPPED]\n"
                f"Final Capital: ${metrics['current_capital']:.2f}\n"
                f"Total P&L: ${metrics['total_pnl']:.2f}\n"
                f"Win Rate: {metrics['win_rate']:.1f}%\n"
                f"Total Trades: {metrics['total_trades']}\n"
                f"Closed Trades: {len(closed)}"
            )

    def _trade_execution_loop(self):
        print("[PRO] Trade execution loop started")
        while self.running:
            try:
                if not self.risk_manager.can_trade():
                    time.sleep(10)
                    continue

                signals = self.signal_engine.signal_history[-10:]
                high_priority_signals = [
                    s
                    for s in signals
                    if s["priority"] == "HIGH" and s["action"] != "no_trade"
                ]

                for signal in high_priority_signals:
                    if not self.running:
                        break

                    if not self.risk_manager.can_trade():
                        break

                    already_traded = any(
                        t["market_id"] == signal["market_id"] and t["status"] == "open"
                        for t in db.get_open_trades()
                    )
                    if already_traded:
                        continue

                    self._execute_pro_trade(signal)

            except Exception as e:
                print(f"[PRO] Execution error: {e}")

            time.sleep(5)

    def _execute_pro_trade(self, signal):
        market_id = signal["market_id"]
        action = signal["action"]
        price = signal.get("polymarket_price", 0)

        confidence = 0.8
        for s in signal.get("signals", []):
            if s.get("type") == "llm":
                confidence = s.get("confidence", 0.8)
                break

        edge = 0.05
        for s in signal.get("signals", []):
            if "edge" in s:
                edge = abs(s["edge"])
                break

        position_size = self.risk_manager.calculate_position_size(confidence, edge)

        if position_size <= 0:
            print(f"[PRO] Position size too small, skipping")
            return

        side = "yes" if "buy_yes" in action else "no"

        order_result = self.executor.place_order(
            market_id=market_id, side=side, size=position_size, price=price
        )

        if order_result:
            trade = self.risk_manager.execute_trade(
                market_id=market_id,
                action=action,
                price=price,
                position_size=position_size,
                entry_btc_price=signal.get("btc_price", 0),
            )

            if trade:
                trade["order_id"] = order_result.get("order_id")
                db.update_trade(trade)

                if self.telegram_bot:
                    self.telegram_bot.send_message(
                        f"[PRO TRADE EXECUTED]\n"
                        f"⚠️ LIVE ORDER\n"
                        f"Market: {market_id}\n"
                        f"Action: {action}\n"
                        f"Size: ${position_size:.2f}\n"
                        f"Price: {price}\n"
                        f"Order ID: {order_result.get('order_id')}"
                    )
        else:
            print(f"[PRO] Order failed for {market_id}")

    def _monitor_open_positions(self):
        print("[PRO] Position monitor started")
        while self.running:
            try:
                open_trades = db.get_open_trades()

                for trade in open_trades:
                    market_id = trade["market_id"]
                    entry_price = trade["entry_price"]
                    action = trade["action"]

                    current_price = self._get_current_price(market_id)
                    if not current_price:
                        continue

                    should_exit, reason = self._check_exit_conditions(
                        trade, current_price
                    )

                    if should_exit:
                        side = "yes" if "buy_yes" in action else "no"
                        cancel_result = self.executor.cancel_order(
                            trade.get("order_id", "")
                        )

                        closed_trade = self.risk_manager.close_trade(
                            trade_id=trade["trade_id"],
                            exit_price=current_price,
                            reason=reason,
                        )

                        if closed_trade:
                            pnl = closed_trade.get("pnl", 0)
                            if pnl < 0:
                                self.consecutive_losses += 1
                            else:
                                self.consecutive_losses = 0

                            if self.telegram_bot:
                                emoji = "🔴" if pnl < 0 else "🟢"
                                self.telegram_bot.send_message(
                                    f"{emoji} [PRO TRADE CLOSED]\n"
                                    f"Market: {market_id}\n"
                                    f"Reason: {reason}\n"
                                    f"Entry: {entry_price}\n"
                                    f"Exit: {current_price}\n"
                                    f"P&L: ${pnl:.2f}"
                                )

                            if self.consecutive_losses >= self.max_consecutive_losses:
                                print(f"[PRO] Max consecutive losses reached - pausing")
                                if self.telegram_bot:
                                    self.telegram_bot.send_message(
                                        f"[PRO] WARNING: {self.consecutive_losses} consecutive losses\n"
                                        f"Pausing trading for review"
                                    )
                                time.sleep(300)
                                self.consecutive_losses = 0

            except Exception as e:
                print(f"[PRO] Monitor error: {e}")

            time.sleep(5)

    def _health_monitor(self):
        print("[PRO] Health monitor started")
        while self.running:
            try:
                time.sleep(300)

                if self.telegram_bot:
                    metrics = self.risk_manager.get_metrics()
                    balance = self.executor.get_balance()

                    self.telegram_bot.send_message(
                        f"[PRO HEALTH CHECK]\n"
                        f"Capital: ${metrics['current_capital']:.2f}\n"
                        f"Wallet: ${balance:.2f}\n"
                        f"P&L: ${metrics['total_pnl']:.2f}\n"
                        f"Trades: {metrics['total_trades']}\n"
                        f"Win Rate: {metrics['win_rate']:.1f}%\n"
                        f"Consecutive Losses: {self.consecutive_losses}"
                    )

            except Exception as e:
                print(f"[PRO] Health monitor error: {e}")

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
            if pnl_pct >= 0.08:
                return True, "take_profit_8pct"
            if pnl_pct <= -0.03:
                return True, "stop_loss_3pct"
        else:
            no_entry = 1 - entry_price
            no_current = 1 - current_price
            pnl_pct = (no_current - no_entry) / no_entry
            if pnl_pct >= 0.08:
                return True, "take_profit_8pct"
            if pnl_pct <= -0.03:
                return True, "stop_loss_3pct"

        hold_time = (time.time() * 1000) - trade["entry_time"]
        if hold_time > 1800000:
            return True, "timeout_30min"

        return False, None

    def get_metrics(self):
        metrics = self.risk_manager.get_metrics()
        metrics["wallet_balance"] = self.executor.get_balance()
        metrics["consecutive_losses"] = self.consecutive_losses
        return metrics
