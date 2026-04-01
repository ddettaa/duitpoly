import sqlite3
import os
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


db = SQLiteHandler()
