# Polymarket Trading Engine - Phase 1

## Overview

Phase 1 focuses on **data collection and latency measurement** for crypto markets on Polymarket.

## Architecture

```
                    [Data Sources]
            +----------+----------+
            |                     |
    [Polymarket API]      [Binance WebSocket]
            |                     |
            +---------+-----------+
                      |
           [Data Normalization]
                      |
            +---------+-----------+
            |                     |
   [Latency Detection]   [LLM Analysis (Slow)]
            |                     |
            +---------+-----------+
                      |
                 [SQLite DB]
                      |
              [Telegram Alerts]
```

## Quick Start

### 1. Setup Environment

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
MINIMAX_API_KEY=your_minimax_api_key
```

### 3. Get Telegram Keys

**Bot Token:**
1. Open Telegram and search for @BotFather
2. Send `/newbot`
3. Follow instructions, get token

**Chat ID:**
1. Search for @userinfobot on Telegram
2. Send any message
3. Get your numeric Chat ID

### 4. Run the Engine

```bash
python main.py
```

## Project Structure

```
polymarket/
├── config/
│   ├── config.py           # Main configuration
│   └── telegram_config.py  # Telegram alert settings
├── data/
│   └── trading.db          # SQLite database (auto-created)
├── src/
│   ├── data_collector/
│   │   ├── polymarket_client.py  # Polymarket API
│   │   ├── btc_websocket.py      # BTC price feed
│   │   └── smart_feed_client.py  # Smart feed API
│   ├── latency_detector/
│   │   └── latency_analyzer.py   # Latency detection logic
│   ├── llm/
│   │   └── minimax_client.py     # MiniMax LLM integration
│   ├── monitoring/
│   │   └── telegram_bot.py       # Telegram alerts
│   └── db/
│       └── sqlite_handler.py     # Database operations
├── main.py                # Entry point
├── test_system.py          # Test suite
└── requirements.txt
```

## What Phase 1 Does

1. **Polymarket Data Collection**
   - Polls crypto markets every 500ms
   - Records price, volume, liquidity

2. **BTC Price Feed**
   - Connects to Binance WebSocket
   - Real-time BTC/USDT price

3. **Latency Detection**
   - Detects when Polymarket lags behind BTC moves
   - Logs deviation events to SQLite

4. **LLM Analysis (Slow)**
   - Analyzes market questions every 15 minutes
   - Estimates probability and edge
   - Alerts on trading opportunities

5. **Telegram Alerts**
   - Latency spikes (>500ms)
   - High deviation events (>0.5%)
   - Trading opportunities (edge >5%)
   - Hourly health checks
   - Daily summary at 18:00

## Database Schema

### price_snapshots
- market_id, question, price_yes/no, btc_price, volume, liquidity, timestamp

### btc_feed
- btc_price, timestamp

### latency_events
- market_id, btc_price, polymarket_price, deviation_pct, latency_ms, direction

### llm_analysis
- market_id, question, predicted_probability, confidence, edge, recommended_action

## Success Metrics (Phase 1)

| Metric | Target |
|--------|--------|
| Data points | >500 over 7 days |
| Latency events | >100 captured |
| System uptime | >95% |

## Phase 2+ Goals

- **Phase 2**: LLM Engine v1 (MiniMax integration)
- **Phase 3**: Signal Fusion & Backtest
- **Phase 4**: Paper Trading (FREE MODE)
- **Phase 5**: Pro Mode with real capital

## Troubleshooting

**Bot not sending messages:**
- Verify TELEGRAM_BOT_TOKEN is correct
- Verify TELEGRAM_CHAT_ID is numeric
- Test bot manually on Telegram first

**No latency events:**
- Check if BTC price is actually moving
- Verify Polymarket API is accessible
- Check database for price_snapshots records

**LLM not analyzing:**
- Verify MINIMAX_API_KEY is set
- Check API rate limits
- Look at logs for error messages
