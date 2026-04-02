import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

print("=== SYSTEM CHECK ===")

from src.db.sqlite_handler import SQLiteHandler

db = SQLiteHandler()

stats = db.get_latency_stats()
print("Latency events:", stats.get("count", 0))

data_points = db.get_data_points_count()
print("Data points:", data_points)

signal_stats = db.get_signal_stats()
print("Signal stats:", signal_stats)

btc_price, ts = db.get_latest_btc_price()
print("Latest BTC:", btc_price)

print("=== SYSTEM RUNNING ===")
