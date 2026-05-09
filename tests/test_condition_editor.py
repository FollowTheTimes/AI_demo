import pytest
import json
from engines.condition_editor import ConditionEditor


@pytest.fixture
def sample_cube():
    return {
        "title": "试卡行为分析",
        "name": "m_test_shika",
        "ctype": "1",
        "version": "datacube_20260509_A1200",
        "script": {
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
            "cloneRel": {},
        },
    }


@pytest.fixture
def editor():
    return ConditionEditor()


class TestParseConditions:
    def test_parse_returns_list(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        assert isinstance(conditions, list)

    def test_parse_finds_where_conditions(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        assert len(conditions) == 2

    def test_condition_has_required_fields(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        cond = conditions[0]
        assert "table_id" in cond
        assert "field" in cond
        assert "title" in cond
        assert "type" in cond
        assert "current_value" in cond
        assert "available_operators" in cond

    def test_string_condition_current_value(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        jdbz_cond = [c for c in conditions if c["field"] == "jdbz"][0]
        assert jdbz_cond["current_value"] == "进"

    def test_decimal_condition_current_value(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        je_cond = [c for c in conditions if c["field"] == "jy_je"][0]
        assert je_cond["current_value"] == {"charL": "1000", "charU": "50000"}

    def test_string_type_operators(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        jdbz_cond = [c for c in conditions if c["field"] == "jdbz"][0]
        assert "等于" in jdbz_cond["available_operators"]
        assert "排除" in jdbz_cond["available_operators"]

    def test_decimal_type_operators(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        je_cond = [c for c in conditions if c["field"] == "jy_je"][0]
        assert "大于等于" in je_cond["available_operators"]
        assert "介于" in je_cond["available_operators"]

    def test_empty_where_returns_empty(self, editor, sample_cube):
        conditions = editor.parse_conditions(sample_cube)
        t2_conditions = [c for c in conditions if c["table_id"] == "t2"]
        assert len(t2_conditions) == 0

    def test_parse_with_script_as_string(self, editor):
        cube = {
            "title": "test",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {
                            "w1": {"field": "ajbh", "title": "案件编号", "type": "string", "attr": {"charL": "", "charU": "", "multiequals": "A001", "isExcept": False}},
                        },
                    }
                },
                "cloneRel": {},
            }),
        }
        conditions = editor.parse_conditions(cube)
        assert len(conditions) == 1
        assert conditions[0]["field"] == "ajbh"


class TestUpdateConditions:
    def test_update_string_condition(self, editor, sample_cube):
        updated = editor.update_conditions(sample_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
        ])
        where = updated["script"]["tables"]["t1"]["where"]["w1"]
        assert where["attr"]["multiequals"] == "出"

    def test_update_decimal_condition(self, editor, sample_cube):
        updated = editor.update_conditions(sample_cube, [
            {"table_id": "t1", "field": "jy_je", "value": {"charL": "5000", "charU": "100000"}},
        ])
        where = updated["script"]["tables"]["t1"]["where"]["w2"]
        assert where["attr"]["charL"] == "5000"
        assert where["attr"]["charU"] == "100000"

    def test_update_updates_where_sql(self, editor, sample_cube):
        updated = editor.update_conditions(sample_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
        ])
        t1 = updated["script"]["tables"]["t1"]
        assert "whereSql" in t1
        assert "executeSql" in t1["whereSql"]

    def test_update_nonexistent_field_returns_error(self, editor, sample_cube):
        result = editor.update_conditions(sample_cube, [
            {"table_id": "t1", "field": "nonexistent_field", "value": "test"},
        ])
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_update_nonexistent_table_returns_error(self, editor, sample_cube):
        result = editor.update_conditions(sample_cube, [
            {"table_id": "t99", "field": "jdbz", "value": "test"},
        ])
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_update_preserves_other_conditions(self, editor, sample_cube):
        updated = editor.update_conditions(sample_cube, [
            {"table_id": "t1", "field": "jdbz", "value": "出"},
        ])
        w2 = updated["script"]["tables"]["t1"]["where"]["w2"]
        assert w2["attr"]["charL"] == "1000"

    def test_update_with_script_as_string(self, editor):
        cube = {
            "title": "test",
            "script": json.dumps({
                "tables": {
                    "t1": {
                        "tableId": "t1",
                        "name": "tt.jz_bank_bill",
                        "title": "银行交易流水表",
                        "where": {
                            "w1": {"field": "ajbh", "title": "案件编号", "type": "string", "attr": {"charL": "", "charU": "", "multiequals": "A001", "isExcept": False}},
                        },
                    }
                },
                "cloneRel": {},
            }),
        }
        updated = editor.update_conditions(cube, [
            {"table_id": "t1", "field": "ajbh", "value": "B002"},
        ])
        script = updated["script"]
        if isinstance(script, str):
            script = json.loads(script)
        assert script["tables"]["t1"]["where"]["w1"]["attr"]["multiequals"] == "B002"
