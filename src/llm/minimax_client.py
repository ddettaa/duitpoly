import os
import requests
import time
import re
import json
from config.config import LLM_MIN_CONFIDENCE, LLM_EDGE_THRESHOLD


class MiniMaxClient:
    def __init__(self, api_key=None, telegram_bot=None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.base_url = "https://api.minimax.io/v1"
        self.telegram_bot = telegram_bot
        self.last_call_time = 0
        self.min_interval = 2.0
        self._is_configured = bool(self.api_key and len(self.api_key) > 10)

    def analyze_market(
        self, market_question, market_price_yes, btc_price=None, trend=None
    ):
        if not self._is_configured:
            print("[MiniMax] API key not configured - using heuristic fallback")
            return self._heuristic_analysis(
                market_question, market_price_yes, btc_price, trend
            )

        prompt = self._build_prompt(market_question, market_price_yes, btc_price, trend)

        current_time = time.time()
        if current_time - self.last_call_time < self.min_interval:
            time.sleep(self.min_interval - (current_time - self.last_call_time))

        try:
            response = self._call_minimax(prompt)
            self.last_call_time = time.time()
            if not response:
                return self._heuristic_analysis(
                    market_question, market_price_yes, btc_price, trend
                )
            return self._parse_response(response, market_price_yes)
        except Exception as e:
            print(f"[MiniMax] Error: {e}")
            return self._heuristic_analysis(
                market_question, market_price_yes, btc_price, trend
            )

    def _heuristic_analysis(self, market_question, market_price_yes, btc_price, trend):
        predicted_prob = market_price_yes
        confidence = 0.3
        reasoning = "LLM unavailable - using market price as estimate"

        edge = predicted_prob - market_price_yes

        if edge > 0.08:
            action = "buy_yes"
        elif edge < -0.08:
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
            "llm_available": False,
        }

    def _build_prompt(self, market_question, market_price_yes, btc_price, trend):
        btc_str = f"BTC {btc_price}" if btc_price else "BTC unknown"
        trend_str = f"trend {trend}" if trend else "trend neutral"

        return f"Market analysis request. Q: {market_question[:100]}. YES: {market_price_yes}. {btc_str}. {trend_str}. Give array: [0.XX, 0.XX, 'text']"

    def _call_minimax(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 1000,
        }

        response = requests.post(
            f"{self.base_url}/text/chatcompletion_v2",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("base_resp", {}).get("status_code", 0) != 0:
                raise Exception(
                    f"API error: {result.get('base_resp', {}).get('status_msg', 'unknown')}"
                )
            return result
        else:
            raise Exception(f"HTTP error: {response.status_code}")

    def _parse_response(self, response, market_price_yes):
        try:
            choice = (response.get("choices") or [{}])[0] or {}
            msg = choice.get("message", {}) or {}

            raw_content = msg.get("content") or msg.get("reasoning_content") or ""
            if isinstance(raw_content, list):
                raw_content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in raw_content
                )

            text = str(raw_content).strip()

            # Try parse JSON array format: [0.XX, 0.XX, "text"]
            json_match = re.search(r"\[[\s\S]*\]", text)
            if json_match:
                try:
                    arr = json.loads(json_match.group())
                    if isinstance(arr, list) and len(arr) >= 2:
                        predicted_prob = float(arr[0])
                        confidence = float(arr[1])
                        reasoning = str(arr[2]) if len(arr) > 2 else "analysis"

                        predicted_prob = max(0.01, min(0.99, predicted_prob))
                        confidence = max(0.1, min(1.0, confidence))

                        if confidence < LLM_MIN_CONFIDENCE:
                            predicted_prob = (
                                predicted_prob * 0.5 + market_price_yes * 0.5
                            )

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
                            "reasoning": reasoning[:100],
                            "edge": round(edge, 4),
                            "recommended_action": action,
                            "market_price_yes": market_price_yes,
                            "llm_available": True,
                        }
                except:
                    pass

            # Fallback: try to extract any numbers
            numbers = re.findall(r"\b0\.[0-9]+\b", text)
            if len(numbers) >= 2:
                predicted_prob = float(numbers[0])
                confidence = float(numbers[1])
                reasoning = "extracted from response"

                predicted_prob = max(0.01, min(0.99, predicted_prob))
                confidence = max(0.1, min(1.0, confidence))

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
                    "llm_available": True,
                }

            raise Exception("Could not parse response")
        except Exception as e:
            print(f"[MiniMax] Parse error: {e}")
            return self._heuristic_analysis("", market_price_yes, None, None)

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
