# PRD: AI智能建模引擎（LLM驱动版）

## Problem Statement

公安大数据研判分析平台的分析人员需要手工配置 `.cube` 模型文件来执行数据建模分析（如试卡行为分析、资金快进快出分析等）。手工建模门槛高、耗时长，且只能创建已有类型的模型变体。分析人员希望能用一句话描述需求，由AI自动生成可用的模型文件，甚至能生成现有12种类型之外的全新模型。

## Solution

构建一个LLM驱动的AI智能建模引擎，接收用户自然语言描述，通过内网大模型自动生成符合平台规范的 `.cube` 模型文件。12个现有模板作为 few-shot 示例帮助LLM学习结构规律，数据源表限定为已注册表以确保生成结果可直接在平台运行。生成后用户可微调筛选条件，确认后下载 `.cube` 文件手动导入平台。

## User Stories

1. As a 数据分析人员, I want to 用一句话描述建模需求并自动生成模型文件, so that 我不需要手工配置复杂的筛选条件和表关联
2. As a 数据分析人员, I want to 生成现有12种类型之外的全新模型, so that 我可以应对12种模板无法覆盖的新分析场景
3. As a 数据分析人员, I want to 生成后微调筛选条件, so that 我可以在AI生成的基础上做小幅调整而无需重新生成
4. As a 数据分析人员, I want to 下载生成的.cube文件, so that 我可以手动导入到公安大数据研判分析平台
5. As a 数据分析人员, I want to 系统自动校验生成结果, so that 我拿到的文件格式一定是合法的
6. As a 数据分析人员, I want to 看到生成结果中使用了哪些数据源表和筛选条件, so that 我可以理解AI的建模逻辑
7. As a 数据分析人员, I want to 在需求涉及未注册表时收到提示, so that 我知道需要先注册新数据源
8. As a 数据分析人员, I want to 系统在政务内网完全离线运行, so that 数据不会泄露到外网
9. As a 系统管理员, I want to 注册新的数据源表, so that AI生成时可以引用更多数据源
10. As a 系统管理员, I want to 配置内网大模型的API地址和格式, so that 系统可以对接不同的大模型服务
11. As a 数据分析人员, I want to 查看所有可用的模板列表, so that 我可以了解现有建模能力
12. As a 数据分析人员, I want to 查看所有已注册的数据源表和字段, so that 我可以在描述需求时使用正确的表名和字段名
13. As a 数据分析人员, I want to AI生成时自动选择最相关的模板作为参考, so that 生成结果更符合已有建模规范
14. As a 数据分析人员, I want to 生成失败时系统自动重试, so that 我不需要反复提交相同需求
15. As a 数据分析人员, I want to 3次重试仍失败时看到错误提示和最佳尝试结果, so that 我可以手动修正或调整描述
16. As a 数据分析人员, I want to 微调筛选条件时看到字段名和操作符的可选列表, so that 我不会输入无效的条件
17. As a 数据分析人员, I want to 使用数据清洗功能独立清洗原始数据, so that 导入平台的数据质量更高
18. As a 数据分析人员, I want to AI引擎嵌入现有平台界面, so that 我不需要在多个系统之间切换
19. As a 系统管理员, I want to 查看生成历史记录, so that 我可以追溯模型来源
20. As a 数据分析人员, I want to 在生成结果中看到匹配的参考模板和相似度, so that 我可以判断生成结果的可靠程度

## Implementation Decisions

### 模块架构

系统由7个模块组成，5个新建 + 2个保留：

#### 新建模块

**1. LLM Gateway** — 统一的内网大模型调用层

- 屏蔽不同LLM API格式的差异（Ollama `/api/generate`、OpenAI兼容 `/v1/chat/completions`、自定义API）
- 提供统一的 `generate(prompt, system_prompt, format_json) -> str` 接口
- 支持配置切换API类型，默认Ollama格式
- 内置超时控制和错误处理
- 支持流式/非流式两种模式

**2. Cube Generator** — 核心生成器

- 接收意图解析结果 + RAG检索到的参考模板 + 数据源schema
- 构建 few-shot prompt：系统指令 + 数据源schema + 参考模板示例 + 用户需求
- 调用 LLM Gateway 获取生成结果
- 解析LLM输出为 `.cube` JSON结构
- 与 Cube Validator 配合实现自动校验+重试（最多3次）
- 记录每次生成的prompt和结果用于调试

**3. Cube Validator** — 校验器

- 校验JSON格式合法性
- 校验必填字段存在：title, name, ctype, version, script
- 校验script内部结构：tables非空，每个table包含tableId/name/title/where
- 校验数据源表名在已注册表中
- 校验字段名在对应表的schema中存在
- 校验where条件结构合法（field/title/type/attr）
- 校验cloneRel引用的表ID在tables中存在
- 返回校验结果：通过/失败 + 具体错误列表

**4. Schema Registry** — 数据源表注册中心

- 从 `knowledge/schemas/` 目录加载所有schema文件
- 提供查询接口：获取所有表名、获取表字段列表、校验表名/字段名是否存在
- 支持热加载：新增schema文件后无需重启
- 为 LLM prompt 提供结构化的表和字段描述

**5. Condition Editor** — 筛选条件微调器

- 解析 `.cube` 文件中 tables 的 where 条件
- 提供结构化的条件列表（字段名/标题/类型/当前值）
- 支持修改条件值并重新序列化到 `.cube` 文件
- 同步更新 whereSql 字段
- 不允许增删表或修改表结构

#### 保留模块

**6. RAG Retriever** — 模板检索器（已有，需适配）

- 保留现有的模板加载和索引构建逻辑
- 新增：为 Cube Generator 提供结构化的模板摘要（而非直接返回完整模板），减少prompt token消耗
- 新增：按用户意图智能选择1-3个最相关模板作为 few-shot 示例

**7. Data Cleaner** — 数据清洗引擎（已有，保持不变）

- 独立功能，与模型生成流程无关
- 保留现有的身份证校验、手机号提取、金额标准化、去重、时间标准化功能

### API 设计

```
POST /api/generate
  请求: { "description": "用户需求描述" }
  响应: {
    "success": bool,
    "model_type": "意图类型",
    "confidence": float,
    "file_path": "生成的.cube文件路径",
    "file_name": "文件名",
    "cube_content": { ... },
    "referenced_templates": [...],
    "validation_passed": bool,
    "retry_count": int,
    "conditions": [ { 可编辑的筛选条件列表 } ]
  }

PATCH /api/conditions
  请求: { "cube_content": { ... }, "conditions": [ { 修改后的条件 } ] }
  响应: { "success": bool, "cube_content": { ... }, "file_path": "更新后的文件路径" }

GET /api/schemas
  响应: { "tables": [ { "name": "表名", "label": "中文名", "fields": [...] } ] }

POST /api/clean
  请求: { "data": [...], "rules": [...] }
  响应: { "success": bool, "cleaned_count": int, "report": { ... } }

GET /api/templates
  响应: { "templates": [ { "name": "", "title": "", "bz": "" } ] }

GET /api/health
  响应: { "status": "ok", "templates_loaded": int, "schemas_loaded": int, "llm_available": bool }
```

### LLM Prompt 策略

Cube Generator 构建 prompt 时遵循以下结构：

1. **系统指令**：定义角色（公安数据建模专家）、输出格式（严格JSON）、约束（只能用已注册表）
2. **数据源schema**：所有已注册表的名称、中文名、字段列表及类型
3. **参考模板示例**：RAG检索到的1-3个最相关模板的完整 `.cube` 结构
4. **用户需求**：原始描述 + 意图解析结果
5. **格式约束**：必须输出合法JSON，必须包含哪些字段

### 校验重试策略

- 第1次生成后校验，通过则直接返回
- 校验失败时，将校验错误信息追加到prompt中，重新调用LLM
- 最多重试3次
- 3次均失败则返回第1次生成结果 + 所有校验错误列表，标记 `validation_passed: false`

## Testing Decisions

### 测试原则

- 只测试外部行为，不测试实现细节
- 每个模块独立测试，使用mock替代外部依赖

### Cube Validator 测试

- 测试合法 `.cube` 文件通过校验
- 测试非法JSON被正确拒绝
- 测试缺少必填字段（title/name/ctype/version/script）被检测
- 测试引用未注册表名被检测
- 测试引用不存在字段名被检测
- 测试where条件结构不合法被检测
- 测试cloneRel引用不存在的tableId被检测
- 测试空tables被检测

### Cube Generator 测试

- 测试prompt构建包含schema、模板示例、用户需求
- 测试LLM返回合法JSON时正确解析
- 测试LLM返回非法JSON时触发重试
- 测试重试次数不超过3次
- 测试3次重试失败后返回最佳尝试+错误列表
- 测试校验错误信息正确追加到重试prompt中
- 使用mock LLM Gateway，不依赖真实大模型

### Schema Registry 测试

- 测试加载schema文件并正确解析
- 测试查询表名存在/不存在
- 测试查询字段名存在/不存在
- 测试获取所有表列表
- 测试获取指定表的字段列表
- 测试schema文件不存在时的降级处理

### Condition Editor 测试

- 测试解析where条件为结构化列表
- 测试修改条件值后正确序列化回 `.cube`
- 测试修改条件后whereSql同步更新
- 测试不允许修改表结构（增删表操作被拒绝）
- 测试修改不存在的字段被拒绝

## Out of Scope

- **自动导入平台**：第一版不实现自动调用平台API导入，用户需手动导入（ADR-0005）
- **平台界面嵌入**：前端界面独立提供，嵌入现有平台的具体集成方式不在本PRD范围
- **用户认证**：AI引擎不实现用户登录，认证由现有平台处理
- **模型运行**：AI引擎只生成 `.cube` 文件，不执行模型运行
- **数据存储**：AI引擎不存储业务数据，只存储生成的 `.cube` 文件
- **多轮对话**：一步生成，不支持多轮交互式生成
- **LLM训练/微调**：使用现有内网大模型，不做模型训练或微调
- **数据清洗与模型生成的联动**：数据清洗是独立功能，不作为模型生成的前置步骤

## Further Notes

- 现有 `d:\demo\ai_engine` 目录中的代码是模板填充架构（v1），需要升级为LLM驱动架构（v2）
- 保留 `rag_retriever.py` 和 `data_cleaner.py` 的核心逻辑，其余模块需要重写
- 内网大模型API格式待确认，LLM Gateway 需要支持多种API格式的适配
- 12个 `.cube` 模板文件已复制到 `knowledge/templates/` 目录
- 数据源schema已定义在 `knowledge/schemas/bank_tables.json`
- 5个ADR文档已保存在 `docs/adr/` 目录
- CONTEXT.md 统一语言文档已保存在项目根目录
