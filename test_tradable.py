import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from src.data_collector.polymarket_client import PolymarketClient
from src.engine.signal_engine import SignalEngine

pm = PolymarketClient()
markets = pm.get_crypto_markets(limit=20)

print("=== CHECK TRADABLE MARKETS ===")
tradable = [m for m in markets if 0.2 < m["price_yes"] < 0.8]
print("Tradable:", len(tradable))

for m in tradable:
    print(f"\n{m['question']}")
    print(f"  Price: {m['price_yes']:.4f}")

# Simulate BTC history with some change
btc_history = [
    {"price": 68500, "time": time.time() - 300},
    {"price": 68700, "time": time.time() - 200},
    {"price": 68900, "time": time.time() - 100},
    {"price": 69100, "time": time.time()},
]

print("\n=== SIMULATED MOMENTUM ===")
print("BTC: 68500 -> 69100 = +0.88%")

signal_engine = SignalEngine(llm_client=None, latency_detector=None)
signal_engine._btc_history = btc_history

for m in tradable:
    signal = signal_engine.check_opportunity(
        btc_data={"btc_price": 69100, "timestamp_ms": int(time.time() * 1000)},
        polymarket_data={
            "market_id": m["id"],
            "market_question": m["question"],
            "price_yes": m["price_yes"],
            "timestamp_ms": int(time.time() * 1000),
        },
    )

    print(f"\n{m['question'][:50]}...")
    print(f"  Price: {m['price_yes']:.4f}")
    print(f"  Signal: {signal['priority']} / {signal['action']}")
    print(f"  Signals: {len(signal.get('signals', []))}")
    for s in signal.get("signals", []):
        print(f"    - {s}")
