import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from src.engine.signal_engine import SignalEngine

# Simulate BTC going up
btc_history = [
    {"price": 68500, "time": time.time() - 300},
    {"price": 68700, "time": time.time() - 200},
    {"price": 68900, "time": time.time() - 100},
    {"price": 69100, "time": time.time()},
]

signal_engine = SignalEngine(llm_client=None, latency_detector=None)
signal_engine._btc_history = btc_history

market = {
    "id": "test_market",
    "question": "Will Bitcoin reach $72,000 March 30-April 5?",
    "price_yes": 0.3150,
}

print("BTC: 68500 -> 69100 (+0.88%)")
print("Market:", market["question"])
print("Price:", market["price_yes"])

signal = signal_engine.check_opportunity(
    btc_data={"btc_price": 69100, "timestamp_ms": int(time.time() * 1000)},
    polymarket_data=market,
)

print("\nResult:")
print("  Priority:", signal["priority"])
print("  Action:", signal["action"])
print("  Signals:", len(signal.get("signals", [])))
for s in signal.get("signals", []):
    print("   ", s)

if signal["priority"] == "HIGH":
    print("\n>>> WOULD EXECUTE TRADE!")
