# AI智能建模引擎 - 统一语言

## 核心概念

### 模型 (Model)
一个 `.cube` 文件，是公安大数据研判分析平台可导入的分析配置单元。包含数据源表、筛选条件、扩展列、克隆关系等完整结构。

### 建模 (Modeling)
根据用户自然语言描述，由AI自动生成 `.cube` 模型文件的过程。

### 模板 (Template)
12个由数据大师手工创建的正确 `.cube` 文件，作为LLM生成的参考示例（教材）。模板不直接拷贝，仅作为 few-shot 示例喂给LLM参考其结构规律。

### 意图 (Intent)
用户自然语言描述中蕴含的建模需求，包含模型类型、筛选条件、关键词等信息。由 IntentParser 解析，优先使用 LLMGateway 进行语义解析，降级为关键词匹配。

### 数据源表 (Data Source Table)
平台中已注册的数据库表，如 `tt.jz_bank_bill`（银行交易流水表）、`tt.jz_bank_zh`（银行账户表）、`tt.jz_bank_zhxx`（账户信息类型表）。LLM生成时**必须引用已注册表**，不能凭空创造表名。表定义统一由 SchemaRegistry 管理，config.py 中不再重复定义。

### 筛选条件 (Where Condition)
模型中对数据源表的过滤规则，如金额范围、时间范围、账户类型、借贷方向等。用户可在生成后微调筛选条件。whereSql 生成逻辑统一由 WhereSqlBuilder 处理。

### 扩展列 (Extend Column)
模型中基于已有字段计算得出的衍生字段，如"净流入=流入-流出"。

### 克隆关系 (Clone Relation)
模型中表与表之间的派生关系，表示一个表是从另一个表克隆并修改条件而来。

### 校验 (Validation)
对LLM生成的 `.cube` 文件进行JSON格式、必填字段、数据源表名合法性检查。不合法则自动重试生成。校验器内部使用 parse_script 统一处理 script 字段的 str/dict 双态。

## 架构概念

### LLMGateway（统一LLM调用层）
系统与LLM交互的唯一通道。封装 Ollama (`/api/generate`) 和 OpenAI (`/v1/chat/completions`) 两种API格式，提供统一的 `generate()` 接口。所有需要调用LLM的模块（IntentParser、CubeGenerator）均通过此网关，不直接调用HTTP接口。

### WhereSqlBuilder（whereSql统一生成器）
从筛选条件字典生成 whereSql JSON 结构的独立模块。处理 char/string（in/not in）、decimal/number/int（比较/区间）、date 等类型的SQL生成。ConditionEditor 和 CubeGenerator 均使用此模块，消除了原先的重复逻辑。

### parse_script（script解析工具函数）
统一处理 `.cube` 文件中 script 字段的 str/dict 双态问题。script 可能是 JSON 字符串或已解析的字典，parse_script 将其统一转为字典返回。被 CubeValidator、RAGRetriever、CubeGenerator、ConditionEditor 等模块共用。

### create_app（应用工厂函数）
FastAPI 应用的工厂函数，封装所有模块的初始化和依赖组装。包括日志配置、中间件注册、静态文件挂载、LLMGateway 实例化、各引擎模块的创建与注入、路由注册。main.py 中 `app = create_app()` 即完成全部初始化。

### SchemaRegistry（数据源表注册中心）
数据源表定义的唯一权威来源。加载 `knowledge/schemas/` 下的 JSON 文件，提供表名查询、字段查询、合法性校验。config.py 中的 `DATA_SOURCE_TABLES` 已删除，消除知识重复。

## 模块地图

```
ai_engine/
├── main.py                    # create_app() 工厂函数，应用入口
├── config.py                  # 配置常量（LLM、路径等）
├── engines/
│   ├── llm_gateway.py         # LLMGateway - 统一LLM调用层
│   ├── intent_parser.py       # IntentParser - 意图解析（依赖LLMGateway）
│   ├── cube_generator.py      # CubeGenerator - 核心生成器
│   ├── cube_validator.py      # CubeValidator - 校验器
│   ├── condition_editor.py    # ConditionEditor - 筛选条件微调
│   ├── where_sql_builder.py   # WhereSqlBuilder - whereSql生成
│   ├── rag_retriever.py       # RAGRetriever - 模板检索
│   ├── schema_registry.py     # SchemaRegistry - 数据源表注册
│   ├── data_cleaner.py        # DataCleaner - 数据清洗
│   └── cube_utils.py          # parse_script 等工具函数
├── integrations/
│   └── datacube_importer.py   # 平台导入对接器（暂未启用）
├── knowledge/
│   ├── schemas/               # 数据源表schema定义（唯一权威来源）
│   │   └── bank_tables.json
│   └── templates/             # 12个.cube模板文件（few-shot示例）
├── static/
│   └── index.html             # 前端界面
├── tests/
│   ├── test_schema_registry.py
│   ├── test_cube_validator.py
│   ├── test_llm_gateway.py
│   ├── test_rag_retriever.py
│   ├── test_cube_generator.py
│   ├── test_condition_editor.py
│   ├── test_data_cleaner.py
│   ├── test_integration.py    # 集成回归测试
│   └── test_api.py            # API端点回归测试
└── docs/
    ├── adr/                   # 架构决策记录
    └── issues/                # Issue追踪
```

### 依赖关系

```
用户请求
  │
  ▼
main.py (create_app)
  ├── LLMGateway ←── IntentParser ←── CubeGenerator
  │                   └───────────────┘
  ├── SchemaRegistry ←── CubeValidator ←── CubeGenerator
  │       └──────────────────────────────────┘
  ├── RAGRetriever ←── CubeGenerator
  ├── ConditionEditor ←── WhereSqlBuilder
  ├── DataCleaner
  └── DataCubeImporter（暂未启用）
```

## 系统边界

### AI建模引擎
接收用户自然语言描述，通过LLM驱动生成 `.cube` 模型文件的独立服务。部署为 Python FastAPI 服务。

### 公安大数据研判分析平台 (DataCube Platform)
现有Java Web (Struts) 系统，运行在 `127.0.0.1:8561`，负责数据存储、模型运行、结果展示。AI建模引擎生成的 `.cube` 文件需导入此平台才能使用。

### 数据清洗 (Data Cleaning)
独立功能，与模型生成无关。负责对原始数据做去重、格式化、校验等处理。支持通过 `rules` 参数自定义清洗规则。

## 生成模式

### LLM驱动生成
核心生成方式。LLM直接生成完整的 `.cube` JSON结构，模板仅作为参考示例。支持生成现有12种类型之外的全新模型。生成流程：意图解析 → RAG检索模板 → 构建prompt → LLMGateway调用 → 解析输出 → 校验 → 失败重试（最多3次）。

### 关键词匹配
辅助方式。当用户描述中包含明确关键词时，快速匹配到对应模板类型，作为LLM生成的参考上下文。当 LLMGateway 不可用时自动降级为此模式。

## 部署约束

- 政务内网，完全离线
- 使用内网大模型服务（支持 Ollama 和 OpenAI 兼容API格式）
- 数据源表可扩展（不限于现有3张表），通过 SchemaRegistry 管理
- 用户界面嵌入现有平台
- 先手动导入 `.cube` 文件，后期再对接平台API实现自动导入
