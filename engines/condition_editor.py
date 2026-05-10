import json
import copy
import logging
from engines.where_sql_builder import build_where_sql

logger = logging.getLogger(__name__)

OPERATORS_BY_TYPE = {
    "string": ["等于", "排除", "包含"],
    "char": ["等于", "排除", "包含"],
    "decimal": ["大于等于", "小于等于", "介于", "等于"],
    "number": ["大于等于", "小于等于", "介于", "等于"],
    "date": ["之后", "之前", "介于"],
    "int": ["大于等于", "小于等于", "介于", "等于"],
}


class ConditionEditor:
    def parse_conditions(self, cube_content: dict) -> list:
        conditions = []
        if not isinstance(cube_content, dict):
            return conditions

        script = cube_content.get("script", {})
        if isinstance(script, str):
            try:
                script = json.loads(script)
            except (json.JSONDecodeError, TypeError):
                return conditions

        if not isinstance(script, dict):
            return conditions

        for table_id, table in script.get("tables", {}).items():
            where = table.get("where", {})
            if not where:
                continue
            for where_key, condition in where.items():
                if not isinstance(condition, dict):
                    continue
                field = condition.get("field", "")
                title = condition.get("title", "")
                cond_type = condition.get("type", "string")
                attr = condition.get("attr", {})

                current_value = self._extract_current_value(cond_type, attr)

                operators = OPERATORS_BY_TYPE.get(cond_type, ["等于", "排除"])

                conditions.append({
                    "table_id": table_id,
                    "where_key": where_key,
                    "field": field,
                    "title": title,
                    "type": cond_type,
                    "current_value": current_value,
                    "available_operators": operators,
                })

        return conditions

    def update_conditions(self, cube_content: dict, conditions: list) -> dict:
        cube = copy.deepcopy(cube_content)
        errors = []

        script = cube.get("script", {})
        if isinstance(script, str):
            try:
                script = json.loads(script)
                cube["script"] = script
            except (json.JSONDecodeError, TypeError):
                return {"errors": [{"message": "script不是合法JSON"}]}

        if not isinstance(script, dict):
            return {"errors": [{"message": "script格式错误"}]}

        tables = script.get("tables", {})

        for cond_update in conditions:
            table_id = cond_update.get("table_id", "")
            field = cond_update.get("field", "")
            value = cond_update.get("value")

            if table_id not in tables:
                errors.append({"table_id": table_id, "field": field, "message": f"tableId不存在: {table_id}"})
                continue

            table = tables[table_id]
            where = table.get("where", {})

            found = False
            for where_key, condition in where.items():
                if isinstance(condition, dict) and condition.get("field") == field:
                    self._apply_value(condition, value)
                    found = True
                    break

            if not found:
                errors.append({"table_id": table_id, "field": field, "message": f"字段不存在: {field}"})

        for table_id, table in tables.items():
            where = table.get("where", {})
            if where:
                self._update_where_sql(table, where)

        if errors:
            cube["errors"] = errors

        return cube

    def _extract_current_value(self, cond_type, attr):
        if cond_type in ("decimal", "number", "int"):
            char_l = attr.get("charL", "")
            char_u = attr.get("charU", "")
            if char_l and char_u:
                return {"charL": char_l, "charU": char_u}
            elif char_l:
                return {"charL": char_l, "charU": ""}
            elif char_u:
                return {"charL": "", "charU": char_u}
            return {"charL": "", "charU": ""}
        elif cond_type == "date":
            char_l = attr.get("charL", "")
            char_u = attr.get("charU", "")
            if char_l and char_u:
                return {"charL": char_l, "charU": char_u}
            return {"charL": char_l, "charU": char_u}
        else:
            return attr.get("multiequals", "")

    def _apply_value(self, condition, value):
        cond_type = condition.get("type", "string")
        attr = condition.get("attr", {})

        if cond_type in ("decimal", "number", "int", "date"):
            if isinstance(value, dict):
                attr["charL"] = value.get("charL", "")
                attr["charU"] = value.get("charU", "")
            else:
                attr["charL"] = str(value)
                attr["charU"] = ""
        else:
            if isinstance(value, list):
                attr["multiequals"] = ",".join(str(v) for v in value)
            else:
                attr["multiequals"] = str(value)

        condition["attr"] = attr

    def _update_where_sql(self, table, where):
        where_sql = build_where_sql(where)
        if where_sql:
            table["whereSql"] = where_sql
