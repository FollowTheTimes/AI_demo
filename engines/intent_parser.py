import json
import re
import logging
import httpx
from config import MODELING_TYPE_MAP, OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class IntentParser:

    def __init__(self):
        self.type_map = MODELING_TYPE_MAP
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.ollama_model = OLLAMA_MODEL

    async def parse(self, user_input: str) -> dict:
        keywords = self._extract_keywords(user_input)
        conditions = self._extract_conditions(user_input)

        model_type, confidence = self._keyword_match(keywords)
        if model_type:
            return {
                "model_type": model_type,
                "confidence": confidence,
                "keywords": keywords,
                "conditions": conditions,
                "description": user_input,
            }

        llm_result = await self._llm_parse(user_input, keywords)
        if llm_result:
            llm_result["conditions"] = conditions
            llm_result["description"] = user_input
            if "keywords" not in llm_result:
                llm_result["keywords"] = keywords
            return llm_result

        return {
            "model_type": "资金万能表",
            "confidence": 0.3,
            "keywords": keywords,
            "conditions": conditions,
            "description": user_input,
        }

    def _extract_keywords(self, text: str) -> list:
        words = re.findall(r"[\u4e00-\u9fa5]+|[a-zA-Z]+|\d+(?:\.\d+)?", text)
        return words

    def _extract_conditions(self, text: str) -> dict:
        conditions = {}

        amount_pattern = r"(\d+(?:\.\d+)?)\s*[万百千]?\s*[元块]?[-~至到]\s*(\d+(?:\.\d+)?)\s*[万百千]?\s*[元块]?"
        amount_match = re.search(amount_pattern, text)
        if amount_match:
            conditions["金额范围"] = [amount_match.group(1), amount_match.group(2)]

        time_pattern = r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)\s*[-~至到]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)"
        time_match = re.search(time_pattern, text)
        if time_match:
            conditions["时间范围"] = [time_match.group(1), time_match.group(2)]

        account_types = ["借记卡", "信用卡", "储蓄卡", "对公账户", "个人账户"]
        for at in account_types:
            if at in text:
                conditions["账户类型"] = at
                break

        directions = ["收入", "支出", "转入", "转出", "进账", "出账", "借贷"]
        for d in directions:
            if d in text:
                conditions["交易方向"] = d
                break

        banks = ["工商银行", "建设银行", "农业银行", "中国银行", "招商银行", "交通银行", "邮储银行"]
        for bank in banks:
            if bank in text:
                conditions["银行"] = bank
                break

        return conditions

    def _keyword_match(self, keywords: list) -> tuple:
        text = "".join(keywords).lower()
        best_match = None
        best_score = 0.0

        for model_type, type_keywords in self.type_map.items():
            for kw in type_keywords:
                if kw.lower() in text:
                    score = len(kw) / len(text) if text else 0
                    score = max(score, 0.5)
                    if score > best_score:
                        best_score = score
                        best_match = model_type

        if best_match:
            return best_match, min(best_score + 0.3, 0.95)

        return None, 0.0

    async def _llm_parse(self, user_input: str, keywords: list) -> dict:
        prompt = f"""你是一个意图解析助手。请根据用户的自然语言描述，解析出建模意图。

用户描述：{user_input}

请从以下建模类型中选择最匹配的一个：
{json.dumps(list(self.type_map.keys()), ensure_ascii=False)}

请严格按照以下JSON格式返回，不要返回其他内容：
{{"model_type": "建模类型", "confidence": 0.9, "keywords": ["关键词列表"], "description": "意图描述"}}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "")

                json_match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    if "model_type" in parsed:
                        parsed["confidence"] = float(parsed.get("confidence", 0.7))
                        return parsed

        except (httpx.HTTPError, json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM解析失败: {e}")

        return None
