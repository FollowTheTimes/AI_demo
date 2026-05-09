# Issue 007: 文件下载 + 前端界面

## What to build

实现 `.cube` 文件下载功能和完整的前端界面。前端界面包含：需求输入区、生成结果展示区（模型类型/置信度/参考模板/筛选条件）、筛选条件微调区、文件下载按钮、数据源表查看区、模板列表区。界面风格为深色政务风格，与公安大数据研判分析平台视觉一致。

## Acceptance criteria

- [ ] `GET /api/download/{file_name}` 端点提供 `.cube` 文件下载
- [ ] 前端界面包含需求输入文本框和生成按钮
- [ ] 生成结果展示：模型类型、置信度进度条、参考模板及相似度、重试次数、校验状态
- [ ] 筛选条件微调区：显示当前条件，支持修改值，点击"应用"调用 PATCH /api/conditions
- [ ] 文件下载按钮：点击下载生成的 `.cube` 文件
- [ ] 数据源表查看区：显示所有已注册表和字段（调用 GET /api/schemas）
- [ ] 模板列表区：显示12个模板的名称和描述（调用 GET /api/templates）
- [ ] 生成过程中显示loading状态
- [ ] 错误信息友好展示（未注册表提示、LLM不可用提示等）
- [ ] 深色政务风格UI，响应式布局
- [ ] 纯HTML+CSS+JS，无外部依赖

## Blocked by

- Issue 005 (Cube Generator + 生成API)
- Issue 006 (Condition Editor + 微调API)

## Agent Brief

**Category:** enhancement
**Summary:** 实现文件下载端点和完整前端界面

**Current behavior:**
现有前端界面是模板填充架构的界面，需要升级为LLM驱动架构的界面。没有文件下载功能。

**Desired behavior:**
实现 `GET /api/download/{file_name}` 下载端点。前端界面包含：需求输入区、生成结果展示区（模型类型/置信度/参考模板/筛选条件）、筛选条件微调区、文件下载按钮、数据源表查看区、模板列表区。深色政务风格，纯HTML+CSS+JS无外部依赖。

**Key interfaces:**
- `GET /api/download/{file_name}` — 文件下载端点
- 前端界面各区域与API端点的交互：
  - 生成 → POST /api/generate
  - 微调 → PATCH /api/conditions
  - 下载 → GET /api/download/{file_name}
  - 数据源 → GET /api/schemas
  - 模板 → GET /api/templates

**Acceptance criteria:**
- [ ] 文件下载端点正常工作
- [ ] 需求输入区和生成按钮
- [ ] 生成结果展示完整
- [ ] 筛选条件微调区可编辑
- [ ] 文件下载按钮正常
- [ ] 数据源表查看区
- [ ] 模板列表区
- [ ] loading状态展示
- [ ] 错误信息友好展示
- [ ] 深色政务风格UI
- [ ] 纯HTML+CSS+JS

**Out of scope:**
- 嵌入现有平台的具体集成
- 用户认证
- 生成历史记录页面
- 数据清洗UI（后续独立实现）
