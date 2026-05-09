# Issue 001: Schema Registry + 数据源查询API

## What to build

实现数据源表注册中心模块和对应的查询API。Schema Registry 从 `knowledge/schemas/` 目录加载所有 JSON schema 文件，提供表名查询、字段查询、合法性校验等接口。同时实现 `GET /api/schemas` API 端点，返回所有已注册数据源表的结构化信息。更新 `GET /api/health` 端点，增加 `schemas_loaded` 字段。

## Acceptance criteria

- [ ] Schema Registry 能从 `knowledge/schemas/bank_tables.json` 加载3张表（tt.jz_bank_bill, tt.jz_bank_zh, tt.jz_bank_zhxx）
- [ ] `table_exists(table_name)` 方法正确判断表名是否存在
- [ ] `field_exists(table_name, field_name)` 方法正确判断字段名是否存在于指定表中
- [ ] `get_all_tables()` 返回所有已注册表列表（含名称、中文名、描述）
- [ ] `get_table_fields(table_name)` 返回指定表的字段列表（含名称、中文名、类型）
- [ ] `get_schema_for_prompt()` 返回适合嵌入LLM prompt的结构化描述
- [ ] schema文件不存在时优雅降级，不崩溃
- [ ] `GET /api/schemas` 返回所有表和字段的JSON
- [ ] `GET /api/health` 返回 `schemas_loaded` 数量
- [ ] Schema Registry 有完整的单元测试

## Blocked by

None - can start immediately

## Agent Brief

**Category:** enhancement
**Summary:** 实现数据源表注册中心，提供表名/字段查询和合法性校验接口

**Current behavior:**
项目中已有 `knowledge/schemas/bank_tables.json` 定义了3张数据源表，但没有加载和查询这些schema的模块。其他模块（Cube Validator、Cube Generator）需要查询表名和字段名是否存在。

**Desired behavior:**
Schema Registry 从 `knowledge/schemas/` 目录加载所有 JSON schema 文件，提供 `table_exists()`, `field_exists()`, `get_all_tables()`, `get_table_fields()`, `get_schema_for_prompt()` 等接口。`GET /api/schemas` 返回所有表和字段。`GET /api/health` 返回 `schemas_loaded` 数量。schema文件不存在时优雅降级。

**Key interfaces:**
- `SchemaRegistry` 类 — 核心注册中心，提供查询和校验方法
- `table_exists(table_name: str) -> bool` — 判断表名是否已注册
- `field_exists(table_name: str, field_name: str) -> bool` — 判断字段名是否存在于指定表中
- `get_all_tables() -> list[dict]` — 返回所有已注册表列表
- `get_table_fields(table_name: str) -> list[dict]` — 返回指定表的字段列表
- `get_schema_for_prompt() -> str` — 返回适合嵌入LLM prompt的结构化描述
- `GET /api/schemas` — API端点，返回所有表和字段
- `GET /api/health` — 增加 `schemas_loaded` 字段

**Acceptance criteria:**
- [ ] SchemaRegistry 能加载 bank_tables.json 中的3张表
- [ ] table_exists 正确判断表名存在/不存在
- [ ] field_exists 正确判断字段名存在/不存在
- [ ] get_all_tables 返回完整表列表
- [ ] get_table_fields 返回指定表的字段列表
- [ ] get_schema_for_prompt 返回结构化的prompt描述
- [ ] schema文件不存在时不崩溃
- [ ] GET /api/schemas 正常返回
- [ ] GET /api/health 包含 schemas_loaded
- [ ] 有完整的单元测试

**Out of scope:**
- 数据源表的热加载（后续优化）
- 数据源表的CRUD操作（只需读取）
- 数据库连接（只读取JSON文件）
