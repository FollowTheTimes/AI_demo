import json
import os
import re
import logging
from datetime import datetime

from config import OUTPUT_DIR
from engines.llm_gateway import LLMConnectionError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的公安大数据建模助手。你的任务是根据用户的需求描述，生成符合规范的.cube模型文件JSON结构。

关键规则：
1. 数据源表必须使用已注册的表名，不能创造新表名
2. 字段名必须使用已注册表中存在的字段
3. where条件必须包含field、title、type三个必填字段
4. cloneRel中的sourceId和targetId必须引用tables中存在的tableId
5. 必须包含title、name、ctype、version、script五个顶层字段
6. script中的tables不能为空

请严格按照以下JSON格式输出，不要包含任何其他文字说明。"""

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

        if few_shot_examples:
            prompt_parts.append("\n## 参考示例")
            for i, example in enumerate(few_shot_examples, 1):
                example_json = json.dumps(example, ensure_ascii=False, indent=2)
                prompt_parts.append(f"\n### 示例{i}: {example.get('title', '')}\n```json\n{example_json}\n```")

        prompt_parts.append("\n请根据以上信息，生成一个符合规范的.cube模型JSON。")

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

    def _extract_conditions(self, cube):
        conditions = []
        if not cube or not isinstance(cube, dict):
            return conditions

        script = cube.get("script", {})
        if isinstance(script, str):
            try:
                script = json.loads(script)
            except (json.JSONDecodeError, TypeError):
                return conditions

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
