import json
import logging

logger = logging.getLogger(__name__)


class CubeValidator:
    TOP_LEVEL_REQUIRED = ["title", "name", "ctype", "version", "script"]
    TABLE_REQUIRED = ["tableId", "name", "title"]
    WHERE_REQUIRED = ["field", "title", "type"]

    def __init__(self, schema_registry):
        self.schema_registry = schema_registry

    def validate(self, cube):
        errors = []

        if not isinstance(cube, dict):
            return {"valid": False, "errors": [{"path": "", "message": "cube必须是字典对象"}]}

        for field in self.TOP_LEVEL_REQUIRED:
            if field not in cube:
                errors.append({"path": field, "message": f"缺少必填字段: {field}"})

        if "script" in cube:
            script = self._parse_script(cube["script"])
            if script is None:
                errors.append({"path": "script", "message": "script不是合法的JSON字符串"})
            else:
                self._validate_script(script, errors)

        return {"valid": len(errors) == 0, "errors": errors}

    def _parse_script(self, script):
        if isinstance(script, dict):
            return script
        try:
            return json.loads(script)
        except (json.JSONDecodeError, TypeError):
            return None

    def _validate_script(self, script, errors):
        tables = script.get("tables", {})
        if not tables:
            errors.append({"path": "script.tables", "message": "tables不能为空"})
            return

        for table_id, table in tables.items():
            self._validate_table(table_id, table, errors)

        clone_rel = script.get("cloneRel", {})
        if clone_rel:
            self._validate_clone_rel(clone_rel, tables, errors)

    def _validate_table(self, table_id, table, errors):
        for field in self.TABLE_REQUIRED:
            if field not in table:
                errors.append({"path": f"script.tables.{table_id}.{field}", "message": f"table缺少必填字段: {field}"})

        table_name = table.get("name", "")
        if table_name and not self.schema_registry.table_exists(table_name):
            errors.append({"path": f"script.tables.{table_id}.name", "message": f"未注册的数据源表: {table_name}"})

        where = table.get("where", {})
        if where:
            self._validate_where(table_id, table_name, where, errors)

    def _validate_where(self, table_id, table_name, where, errors):
        for field_key, condition in where.items():
            if not isinstance(condition, dict):
                errors.append({"path": f"script.tables.{table_id}.where.{field_key}", "message": f"where条件必须是对象: {field_key}"})
                continue

            for req in self.WHERE_REQUIRED:
                if req not in condition:
                    errors.append({"path": f"script.tables.{table_id}.where.{field_key}.{req}", "message": f"where条件缺少必填字段: {req}"})

            field_name = condition.get("field", "")
            if field_name and table_name and self.schema_registry.table_exists(table_name):
                if not self.schema_registry.field_exists(table_name, field_name):
                    errors.append({"path": f"script.tables.{table_id}.where.{field_key}.field", "message": f"字段不存在: {field_name}"})

    def _validate_clone_rel(self, clone_rel, tables, errors):
        for key, rel in clone_rel.items():
            if isinstance(rel, dict):
                for id_field in ["sourceId", "targetId"]:
                    ref_id = rel.get(id_field, "")
                    if ref_id and ref_id not in tables:
                        errors.append({"path": f"script.cloneRel.{key}.{id_field}", "message": f"cloneRel引用不存在的tableId: {ref_id}"})
