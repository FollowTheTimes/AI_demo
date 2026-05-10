import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_llm_gateway():
    gw = AsyncMock()
    gw.check_available = AsyncMock(return_value=False)
    gw.generate = AsyncMock(return_value=json.dumps({
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
    return gw


@pytest.fixture
def client(mock_llm_gateway):
    with patch("main.LLMGateway", return_value=mock_llm_gateway):
        from main import create_app
        app = create_app()
        with TestClient(app) as c:
            yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "templates_loaded" in data
        assert "schemas_loaded" in data
        assert "llm_available" in data

    def test_health_llm_available_is_boolean(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert isinstance(data["llm_available"], bool)


class TestSchemasEndpoint:
    def test_schemas_returns_tables(self, client):
        resp = client.get("/api/schemas")
        assert resp.status_code == 200
        data = resp.json()
        assert "tables" in data
        assert isinstance(data["tables"], list)

    def test_schemas_table_structure(self, client):
        resp = client.get("/api/schemas")
        data = resp.json()
        if len(data["tables"]) > 0:
            table = data["tables"][0]
            assert "name" in table
            assert "label" in table
            assert "fields" in table


class TestTemplatesEndpoint:
    def test_templates_returns_list(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)

    def test_templates_structure(self, client):
        resp = client.get("/api/templates")
        data = resp.json()
        if len(data["templates"]) > 0:
            t = data["templates"][0]
            assert "name" in t
            assert "title" in t
            assert "bz" in t


class TestGenerateEndpoint:
    def test_generate_returns_result(self, client):
        resp = client.post("/api/generate", json={"description": "分析试卡行为"})
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "cube_content" in data

    def test_generate_with_empty_description(self, client):
        resp = client.post("/api/generate", json={"description": ""})
        assert resp.status_code == 200

    def test_generate_result_has_conditions(self, client):
        resp = client.post("/api/generate", json={"description": "分析试卡行为"})
        data = resp.json()
        if data.get("success"):
            assert "conditions" in data
            assert isinstance(data["conditions"], list)


class TestConditionsEndpoints:
    def test_parse_conditions(self, client):
        cube_content = {
            "title": "test",
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
                        },
                    },
                },
                "cloneRel": {},
            },
        }
        resp = client.post("/api/parse-conditions", json=cube_content)
        assert resp.status_code == 200
        data = resp.json()
        assert "conditions" in data
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["field"] == "jdbz"

    def test_update_conditions(self, client):
        cube_content = {
            "title": "test",
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
                        },
                    },
                },
                "cloneRel": {},
            },
        }
        resp = client.patch("/api/conditions", json={
            "cube_content": cube_content,
            "conditions": [{"table_id": "t1", "field": "jdbz", "value": "出"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["cube_content"]["script"]["tables"]["t1"]["where"]["w1"]["attr"]["multiequals"] == "出"

    def test_update_conditions_nonexistent_field(self, client):
        cube_content = {
            "title": "test",
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
                        },
                    },
                },
                "cloneRel": {},
            },
        }
        resp = client.patch("/api/conditions", json={
            "cube_content": cube_content,
            "conditions": [{"table_id": "t1", "field": "nonexistent", "value": "test"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False


class TestCleanEndpoint:
    def test_clean_data(self, client):
        resp = client.post("/api/clean", json={
            "data": [
                {"jylsh": "001", "jy_je": "1,000", "jdbz": "贷"},
                {"jylsh": "001", "jy_je": "1,000", "jdbz": "贷"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["cleaned_count"] == 1
        assert data["original_count"] == 2

    def test_clean_with_rules(self, client):
        resp = client.post("/api/clean", json={
            "data": [{"jy_je": "1,000"}],
            "rules": ["amount"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_clean_empty_data(self, client):
        resp = client.post("/api/clean", json={"data": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["cleaned_count"] == 0


class TestDownloadEndpoint:
    def test_download_nonexistent_file(self, client):
        resp = client.get("/api/download/nonexistent.cube")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
