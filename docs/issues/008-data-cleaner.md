# Issue 008: 数据清洗独立功能

## What to build

保留并完善现有 Data Cleaner 模块，确保其作为独立功能正常工作。实现 `POST /api/clean` API端点的完整对接，支持选择清洗规则（身份证校验、手机号提取、金额标准化、去重、时间标准化），返回清洗后的数据和清洗报告。

## Acceptance criteria

- [ ] `POST /api/clean` 接收 `{"data": [...], "rules": ["id_card", "phone", "amount", "deduplicate", "datetime"]}` 
- [ ] rules参数控制启用哪些清洗规则，为空时启用全部
- [ ] 身份证校验：验证18位格式和校验位，标记异常
- [ ] 手机号提取：从摘要字段提取11位手机号
- [ ] 金额标准化：确保jy_je为数值类型
- [ ] 去重：基于交易流水号或(账号+时间+金额)组合
- [ ] 时间标准化：统一为YYYY-MM-DD HH:MM:SS格式
- [ ] 借贷标志标准化：统一为"进"和"出"
- [ ] 空值处理：空字符串统一为null
- [ ] 返回清洗报告：原始条数、清洗后条数、重复条数、异常条数
- [ ] Data Cleaner 有单元测试

## Blocked by

None - can start immediately

## Agent Brief

**Category:** enhancement
**Summary:** 完善数据清洗独立功能，确保API端点完整对接

**Current behavior:**
Data Cleaner模块已存在基本实现，但POST /api/clean端点可能未完全对接，清洗规则选择功能需要验证。

**Desired behavior:**
确保POST /api/clean端点完整对接，支持rules参数选择清洗规则（id_card/phone/amount/deduplicate/datetime），为空时启用全部。返回清洗后数据和清洗报告（原始条数/清洗后条数/重复条数/异常条数）。

**Key interfaces:**
- `POST /api/clean` — 请求：`{"data": [...], "rules": [...]}`
- `DataCleaner.clean(data, rules)` — 支持rules参数
- `DataCleaner.generate_clean_report(original, cleaned)` — 清洗报告

**Acceptance criteria:**
- [ ] POST /api/clean正常工作
- [ ] rules参数控制启用规则
- [ ] rules为空启用全部
- [ ] 身份证校验正常
- [ ] 手机号提取正常
- [ ] 金额标准化正常
- [ ] 去重正常
- [ ] 时间标准化正常
- [ ] 借贷标志标准化正常
- [ ] 空值处理正常
- [ ] 返回清洗报告
- [ ] 有单元测试

**Out of scope:**
- 数据清洗与模型生成的联动
- 可视化清洗报告UI
- 自定义清洗规则
- 清洗规则优先级排序
