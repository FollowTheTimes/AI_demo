import json


def parse_script(script):
    if isinstance(script, dict):
        return script
    if isinstance(script, str):
        try:
            return json.loads(script)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def normalize_tables(script):
    if not isinstance(script, dict):
        return script

    tables = script.get("tables")
    if tables is None:
        script["tables"] = {}
        return script

    if isinstance(tables, dict):
        return script

    if isinstance(tables, list):
        normalized = {}
        for i, table in enumerate(tables):
            if isinstance(table, dict):
                table_id = table.get("tableId") or table.get("table_id") or f"table-{i+1}"
                table["tableId"] = table_id
                normalized[table_id] = table
        script["tables"] = normalized
        return script

    script["tables"] = {}
    return script
