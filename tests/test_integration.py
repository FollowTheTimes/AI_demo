import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from engines.schema_registry import SchemaRegistry
from engines.cube_validator import CubeValidator
from engines.condition_editor import ConditionEditor
from engines.rag_retriever import RAGRetriever
from engines.cube_generator import CubeGenerator
from engines.intent_parser import IntentParser
from engines.llm_gateway import LLMGateway
from engines.data_cleaner import DataCleaner
from engines.where_sql_builder import build_where_sql
from engines.cube_utils import parse_script


@pytest.fixture
def schema_registry():
    sr = SchemaRegistry(schema_dir="nonexistent")
    sr._schemas = {
        "tt.jz_bank_bill": {
            "name": "银行交易流水表",
            "description": "存储银行交易流水明细数据",
            "fields": [
                {"name": "ajbh", "label": "案件编号", "type": "string"},
                {"name": "jy_je", "label": "交易金额", "type": "decimal"},
                {"name": "jdbz", "label": "借贷标志", "type": "string"},
            ],
        },
        "tt.jz_bank_zh": {
            "name": "银行账户表",
            "description": "存储银行账户基本信息",
            "fields": [
                {"name": "zh", "label": "账号", "type": "string"},
            ],
        },
    }
    sr._loaded = True
    return sr


@pytest.fixture
def valid_cube():
    return {
        "title": "试卡行为分析",
        "name": "m_test_shika",
        "ctype": "1",
        "version": "datacube_20260509_A1200",
        "script": json.dumps({
            "tables": {
                "t1": {
                    "tableId": "t1",
                    "name": "tt.jz_bank_bill",
                    "title": "银行交易流水表",
                    "where": {
                        "w1": {
                            "field": "jdbz",
                            "title": "借贷标志",
                            "type": "string",
                            "attr": {"charL": "", "charU": "", "multiequals": "进", "isExcept": False},
                        },
                        "w2": {
                            "field": "jy_je",
                            "title": "交易金额",
                            "type": "decimal",
                            "attr": {"charL": "1000", "charU": "50000", "multiequals": "", "isExcept": False},
                        },
                    },
                },
                "t2": {
                    "tableId": "t2",
                    "name": "tt.jz_bank_zh",
                    "title": "银行账户表",
                    "where": {},
                },
            },
            "cloneRel": {"r1": {"sourceId": "t1", "targetId": "t2"}},
        }),
    }


class TestSchemaRegistryAndValidatorIntegration:
    def test_registered_table_passes_validation(self, schema_registry, valid_cube):
        validator = CubeValidator(schema_registry)
        result = validator.validate(valid_cube)
        assert result["valid"] is True

    def test_unregistered_table_fails_validation(self, schema_registry, valid_cube):
        script = json.loads(valid_cube["script"])
        script["tables"]["t1"]["name"] = "tt.nonexistent_table"
        valid_cube["script"] = json.dumps(script)

        validator = CubeValidator(schema_registry)
        result = validator.validate(valid_cube)
        assert result["valid"] is False
        errors = [e for e in result["errors"] if "未注册" in e["message"]]
        assert len(errors) > 0

    def test_nonexistent_field_fails_validation(self, schema_registry, valid_cube):
        script = json.loads(valid_cube["script"])
        script["tables"]["t1"]["where"]["w1"]["field"] = "nonexistent_field"
        valid_cube["script"] = json.dumps(script)

        validator = CubeValidator(schema_registry)
        result = validator.validate(valid_cube)
        assert result["valid"] is False
        errors = [e for e in result["errors"] if "字段不存在" in e["message"]]
        assert len(errors) > 0

    def test_schema_registry_provides_prompt_info(self, schema_registry):
        prompt = schema_registry.get_schema_for_prompt()
        assert "tt.jz_bank_bill" in prompt
        assert "ajbh" in prompt
        assert "jy_je" in prompt


class TestValidatorAndConditionEditorIntegration:
    def test_valid_cube_conditions_parseable(self, schema_registry, valid_cube):
        validator = CubeValidator(schema_registry)
        result = validator.validate(valid_cube)
        assert result["valid"] is True

        editor = ConditionEditor()
        conditions = editor.parse_conditions(valid_cube)
        assert len(conditions) == 2
        assert conditions[0]["field"] == "jdbz"
        assert conditions[1]["field"] == "jy_je"

    def test_update_conditions_preserves_validity(self, schema_registry, valid_cube):
        editor = ConditionEditor()
        updated = editor.update_conditions(valid_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
            {"table_id": "t1", "field": "jy_je", "value": {"charL": "5000", "charU": "100000"}},
        ])

        validator = CubeValidator(schema_registry)
        result = validator.validate(updated)
        assert result["valid"] is True

    def test_update_conditions_generates_valid_where_sql(self, valid_cube):
        editor = ConditionEditor()
        updated = editor.update_conditions(valid_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
        ])

        script = parse_script(updated["script"])
        t1 = script["tables"]["t1"]
        assert "whereSql" in t1
        assert "executeSql" in t1["whereSql"]
        assert '"jdbz"' in t1["whereSql"]["executeSql"]


class TestRAGRetrieverAndCubeGeneratorIntegration:
    @pytest.mark.asyncio
    async def test_rag_provides_examples_for_generator(self):
        rag = RAGRetriever()
        rag.templates = [
            {
                "title": "试卡行为分析",
                "name": "m_test",
                "bz": "分析试卡行为",
                "ctype": "1",
                "version": "1.0",
                "script": json.dumps({
                    "tables": {
                        "t1": {"tableId": "t1", "name": "tt.jz_bank_bill", "title": "银行交易流水表", "where": {}},
                    },
                    "cloneRel": {},
                }),
            },
        ]
        rag.build_index()

        examples = rag.get_few_shot_examples({"model_type": "试卡", "keywords": ["试卡"]}, max_examples=1)
        assert len(examples) == 1
        assert examples[0]["title"] == "试卡行为分析"
        assert isinstance(examples[0]["script"], dict)

    @pytest.mark.asyncio
    async def test_full_generator_flow_with_mock_llm(self, schema_registry):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=json.dumps({
            "title": "试卡行为分析",
            "name": "m_test",
            "ctype": "1",
            "version": "datacube_20260509_A1200",
            "script": {
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {"w1": {"field": "jdbz", "title": "借贷标志", "type": "string"}},
                    },
                },
                "cloneRel": {},
            },
        }))

        rag = RAGRetriever()
        rag.templates = []
        rag.build_index()

        intent = IntentParser(llm_gateway=None)
        validator = CubeValidator(schema_registry)

        generator = CubeGenerator(
            llm_gateway=llm,
            schema_registry=schema_registry,
            rag_retriever=rag,
            intent_parser=intent,
            validator=validator,
        )

        result = await generator.generate("分析试卡行为")
        assert result["success"] is True
        assert result["cube_content"]["title"] == "试卡行为分析"
        assert result["validation_passed"] is True
        assert len(result["conditions"]) == 1


class TestParseScriptIntegration:
    def test_parse_script_used_by_validator(self, schema_registry):
        cube = {
            "title": "test",
            "name": "m_test",
            "ctype": "1",
            "version": "1.0",
            "script": '{"tables": {"t1": {"tableId": "t1", "name": "tt.jz_bank_bill", "title": "银行交易流水表", "where": {}}}, "cloneRel": {}}',
        }
        validator = CubeValidator(schema_registry)
        result = validator.validate(cube)
        assert result["valid"] is True

    def test_parse_script_used_by_condition_editor(self):
        cube = {
            "title": "test",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {"w1": {"field": "ajbh", "title": "案件编号", "type": "string", "attr": {"charL": "", "charU": "", "multiequals": "A001", "isExcept": False}}},
                    }
                },
                "cloneRel": {},
            }),
        }
        editor = ConditionEditor()
        conditions = editor.parse_conditions(cube)
        assert len(conditions) == 1
        assert conditions[0]["field"] == "ajbh"

    def test_parse_script_used_by_rag_retriever(self):
        rag = RAGRetriever()
        rag.templates = [
            {
                "title": "test",
                "name": "m_test",
                "bz": "test",
                "script": json.dumps({"tables": {"t1": {"name": "test"}}, "cloneRel": {}}),
            },
        ]
        rag.build_index()

        summary = rag.get_template_summary(rag.templates[0])
        assert summary["script"]["tables"]["t1"]["name"] == "test"


class TestWhereSqlBuilderIntegration:
    def test_condition_editor_uses_where_sql_builder(self, valid_cube):
        editor = ConditionEditor()
        updated = editor.update_conditions(valid_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
        ])

        script = parse_script(updated["script"])
        where = script["tables"]["t1"]["where"]
        where_sql = build_where_sql(where)
        assert where_sql is not None
        assert '"jdbz" in' in where_sql["executeSql"]

    def test_where_sql_builder_handles_all_condition_types(self):
        where = {
            "w1": {"field": "jdbz", "type": "string", "attr": {"multiequals": "进", "isExcept": False}},
            "w2": {"field": "jy_je", "type": "decimal", "attr": {"charL": "1000", "charU": "50000", "multiequals": "", "isExcept": False}},
            "w3": {"field": "sj", "type": "date", "attr": {"charL": "2024-01-01", "charU": "2024-12-31"}},
        }
        result = build_where_sql(where)
        assert '"jdbz" in' in result["executeSql"]
        assert '"jy_je" >=' in result["executeSql"]
        assert '"sj" >=' in result["executeSql"]


class TestDataCleanerIntegration:
    def test_clean_with_schema_aware_rules(self):
        cleaner = DataCleaner()
        data = [
            {"sfzh": "110101199001011234", "jy_je": "1,000.50", "jdbz": "贷", "sj": "2024/01/15 10:30:00"},
            {"sfzh": "12345", "jy_je": "abc", "jdbz": "借", "sj": "invalid"},
        ]
        cleaned = cleaner.clean(data)
        assert len(cleaned) == 2
        assert cleaned[0]["jy_je"] == 1000.50
        assert cleaned[0]["jdbz"] == "进"
        assert cleaned[1].get("_id_card_anomaly") is True

    def test_clean_report_matches_cleaned_data(self):
        cleaner = DataCleaner()
        data = [
            {"jylsh": "001", "jy_je": "1,000"},
            {"jylsh": "001", "jy_je": "1,000"},
            {"jylsh": "002", "jy_je": "2,000"},
        ]
        cleaned = cleaner.clean(data)
        report = cleaner.generate_clean_report(data, cleaned)
        assert report["原始数据条数"] == 3
        assert report["清洗后数据条数"] == 2
        assert report["去除重复条数"] == 1


class TestEndToEndGenerateAndTune:
    @pytest.mark.asyncio
    async def test_generate_then_parse_then_update_conditions(self, schema_registry):
        llm = AsyncMock()
        llm.generate = AsyncMock(return_value=json.dumps({
            "title": "资金快进快出分析",
            "name": "m_test_kuaijin",
            "ctype": "1",
            "version": "datacube_20260509_A1200",
            "script": {
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {
                            "w1": {"field": "jdbz", "title": "借贷标志", "type": "string", "attr": {"charL": "", "charU": "", "multiequals": "进", "isExcept": False}},
                            "w2": {"field": "jy_je", "title": "交易金额", "type": "decimal", "attr": {"charL": "10000", "charU": "", "multiequals": "", "isExcept": False}},
                        },
                    },
                },
                "cloneRel": {},
            },
        }))

        rag = RAGRetriever()
        rag.templates = []
        rag.build_index()
        intent = IntentParser(llm_gateway=None)
        validator = CubeValidator(schema_registry)

        generator = CubeGenerator(
            llm_gateway=llm,
            schema_registry=schema_registry,
            rag_retriever=rag,
            intent_parser=intent,
            validator=validator,
        )

        result = await generator.generate("分析资金快进快出")
        assert result["success"] is True

        editor = ConditionEditor()
        conditions = editor.parse_conditions(result["cube_content"])
        assert len(conditions) == 2

        updated = editor.update_conditions(result["cube_content"], [
            {"table_id": "t1", "field": "jy_je", "value": {"charL": "50000", "charU": "500000"}},
        ])

        validation = validator.validate(updated)
        assert validation["valid"] is True

        script = parse_script(updated["script"])
        assert script["tables"]["t1"]["where"]["w2"]["attr"]["charL"] == "50000"
        assert "whereSql" in script["tables"]["t1"]

    @pytest.mark.asyncio
    async def test_generate_with_validation_retry(self, schema_registry):
        bad_cube = json.dumps({
            "title": "bad",
            "name": "m_test",
            "ctype": "1",
            "version": "1.0",
            "script": {"tables": {}, "cloneRel": {}},
        })
        good_cube = json.dumps({
            "title": "试卡行为分析",
            "name": "m_test",
            "ctype": "1",
            "version": "datacube_20260509_A1200",
            "script": {
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {"w1": {"field": "jdbz", "title": "借贷标志", "type": "string"}},
                    },
                },
                "cloneRel": {},
            },
        })

        llm = AsyncMock()
        llm.generate = AsyncMock(side_effect=[bad_cube, good_cube])

        rag = RAGRetriever()
        rag.templates = []
        rag.build_index()
        intent = IntentParser(llm_gateway=None)
        validator = CubeValidator(schema_registry)

        generator = CubeGenerator(
            llm_gateway=llm,
            schema_registry=schema_registry,
            rag_retriever=rag,
            intent_parser=intent,
            validator=validator,
        )

        result = await generator.generate("分析试卡行为")
        assert result["success"] is True
        assert result["retry_count"] == 1
        assert result["validation_passed"] is True
