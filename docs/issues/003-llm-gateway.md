# Issue 003: LLM Gateway + 配置系统

## What to build

实现统一的内网大模型调用层和配置系统。LLM Gateway 屏蔽不同LLM API格式的差异，提供统一的 `generate(prompt, system_prompt, format_json)` 接口。支持Ollama `/api/generate` 和 OpenAI兼容 `/v1/chat/completions` 两种API格式，通过配置切换。更新 config.py 增加 LLM 相关配置项（API类型、地址、模型名、超时时间）。

## Acceptance criteria

- [ ] LLM Gateway 提供 `async generate(prompt, system_prompt, format_json) -> str` 接口
- [ ] 支持 Ollama API 格式（`/api/generate`），默认启用
- [ ] 支持 OpenAI 兼容 API 格式（`/v1/chat/completions`）
- [ ] 通过 `config.py` 中的 `LLM_API_TYPE` 配置切换API格式（"ollama" / "openai"）
- [ ] 内置超时控制，默认30秒，可配置
- [ ] 网络错误时抛出明确异常，不崩溃
- [ ] `format_json=True` 时，prompt中追加JSON格式约束指令
- [ ] config.py 新增配置项：LLM_API_TYPE, LLM_API_URL, LLM_MODEL_NAME, LLM_TIMEOUT, LLM_MAX_TOKENS
- [ ] `GET /api/health` 返回 `llm_available` 布尔值（尝试连接LLM服务）
- [ ] LLM Gateway 有单元测试（使用mock，不依赖真实大模型）

## Blocked by

- Issue 001 (Schema Registry，需要schema信息构建测试prompt)

注意：此任务为 HITL，需要确认内网大模型的API格式后才能最终配置。但代码实现可先完成，后续只需修改配置即可。

## Agent Brief

**Category:** enhancement
**Summary:** 实现统一的内网大模型调用层，屏蔽Ollama/OpenAI兼容API差异

**Current behavior:**
config.py中有OLLAMA_BASE_URL和OLLAMA_MODEL配置，但没有统一的LLM调用模块。各模块直接使用httpx调用Ollama API，不支持其他API格式。

**Desired behavior:**
LLM Gateway 提供统一的 `async generate(prompt, system_prompt, format_json) -> str` 接口。支持Ollama `/api/generate` 和 OpenAI兼容 `/v1/chat/completions` 两种API格式，通过config切换。内置超时控制和错误处理。`format_json=True` 时追加JSON格式约束指令。`GET /api/health` 返回 `llm_available` 布尔值。

**Key interfaces:**
- `LLMGateway` 类 — 统一调用层
- `async generate(prompt: str, system_prompt: str = "", format_json: bool = False) -> str` — 核心方法
- config新增：`LLM_API_TYPE`（"ollama"/"openai"）、`LLM_API_URL`、`LLM_MODEL_NAME`、`LLM_TIMEOUT`、`LLM_MAX_TOKENS`
- `GET /api/health` 增加 `llm_available` 字段

**Acceptance criteria:**
- [ ] generate接口正常工作
- [ ] 支持Ollama API格式
- [ ] 支持OpenAI兼容API格式
- [ ] 通过LLM_API_TYPE配置切换
- [ ] 超时控制正常
- [ ] 网络错误时抛出明确异常
- [ ] format_json=True时追加格式约束
- [ ] config新增5个配置项
- [ ] health端点返回llm_available
- [ ] 有单元测试（使用mock）

**Out of scope:**
- 流式输出支持
- 多模型并行调用
- LLM响应缓存
- Token用量统计
