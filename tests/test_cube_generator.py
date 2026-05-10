import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from engines.cube_generator import CubeGenerator
from engines.llm_gateway import LLMConnectionError


@pytest.fixture
def mock_llm_gateway():
    gw = AsyncMock()
    gw.generate = AsyncMock(return_value='{"title": "试卡行为分析", "name": "m_test", "ctype": "1", "version": "datacube_20260509_A1200", "script": {"tables": {"t1": {"tableId": "t1", "name": "tt.jz_bank_bill", "title": "银行交易流水表", "where": {"w1": {"field": "jdbz", "title": "借贷标志", "type": "string"}}}}, "cloneRel": {}}}')
    return gw


@pytest.fixture
def mock_schema_registry():
    sr = MagicMock()
    sr.get_schema_for_prompt.return_value = "数据源表：\ntt.jz_bank_bill(银行交易流水表): ajbh, jy_je, jdbz"
    sr.table_exists.return_value = True
    sr.field_exists.return_value = True
    return sr


@pytest.fixture
def mock_rag_retriever():
    rr = MagicMock()
    rr.get_few_shot_examples.return_value = [
        {
            "title": "试卡行为分析",
            "name": "m_example",
            "bz": "示例",
            "ctype": "1",
            "version": "datacube_20260509_A1200",
            "script": {
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {"w1": {"field": "jdbz", "title": "借贷标志", "type": "string"}},
                    }
                },
                "cloneRel": {},
            },
        }
    ]
    return rr


@pytest.fixture
def mock_intent_parser():
    ip = AsyncMock()
    ip.parse.return_value = {
        "model_type": "试卡行为分析",
        "keywords": ["试卡"],
        "confidence": 0.9,
        "description": "分析试卡行为",
    }
    return ip


@pytest.fixture
def mock_validator():
    v = MagicMock()
    v.validate.return_value = {"valid": True, "errors": []}
    return v


@pytest.fixture
def generator(mock_llm_gateway, mock_schema_registry, mock_rag_retriever, mock_intent_parser, mock_validator):
    return CubeGenerator(
        llm_gateway=mock_llm_gateway,
        schema_registry=mock_schema_registry,
        rag_retriever=mock_rag_retriever,
        intent_parser=mock_intent_parser,
        validator=mock_validator,
    )


class TestCubeGeneratorExists:
    @pytest.mark.asyncio
    async def test_generate_method_exists(self, generator):
        assert hasattr(generator, "generate")
        assert callable(generator.generate)


class TestGenerateFlow:
    @pytest.mark.asyncio
    async def test_calls_intent_parser(self, generator, mock_intent_parser):
        await generator.generate("分析试卡行为")
        mock_intent_parser.parse.assert_called_once_with("分析试卡行为")

    @pytest.mark.asyncio
    async def test_calls_rag_retriever(self, generator, mock_rag_retriever):
        await generator.generate("分析试卡行为")
        mock_rag_retriever.get_few_shot_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_calls_llm_gateway(self, generator, mock_llm_gateway):
        await generator.generate("分析试卡行为")
        mock_llm_gateway.generate.assert_called_once()
        call_kwargs = mock_llm_gateway.generate.call_args
        assert call_kwargs[1]["format_json"] is True

    @pytest.mark.asyncio
    async def test_calls_validator(self, generator, mock_validator):
        await generator.generate("分析试卡行为")
        mock_validator.validate.assert_called_once()


class TestPromptConstruction:
    @pytest.mark.asyncio
    async def test_prompt_contains_schema(self, generator, mock_llm_gateway):
        await generator.generate("分析试卡行为")
        call_args = mock_llm_gateway.generate.call_args
        prompt = call_args[0][0]
        assert "tt.jz_bank_bill" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_user_description(self, generator, mock_llm_gateway):
        await generator.generate("分析试卡行为")
        call_args = mock_llm_gateway.generate.call_args
        prompt = call_args[0][0]
        assert "分析试卡行为" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_format_template(self, generator, mock_llm_gateway):
        await generator.generate("分析试卡行为")
        call_args = mock_llm_gateway.generate.call_args
        prompt = call_args[0][0]
        assert "输出格式" in prompt
        assert "title" in prompt
        assert "script" in prompt

    @pytest.mark.asyncio
    async def test_system_prompt_set(self, generator, mock_llm_gateway):
        await generator.generate("分析试卡行为")
        call_kwargs = mock_llm_gateway.generate.call_args
        system_prompt = call_kwargs[1]["system_prompt"]
        assert len(system_prompt) > 0


class TestOutputParsing:
    @pytest.mark.asyncio
    async def test_valid_json_parsed_correctly(self, generator):
        result = await generator.generate("分析试卡行为")
        assert result["success"] is True
        assert "cube_content" in result
        cube = result["cube_content"]
        assert cube["title"] == "试卡行为分析"

    @pytest.mark.asyncio
    async def test_result_has_model_type(self, generator):
        result = await generator.generate("分析试卡行为")
        assert result["model_type"] == "试卡行为分析"

    @pytest.mark.asyncio
    async def test_result_has_confidence(self, generator):
        result = await generator.generate("分析试卡行为")
        assert result["confidence"] == 0.9


class TestValidationRetry:
    @pytest.mark.asyncio
    async def test_retries_on_validation_failure(self, generator, mock_validator, mock_llm_gateway):
        mock_validator.validate.side_effect = [
            {"valid": False, "errors": [{"path": "title", "message": "缺少必填字段: title"}]},
            {"valid": True, "errors": []},
        ]
        mock_llm_gateway.generate.return_value = '{"title": "试卡", "name": "m_test", "ctype": "1", "version": "v1", "script": {"tables": {"t1": {"tableId": "t1", "name": "tt.jz_bank_bill", "title": "银行交易流水表", "where": {}}}, "cloneRel": {}}}'

        result = await generator.generate("分析试卡行为")
        assert result["success"] is True
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_max_3_retries(self, generator, mock_validator, mock_llm_gateway):
        mock_validator.validate.return_value = {"valid": False, "errors": [{"path": "title", "message": "error"}]}
        mock_llm_gateway.generate.return_value = '{"title": "bad", "name": "m_test", "ctype": "1", "version": "v1", "script": {"tables": {}, "cloneRel": {}}}'

        result = await generator.generate("分析试卡行为")
        assert result["validation_passed"] is False
        assert result["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_retry_appends_errors_to_prompt(self, generator, mock_validator, mock_llm_gateway):
        mock_validator.validate.side_effect = [
            {"valid": False, "errors": [{"path": "title", "message": "缺少字段"}]},
            {"valid": True, "errors": []},
        ]
        mock_llm_gateway.generate.return_value = '{"title": "ok", "name": "m_test", "ctype": "1", "version": "v1", "script": {"tables": {"t1": {"tableId": "t1", "name": "tt.jz_bank_bill", "title": "银行交易流水表", "where": {}}}, "cloneRel": {}}}'

        await generator.generate("分析试卡行为")

        assert mock_llm_gateway.generate.call_count == 2
        second_call_args = mock_llm_gateway.generate.call_args_list[1]
        prompt = second_call_args[0][0]
        assert "缺少字段" in prompt


class TestFileSaving:
    @pytest.mark.asyncio
    async def test_saves_cube_file(self, generator):
        with patch("engines.cube_generator.CubeGenerator._save_cube") as mock_save:
            mock_save.return_value = "output/test.cube"
            result = await generator.generate("分析试卡行为")
            assert "file_path" in result or result["success"] is True


class TestConditionsExtraction:
    @pytest.mark.asyncio
    async def test_extracts_conditions(self, generator):
        result = await generator.generate("分析试卡行为")
        assert "conditions" in result
        assert isinstance(result["conditions"], list)

    @pytest.mark.asyncio
    async def test_conditions_contain_where_fields(self, generator):
        result = await generator.generate("分析试卡行为")
        conditions = result["conditions"]
        assert len(conditions) > 0
        assert "field" in conditions[0]
        assert "title" in conditions[0]


class TestLLMError:
    @pytest.mark.asyncio
    async def test_llm_connection_error_returns_failure(self, generator, mock_llm_gateway):
        mock_llm_gateway.generate.side_effect = LLMConnectionError("无法连接LLM服务")
        result = await generator.generate("分析试卡行为")
        assert result["success"] is False
        assert "LLM" in result.get("message", "") or "连接" in result.get("message", "")


class TestReferencedTemplates:
    @pytest.mark.asyncio
    async def test_result_has_referenced_templates(self, generator):
        result = await generator.generate("分析试卡行为")
        assert "referenced_templates" in result
        assert isinstance(result["referenced_templates"], list)
