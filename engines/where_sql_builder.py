def build_where_sql(where: dict) -> dict:
    sql_parts = []
    for field_key, condition in where.items():
        if not isinstance(condition, dict):
            continue
        field = condition.get("field", "")
        cond_type = condition.get("type", "string")
        attr = condition.get("attr", {})

        if cond_type in ("char", "string"):
            values = attr.get("multiequals", "")
            is_except = attr.get("isExcept", False)
            if values:
                value_list = [v.strip() for v in values.split(",")]
                quoted = ",".join(f"'{v}'" for v in value_list)
                if is_except:
                    sql_parts.append(f'"{field}" not in ({quoted})')
                else:
                    sql_parts.append(f'"{field}" in ({quoted})')
        elif cond_type in ("decimal", "number", "int"):
            char_l = attr.get("charL", "")
            char_u = attr.get("charU", "")
            if char_l and char_u:
                sql_parts.append(f'"{field}" >= {char_l} and "{field}" <= {char_u}')
            elif char_l:
                sql_parts.append(f'"{field}" >= {char_l}')
            elif char_u:
                sql_parts.append(f'"{field}" <= {char_u}')
        elif cond_type == "date":
            char_l = attr.get("charL", "")
            char_u = attr.get("charU", "")
            if char_l and char_u:
                sql_parts.append(f'"{field}" >= \'{char_l}\' and "{field}" <= \'{char_u}\'')
            elif char_l:
                sql_parts.append(f'"{field}" >= \'{char_l}\'')
            elif char_u:
                sql_parts.append(f'"{field}" <= \'{char_u}\'')

    if sql_parts:
        return {
            "userSql": "",
            "executeSql": "\n".join(sql_parts),
        }
    return None
