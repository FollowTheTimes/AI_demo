import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from engines.llm_gateway import LLMGateway, LLMConnectionError, LLMTimeoutError


@pytest.fixture
def ollama_config():
    return {
        "api_type": "ollama",
        "api_url": "http://localhost:11434",
        "model_name": "qwen2.5:7b",
        "timeout": 30,
        "max_tokens": 4096,
    }


@pytest.fixture
def openai_config():
    return {
        "api_type": "openai",
        "api_url": "http://localhost:8080",
        "model_name": "qwen2.5:7b",
        "timeout": 30,
        "max_tokens": 4096,
    }


@pytest.fixture
def gateway(ollama_config):
    return LLMGateway(ollama_config)


class TestLLMGatewayExists:
    @pytest.mark.asyncio
    async def test_generate_method_exists(self, gateway):
        assert hasattr(gateway, "generate")
        assert callable(gateway.generate)

    @pytest.mark.asyncio
    async def test_generate_returns_string(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "hello world"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await gateway.generate("test prompt")
            assert isinstance(result, str)
            assert result == "hello world"


class TestOllamaAPIFormat:
    @pytest.mark.asyncio
    async def test_calls_ollama_generate_endpoint(self, gateway, ollama_config):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "test result"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("hello")

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/api/generate" in call_args[0][0]
            body = call_args[1]["json"]
            assert body["model"] == ollama_config["model_name"]
            assert body["prompt"] == "hello"
            assert body["stream"] is False

    @pytest.mark.asyncio
    async def test_ollama_with_system_prompt(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("hello", system_prompt="you are a helper")

            body = mock_client.post.call_args[1]["json"]
            assert "you are a helper" in body["system"]


class TestOpenAIAPIFormat:
    @pytest.mark.asyncio
    async def test_calls_openai_chat_endpoint(self, openai_config):
        gw = LLMGateway(openai_config)
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "openai result"}}]
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await gw.generate("hello")
            assert result == "openai result"

            call_args = mock_client.post.call_args
            assert "/v1/chat/completions" in call_args[0][0]
            body = call_args[1]["json"]
            assert body["model"] == openai_config["model_name"]
            assert body["messages"][-1]["role"] == "user"
            assert body["messages"][-1]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_openai_with_system_prompt(self, openai_config):
        gw = LLMGateway(openai_config)
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "ok"}}]
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gw.generate("hello", system_prompt="you are a helper")

            body = mock_client.post.call_args[1]["json"]
            assert body["messages"][0]["role"] == "system"
            assert body["messages"][0]["content"] == "you are a helper"


class TestConfigSwitching:
    @pytest.mark.asyncio
    async def test_ollama_type_uses_ollama_endpoint(self, gateway, ollama_config):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("test")

            url = mock_client.post.call_args[0][0]
            assert url == f"{ollama_config['api_url']}/api/generate"

    @pytest.mark.asyncio
    async def test_openai_type_uses_openai_endpoint(self, openai_config):
        gw = LLMGateway(openai_config)
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "ok"}}]
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gw.generate("test")

            url = mock_client.post.call_args[0][0]
            assert url == f"{openai_config['api_url']}/v1/chat/completions"


class TestTimeoutControl:
    @pytest.mark.asyncio
    async def test_timeout_passed_to_httpx(self, gateway, ollama_config):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("test")

            call_kwargs = mock_client_cls.call_args[1]
            assert call_kwargs["timeout"] == ollama_config["timeout"]

    @pytest.mark.asyncio
    async def test_timeout_raises_llm_timeout_error(self, gateway):
        import httpx
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timed out")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMTimeoutError):
                await gateway.generate("test")


class TestNetworkError:
    @pytest.mark.asyncio
    async def test_connection_error_raises_llm_connection_error(self, gateway):
        import httpx
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("connection refused")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMConnectionError):
                await gateway.generate("test")

    @pytest.mark.asyncio
    async def test_http_error_raises_llm_connection_error(self, gateway):
        import httpx
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_response
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMConnectionError):
                await gateway.generate("test")


class TestFormatJson:
    @pytest.mark.asyncio
    async def test_format_json_appends_constraint_ollama(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "{}"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("build a cube", format_json=True)

            body = mock_client.post.call_args[1]["json"]
            assert "JSON" in body["prompt"]

    @pytest.mark.asyncio
    async def test_format_json_appends_constraint_openai(self, openai_config):
        gw = LLMGateway(openai_config)
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "{}"}}]
            }
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gw.generate("build a cube", format_json=True)

            body = mock_client.post.call_args[1]["json"]
            user_msg = body["messages"][-1]["content"]
            assert "JSON" in user_msg

    @pytest.mark.asyncio
    async def test_format_json_false_does_not_append(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"response": "ok"}
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            await gateway.generate("build a cube", format_json=False)

            body = mock_client.post.call_args[1]["json"]
            assert body["prompt"] == "build a cube"


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_check_available_ollama(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await gateway.check_available()
            assert result is True

    @pytest.mark.asyncio
    async def test_check_unavailable(self, gateway):
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("connection refused")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await gateway.check_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_check_available_openai(self, openai_config):
        gw = LLMGateway(openai_config)
        with patch("engines.llm_gateway.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await gw.check_available()
            assert result is True
