import sqlite3
import os
import json
from datetime import datetime
from config.config import DB_PATH


class SQLiteHandler:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._ensure_db_dir()
        self._init_tables()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                market_question TEXT,
                price_yes REAL NOT NULL,
                price_no REAL NOT NULL,
                btc_price REAL NOT NULL,
                volume REAL,
                liquidity REAL,
                timestamp_ms INTEGER NOT NULL,
                source TEXT DEFAULT 'polymarket',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS btc_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                btc_price REAL NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS latency_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                btc_price REAL NOT NULL,
                polymarket_price REAL NOT NULL,
                deviation_pct REAL NOT NULL,
                btc_timestamp_ms INTEGER NOT NULL,
                polymarket_timestamp_ms INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                direction TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                market_question TEXT NOT NULL,
                market_price_yes REAL NOT NULL,
                predicted_probability REAL,
                confidence REAL,
                llm_reasoning TEXT,
                edge REAL,
                recommended_action TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uptime_seconds INTEGER,
                data_points_collected INTEGER,
                latency_events_count INTEGER,
                status TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id TEXT UNIQUE NOT NULL,
                market_id TEXT NOT NULL,
                action TEXT NOT NULL,
                entry_price REAL NOT NULL,
                position_size REAL NOT NULL,
                entry_btc_price REAL,
                entry_time INTEGER NOT NULL,
                exit_price REAL,
                exit_time INTEGER,
                pnl REAL,
                reason TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL,
                edge REAL,
                btc_price REAL,
                polymarket_price REAL,
                signal_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def insert_price_snapshot(
        self,
        market_id,
        market_question,
        price_yes,
        price_no,
        btc_price,
        volume,
        liquidity,
        timestamp_ms,
        source="polymarket",
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO price_snapshots 
            (market_id, market_question, price_yes, price_no, btc_price, volume, liquidity, timestamp_ms, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                market_question,
                price_yes,
                price_no,
                btc_price,
                volume,
                liquidity,
                timestamp_ms,
                source,
            ),
        )
        conn.commit()
        conn.close()

    def insert_btc_feed(self, btc_price, timestamp_ms):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO btc_feed (btc_price, timestamp_ms)
            VALUES (?, ?)
        """,
            (btc_price, timestamp_ms),
        )
        conn.commit()
        conn.close()

    def insert_latency_event(
        self,
        market_id,
        btc_price,
        polymarket_price,
        deviation_pct,
        btc_timestamp_ms,
        polymarket_timestamp_ms,
        latency_ms,
        direction,
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO latency_events 
            (market_id, btc_price, polymarket_price, deviation_pct, btc_timestamp_ms, polymarket_timestamp_ms, latency_ms, direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                btc_price,
                polymarket_price,
                deviation_pct,
                btc_timestamp_ms,
                polymarket_timestamp_ms,
                latency_ms,
                direction,
            ),
        )
        conn.commit()
        conn.close()

    def insert_llm_analysis(
        self,
        market_id,
        market_question,
        market_price_yes,
        predicted_probability,
        confidence,
        llm_reasoning,
        edge,
        recommended_action,
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO llm_analysis 
            (market_id, market_question, market_price_yes, predicted_probability, confidence, llm_reasoning, edge, recommended_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                market_question,
                market_price_yes,
                predicted_probability,
                confidence,
                llm_reasoning,
                edge,
                recommended_action,
            ),
        )
        conn.commit()
        conn.close()

    def insert_system_health(
        self, uptime_seconds, data_points_collected, latency_events_count, status
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO system_health 
            (uptime_seconds, data_points_collected, latency_events_count, status)
            VALUES (?, ?, ?, ?)
        """,
            (uptime_seconds, data_points_collected, latency_events_count, status),
        )
        conn.commit()
        conn.close()

    def insert_trade(self, trade):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO trades 
            (trade_id, market_id, action, entry_price, position_size, entry_btc_price, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                trade["trade_id"],
                trade["market_id"],
                trade["action"],
                trade["entry_price"],
                trade["position_size"],
                trade.get("entry_btc_price", 0),
                trade["entry_time"],
                trade.get("status", "open"),
            ),
        )
        conn.commit()
        conn.close()

    def update_trade(self, trade):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE trades SET
                exit_price = ?,
                exit_time = ?,
                pnl = ?,
                reason = ?,
                status = ?
            WHERE trade_id = ?
        """,
            (
                trade.get("exit_price"),
                trade.get("exit_time"),
                trade.get("pnl"),
                trade.get("reason"),
                trade.get("status", "closed"),
                trade["trade_id"],
            ),
        )
        conn.commit()
        conn.close()

    def insert_signal(
        self,
        market_id,
        signal_type,
        priority,
        action,
        confidence,
        edge,
        btc_price,
        polymarket_price,
        signal_data=None,
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO signals 
            (market_id, signal_type, priority, action, confidence, edge, btc_price, polymarket_price, signal_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                market_id,
                signal_type,
                priority,
                action,
                confidence,
                edge,
                btc_price,
                polymarket_price,
                json.dumps(signal_data) if signal_data else None,
            ),
        )
        conn.commit()
        conn.close()

    def get_latency_stats(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                AVG(latency_ms) as avg_ms,
                MAX(latency_ms) as max_ms,
                AVG(deviation_pct) as avg_deviation,
                MAX(deviation_pct) as max_deviation
            FROM latency_events
        """)
        result = cursor.fetchone()
        conn.close()
        return {
            "count": result[0] or 0,
            "avg_ms": round(result[1], 2) if result[1] else 0,
            "max_ms": result[2] or 0,
            "avg_deviation": round(result[3], 4) if result[3] else 0,
            "max_deviation": round(result[4], 4) if result[4] else 0,
        }

    def get_data_points_count(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM price_snapshots")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def get_latency_events_today(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM latency_events
            WHERE DATE(created_at) = DATE('now')
        """)
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def get_recent_markets(self, limit=20):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT market_id, market_question, price_yes, created_at
            FROM price_snapshots
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )
        results = cursor.fetchall()
        conn.close()
        return results

    def get_latest_btc_price(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT btc_price, timestamp_ms FROM btc_feed
            ORDER BY timestamp_ms DESC LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        return result if result else (0, 0)

    def get_pending_markets_for_analysis(self, limit=10):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT p.market_id, p.market_question, p.price_yes
            FROM price_snapshots p
            LEFT JOIN llm_analysis l ON p.market_id = l.market_id
            WHERE l.market_id IS NULL
            ORDER BY p.created_at DESC
            LIMIT ?
        """,
            (limit,),
        )
        results = cursor.fetchall()
        conn.close()
        return results

    def get_open_trades(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trade_id, market_id, action, entry_price, position_size, entry_btc_price, entry_time
            FROM trades
            WHERE status = 'open'
        """)
        results = cursor.fetchall()
        conn.close()
        trades = []
        for r in results:
            trades.append(
                {
                    "trade_id": r[0],
                    "market_id": r[1],
                    "action": r[2],
                    "entry_price": r[3],
                    "position_size": r[4],
                    "entry_btc_price": r[5],
                    "entry_time": r[6],
                }
            )
        return trades

    def get_trade_stats(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM trades
            WHERE status = 'closed'
        """)
        result = cursor.fetchone()
        conn.close()
        return {
            "total": result[0] or 0,
            "wins": result[1] or 0,
            "losses": result[2] or 0,
            "total_pnl": round(result[3], 2) if result[3] else 0,
            "avg_pnl": round(result[4], 2) if result[4] else 0,
        }

    def get_signal_stats(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN priority = 'HIGH' THEN 1 ELSE 0 END) as high_priority,
                SUM(CASE WHEN action LIKE 'buy_yes' THEN 1 ELSE 0 END) as buy_yes,
                SUM(CASE WHEN action LIKE 'buy_no' THEN 1 ELSE 0 END) as buy_no
            FROM signals
        """)
        result = cursor.fetchone()
        conn.close()
        return {
            "total": result[0] or 0,
            "high_priority": result[1] or 0,
            "buy_yes": result[2] or 0,
            "buy_no": result[3] or 0,
        }

    def get_historical_prices(self, market_id, limit=100):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT price_yes, btc_price, timestamp_ms
            FROM price_snapshots
            WHERE market_id = ?
            ORDER BY timestamp_ms DESC
            LIMIT ?
        """,
            (market_id, limit),
        )
        results = cursor.fetchall()
        conn.close()
        return results


db = SQLiteHandler()
