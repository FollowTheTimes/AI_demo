import pytest
import json
from engines.rag_retriever import RAGRetriever


@pytest.fixture
def retriever():
    r = RAGRetriever()
    r.templates = [
        {
            "title": "试卡行为分析",
            "name": "m_test_shika",
            "bz": "分析试卡行为",
            "ctype": "1",
            "version": "1.0",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {
                            "w1": {"field": "jdbz", "title": "借贷标志", "type": "string", "value": "1"}
                        },
                        "data": {"rows": [{"ajbh": "A001", "jy_je": 100}], "total": 1}
                    }
                },
                "cloneRel": {}
            })
        },
        {
            "title": "沉寂卡分析",
            "name": "m_test_chenji",
            "bz": "分析沉寂卡",
            "ctype": "1",
            "version": "1.0",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_zh",
                        "title": "银行账户表",
                        "where": {
                            "w1": {"field": "zh", "title": "账号", "type": "string", "value": ""}
                        },
                        "data": {"rows": [{"zh": "6222..."}], "total": 1}
                    }
                },
                "cloneRel": {}
            })
        },
        {
            "title": "资金快进快出分析",
            "name": "m_test_kuaijin",
            "bz": "分析资金快进快出",
            "ctype": "1",
            "version": "1.0",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {
                            "w1": {"field": "jy_je", "title": "交易金额", "type": "decimal", "value": "10000"}
                        },
                        "data": {"rows": [], "total": 0}
                    },
                    "t2": {
                        "tableId": "t2",
                        "name": "tt.jz_bank_zh",
                        "title": "银行账户表",
                        "where": {},
                        "data": {"rows": [], "total": 0}
                    }
                },
                "cloneRel": {"r1": {"sourceId": "t1", "targetId": "t2"}}
            })
        },
    ]
    r.build_index()
    return r


class TestGetTemplateSummary:
    def test_summary_has_basic_fields(self, retriever):
        template = retriever.templates[0]
        summary = retriever.get_template_summary(template)
        assert "title" in summary
        assert "name" in summary
        assert "bz" in summary

    def test_summary_removes_data_rows(self, retriever):
        template = retriever.templates[0]
        summary = retriever.get_template_summary(template)
        script = summary.get("script", {})
        for table in script.get("tables", {}).values():
            assert "data" not in table or "rows" not in table.get("data", {})

    def test_summary_preserves_where(self, retriever):
        template = retriever.templates[0]
        summary = retriever.get_template_summary(template)
        script = summary.get("script", {})
        tables = script.get("tables", {})
        assert "where" in tables.get("t1", {})

    def test_summary_preserves_clone_rel(self, retriever):
        template = retriever.templates[2]
        summary = retriever.get_template_summary(template)
        script = summary.get("script", {})
        assert "cloneRel" in script


class TestSearchReturnsSummary:
    def test_search_result_contains_summary(self, retriever):
        results = retriever.search({"model_type": "试卡", "keywords": ["试卡"]})
        assert len(results) > 0
        result = results[0]
        assert "summary" in result
        assert "title" in result["summary"]

    def test_search_summary_no_data_rows(self, retriever):
        results = retriever.search({"model_type": "试卡", "keywords": ["试卡"]})
        for result in results:
            summary = result["summary"]
            script = summary.get("script", {})
            for table in script.get("tables", {}).values():
                assert "data" not in table or "rows" not in table.get("data", {})

    def test_search_still_has_score_and_match_type(self, retriever):
        results = retriever.search({"model_type": "试卡", "keywords": ["试卡"]})
        assert len(results) > 0
        result = results[0]
        assert "score" in result
        assert "match_type" in result


class TestGetFewShotExamples:
    def test_returns_up_to_max_examples(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "试卡", "keywords": ["试卡"]}, max_examples=2
        )
        assert len(examples) <= 2

    def test_examples_have_full_structure(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "试卡", "keywords": ["试卡"]}, max_examples=3
        )
        assert len(examples) > 0
        example = examples[0]
        assert "title" in example
        assert "name" in example
        assert "script" in example

    def test_examples_no_data_rows(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "试卡", "keywords": ["试卡"]}, max_examples=3
        )
        for example in examples:
            script = example.get("script", {})
            for table in script.get("tables", {}).values():
                assert "data" not in table or "rows" not in table.get("data", {})

    def test_examples_preserve_where(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "试卡", "keywords": ["试卡"]}, max_examples=3
        )
        assert len(examples) > 0
        example = examples[0]
        script = example.get("script", {})
        tables = script.get("tables", {})
        assert "where" in list(tables.values())[0]

    def test_examples_preserve_clone_rel(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "资金快进快出", "keywords": ["快进快出"]}, max_examples=3
        )
        found = False
        for example in examples:
            script = example.get("script", {})
            if script.get("cloneRel"):
                found = True
                break
        assert found

    def test_default_max_examples_is_3(self, retriever):
        examples = retriever.get_few_shot_examples(
            {"model_type": "", "keywords": ["分析"]}
        )
        assert len(examples) <= 3


class TestExistingFunctionalityPreserved:
    def test_load_templates_still_works(self):
        r = RAGRetriever()
        r.template_dir = "nonexistent_dir"
        result = r.load_templates()
        assert isinstance(result, list)

    def test_build_index_still_works(self, retriever):
        assert len(retriever.index) == 3

    def test_get_template_still_works(self, retriever):
        template = retriever.get_template("试卡行为分析")
        assert template is not None
        assert template["title"] == "试卡行为分析"
