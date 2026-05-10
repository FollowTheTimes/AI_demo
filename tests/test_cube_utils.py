import pytest
import json
from engines.cube_utils import parse_script


class TestParseScript:
    def test_dict_passthrough(self):
        d = {"tables": {}}
        assert parse_script(d) is d

    def test_valid_json_string(self):
        s = '{"tables": {}}'
        result = parse_script(s)
        assert result == {"tables": {}}

    def test_invalid_json_string(self):
        assert parse_script("not json") is None

    def test_none_input(self):
        assert parse_script(None) is None

    def test_number_input(self):
        assert parse_script(42) is None

    def test_empty_string(self):
        assert parse_script("") is None

    def test_complex_json_string(self):
        data = {"tables": {"t1": {"name": "test"}}, "cloneRel": {}}
        s = json.dumps(data, ensure_ascii=False)
        result = parse_script(s)
        assert result == data
