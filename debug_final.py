import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

print("=== SIGNAL DEBUG ===\n")

from src.data_collector.polymarket_client import PolymarketClient
from src.data_collector.btc_chainlink import BTCCollector
from src.engine.signal_engine import SignalEngine

# Init
pm = PolymarketClient()
markets = pm.get_crypto_markets(limit=5)
print(f"Markets: {len(markets)}\n")

btc = BTCCollector(interval_seconds=5)
btc.start()
time.sleep(3)
btc_price, btc_ts = btc.get_last_price()
print(f"BTC Price: {btc_price}")
print(f"BTC History: {len(btc.price_history)} points")
btc.stop()

# Create signal engine
signal_engine = SignalEngine(llm_client=None, latency_detector=None)
signal_engine._btc_history = btc.price_history[-5:] if btc.price_history else []

print(f"Signal engine BTC history: {len(signal_engine._btc_history)} points\n")

# Test signal
for m in markets[:3]:
    signal = signal_engine.check_opportunity(
        btc_data={"btc_price": btc_price, "timestamp_ms": int(time.time() * 1000)},
        polymarket_data={
            "market_id": m["id"],
            "market_question": m["question"],
            "price_yes": m["price_yes"],
            "timestamp_ms": int(time.time() * 1000),
        },
    )

    print(f"Market: {m['question'][:50]}...")
    print(f"  Price: {m['price_yes']:.4f}")
    print(f"  Signal: {signal['priority']} / {signal['action']}")
    print(f"  Signals count: {len(signal.get('signals', []))}")
    for s in signal.get("signals", []):
        print(f"    - {s}")
    print()
