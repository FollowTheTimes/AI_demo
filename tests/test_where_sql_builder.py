import pytest
from engines.where_sql_builder import build_where_sql


class TestCharType:
    def test_equals_generates_in_sql(self):
        where = {
            "w1": {"field": "jdbz", "type": "char", "attr": {"multiequals": "进", "isExcept": False}},
        }
        result = build_where_sql(where)
        assert result is not None
        assert '"jdbz" in' in result["executeSql"]
        assert "'进'" in result["executeSql"]

    def test_except_generates_not_in_sql(self):
        where = {
            "w1": {"field": "jdbz", "type": "string", "attr": {"multiequals": "出", "isExcept": True}},
        }
        result = build_where_sql(where)
        assert '"jdbz" not in' in result["executeSql"]

    def test_multiple_values(self):
        where = {
            "w1": {"field": "jdbz", "type": "char", "attr": {"multiequals": "进,出", "isExcept": False}},
        }
        result = build_where_sql(where)
        assert "'进'" in result["executeSql"]
        assert "'出'" in result["executeSql"]

    def test_empty_value_returns_none(self):
        where = {
            "w1": {"field": "jdbz", "type": "char", "attr": {"multiequals": "", "isExcept": False}},
        }
        result = build_where_sql(where)
        assert result is None


class TestDecimalType:
    def test_range_generates_between_sql(self):
        where = {
            "w1": {"field": "jy_je", "type": "decimal", "attr": {"charL": "1000", "charU": "50000"}},
        }
        result = build_where_sql(where)
        assert '"jy_je" >= 1000 and "jy_je" <= 50000' in result["executeSql"]

    def test_lower_only(self):
        where = {
            "w1": {"field": "jy_je", "type": "number", "attr": {"charL": "1000", "charU": ""}},
        }
        result = build_where_sql(where)
        assert '"jy_je" >= 1000' in result["executeSql"]

    def test_upper_only(self):
        where = {
            "w1": {"field": "jy_je", "type": "int", "attr": {"charL": "", "charU": "50000"}},
        }
        result = build_where_sql(where)
        assert '"jy_je" <= 50000' in result["executeSql"]

    def test_empty_range_returns_none(self):
        where = {
            "w1": {"field": "jy_je", "type": "decimal", "attr": {"charL": "", "charU": ""}},
        }
        result = build_where_sql(where)
        assert result is None


class TestDateType:
    def test_date_range(self):
        where = {
            "w1": {"field": "sj", "type": "date", "attr": {"charL": "2024-01-01", "charU": "2024-12-31"}},
        }
        result = build_where_sql(where)
        assert '"sj" >= ' in result["executeSql"]
        assert "'2024-01-01'" in result["executeSql"]

    def test_date_lower_only(self):
        where = {
            "w1": {"field": "sj", "type": "date", "attr": {"charL": "2024-01-01", "charU": ""}},
        }
        result = build_where_sql(where)
        assert '"sj" >= ' in result["executeSql"]


class TestMultipleConditions:
    def test_multiple_conditions_joined(self):
        where = {
            "w1": {"field": "jdbz", "type": "char", "attr": {"multiequals": "进", "isExcept": False}},
            "w2": {"field": "jy_je", "type": "decimal", "attr": {"charL": "1000", "charU": "50000"}},
        }
        result = build_where_sql(where)
        assert '"jdbz" in' in result["executeSql"]
        assert '"jy_je" >=' in result["executeSql"]
        assert "\n" in result["executeSql"]

    def test_empty_where_returns_none(self):
        result = build_where_sql({})
        assert result is None

    def test_non_dict_condition_skipped(self):
        where = {
            "w1": "not a dict",
            "w2": {"field": "jdbz", "type": "char", "attr": {"multiequals": "进", "isExcept": False}},
        }
        result = build_where_sql(where)
        assert result is not None
        assert '"jdbz"' in result["executeSql"]

    def test_result_has_userSql(self):
        where = {
            "w1": {"field": "jdbz", "type": "char", "attr": {"multiequals": "进", "isExcept": False}},
        }
        result = build_where_sql(where)
        assert "userSql" in result
        assert result["userSql"] == ""
