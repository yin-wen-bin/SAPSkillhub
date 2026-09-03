---
title: SAP 银行来款证据
summary: 从固定只读银行对账单来源读取有界、可审计的信用来款、冲销和处理证据。
tags: [sap, fi, bank-statement, 银行来款, 只读]
systems: [SAP S/4HANA]
---

## 功能概述

本 Skill 按公司代码和价值日期范围读取 SAP 银行对账单信用行，输出稳定键、日期、Decimal 金额、币种、冲销状态、处理状态和脱敏付款方账号。

它不使用 Payment Advice，不匹配客户或发票，也不把银行流水自动解释为应收账款已结清。

## 适用场景

用于取得限定公司代码和价值日期范围内的银行对账单信用来款证据，尤其适合需要分别核对有效、冲销和处理状态的只读审计场景。

## 前置条件

- 固定来源 Profile 已完成目标系统验证并启用。
- SAPSkillhub 自主管理的 ADT 连接启用 TLS 校验。
- Skill 本地忽略的 `.env` 已配置账号 HMAC 密钥和对应 key ID。

## 用法

输入和输出必须放在仓库忽略目录：

```powershell
python run.py --input ..\..\..\.artifacts\bank-receipt\input.json --output ..\..\..\.artifacts\bank-receipt\output.json
```

## 输入

严格 Schema 只接受版本、公司代码、起止日期和可选银行参考。日期固定表示价值日期，最多31天；`receipt_reference`只执行精确匹配。连接、URL、对象、字段、SQL、凭据、TLS和分页参数均被拒绝。

## 输出

输出包含来款明细、有效与冲销金额的分币种汇总、固定来源 Profile、三类完整性信号、安全问题代码、时间戳和制品哈希。账号只包含末四位掩码和 HMAC。

## 完整性

只有元数据、稳定键分页、行数、金额、币种和状态均完整时才返回明细与币种汇总。权威完整零结果为 `complete/not_found`；任何来源或行级异常均为 `partial/source_unavailable`，且不输出部分明细。

## 隐私

原始账号不离开进程。账号仅输出末四位掩码和带本地密钥的 HMAC-SHA-256。付款人名称和银行参考只允许出现在忽略目录的输出 JSON 中，不进入日志、错误或 Git。

## 限制与注意事项

相关会计凭证只表示银行对账单处理关系，不证明客户识别、发票分配、应收清账或业务到账。来源、分页或任一必填证据不完整时不会返回部分明细。

## 示例

```json
{
  "schema_version": 1,
  "company_code": "1710",
  "date_from": "2023-11-01",
  "date_to": "2023-11-30"
}
```
