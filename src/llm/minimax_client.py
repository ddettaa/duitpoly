import os
import requests
import time
from config.config import LLM_MIN_CONFIDENCE, LLM_EDGE_THRESHOLD


class MiniMaxClient:
    def __init__(self, api_key=None, telegram_bot=None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.base_url = "https://api.minimax.chat/v1"
        self.telegram_bot = telegram_bot
        self.last_call_time = 0
        self.min_interval = 1.0

    def analyze_market(
        self, market_question, market_price_yes, btc_price=None, trend=None
    ):
        prompt = self._build_prompt(market_question, market_price_yes, btc_price, trend)

        current_time = time.time()
        if current_time - self.last_call_time < self.min_interval:
            time.sleep(self.min_interval - (current_time - self.last_call_time))

        try:
            response = self._call_minimax(prompt)
            self.last_call_time = time.time()
            return self._parse_response(response, market_price_yes)
        except Exception as e:
            print(f"[MiniMax] Error: {e}")
            return None

    def _build_prompt(self, market_question, market_price_yes, btc_price, trend):
        btc_info = (
            f"Current BTC price: ${btc_price}"
            if btc_price
            else "BTC price data not available"
        )
        trend_info = f"BTC trend: {trend}" if trend else "No clear trend"

        return f"""You are a prediction market analyst. Analyze this Polymarket question:

Question: {market_question}
Current YES price: {market_price_yes} (implies {market_price_yes * 100:.1f}% probability of YES)
{btc_info}
{trend_info}

Based on the question and market data, estimate:
1. The actual probability of YES (between 0 and 1)
2. Your confidence in this estimate (between 0 and 1)
3. Brief reasoning (2-3 sentences max)

Output format (JSON only, no other text):
{{
    "predicted_probability": 0.XX,
    "confidence": 0.XX,
    "reasoning": "your brief reasoning here"
}}

Important rules:
- If uncertain, shrink your prediction toward {market_price_yes}
- Avoid longshot bias (don't overestimate extreme probabilities)
- Focus on information that would affect the probability
- Output valid JSON only"""

    def _call_minimax(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "MiniMax-Text-01",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 300,
        }

        response = requests.post(
            f"{self.base_url}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API error: {response.status_code} - {response.text}")

    def _parse_response(self, response, market_price_yes):
        try:
            content = response["choices"][0]["message"]["content"]
            import json

            data = json.loads(content)

            predicted_prob = float(data.get("predicted_probability", market_price_yes))
            confidence = float(data.get("confidence", 0.5))
            reasoning = str(data.get("reasoning", ""))

            predicted_prob = max(0.01, min(0.99, predicted_prob))
            confidence = max(0.1, min(1.0, confidence))

            if confidence < LLM_MIN_CONFIDENCE:
                predicted_prob = predicted_prob * 0.5 + market_price_yes * 0.5

            edge = predicted_prob - market_price_yes

            if edge > 0.05:
                action = "buy_yes"
            elif edge < -0.05:
                action = "buy_no"
            else:
                action = "no_trade"

            return {
                "predicted_probability": round(predicted_prob, 4),
                "confidence": round(confidence, 4),
                "reasoning": reasoning,
                "edge": round(edge, 4),
                "recommended_action": action,
                "market_price_yes": market_price_yes,
            }
        except Exception as e:
            print(f"[MiniMax] Parse error: {e}")
            return None

    def analyze_batch(self, markets_data):
        results = []
        for market in markets_data:
            result = self.analyze_market(
                market_question=market["question"],
                market_price_yes=market["price_yes"],
                btc_price=market.get("btc_price"),
                trend=market.get("trend"),
            )
            if result:
                results.append(result)
            time.sleep(1)
        return results

    def check_and_alert_opportunity(self, analysis_result):
        if analysis_result and self.telegram_bot:
            if (
                abs(analysis_result["edge"]) >= LLM_EDGE_THRESHOLD
                and analysis_result["confidence"] >= LLM_MIN_CONFIDENCE
            ):
                self.telegram_bot.send_alert(
                    alert_type="opportunity",
                    data={
                        "market_id": analysis_result.get("market_id", "unknown"),
                        "edge": f"{analysis_result['edge']:.2%}",
                        "confidence": f"{analysis_result['confidence']:.0%}",
                        "action": analysis_result["recommended_action"],
                    },
                )
