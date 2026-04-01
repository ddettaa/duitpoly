from src.db.sqlite_handler import db
from config.config import RISK_PER_TRADE_PCT, MAX_DAILY_LOSS_PCT
import time


class RiskManager:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_start_capital = initial_capital
        self.daily_loss_limit = initial_capital * (MAX_DAILY_LOSS_PCT / 100)
        self.risk_per_trade_limit = initial_capital * (RISK_PER_TRADE_PCT / 100)
        self.open_trades = []
        self.daily_trades = 0
        self.last_reset_date = self._get_today_date()
        self.total_trades = 0
        self.total_wins = 0
        self.total_losses = 0

    def _get_today_date(self):
        return time.strftime("%Y-%m-%d")

    def _reset_daily_if_needed(self):
        today = self._get_today_date()
        if today != self.last_reset_date:
            self.daily_start_capital = self.current_capital
            self.daily_loss_limit = self.current_capital * (MAX_DAILY_LOSS_PCT / 100)
            self.daily_trades = 0
            self.last_reset_date = today
            print(
                f"[RiskManager] New day - Reset daily tracking. Capital: ${self.current_capital:.2f}"
            )

    def can_trade(self):
        self._reset_daily_if_needed()

        daily_loss = self.daily_start_capital - self.current_capital
        if daily_loss >= self.daily_loss_limit:
            print(
                f"[RiskManager] Daily loss limit reached: ${daily_loss:.2f} >= ${self.daily_loss_limit:.2f}"
            )
            return False

        if len(self.open_trades) >= 5:
            print(f"[RiskManager] Max open trades reached: {len(self.open_trades)}")
            return False

        return True

    def calculate_position_size(self, signal_confidence, edge):
        if not self.can_trade():
            return 0

        base_size = self.risk_per_trade_limit

        confidence_multiplier = min(1.5, max(0.5, signal_confidence))
        edge_multiplier = min(2.0, max(0.5, abs(edge) / 0.05))

        position_size = base_size * confidence_multiplier * edge_multiplier

        position_size = min(position_size, self.current_capital * 0.1)

        return round(position_size, 2)

    def execute_trade(self, market_id, action, price, position_size, entry_btc_price):
        if not self.can_trade():
            return None

        trade = {
            "trade_id": f"trade_{int(time.time() * 1000)}",
            "market_id": market_id,
            "action": action,
            "entry_price": price,
            "position_size": position_size,
            "entry_btc_price": entry_btc_price,
            "entry_time": int(time.time() * 1000),
            "status": "open",
        }

        self.open_trades.append(trade)
        self.daily_trades += 1
        self.total_trades += 1

        db.insert_trade(trade)

        print(f"[RiskManager] Trade opened: {action} {position_size} @ {price}")
        return trade

    def close_trade(self, trade_id, exit_price, reason="signal"):
        trade = None
        for t in self.open_trades:
            if t["trade_id"] == trade_id:
                trade = t
                break

        if not trade:
            print(f"[RiskManager] Trade not found: {trade_id}")
            return None

        pnl = self._calculate_pnl(trade, exit_price)

        trade["exit_price"] = exit_price
        trade["exit_time"] = int(time.time() * 1000)
        trade["pnl"] = pnl
        trade["reason"] = reason
        trade["status"] = "closed"

        self.current_capital += pnl
        self.open_trades.remove(trade)

        if pnl > 0:
            self.total_wins += 1
        else:
            self.total_losses += 1

        db.update_trade(trade)

        print(f"[RiskManager] Trade closed: {trade_id} PnL: ${pnl:.2f}")
        return trade

    def _calculate_pnl(self, trade, exit_price):
        if "buy_yes" in trade["action"]:
            if exit_price > trade["entry_price"]:
                pnl = trade["position_size"] * (
                    (exit_price - trade["entry_price"]) / trade["entry_price"]
                )
            else:
                pnl = -trade["position_size"] * (
                    (trade["entry_price"] - exit_price) / trade["entry_price"]
                )
        elif "buy_no" in trade["action"]:
            no_entry = 1 - trade["entry_price"]
            no_exit = 1 - exit_price
            if no_exit > no_entry:
                pnl = trade["position_size"] * ((no_exit - no_entry) / no_entry)
            else:
                pnl = -trade["position_size"] * ((no_entry - no_exit) / no_exit)
        else:
            pnl = 0

        return round(pnl, 2)

    def get_metrics(self):
        self._reset_daily_if_needed()

        total_closed = self.total_wins + self.total_losses
        win_rate = (self.total_wins / total_closed * 100) if total_closed > 0 else 0

        return {
            "current_capital": round(self.current_capital, 2),
            "initial_capital": self.initial_capital,
            "total_pnl": round(self.current_capital - self.initial_capital, 2),
            "total_trades": self.total_trades,
            "open_trades": len(self.open_trades),
            "daily_trades": self.daily_trades,
            "win_rate": round(win_rate, 2),
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "daily_pnl": round(self.current_capital - self.daily_start_capital, 2),
            "can_trade": self.can_trade(),
        }

    def force_stop(self, reason="manual"):
        closed_trades = []
        for trade in self.open_trades[:]:
            trade_id = trade["trade_id"]
            self.close_trade(trade_id, trade["entry_price"], reason=reason)
            trade["forced"] = True
            closed_trades.append(trade)

        print(f"[RiskManager] Force stop executed. Closed {len(closed_trades)} trades.")
        return closed_trades
