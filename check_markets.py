from src.data_collector.polymarket_client import PolymarketClient

client = PolymarketClient()
markets = client.get_crypto_markets(limit=200)

mid_range = [m for m in markets if 0.15 < m["price_yes"] < 0.85]

print(f"\nTotal markets: {len(markets)}")
print(f"Mid-range (0.15-0.85): {len(mid_range)}")
print("\nMid-range markets:")
for m in mid_range[:15]:
    print(f"  {m['price_yes']:.4f} - {m['question'][:70]}")
