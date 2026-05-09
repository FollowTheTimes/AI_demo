# Issue 005: Cube Generator + 生成API（核心）

## What to build

实现核心的 `.cube` 模型生成器和 `POST /api/generate` API端点。Cube Generator 接收用户自然语言描述，通过意图解析 → RAG检索参考模板 → 构建few-shot prompt → 调用LLM Gateway → 解析输出 → Cube Validator校验 → 自动重试的完整流程，生成合法的 `.cube` 文件。这是整个系统的核心切片。

## Acceptance criteria

- [ ] `POST /api/generate` 接收 `{"description": "用户需求"}` 返回生成结果
- [ ] 生成流程：意图解析 → RAG检索 → prompt构建 → LLM调用 → 输出解析 → 校验 → 重试
- [ ] prompt构建包含：系统指令 + 数据源schema + 参考模板示例 + 用户需求 + 格式约束
- [ ] LLM返回合法JSON时正确解析为 `.cube` 结构
- [ ] LLM返回非法JSON或校验失败时自动重试，最多3次
- [ ] 重试时将校验错误信息追加到prompt中
- [ ] 3次重试均失败时返回第1次结果 + 所有校验错误，标记 `validation_passed: false`
- [ ] 响应包含：success, model_type, confidence, file_path, file_name, cube_content, referenced_templates, validation_passed, retry_count, conditions
- [ ] 生成的 `.cube` 文件保存到 output 目录
- [ ] 生成结果中 conditions 字段包含可编辑的筛选条件列表
- [ ] 用户需求涉及未注册表时返回提示信息
- [ ] Cube Generator 有单元测试（使用mock LLM Gateway和mock Validator）

## Blocked by

- Issue 001 (Schema Registry)
- Issue 002 (Cube Validator)
- Issue 003 (LLM Gateway)
- Issue 004 (RAG Retriever 适配)

## Agent Brief

**Category:** enhancement
**Summary:** 实现核心的.cube模型生成器，通过LLM驱动生成完整模型文件

**Current behavior:**
现有CubeBuilder使用copy.deepcopy(template)模板填充方式，只能生成现有12种类型的变体，无法创造全新类型模型。

**Desired behavior:**
Cube Generator 接收用户自然语言描述，通过意图解析→RAG检索参考模板→构建few-shot prompt→调用LLM Gateway→解析输出→Cube Validator校验→自动重试的完整流程，生成合法的.cube文件。LLM直接生成完整JSON结构，模板仅作为参考示例。校验失败时自动重试最多3次，将校验错误追加到prompt中。3次均失败返回第1次结果+错误列表。

**Key interfaces:**
- `CubeGenerator` 类 — 核心生成器
- `async generate(description: str) -> dict` — 主生成方法
- 依赖 `LLMGateway` 调用大模型
- 依赖 `RAGRetriever` 获取few-shot示例
- 依赖 `SchemaRegistry` 获取数据源schema
- 依赖 `CubeValidator` 校验生成结果
- 依赖 `IntentParser` 解析用户意图
- `POST /api/generate` — API端点
- 响应结构：success, model_type, confidence, file_path, file_name, cube_content, referenced_templates, validation_passed, retry_count, conditions

**Acceptance criteria:**
- [ ] POST /api/generate 正常工作
- [ ] 生成流程完整：意图→检索→prompt→LLM→解析→校验→重试
- [ ] prompt包含系统指令+schema+模板示例+用户需求+格式约束
- [ ] 合法JSON正确解析
- [ ] 校验失败自动重试，最多3次
- [ ] 重试时追加校验错误到prompt
- [ ] 3次失败返回第1次结果+错误列表
- [ ] .cube文件保存到output目录
- [ ] conditions字段包含可编辑筛选条件
- [ ] 未注册表时返回提示
- [ ] 有单元测试（mock所有依赖）

**Out of scope:**
- 多轮交互式生成
- 生成结果缓存
- 生成历史记录查询
- 流式生成（边生成边返回）
