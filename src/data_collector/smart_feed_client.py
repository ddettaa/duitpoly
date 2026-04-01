import requests
import time


class SmartFeedClient:
    def __init__(self, base_url="https://www.polyman.fun/api/feed"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_smart_feed(self, limit=20, page=0):
        try:
            url = f"{self.base_url}"
            params = {"type": "smart", "limit": limit, "page": page}
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"[SmartFeed] Error: {e}")
            return []

    def get_crypto_feed(self, limit=20):
        feed = self.get_smart_feed(limit=limit)

        crypto_items = []
        for item in feed:
            question = item.get("question", "").lower()
            if any(
                crypto in question
                for crypto in ["btc", "bitcoin", "eth", "ethereum", "crypto"]
            ):
                crypto_items.append(item)

        return crypto_items

    def poll(self, interval_seconds=60, callback=None):
        while True:
            try:
                feed = self.get_smart_feed(limit=20)
                if callback:
                    for item in feed:
                        callback(item)
            except Exception as e:
                print(f"[SmartFeed] Poll error: {e}")

            time.sleep(interval_seconds)
