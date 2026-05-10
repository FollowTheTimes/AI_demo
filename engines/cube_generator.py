import json
import os
import re
import logging
from datetime import datetime

from config import OUTPUT_DIR
from engines.llm_gateway import LLMConnectionError, LLMTimeoutError
from engines.cube_utils import parse_script, normalize_tables

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的公安大数据建模助手。你的任务是根据用户的需求描述，生成符合规范的.cube模型文件JSON结构。

输出格式要求：
1. 顶层必须有5个字段：title、name、ctype、version、script
2. script是一个包含tables和cloneRel的对象
3. tables的value是对象（key为tableId），不能是数组
4. 每个table必须有tableId、name、title
5. where条件必须有field、title、type、attr
6. 只能使用"可用数据源表"中列出的表名和字段

表名映射规则（重要）：
- table的name字段必须使用"可用数据源表"中的英文表名（如tt.jz_bank_zh），不能用中文
- 表名后面跟着中文的才是标题

直接输出JSON，不要使用markdown代码块，不要输出任何其他文字。"""

MAX_RETRIES = 3


class CubeGenerator:
    def __init__(self, llm_gateway, schema_registry, rag_retriever, intent_parser, validator):
        self.llm_gateway = llm_gateway
        self.schema_registry = schema_registry
        self.rag_retriever = rag_retriever
        self.intent_parser = intent_parser
        self.validator = validator
        self.output_dir = OUTPUT_DIR

    async def generate(self, description: str) -> dict:
        try:
            intent = await self.intent_parser.parse(description)
        except Exception as e:
            logger.error(f"意图解析失败: {e}")
            intent = {"model_type": "", "keywords": [], "confidence": 0, "description": description}

        model_type = intent.get("model_type", "")
        keywords = intent.get("keywords", [])
        confidence = intent.get("confidence", 0)

        few_shot_examples = self.rag_retriever.get_few_shot_examples(intent, max_examples=3)
        schema_info = self.schema_registry.get_schema_for_prompt()

        prompt = self._build_prompt(description, schema_info, few_shot_examples)

        first_result = None
        all_errors = []
        retry_count = 0

        for attempt in range(MAX_RETRIES):
            retry_count = attempt
            try:
                current_prompt = prompt
                if all_errors:
                    error_text = "\n".join(
                        f"- {e.get('path', '')}: {e.get('message', '')}" for e in all_errors
                    )
                    current_prompt = prompt + f"\n\n上次生成的结果存在以下校验错误，请修正：\n{error_text}"

                llm_output = await self.llm_gateway.generate(
                    current_prompt,
                    system_prompt=SYSTEM_PROMPT,
                    format_json=True,
                )

                cube = self._parse_llm_output(llm_output)
                if cube is None:
                    all_errors.append({"path": "", "message": "LLM输出不是合法JSON"})
                    continue

                cube = self._normalize_cube(cube)

                if first_result is None:
                    first_result = cube

                validation = self.validator.validate(cube)
                if validation["valid"]:
                    conditions = self._extract_conditions(cube)
                    file_path = self._save_cube(cube)
                    referenced = [ex.get("title", "") for ex in few_shot_examples]

                    return {
                        "success": True,
                        "model_type": model_type,
                        "confidence": confidence,
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "cube_content": cube,
                        "referenced_templates": referenced,
                        "validation_passed": True,
                        "retry_count": retry_count,
                        "conditions": conditions,
                    }

                all_errors = validation["errors"]

            except LLMConnectionError as e:
                logger.error(f"LLM连接错误: {e}")
                return {
                    "success": False,
                    "model_type": model_type,
                    "confidence": confidence,
                    "message": f"LLM服务连接失败: {e}",
                    "cube_content": None,
                    "referenced_templates": [],
                    "validation_passed": False,
                    "retry_count": retry_count,
                    "conditions": [],
                }

            except LLMTimeoutError as e:
                logger.error(f"LLM超时: {e}")
                return {
                    "success": False,
                    "model_type": model_type,
                    "confidence": confidence,
                    "message": f"LLM请求超时，请稍后重试: {e}",
                    "cube_content": None,
                    "referenced_templates": [],
                    "validation_passed": False,
                    "retry_count": retry_count,
                    "conditions": [],
                }

        conditions = self._extract_conditions(first_result) if first_result else []
        file_path = self._save_cube(first_result) if first_result else ""
        referenced = [ex.get("title", "") for ex in few_shot_examples]

        return {
            "success": True,
            "model_type": model_type,
            "confidence": confidence,
            "file_path": file_path,
            "file_name": os.path.basename(file_path) if file_path else "",
            "cube_content": first_result,
            "referenced_templates": referenced,
            "validation_passed": False,
            "retry_count": retry_count,
            "conditions": conditions,
            "validation_errors": all_errors,
        }

    def _build_prompt(self, description, schema_info, few_shot_examples):
        prompt_parts = []

        prompt_parts.append(f"## 用户需求\n{description}")

        prompt_parts.append(f"\n## 可用数据源表\n{schema_info}")

        prompt_parts.append("\n请根据以上信息，生成一个符合规范的.cube模型JSON。")
        prompt_parts.append("\n输出格式：")
        prompt_parts.append('{')
        prompt_parts.append('  "title": "模型标题",')
        prompt_parts.append('  "name": "模型英文名",')
        prompt_parts.append('  "bz": "模型描述",')
        prompt_parts.append('  "ctype": "1",')
        prompt_parts.append('  "version": "datacube_20260317_T1710",')
        prompt_parts.append('  "script": {')
        prompt_parts.append('    "tables": {')
        prompt_parts.append('      "table-1": {')
        prompt_parts.append('        "tableId": "table-1",')
        prompt_parts.append('        "name": "已注册的表名",')
        prompt_parts.append('        "title": "表标题",')
        prompt_parts.append('        "where": {')
        prompt_parts.append('          "w1": {')
        prompt_parts.append('            "field": "字段名",')
        prompt_parts.append('            "title": "字段标题",')
        prompt_parts.append('            "type": "字段类型(string/decimal/date等)",')
        prompt_parts.append('            "attr": {"charL": "", "charU": "", "multiequals": "值", "isExcept": false}')
        prompt_parts.append('          }')
        prompt_parts.append('        }')
        prompt_parts.append('      }')
        prompt_parts.append('    },')
        prompt_parts.append('    "cloneRel": {}')
        prompt_parts.append('  }')
        prompt_parts.append('}')
        prompt_parts.append("\n注意：")
        prompt_parts.append("- 只能使用上面'可用数据源表'中列出的表名和字段")
        prompt_parts.append("- tables必须是对象（key-value），不能是数组")
        prompt_parts.append("- 不要使用markdown代码块包裹，不要输出任何其他文字")

        return "\n".join(prompt_parts)

    def _parse_llm_output(self, output: str):
        if isinstance(output, dict):
            return output
        try:
            cleaned = output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None

    def _normalize_cube(self, cube):
        if not isinstance(cube, dict):
            return cube
        script = cube.get("script")
        if script is None:
            return cube
        script = parse_script(script)
        if script is None:
            return cube
        script = normalize_tables(script)
        cube["script"] = script
        return cube

    def _extract_conditions(self, cube):
        conditions = []
        if not cube or not isinstance(cube, dict):
            return conditions

        script = cube.get("script", {})
        script = parse_script(script)
        if not isinstance(script, dict):
            return conditions

        for table_id, table in script.get("tables", {}).items():
            where = table.get("where", {})
            for field_key, condition in where.items():
                if isinstance(condition, dict) and "field" in condition and "title" in condition:
                    conditions.append({
                        "field": condition["field"],
                        "title": condition["title"],
                        "type": condition.get("type", ""),
                        "table_id": table_id,
                        "where_key": field_key,
                    })

        return conditions

    def _save_cube(self, cube):
        if not cube:
            return ""
        os.makedirs(self.output_dir, exist_ok=True)
        name = cube.get("title", cube.get("name", "未命名模型"))
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{safe_name}_{timestamp}.cube"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cube, f, ensure_ascii=False, indent=2)
        return filepath
