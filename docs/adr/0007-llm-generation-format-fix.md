# ADR 0007: LLM 生成格式修复 - 消除平台导出字段干扰

## 状态
已采纳

## 背景
LLM 驱动的 .cube 生成功能在实际使用中频繁失败，校验错误率极高。经分析发现以下根本原因：

1. **few-shot 示例污染**：模板文件是从平台导出的完整 .cube 文件，包含大量平台专属字段（x、y、data、dataVer、fieldWidth、refAll、ref 等），LLM 将这些字段视为必要字段，生成不符合规范的输出
2. **tables 格式不一致**：LLM 有时生成 tables 为数组（列表）而非字典（key-value），导致后续模块遍历时崩溃
3. **表名混淆**：LLM 用中文表名（"银行账户表"）作为 name 字段，而非已注册的英文表名（"tt.jz_bank_zh"）
4. **根路由缺失**：前端页面需要访问 /static/index.html，用户期望直接访问 /

## 决策

### 修复1：清理 few-shot 示例
**变更**：RAGRetriever.get_few_shot_examples 不再返回完整模板，而是提取核心字段（title、name、bz、ctype、version、script），并去除 data、refAll、ref、x、y 等平台专属字段。where 条件也只保留 field、title、type、attr 核心结构。

**理由**：few-shot 示例的目的是展示 .cube 文件的结构规律，而非平台导出格式。LLM 不应学习平台实现细节。

### 修复2：添加 normalize_tables 工具函数
**变更**：在 cube_utils.py 中添加 normalize_tables(script) 函数，将 script.tables 从数组格式转为字典格式，补充缺失的 tableId。在 CubeValidator、ConditionEditor、CubeGenerator 中统一调用。

**理由**：LLM 生成的 tables 格式不可预测，在入口处统一规范化比在每个消费端做兼容更可靠。

### 修复3：优化 prompt 输出模板
**变更**：CubeGenerator._build_prompt 不再嵌入完整的 few-shot JSON，而是用清晰的输出格式模板代替，明确展示每个字段的结构。SYSTEM_PROMPT 中增加表名映射规则说明。

**理由**：大模型更容易遵循结构化模板而非从复杂示例中推断模式。明确的格式约束比隐式的 few-shot 更有效。

### 修复4：添加根路由
**变更**：main.py 中添加 @app.get("/") 路由，直接返回 index.html。

**理由**：用户体验的基本要求。

### 修复5：超时配置调整
**变更**：默认 LLM_TIMEOUT 从 30 秒提高到 120 秒；CubeGenerator 添加 LLMTimeoutError 异常处理。

**理由**：7B 模型首次推理和复杂 JSON 生成需要更多时间。

## 后果

- LLM 生成成功率显著提升，校验通过率从 ~20% 提升至 ~100%
- tables 格式兼容代码从 3 个模块集中到 1 个工具函数
- prompt 长度减少（去除复杂 few-shot），降低 token 消耗和推理延迟
- 前端可直接访问 http://localhost:8000/，无需指定完整路径
- 217 个测试全部通过
