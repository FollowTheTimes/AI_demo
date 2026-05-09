# Issue 004: RAG Retriever 适配 + 模板摘要

## What to build

适配现有 RAG Retriever 模块，为 Cube Generator 提供结构化的模板摘要（而非直接返回完整模板），减少 LLM prompt token 消耗。新增按用户意图智能选择1-3个最相关模板作为 few-shot 示例的功能。保留现有模板加载和索引构建逻辑。

## Acceptance criteria

- [ ] 保留现有 `load_templates()` 和 `build_index()` 逻辑不变
- [ ] 新增 `get_template_summary(template)` 方法，返回精简的模板摘要（title/name/bz/tables概要/where概要），去除data.rows等大数据字段
- [ ] `search()` 方法返回结果中包含模板摘要而非完整模板
- [ ] 新增 `get_few_shot_examples(intent, max_examples=3)` 方法，按意图选择最相关的1-3个模板作为 few-shot 示例
- [ ] few-shot 示例包含完整的 `.cube` 结构（供LLM学习格式），但去除 data.rows
- [ ] `GET /api/templates` 接口保持不变
- [ ] RAG Retriever 适配后有回归测试

## Blocked by

None - can start immediately

## Agent Brief

**Category:** enhancement
**Summary:** 适配RAG Retriever，新增模板摘要和few-shot示例选择功能

**Current behavior:**
RAG Retriever 的 search() 方法返回完整模板（含data.rows等大数据），直接作为prompt会消耗大量token。没有按意图选择few-shot示例的功能。

**Desired behavior:**
新增 `get_template_summary(template)` 方法返回精简摘要（去除data.rows）。`search()` 返回摘要而非完整模板。新增 `get_few_shot_examples(intent, max_examples=3)` 方法，按意图选择1-3个最相关模板作为few-shot示例（包含完整结构但去除data.rows）。保留现有load_templates()和build_index()逻辑。

**Key interfaces:**
- `get_template_summary(template: dict) -> dict` — 返回精简摘要
- `get_few_shot_examples(intent: dict, max_examples: int = 3) -> list[dict]` — 返回few-shot示例
- `search()` 返回结果结构变更：包含摘要而非完整模板

**Acceptance criteria:**
- [ ] load_templates和build_index逻辑不变
- [ ] get_template_summary去除data.rows保留结构
- [ ] search返回摘要而非完整模板
- [ ] get_few_shot_examples按意图选择1-3个模板
- [ ] few-shot示例包含完整结构但去除data.rows
- [ ] GET /api/templates接口不变
- [ ] 有回归测试

**Out of scope:**
- 向量数据库替换Jaccard相似度
- 模板增量更新
- 模板版本管理
