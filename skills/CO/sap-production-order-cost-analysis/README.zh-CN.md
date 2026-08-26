---
title: SAP 生产订单成本分析
summary: 按成本要素读取严格只读的生产订单计划、目标和实际成本证据。
tags: [sap, co, 生产订单, 目标成本, 只读]
systems: [SAP S/4HANA]
---

## 功能概述

本 Skill 针对一个有界生产订单和会计期间读取可审计的成本证据。它先证明 AUFK 成本对象关系，再实时验证 `I_MfgOrderActlPlanTgtLdgrCost`，并且只在 SAP 总行数和全部金额均验证通过后按成本要素返回计划、目标和实际成本。

## 适用场景

用于确定性 Agent 比较生产订单计划、目标和实际成本。不用于物料价格比较，也不会运行成本计算、差异计算、结算或重估。

## 前置条件

- 已配置并保护 Skill 内部拥有的默认 ADT profile。
- 目标系统允许只读访问 AUFK 和发布的生产订单成本 CDS。
- ADT Data Preview 可用并启用 TLS 证书校验。
- 已安装 Python 3.10+ 和 `scripts/requirements.txt` 中的 `requests`。

## 用法

在本 Skill 目录执行：

```powershell
python run.py --input input.json --output .artifacts\production-order-cost\output.json
```

## 输入

输入契约见 `references/input.schema.json`。调用方只能提供生产订单、固定目标成本版本，以及可选会计年度/期间或由平台解析的会计期间范围。连接、数据对象、原始 SQL 和任意 CDS 参数选择都会被拒绝。

## 输出

输出契约见 `references/output.schema.json`，包含订单上下文、分析范围、AUFK 关系证据、成本要素明细、汇总、完整性、验证问题、时间戳和哈希。精确十进制数使用字符串保存。

## 限制与注意事项

`partial` 表示证据契约不完整。空结果、截断、行数不一致、关系冲突或无效金额均不生成成本明细和汇总。缺少计划或目标成本时不得按零解释，不得用物料标准单价替代生产订单目标成本，也不得静默合计不同账本、币种、币种角色或期间。

## 示例

```json
{
  "schema_version": 1,
  "manufacturing_order": "1001233",
  "fiscal_year": "2020",
  "period": 11,
  "target_cost_variant": 1
}
```
