# Latency Detection
LATENCY_THRESHOLD_PCT = 0.003  # 0.3% deviation trigger
LATENCY_ALERT_THRESHOLD_MS = 500  # Alert if latency > 500ms

# Polymarket
POLYMARKET_POLL_INTERVAL_MS = 500
POLYMARKET_API_URL = "https://clob.polymarket.com"
CRYPTO_ONLY_TAGS = ["crypto", "defi", "bitcoin", "ethereum"]

# BTC Feed
BTC_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

# LLM (Slow Analysis)
LLM_ANALYSIS_INTERVAL_MINUTES = 15
LLM_MIN_CONFIDENCE = 0.6
LLM_EDGE_THRESHOLD = 0.05

# Risk Management
RISK_PER_TRADE_PCT = 0.5  # 0.5% per trade
MAX_DAILY_LOSS_PCT = 2.0  # 2% daily loss limit

# Database
DB_PATH = "data/trading.db"
