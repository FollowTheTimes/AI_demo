import json
import os
import copy
import logging
from config import KNOWLEDGE_DIR
from engines.cube_utils import parse_script

logger = logging.getLogger(__name__)


class RAGRetriever:

    def __init__(self):
        self.templates = []
        self.index = {}
        self.template_dir = os.path.join(KNOWLEDGE_DIR, "templates")

    def load_templates(self) -> list:
        self.templates = []
        if not os.path.exists(self.template_dir):
            logger.warning(f"模板目录不存在: {self.template_dir}")
            return self.templates

        for filename in os.listdir(self.template_dir):
            if not filename.endswith(".cube"):
                continue
            filepath = os.path.join(self.template_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    cube_data = json.load(f)

                script_raw = cube_data.get("script", "{}")
                if isinstance(script_raw, str):
                    cube_data["script"] = json.loads(script_raw)

                self.templates.append(cube_data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"加载模板失败 {filename}: {e}")

        return self.templates

    def build_index(self) -> dict:
        self.index = {}
        for template in self.templates:
            title = template.get("title", "")
            name = template.get("name", "")
            bz = template.get("bz", "") or ""

            index_text = f"{title} {name} {bz}".lower()
            tokens = set(self._tokenize(index_text))

            script = template.get("script", {})
            if isinstance(script, dict):
                tables = script.get("tables", {})
                for table_info in tables.values():
                    table_name = table_info.get("name", "")
                    table_title = table_info.get("title", "")
                    tokens.update(self._tokenize(f"{table_name} {table_title}".lower()))

            self.index[title] = {
                "template": template,
                "tokens": tokens,
            }

        return self.index

    def search(self, intent: dict, top_k: int = 3) -> list:
        model_type = intent.get("model_type", "")
        keywords = intent.get("keywords", [])

        exact_matches = []
        for title, entry in self.index.items():
            if model_type and model_type in title:
                exact_matches.append({
                    "template": entry["template"],
                    "score": 1.0,
                    "match_type": "精确匹配",
                })

        keyword_results = []
        query_tokens = set(self._tokenize(f"{model_type} {' '.join(keywords)}".lower()))

        for title, entry in self.index.items():
            if any(m["template"].get("title") == title for m in exact_matches):
                continue

            similarity = self._calculate_similarity(query_tokens, entry["tokens"])
            if similarity > 0:
                keyword_results.append({
                    "template": entry["template"],
                    "score": similarity,
                    "match_type": "关键词匹配",
                })

        keyword_results.sort(key=lambda x: x["score"], reverse=True)

        results = exact_matches + keyword_results
        results = results[:top_k]
        for result in results:
            result["summary"] = self.get_template_summary(result["template"])
        return results

    def get_template_summary(self, template: dict) -> dict:
        summary = {
            "title": template.get("title", ""),
            "name": template.get("name", ""),
            "bz": template.get("bz", ""),
        }
        script = template.get("script", {})
        script = parse_script(script)
        if script is None:
            script = {}

        if isinstance(script, dict):
            script_summary = {"tables": {}, "cloneRel": script.get("cloneRel", {})}
            for table_id, table in script.get("tables", {}).items():
                table_copy = copy.deepcopy(table)
                if "data" in table_copy:
                    del table_copy["data"]
                script_summary["tables"][table_id] = table_copy
            summary["script"] = script_summary

        return summary

    def get_few_shot_examples(self, intent: dict, max_examples: int = 3) -> list:
        search_results = self.search(intent, top_k=max_examples)
        examples = []
        for result in search_results:
            template = result["template"]
            example = {
                "title": template.get("title", ""),
                "name": template.get("name", ""),
                "bz": template.get("bz", ""),
                "ctype": template.get("ctype", "1"),
                "version": template.get("version", ""),
            }
            script = template.get("script", {})
            script = parse_script(script)
            if script is not None:
                example["script"] = script
            else:
                script = {}

            if isinstance(script, dict):
                clean_tables = {}
                for table_id, table in script.get("tables", {}).items():
                    clean_table = {
                        "tableId": table.get("tableId", table_id),
                        "name": table.get("name", ""),
                        "title": table.get("title", ""),
                    }
                    if "where" in table:
                        clean_where = {}
                        for wk, wc in table["where"].items():
                            if isinstance(wc, dict):
                                clean_where[wk] = {
                                    "field": wc.get("field", ""),
                                    "title": wc.get("title", ""),
                                    "type": wc.get("type", "string"),
                                    "attr": wc.get("attr", {}),
                                }
                        clean_table["where"] = clean_where
                    if "whereSql" in table:
                        clean_table["whereSql"] = table["whereSql"]
                    clean_tables[table_id] = clean_table
                script["tables"] = clean_tables

                clone_rel = script.get("cloneRel", {})
                if clone_rel:
                    clean_clone = {}
                    for key, rel in clone_rel.items():
                        if isinstance(rel, dict):
                            clean_clone[key] = {
                                "sourceId": rel.get("sourceId", rel.get("from", "")),
                                "targetId": rel.get("targetId", rel.get("to", "")),
                            }
                        else:
                            clean_clone[key] = rel
                    script["cloneRel"] = clean_clone
                else:
                    script["cloneRel"] = {}

            examples.append(example)
        return examples

    def get_template(self, name: str) -> dict:
        for template in self.templates:
            if template.get("name") == name or template.get("title") == name:
                return template
        return None

    def _calculate_similarity(self, set_a: set, set_b: set) -> float:
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _tokenize(self, text: str) -> list:
        tokens = []
        current = ""
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                if current:
                    tokens.append(current.lower())
                    current = ""
                tokens.append(ch)
            elif ch.isalnum():
                current += ch
            else:
                if current:
                    tokens.append(current.lower())
                    current = ""
        if current:
            tokens.append(current.lower())
        return tokens
