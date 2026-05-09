# Issue 002: Cube Validator + 校验测试

## What to build

实现 `.cube` 文件校验器模块。Cube Validator 接收一个 `.cube` JSON 对象，校验其结构合法性，包括JSON格式、必填字段、数据源表名、字段名、where条件结构、cloneRel引用等。返回校验结果（通过/失败）和具体错误列表。依赖 Schema Registry 进行表名和字段名校验。

## Acceptance criteria

- [ ] 合法 `.cube` 文件通过校验，返回 `{"valid": True, "errors": []}`
- [ ] 非法JSON被正确拒绝
- [ ] 缺少必填字段（title/name/ctype/version/script）被检测
- [ ] script内部tables为空被检测
- [ ] table缺少必填字段（tableId/name/title）被检测
- [ ] 引用未注册表名被检测（依赖Schema Registry）
- [ ] where条件中引用不存在字段名被检测
- [ ] where条件结构不合法（缺少field/title/type/attr）被检测
- [ ] cloneRel引用不存在的tableId被检测
- [ ] 返回结构包含 `valid` 布尔值和 `errors` 列表（每项含字段路径和错误描述）
- [ ] Cube Validator 有完整的单元测试，覆盖上述所有场景

## Blocked by

- Issue 001 (Schema Registry)

## Agent Brief

**Category:** enhancement
**Summary:** 实现.cube文件校验器，校验JSON格式、必填字段、数据源表名、字段名、where条件结构

**Current behavior:**
没有校验器，LLM生成的.cube文件可能格式不合法，无法被平台导入。

**Desired behavior:**
Cube Validator 接收.cube JSON对象，校验JSON格式、必填字段（title/name/ctype/version/script）、script内部结构（tables非空、每个table包含tableId/name/title/where）、数据源表名在已注册表中、字段名在对应表schema中存在、where条件结构合法、cloneRel引用的tableId存在。返回 `{"valid": bool, "errors": [{"path": str, "message": str}]}`。

**Key interfaces:**
- `CubeValidator` 类 — 核心校验器
- `validate(cube: dict) -> dict` — 校验方法，返回 `{"valid": bool, "errors": list}`
- 依赖 `SchemaRegistry` 进行表名和字段名校验
- 错误列表每项包含 `path`（字段路径）和 `message`（错误描述）

**Acceptance criteria:**
- [ ] 合法.cube通过校验
- [ ] 非法JSON被拒绝
- [ ] 缺少必填字段被检测
- [ ] tables为空被检测
- [ ] table缺少必填字段被检测
- [ ] 引用未注册表名被检测
- [ ] where中引用不存在字段名被检测
- [ ] where条件结构不合法被检测
- [ ] cloneRel引用不存在tableId被检测
- [ ] 返回结构包含valid和errors
- [ ] 有完整的单元测试

**Out of scope:**
- 自动修复不合法的.cube文件
- 校验extend扩展列的计算逻辑正确性
- 校验whereSql的SQL语法正确性
