import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from src.data_collector.polymarket_client import PolymarketClient

pm = PolymarketClient()
markets = pm.get_crypto_markets(limit=50)

print("=== MID-RANGE MARKETS (0.2-0.8) ===")
mid = [m for m in markets if 0.2 < m["price_yes"] < 0.8]
print("Found", len(mid), "mid-range markets out of", len(markets))

for m in mid[:15]:
    q = m["question"]
    p = m["price_yes"]
    print(f"  {q[:60]}... @ {p:.4f}")
