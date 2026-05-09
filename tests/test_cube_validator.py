import json
import pytest

from engines.cube_validator import CubeValidator
from engines.schema_registry import SchemaRegistry


@pytest.fixture
def schema_registry():
    r = SchemaRegistry(schema_dir="nonexistent")
    r._schemas = {
        "tt.jz_bank_bill": {
            "name": "银行交易流水表",
            "description": "测试",
            "fields": [
                {"name": "ajbh", "label": "案件编号", "type": "string"},
                {"name": "jy_je", "label": "交易金额", "type": "decimal"},
                {"name": "jdbz", "label": "借贷标志", "type": "string"},
            ],
        },
        "tt.jz_bank_zh": {
            "name": "银行账户表",
            "description": "测试",
            "fields": [
                {"name": "zh", "label": "账号", "type": "string"},
            ],
        },
    }
    r._loaded = True
    return r


@pytest.fixture
def validator(schema_registry):
    return CubeValidator(schema_registry)


def make_valid_cube():
    script = {
        "tables": {
            "table-1": {
                "tableId": "table-1",
                "name": "tt.jz_bank_bill",
                "title": "银行交易流水表",
                "where": {
                    "jy_je": {"field": "jy_je", "title": "交易金额", "type": "number", "attr": {"numberL": 1000, "numberU": 50000}},
                    "jdbz": {"field": "jdbz", "title": "借贷标志", "type": "char", "attr": {"charL": "", "charU": "", "isExcept": False, "multiequals": "进"}},
                },
                "whereSql": {"executeSql": "", "userSql": ""},
                "extend": [],
                "data": {},
                "fieldWidth": {},
                "tableType": "cube",
                "sortOrder": "asc",
            }
        },
        "cloneRel": {},
    }
    return {
        "title": "测试模型",
        "name": "测试模型",
        "img": "",
        "bz": "测试描述",
        "ctype": "12",
        "version": "datacube_20260509_A0001",
        "script": json.dumps(script, ensure_ascii=False),
    }


class TestValidCube:
    def test_valid_cube_passes(self, validator):
        cube = make_valid_cube()
        result = validator.validate(cube)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_cube_with_dict_script(self, validator):
        cube = make_valid_cube()
        cube["script"] = json.loads(cube["script"])
        result = validator.validate(cube)
        assert result["valid"] is True


class TestNonDictInput:
    def test_string_input_rejected(self, validator):
        result = validator.validate("not a dict")
        assert result["valid"] is False
        assert any("字典对象" in e["message"] for e in result["errors"])

    def test_list_input_rejected(self, validator):
        result = validator.validate([1, 2, 3])
        assert result["valid"] is False

    def test_none_input_rejected(self, validator):
        result = validator.validate(None)
        assert result["valid"] is False


class TestMissingTopLevelFields:
    def test_missing_title(self, validator):
        cube = make_valid_cube()
        del cube["title"]
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any(e["path"] == "title" for e in result["errors"])

    def test_missing_name(self, validator):
        cube = make_valid_cube()
        del cube["name"]
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any(e["path"] == "name" for e in result["errors"])

    def test_missing_ctype(self, validator):
        cube = make_valid_cube()
        del cube["ctype"]
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any(e["path"] == "ctype" for e in result["errors"])

    def test_missing_version(self, validator):
        cube = make_valid_cube()
        del cube["version"]
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any(e["path"] == "version" for e in result["errors"])

    def test_missing_script(self, validator):
        cube = make_valid_cube()
        del cube["script"]
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any(e["path"] == "script" for e in result["errors"])

    def test_missing_multiple_fields(self, validator):
        cube = {"title": "only title"}
        result = validator.validate(cube)
        assert result["valid"] is False
        assert len(result["errors"]) == 4


class TestInvalidScript:
    def test_script_not_valid_json(self, validator):
        cube = make_valid_cube()
        cube["script"] = "{invalid json"
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("script" in e["path"] and "JSON" in e["message"] for e in result["errors"])

    def test_script_is_number(self, validator):
        cube = make_valid_cube()
        cube["script"] = 123
        result = validator.validate(cube)
        assert result["valid"] is False


class TestEmptyTables:
    def test_empty_tables_dict(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"] = {}
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("tables" in e["path"] for e in result["errors"])

    def test_missing_tables_key(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        del script["tables"]
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False


class TestTableMissingFields:
    def test_missing_tableId(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        del script["tables"]["table-1"]["tableId"]
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("tableId" in e["path"] for e in result["errors"])

    def test_missing_table_name(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        del script["tables"]["table-1"]["name"]
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("name" in e["path"] for e in result["errors"])

    def test_missing_table_title(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        del script["tables"]["table-1"]["title"]
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("title" in e["path"] for e in result["errors"])


class TestUnregisteredTable:
    def test_unregistered_table_name(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["name"] = "tt.nonexistent_table"
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("未注册" in e["message"] for e in result["errors"])

    def test_registered_table_name_passes(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["name"] = "tt.jz_bank_zh"
        script["tables"]["table-1"]["title"] = "银行账户表"
        script["tables"]["table-1"]["where"] = {}
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is True


class TestNonExistentField:
    def test_where_field_not_in_schema(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["where"] = {
            "bad_field": {"field": "nonexistent_col", "title": "不存在字段", "type": "string"}
        }
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("字段不存在" in e["message"] for e in result["errors"])

    def test_where_valid_field_passes(self, validator):
        cube = make_valid_cube()
        result = validator.validate(cube)
        assert result["valid"] is True


class TestInvalidWhereStructure:
    def test_where_condition_not_dict(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["where"] = {
            "jy_je": "not a dict"
        }
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("where条件必须是对象" in e["message"] for e in result["errors"])

    def test_where_missing_required_keys(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["where"] = {
            "jy_je": {"attr": {"numberL": 1000}}
        }
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        missing_field_errors = [e for e in result["errors"] if "where" in e["path"] and "缺少必填字段" in e["message"]]
        assert len(missing_field_errors) >= 1

    def test_where_empty_dict_passes(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-1"]["where"] = {}
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is True


class TestCloneRelInvalidRef:
    def test_clone_rel_references_nonexistent_table(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["cloneRel"] = {
            "rel-1": {"sourceId": "table-999", "targetId": "table-1"}
        }
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is False
        assert any("cloneRel" in e["path"] and "不存在" in e["message"] for e in result["errors"])

    def test_clone_rel_valid_reference_passes(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["tables"]["table-2"] = {
            "tableId": "table-2",
            "name": "tt.jz_bank_zh",
            "title": "银行账户表",
            "where": {},
        }
        script["cloneRel"] = {
            "rel-1": {"sourceId": "table-1", "targetId": "table-2"}
        }
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is True

    def test_empty_clone_rel_passes(self, validator):
        cube = make_valid_cube()
        script = json.loads(cube["script"])
        script["cloneRel"] = {}
        cube["script"] = json.dumps(script, ensure_ascii=False)
        result = validator.validate(cube)
        assert result["valid"] is True
