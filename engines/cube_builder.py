import copy
import json
import os
import re
from datetime import datetime

from config import TEMPLATE_DIR, OUTPUT_DIR


class CubeBuilder:

    def __init__(self):
        self.template_dir = TEMPLATE_DIR
        self.output_dir = OUTPUT_DIR

    def build(self, intent_result, template):
        cube = copy.deepcopy(template)

        model_type = intent_result.get("model_type", "")
        description = intent_result.get("description", "")

        cube["title"] = model_type
        cube["name"] = model_type
        if description:
            cube["bz"] = description

        if "conditions" in intent_result:
            where_conditions = self.adapt_conditions(intent_result["conditions"])
            self._apply_where_conditions(cube, where_conditions)

        cube["version"] = self._generate_version()
        self._clear_sample_data(cube)

        return cube

    def adapt_conditions(self, conditions):
        where_conditions = {}

        if not isinstance(conditions, dict):
            return where_conditions

        if "金额范围" in conditions:
            val = conditions["金额范围"]
            if isinstance(val, (list, tuple)) and len(val) == 2:
                where_conditions["jy_je"] = self._build_numeric_condition(
                    "jy_je", "交易金额", "between", val
                )
            else:
                where_conditions["jy_je"] = self._build_numeric_condition(
                    "jy_je", "交易金额", ">=", val
                )

        if "时间范围" in conditions:
            val = conditions["时间范围"]
            if isinstance(val, (list, tuple)) and len(val) == 2:
                where_conditions["sj"] = self._build_date_condition(
                    "sj", "交易时间", "between", val
                )
            else:
                where_conditions["sj"] = self._build_date_condition(
                    "sj", "交易时间", ">=", val
                )

        if "账户类型" in conditions:
            where_conditions["jy_zhlx"] = self._build_char_condition(
                "jy_zhlx", "账户类型", "=", conditions["账户类型"]
            )

        if "交易方向" in conditions:
            direction = conditions["交易方向"]
            jdbz_val = "出"
            if direction in ("收入", "转入", "进账"):
                jdbz_val = "进"
            elif direction in ("支出", "转出", "出账"):
                jdbz_val = "出"
            where_conditions["jdbz"] = self._build_char_condition(
                "jdbz", "借贷标志", "=", jdbz_val
            )

        if "银行" in conditions:
            where_conditions["jy_gsd"] = self._build_char_condition(
                "jy_gsd", "交易归属地", "like", conditions["银行"]
            )

        return where_conditions

    def _build_numeric_condition(self, field, title, operator, value):
        attr = {"charL": "", "charU": "", "multiequals": "", "isExcept": False}

        if operator in (">", "大于"):
            attr["charL"] = str(value)
        elif operator in ("<", "小于"):
            attr["charU"] = str(value)
        elif operator in ("=", "等于"):
            attr["charL"] = str(value)
            attr["charU"] = str(value)
        elif operator in ("between", "介于", "范围"):
            if isinstance(value, (list, tuple)) and len(value) == 2:
                attr["charL"] = str(value[0])
                attr["charU"] = str(value[1])
        elif operator in (">=", "大于等于"):
            attr["charL"] = str(value)
        elif operator in ("<=", "小于等于"):
            attr["charU"] = str(value)
        else:
            attr["multiequals"] = str(value)

        return {"field": field, "title": title, "type": "number", "attr": attr}

    def _build_date_condition(self, field, title, operator, value):
        attr = {"charL": "", "charU": "", "multiequals": "", "isExcept": False}

        if operator in ("between", "介于", "范围"):
            if isinstance(value, (list, tuple)) and len(value) == 2:
                attr["charL"] = str(value[0])
                attr["charU"] = str(value[1])
            else:
                attr["charL"] = str(value)
        elif operator in (">=", "大于等于", "之后"):
            attr["charL"] = str(value)
        elif operator in ("<=", "小于等于", "之前"):
            attr["charU"] = str(value)
        else:
            attr["charL"] = str(value)

        return {"field": field, "title": title, "type": "date", "attr": attr}

    def _build_char_condition(self, field, title, operator, value):
        attr = {"charL": "", "charU": "", "isExcept": False}

        if operator in ("!=", "不等于", "非", "排除"):
            attr["isExcept"] = True
        if operator == "like":
            attr["multiequals"] = str(value)
        elif isinstance(value, (list, tuple)):
            attr["multiequals"] = ",".join(str(v) for v in value)
        else:
            attr["multiequals"] = str(value)

        return {"field": field, "title": title, "type": "char", "attr": attr}

    def _apply_where_conditions(self, cube, where_conditions):
        script = cube.get("script")
        if isinstance(script, str):
            script_data = json.loads(script)
        else:
            script_data = script

        tables = script_data.get("tables", {})
        for table_id, table_info in tables.items():
            where = table_info.get("where", {})
            where.update(where_conditions)
            table_info["where"] = where

            where_sql_parts = []
            for field_name, condition in where_conditions.items():
                cond_type = condition.get("type")
                attr = condition.get("attr", {})

                if cond_type == "char":
                    values = attr.get("multiequals", "")
                    is_except = attr.get("isExcept", False)
                    if values:
                        value_list = [v.strip() for v in values.split(",")]
                        quoted = ",".join(f"'{v}'" for v in value_list)
                        if is_except:
                            where_sql_parts.append(
                                f'"{field_name}" not in ({quoted})'
                            )
                        else:
                            where_sql_parts.append(
                                f'"{field_name}" in ({quoted})'
                            )
                elif cond_type == "number":
                    char_l = attr.get("charL", "")
                    char_u = attr.get("charU", "")
                    if char_l and char_u:
                        where_sql_parts.append(
                            f'"{field_name}" >= {char_l} and "{field_name}" <= {char_u}'
                        )
                    elif char_l:
                        where_sql_parts.append(f'"{field_name}" >= {char_l}')
                    elif char_u:
                        where_sql_parts.append(f'"{field_name}" <= {char_u}')
                elif cond_type == "date":
                    char_l = attr.get("charL", "")
                    char_u = attr.get("charU", "")
                    if char_l and char_u:
                        where_sql_parts.append(
                            f'"{field_name}" >= \'{char_l}\' and "{field_name}" <= \'{char_u}\''
                        )
                    elif char_l:
                        where_sql_parts.append(
                            f'"{field_name}" >= \'{char_l}\''
                        )
                    elif char_u:
                        where_sql_parts.append(
                            f'"{field_name}" <= \'{char_u}\''
                        )

            if where_sql_parts:
                execute_sql = "\n".join(where_sql_parts)
                table_info["whereSql"] = {
                    "userSql": "",
                    "executeSql": execute_sql,
                }

        cube["script"] = json.dumps(script_data, ensure_ascii=False)

    def save(self, cube):
        os.makedirs(self.output_dir, exist_ok=True)
        name = cube.get("name", "未命名模型")
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_name}_{timestamp}.cube"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cube, f, ensure_ascii=False)
        return filepath

    def _generate_version(self):
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        seq = now.strftime("%H%M")
        return f"datacube_{date_str}_A{seq}"

    def _clear_sample_data(self, cube):
        script = cube.get("script")
        if isinstance(script, str):
            script_data = json.loads(script)
        else:
            script_data = script

        tables = script_data.get("tables", {})
        for table_id, table_info in tables.items():
            data = table_info.get("data", {})
            if "rows" in data:
                data["rows"] = []
            data["total"] = 0

        cube["script"] = json.dumps(script_data, ensure_ascii=False)
