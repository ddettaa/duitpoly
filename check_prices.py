import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from src.data_collector.polymarket_client import PolymarketClient

pm = PolymarketClient()
markets = pm.get_crypto_markets(limit=100)

btc_markets = [
    m for m in markets if "April" in m["question"] or "april" in m["question"].lower()
]
print("BTC April markets:", len(btc_markets))

prices = [m["price_yes"] for m in btc_markets]
if prices:
    print("Price range:", min(prices), "-", max(prices))

mid = [m for m in btc_markets if 0.3 < m["price_yes"] < 0.7]
print("Mid-range:", len(mid))
for m in mid:
    q = m["question"]
    p = m["price_yes"]
    print(f"  {p:.4f} - {q[:60]}")
