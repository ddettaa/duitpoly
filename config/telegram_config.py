import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

ALERT_CONFIG = {
    "latency_spike": {
        "threshold_ms": 500,
        "message": "🔴 Latency Spike: {latency_ms}ms on {market_id}",
    },
    "high_deviation": {
        "threshold_pct": 0.5,
        "message": "📊 High Deviation: {deviation_pct}% on {market_id}",
    },
    "opportunity": {
        "edge_threshold": 0.05,
        "message": "💡 Opportunity: {market_id}\nEdge={edge}\nConfidence={confidence}\nAction={action}",
    },
    "daily_summary": {
        "time": "18:00",
        "message": "📈 Daily Summary:\n- Latency events: {count}\n- Avg latency: {avg_ms}ms\n- Max deviation: {max_deviation}%",
    },
    "system_health": {
        "interval_minutes": 60,
        "message": "✅ System OK\nUptime: {uptime_hours}h\nData points: {data_points}",
    },
}
