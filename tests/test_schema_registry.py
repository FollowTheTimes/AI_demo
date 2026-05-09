import json
import os
import tempfile
import pytest

from engines.schema_registry import SchemaRegistry


@pytest.fixture
def sample_schema_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        schema = {
            "tt.test_table1": {
                "name": "测试表1",
                "description": "用于测试的表1",
                "fields": [
                    {"name": "id", "label": "编号", "type": "string"},
                    {"name": "amount", "label": "金额", "type": "decimal"},
                    {"name": "create_time", "label": "创建时间", "type": "datetime"},
                ],
            },
            "tt.test_table2": {
                "name": "测试表2",
                "description": "用于测试的表2",
                "fields": [
                    {"name": "zh", "label": "账号", "type": "string"},
                    {"name": "mc", "label": "名称", "type": "string"},
                ],
            },
        }
        filepath = os.path.join(tmpdir, "test_tables.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False)
        yield tmpdir


@pytest.fixture
def empty_schema_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def registry(sample_schema_dir):
    r = SchemaRegistry(schema_dir=sample_schema_dir)
    r.load()
    return r


@pytest.fixture
def empty_registry(empty_schema_dir):
    r = SchemaRegistry(schema_dir=empty_schema_dir)
    r.load()
    return r


class TestSchemaRegistryLoad:
    def test_load_with_valid_schemas(self, registry):
        assert registry.table_count == 2

    def test_load_with_empty_dir(self, empty_registry):
        assert empty_registry.table_count == 0

    def test_load_with_nonexistent_dir(self):
        r = SchemaRegistry(schema_dir="/nonexistent/path")
        r.load()
        assert r.table_count == 0

    def test_load_ignores_non_json_files(self, sample_schema_dir):
        txt_path = os.path.join(sample_schema_dir, "readme.txt")
        with open(txt_path, "w") as f:
            f.write("not a schema")
        r = SchemaRegistry(schema_dir=sample_schema_dir)
        r.load()
        assert r.table_count == 2

    def test_load_handles_invalid_json(self, sample_schema_dir):
        bad_path = os.path.join(sample_schema_dir, "bad.json")
        with open(bad_path, "w") as f:
            f.write("{invalid json")
        r = SchemaRegistry(schema_dir=sample_schema_dir)
        r.load()
        assert r.table_count == 2

    def test_lazy_load(self, sample_schema_dir):
        r = SchemaRegistry(schema_dir=sample_schema_dir)
        assert r._loaded is False
        r.table_exists("anything")
        assert r._loaded is True


class TestTableExists:
    def test_existing_table(self, registry):
        assert registry.table_exists("tt.test_table1") is True
        assert registry.table_exists("tt.test_table2") is True

    def test_nonexistent_table(self, registry):
        assert registry.table_exists("tt.nonexistent") is False

    def test_empty_registry(self, empty_registry):
        assert empty_registry.table_exists("tt.test_table1") is False


class TestFieldExists:
    def test_existing_field(self, registry):
        assert registry.field_exists("tt.test_table1", "id") is True
        assert registry.field_exists("tt.test_table1", "amount") is True
        assert registry.field_exists("tt.test_table2", "zh") is True

    def test_nonexistent_field(self, registry):
        assert registry.field_exists("tt.test_table1", "nonexistent") is False

    def test_nonexistent_table(self, registry):
        assert registry.field_exists("tt.nonexistent", "id") is False


class TestGetAllTables:
    def test_returns_all_tables(self, registry):
        tables = registry.get_all_tables()
        assert len(tables) == 2
        names = [t["name"] for t in tables]
        assert "tt.test_table1" in names
        assert "tt.test_table2" in names

    def test_table_structure(self, registry):
        tables = registry.get_all_tables()
        t1 = next(t for t in tables if t["name"] == "tt.test_table1")
        assert t1["label"] == "测试表1"
        assert t1["description"] == "用于测试的表1"

    def test_empty_registry(self, empty_registry):
        assert empty_registry.get_all_tables() == []


class TestGetTableFields:
    def test_returns_fields(self, registry):
        fields = registry.get_table_fields("tt.test_table1")
        assert len(fields) == 3
        field_names = [f["name"] for f in fields]
        assert "id" in field_names
        assert "amount" in field_names
        assert "create_time" in field_names

    def test_field_structure(self, registry):
        fields = registry.get_table_fields("tt.test_table1")
        id_field = next(f for f in fields if f["name"] == "id")
        assert id_field["label"] == "编号"
        assert id_field["type"] == "string"

    def test_nonexistent_table(self, registry):
        assert registry.get_table_fields("tt.nonexistent") == []


class TestGetSchemaForPrompt:
    def test_contains_table_names(self, registry):
        prompt = registry.get_schema_for_prompt()
        assert "tt.test_table1" in prompt
        assert "tt.test_table2" in prompt

    def test_contains_field_info(self, registry):
        prompt = registry.get_schema_for_prompt()
        assert "id" in prompt
        assert "编号" in prompt
        assert "amount" in prompt
        assert "金额" in prompt

    def test_empty_registry(self, empty_registry):
        assert empty_registry.get_schema_for_prompt() == ""


class TestTableCount:
    def test_with_schemas(self, registry):
        assert registry.table_count == 2

    def test_empty(self, empty_registry):
        assert empty_registry.table_count == 0
