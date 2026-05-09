# Issue 006: Condition Editor + 微调API

## What to build

实现筛选条件微调器和 `PATCH /api/conditions` API端点。Condition Editor 解析 `.cube` 文件中 tables 的 where 条件，提供结构化的条件列表供用户编辑，支持修改条件值并重新序列化回 `.cube` 文件，同步更新 whereSql 字段。不允许增删表或修改表结构。

## Acceptance criteria

- [ ] `parse_conditions(cube_content)` 方法解析所有表的 where 条件为结构化列表
- [ ] 每个条件包含：table_id, field, title, type, current_value, available_operators
- [ ] `update_conditions(cube_content, conditions)` 方法修改条件值并返回更新后的 cube
- [ ] 修改条件后 whereSql 字段同步更新
- [ ] 不允许增删表（尝试修改表结构时返回错误）
- [ ] 不允许修改不存在的字段（返回错误）
- [ ] `PATCH /api/conditions` 接收 `{"cube_content": {...}, "conditions": [...]}` 返回更新后的 cube
- [ ] 更新后的 `.cube` 文件自动保存到 output 目录
- [ ] Condition Editor 有完整的单元测试

## Blocked by

- Issue 002 (Cube Validator，需要校验修改后的cube合法性)

## Agent Brief

**Category:** enhancement
**Summary:** 实现筛选条件微调器，支持解析/修改/序列化where条件

**Current behavior:**
没有条件微调功能，用户生成模型后无法在不重新生成的情况下调整筛选条件。

**Desired behavior:**
Condition Editor 解析.cube文件中tables的where条件为结构化列表（table_id, field, title, type, current_value, available_operators），支持修改条件值并重新序列化回.cube文件，同步更新whereSql字段。不允许增删表或修改表结构。

**Key interfaces:**
- `ConditionEditor` 类 — 筛选条件微调器
- `parse_conditions(cube_content: dict) -> list[dict]` — 解析where条件
- `update_conditions(cube_content: dict, conditions: list[dict]) -> dict` — 修改条件值
- 每个条件结构：`{"table_id": str, "field": str, "title": str, "type": str, "current_value": any, "available_operators": list[str]}`
- `PATCH /api/conditions` — API端点

**Acceptance criteria:**
- [ ] parse_conditions正确解析where条件
- [ ] 每个条件包含完整结构信息
- [ ] update_conditions正确修改条件值
- [ ] 修改后whereSql同步更新
- [ ] 不允许增删表
- [ ] 不允许修改不存在字段
- [ ] PATCH /api/conditions正常工作
- [ ] 更新后.cube自动保存
- [ ] 有完整单元测试

**Out of scope:**
- 条件增删（只支持修改值）
- 扩展列编辑
- 表关联关系编辑
- 可视化条件编辑器UI（Issue 007处理）
