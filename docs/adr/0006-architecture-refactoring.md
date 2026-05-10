# ADR 0006: 架构重构 - 消除重复与统一通道

## 状态
已采纳

## 背景
系统经过 Issues 001-008 的 TDD 开发后，代码功能完整但存在以下架构问题：

1. **双LLM调用通道**：IntentParser 直接调用 httpx，CubeGenerator 通过 LLMGateway 调用，存在两条独立的LLM调用路径
2. **whereSql重复逻辑**：ConditionEditor 和 CubeGenerator 各自实现了 whereSql 生成逻辑
3. **遗留模块**：CubeBuilder 是 v1 模板填充方案的遗留，v2 已改用 LLM 驱动生成
4. **parse_script重复**：CubeValidator、RAGRetriever、CubeGenerator、ConditionEditor 中有5处重复的 script 解析逻辑
5. **main.py初始化散乱**：所有模块初始化和路由定义混在模块顶层，难以测试和复用
6. **知识重复**：config.py 中的 DATA_SOURCE_TABLES 与 SchemaRegistry 加载的 bank_tables.json 定义了相同的数据源表

## 决策
执行6项重构，逐一消除上述问题。

### 重构1：IntentParser 统一使用 LLMGateway

**变更**：IntentParser 新增 `llm_gateway` 依赖，`_llm_parse` 方法通过 `self.llm_gateway.generate()` 调用LLM，而非直接使用 httpx。当 `llm_gateway=None` 时降级为纯关键词匹配。

**理由**：系统应只有一条LLM调用通道。双通道意味着配置、超时、错误处理逻辑需要维护两份，且无法统一监控和限流。

### 重构2：提取 WhereSqlBuilder

**变更**：从 ConditionEditor 和 CubeGenerator 中提取 whereSql 生成逻辑，创建独立的 `where_sql_builder.py` 模块，提供 `build_where_sql(where: dict) -> dict` 函数。

**理由**：whereSql 生成逻辑涉及 char/string/decimal/number/int/date 等多种类型的处理，属于独立关注点。重复实现不仅增加维护成本，还容易导致行为不一致。

### 重构3：删除 CubeBuilder 遗留模块

**变更**：删除 `engines/cube_builder.py`，v1 的模板填充逻辑不再使用。

**理由**：v2 已采用 LLM 驱动生成（ADR-0001），CubeBuilder 是 v1 遗留代码，无任何模块引用它。保留死代码增加认知负担。

### 重构4：提取 parse_script 工具函数

**变更**：创建 `engines/cube_utils.py`，提供 `parse_script(script)` 函数，统一处理 script 字段的 str/dict 双态。替换 CubeValidator、RAGRetriever、CubeGenerator、ConditionEditor 中的5处重复逻辑。

**理由**：script 字段在 `.cube` 文件中可能是 JSON 字符串或已解析的字典，这个双态问题在多个模块中重复出现。统一处理避免遗漏和实现差异。

### 重构5：create_app 工厂函数

**变更**：main.py 中所有模块初始化和路由注册封装到 `create_app()` 工厂函数中，`app = create_app()` 作为模块级入口。

**理由**：工厂函数使依赖组装可测试、可复用。测试时可以传入不同配置创建应用实例，而非依赖模块级全局状态。

### 重构6：删除 DATA_SOURCE_TABLES

**变更**：从 config.py 中删除 `DATA_SOURCE_TABLES` 字典，数据源表定义的唯一来源是 SchemaRegistry 加载的 `knowledge/schemas/bank_tables.json`。

**理由**：同一知识在两处定义必然导致不同步。SchemaRegistry 是数据源表的权威来源，config.py 中的副本是冗余的。

## 后果

- 系统只有一条LLM调用通道（LLMGateway），所有LLM交互统一管理
- whereSql 生成逻辑集中在一处，修改只需改 WhereSqlBuilder
- 无遗留死代码，降低认知负担
- parse_script 统一处理，消除5处重复
- 应用初始化可通过工厂函数控制，便于测试
- 数据源表定义单一来源，消除不同步风险
- 全部207个测试通过，重构未引入回归
