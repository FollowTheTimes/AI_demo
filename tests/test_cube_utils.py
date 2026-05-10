import pytest
from engines.cube_utils import parse_script, normalize_tables


class TestParseScript:
    def test_dict_passthrough(self):
        d = {"tables": {}}
        assert parse_script(d) is d

    def test_string_parsed(self):
        s = '{"tables": {}}'
        result = parse_script(s)
        assert result == {"tables": {}}

    def test_invalid_string_returns_none(self):
        assert parse_script("not json") is None

    def test_none_returns_none(self):
        assert parse_script(None) is None

    def test_number_returns_none(self):
        assert parse_script(42) is None


class TestNormalizeTablesDictInput:
    def test_dict_tables_unchanged(self):
        script = {"tables": {"table-1": {"tableId": "table-1", "name": "tt.test"}}}
        result = normalize_tables(script)
        assert result["tables"] == {"table-1": {"tableId": "table-1", "name": "tt.test"}}

    def test_empty_dict_tables(self):
        script = {"tables": {}}
        result = normalize_tables(script)
        assert result["tables"] == {}


class TestNormalizeTablesListInput:
    def test_list_tables_converted(self):
        script = {"tables": [
            {"tableId": "t1", "name": "tt.test1"},
            {"tableId": "t2", "name": "tt.test2"},
        ]}
        result = normalize_tables(script)
        assert isinstance(result["tables"], dict)
        assert "t1" in result["tables"]
        assert "t2" in result["tables"]
        assert result["tables"]["t1"]["name"] == "tt.test1"

    def test_list_tables_without_tableId(self):
        script = {"tables": [
            {"name": "tt.test1"},
            {"name": "tt.test2"},
        ]}
        result = normalize_tables(script)
        assert isinstance(result["tables"], dict)
        assert "table-1" in result["tables"]
        assert "table-2" in result["tables"]
        assert result["tables"]["table-1"]["tableId"] == "table-1"

    def test_list_tables_with_table_id_field(self):
        script = {"tables": [
            {"table_id": "custom-1", "name": "tt.test"},
        ]}
        result = normalize_tables(script)
        assert "custom-1" in result["tables"]

    def test_empty_list_tables(self):
        script = {"tables": []}
        result = normalize_tables(script)
        assert result["tables"] == {}

    def test_list_with_non_dict_items_skipped(self):
        script = {"tables": ["invalid", {"tableId": "t1", "name": "tt.test"}]}
        result = normalize_tables(script)
        assert "t1" in result["tables"]
        assert len(result["tables"]) == 1


class TestNormalizeTablesEdgeCases:
    def test_none_tables_becomes_empty_dict(self):
        script = {"tables": None}
        result = normalize_tables(script)
        assert result["tables"] == {}

    def test_missing_tables_key(self):
        script = {"other": "data"}
        result = normalize_tables(script)
        assert result["tables"] == {}

    def test_non_dict_script_returned_as_is(self):
        assert normalize_tables("not a dict") == "not a dict"
        assert normalize_tables(None) is None

    def test_other_types_become_empty_dict(self):
        script = {"tables": "invalid"}
        result = normalize_tables(script)
        assert result["tables"] == {}

    def test_preserves_other_script_fields(self):
        script = {"tables": [], "cloneRel": {"r1": {"sourceId": "t1"}}}
        result = normalize_tables(script)
        assert "cloneRel" in result
