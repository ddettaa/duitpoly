import itertools
import json
from datetime import datetime
from src.db.sqlite_handler import db
from config.config import LLM_EDGE_THRESHOLD, LLM_MIN_CONFIDENCE


class Backtester:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
        self.results = []

    def run_backtest(self, market_id, trades_data, signal_type="combined"):
        """
        Run backtest on historical data.

        trades_data: list of {'timestamp', 'price_yes', 'btc_price', 'llm_edge', 'llm_confidence', 'latency_signal'}
        """
        capital = self.initial_capital
        position = None
        trades = []
        stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl_list": [],
            "max_drawdown": 0,
            "peak_capital": capital,
        }

        for i, bar in enumerate(trades_data):
            if position is None:
                signal = self._check_entry_signal(bar, signal_type)
                if signal and signal["action"] != "no_trade":
                    position_size = self._calculate_size(capital, signal["confidence"])
                    if position_size > 0:
                        position = {
                            "entry_price": bar["price_yes"],
                            "entry_time": bar["timestamp"],
                            "size": position_size,
                            "action": signal["action"],
                            "entry_btc": bar["btc_price"],
                            "signal_type": signal_type,
                        }
            else:
                exit_signal = self._check_exit_signal(bar, position)
                if exit_signal["should_exit"]:
                    pnl = self._calculate_trade_pnl(position, bar["price_yes"])
                    capital += pnl
                    trades.append(
                        {
                            "entry_price": position["entry_price"],
                            "exit_price": bar["price_yes"],
                            "pnl": pnl,
                            "action": position["action"],
                            "hold_time": bar["timestamp"] - position["entry_time"],
                        }
                    )
                    stats["total_trades"] += 1
                    if pnl > 0:
                        stats["wins"] += 1
                    else:
                        stats["losses"] += 1
                    stats["pnl_list"].append(pnl)
                    position = None

                    if capital > stats["peak_capital"]:
                        stats["peak_capital"] = capital
                    drawdown = (stats["peak_capital"] - capital) / stats["peak_capital"]
                    if drawdown > stats["max_drawdown"]:
                        stats["max_drawdown"] = drawdown

        if position:
            final_pnl = self._calculate_trade_pnl(
                position, trades_data[-1]["price_yes"]
            )
            capital += final_pnl
            stats["total_trades"] += 1
            if final_pnl > 0:
                stats["wins"] += 1
            else:
                stats["losses"] += 1
            stats["pnl_list"].append(final_pnl)

        total_pnl = capital - self.initial_capital
        win_rate = (
            (stats["wins"] / stats["total_trades"] * 100)
            if stats["total_trades"] > 0
            else 0
        )
        avg_win = (
            sum(p for p in stats["pnl_list"] if p > 0) / stats["wins"]
            if stats["wins"] > 0
            else 0
        )
        avg_loss = (
            sum(p for p in stats["pnl_list"] if p < 0) / stats["losses"]
            if stats["losses"] > 0
            else 0
        )
        profit_factor = (
            abs(
                sum(p for p in stats["pnl_list"] if p > 0)
                / sum(p for p in stats["pnl_list"] if p < 0)
            )
            if stats["losses"] > 0
            else 0
        )

        result = {
            "market_id": market_id,
            "signal_type": signal_type,
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round((total_pnl / self.initial_capital) * 100, 2),
            "total_trades": stats["total_trades"],
            "win_rate": round(win_rate, 2),
            "wins": stats["wins"],
            "losses": stats["losses"],
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(stats["max_drawdown"] * 100, 2),
            "trades": trades[:10],
        }

        self.results.append(result)
        return result

    def _check_entry_signal(self, bar, signal_type):
        if signal_type == "llm_only":
            if (
                bar.get("llm_confidence", 0) >= LLM_MIN_CONFIDENCE
                and abs(bar.get("llm_edge", 0)) >= LLM_EDGE_THRESHOLD
            ):
                return {
                    "action": "buy_yes" if bar["llm_edge"] > 0 else "buy_no",
                    "confidence": bar["llm_confidence"],
                }
        elif signal_type == "latency_only":
            if bar.get("latency_signal"):
                return {"action": bar["latency_signal"], "confidence": 0.8}
        else:
            edge = bar.get("llm_edge", 0)
            has_latency = bar.get("latency_signal")
            if has_latency:
                return {"action": bar["latency_signal"], "confidence": 0.9}
            elif (
                abs(edge) >= LLM_EDGE_THRESHOLD
                and bar.get("llm_confidence", 0) >= LLM_MIN_CONFIDENCE
            ):
                return {
                    "action": "buy_yes" if edge > 0 else "buy_no",
                    "confidence": bar["llm_confidence"],
                }
        return {"action": "no_trade", "confidence": 0}

    def _check_exit_signal(self, bar, position):
        price_change = (
            abs(bar["price_yes"] - position["entry_price"]) / position["entry_price"]
        )
        if price_change > 0.1:
            return {"should_exit": True, "reason": "price_move_10pct"}
        if bar["timestamp"] - position["entry_time"] > 3600000:
            return {"should_exit": True, "reason": "timeout_1h"}
        return {"should_exit": False}

    def _calculate_size(self, capital, confidence):
        base_size = capital * 0.02
        multiplier = min(1.5, max(0.5, confidence))
        return round(base_size * multiplier, 2)

    def _calculate_trade_pnl(self, position, exit_price):
        if "buy_yes" in position["action"]:
            pnl = position["size"] * (
                (exit_price - position["entry_price"]) / position["entry_price"]
            )
        else:
            no_entry = 1 - position["entry_price"]
            no_exit = 1 - exit_price
            pnl = position["size"] * ((no_exit - no_entry) / no_entry)
        return round(pnl, 2)

    def compare_strategies(self, market_id, trades_data):
        strategies = ["combined", "llm_only", "latency_only"]
        results = []

        for strategy in strategies:
            result = self.run_backtest(market_id, trades_data, strategy)
            results.append(result)

        best = max(results, key=lambda x: x["total_pnl"])
        return {
            "results": results,
            "best_strategy": best["signal_type"],
            "recommendation": best,
        }

    def get_summary(self):
        if not self.results:
            return {}

        total_pnl = sum(r["total_pnl"] for r in self.results)
        avg_win_rate = sum(r["win_rate"] for r in self.results) / len(self.results)
        avg_trades = sum(r["total_trades"] for r in self.results) / len(self.results)
        best_result = max(self.results, key=lambda x: x["total_pnl"])
        worst_result = min(self.results, key=lambda x: x["total_pnl"])

        return {
            "markets_tested": len(self.results),
            "total_pnl_all_markets": round(total_pnl, 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "avg_trades_per_market": round(avg_trades, 1),
            "best_market": best_result["market_id"],
            "best_pnl": best_result["total_pnl"],
            "worst_market": worst_result["market_id"],
            "worst_pnl": worst_result["total_pnl"],
            "results": self.results,
        }

    def save_report(self, filename="backtest_report.json"):
        report = self.get_summary()
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[Backtester] Report saved to {filename}")
        return report
