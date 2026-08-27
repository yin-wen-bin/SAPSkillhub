---
title: SAP 控制对象承诺证据
summary: 按严格财政年度和会计期间读取一个已解析 WBS 或内部订单的承诺证据。
tags: [sap, co, ps, 承诺, 只读]
systems: [SAP S/4HANA]
---

## 功能概述

本严格只读 Skill 接受一个权威解析的 WBS 或内部订单，以及财政年度和会计期间范围。只有对象、类型、期间、币种、稳定键和分页契约全部证明后，才汇总保留符号的有限 Decimal 金额。

## 适用场景

用于确定性 CO/PS 工作流读取采购申请、采购订单及相关 21、22、24、26 承诺类型的剩余承诺。不推算承诺，也不以当前快照替代期间证据。

## 前置条件

- `references/source-profiles.json` 中已启用并验证请求对象类型的数据源。
- 目标源明确提供财政年度、会计期间、剩余金额、币种、币种角色、采购引用和稳定分页。
- SOAP 来源必须具有固定且已批准的只读 action 和 endpoint。
- 已安装 Python 3.10+ 和 `scripts/requirements.txt` 中的 `requests`。

## 用法

在本 Skill 目录执行：

```powershell
python run.py --input input.json --output .artifacts\commitment-evidence\output.json
```

## 输入

输入包含严格的 `resolved_object`、财政年度、`period_from`、`period_to` 和明确的承诺类型列表。期间只能是 1 到 16 的会计期间。调用方选择的连接、来源、SQL、字段、URL 和未知参数均被拒绝。

## 输出

输出包含关系与分析范围、profile 标识、承诺明细、按类型/币种/角色分组且可为 `null` 的总额、源/分页/范围/证据完整性、安全问题代码、时间戳和制品哈希。

## 限制与注意事项

当前目标 profile 有意保持未验证：尚未证明可调用的 Project Commitment SOAP binding；内部订单 COSP/COSS 键记录可读，但期间金额投影会不稳定地返回 `Unknown column VERS`，尚未与权威基线对账。因此正式运行返回 `partial`，明细为空且总额为 `null`。不得丢弃问题行继续汇总，不得把缺失金额按零解释，也不执行汇率换算。

## 示例

```json
{
  "schema_version": 1,
  "resolved_object": {
    "object_type": "WBS",
    "external_id": "P-100.01",
    "internal_id": "557",
    "object_number": "PR00000557",
    "company_code": "KT70",
    "controlling_area": "KT00"
  },
  "fiscal_year": "2026",
  "period_from": 1,
  "period_to": 16,
  "commitment_types": ["21", "22", "24", "26"]
}
```
