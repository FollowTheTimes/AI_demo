import logging
import httpx

logger = logging.getLogger(__name__)

JSON_FORMAT_SUFFIX = "\n\n请严格以合法JSON格式输出，不要包含任何其他文字说明。"


class LLMConnectionError(Exception):
    pass


class LLMTimeoutError(Exception):
    pass


class LLMGateway:
    def __init__(self, config: dict):
        self.api_type = config.get("api_type", "ollama")
        self.api_url = config.get("api_url", "http://localhost:11434")
        self.model_name = config.get("model_name", "qwen2.5:7b")
        self.timeout = config.get("timeout", 30)
        self.max_tokens = config.get("max_tokens", 4096)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        format_json: bool = False,
    ) -> str:
        if format_json:
            prompt = prompt + JSON_FORMAT_SUFFIX

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.api_type == "ollama":
                    return await self._call_ollama(client, prompt, system_prompt)
                elif self.api_type == "openai":
                    return await self._call_openai(client, prompt, system_prompt)
                else:
                    raise LLMConnectionError(f"不支持的API类型: {self.api_type}")
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"LLM请求超时: {e}") from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"无法连接LLM服务: {e}") from e
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"LLM服务返回错误 {e.response.status_code}: {e.response.text}") from e

    async def _call_ollama(self, client, prompt, system_prompt):
        url = f"{self.api_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def _call_openai(self, client, prompt, system_prompt):
        url = f"{self.api_url}/v1/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
        }

        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def check_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                if self.api_type == "ollama":
                    url = f"{self.api_url}/api/tags"
                else:
                    url = f"{self.api_url}/v1/models"
                await client.get(url)
                return True
        except Exception:
            return False
