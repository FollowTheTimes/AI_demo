import json
import os
import logging

from config import SCHEMA_DIR

logger = logging.getLogger(__name__)


class SchemaRegistry:
    def __init__(self, schema_dir=None):
        self.schema_dir = schema_dir or SCHEMA_DIR
        self._schemas = {}
        self._loaded = False

    def load(self):
        self._schemas = {}
        if not os.path.isdir(self.schema_dir):
            logger.warning("Schema directory not found: %s", self.schema_dir)
            self._loaded = True
            return

        for filename in os.listdir(self.schema_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.schema_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for table_name, table_def in data.items():
                        if isinstance(table_def, dict) and "fields" in table_def:
                            self._schemas[table_name] = table_def
                logger.info("Loaded schema file: %s (%d tables)", filename, len(data) if isinstance(data, dict) else 0)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load schema file %s: %s", filename, e)

        self._loaded = True
        logger.info("SchemaRegistry loaded %d tables", len(self._schemas))

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def table_exists(self, table_name: str) -> bool:
        self._ensure_loaded()
        return table_name in self._schemas

    def field_exists(self, table_name: str, field_name: str) -> bool:
        self._ensure_loaded()
        table = self._schemas.get(table_name)
        if not table:
            return False
        fields = table.get("fields", [])
        return any(f.get("name") == field_name for f in fields)

    def get_all_tables(self) -> list:
        self._ensure_loaded()
        result = []
        for table_name, table_def in self._schemas.items():
            result.append({
                "name": table_name,
                "label": table_def.get("name", ""),
                "description": table_def.get("description", ""),
            })
        return result

    def get_table_fields(self, table_name: str) -> list:
        self._ensure_loaded()
        table = self._schemas.get(table_name)
        if not table:
            return []
        return table.get("fields", [])

    def get_schema_for_prompt(self) -> str:
        self._ensure_loaded()
        lines = []
        for table_name, table_def in self._schemas.items():
            label = table_def.get("name", "")
            desc = table_def.get("description", "")
            lines.append(f"表名: {table_name} ({label}) - {desc}")
            lines.append("字段:")
            for field in table_def.get("fields", []):
                fname = field.get("name", "")
                flabel = field.get("label", "")
                ftype = field.get("type", "")
                lines.append(f"  - {fname} ({flabel}, {ftype})")
            lines.append("")
        return "\n".join(lines)

    @property
    def table_count(self) -> int:
        self._ensure_loaded()
        return len(self._schemas)
