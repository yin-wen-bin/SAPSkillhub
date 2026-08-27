---
title: SAP WBS 控制对象解析
summary: 通过固定只读来源将一个 WBS 外部编号解析为权威 SAP 控制对象键。
tags: [sap, co, ps, wbs, 只读]
systems: [SAP S/4HANA]
---

## 功能概述

本 Skill 使用一个去除首尾空格的 WBS 外部编号和公司代码，解析权威内部 WBS 编号、对象号、控制范围及项目关系。正式运行的数据源由版本化 profile 固定。

## 适用场景

当调用方只有用户可见 WBS 外部编号，而 CO/PS 金额证据需要 SAP 内部键时使用。不用于模糊搜索、编码掩码猜测或动态数据源发现。

## 前置条件

- 已配置 SAPSkillhub 自主管理的只读连接并启用 TLS 校验。
- 目标系统允许读取 Project V2 和 Financial WBS。
- 实时元数据 SHA-256 与 `references/source-profiles.json` 一致。
- 已安装 Python 3.10+ 和 `scripts/requirements.txt` 中的 `requests`。

## 用法

在本 Skill 目录执行：

```powershell
python run.py --input input.json --output .artifacts\wbs-resolver\output.json
```

## 输入

严格输入 Schema 仅接受 `schema_version`、`wbs_external_id` 和 `company_code`。WBS 只执行 trim，保留大小写和分隔符。连接、URL、SQL、数据源、字段及未知参数均被拒绝。

## 输出

输出包含请求范围、可为 `null` 的 `resolved_object`、跨源关系检查、安全的 profile 标识、源/分页/证据完整性、问题代码、时间戳和 SHA-256 制品。只有 `complete/resolved` 才返回解析对象。

## 限制与注意事项

已验证 profile 先精确查询 Project V2，再由 Financial WBS 补充并交叉核验。无记录、多记录、分页不完整、元数据变化或关系冲突均返回 `partial`，且不返回解析对象。对象解析不证明承诺、预算、计划、实际成本或业务流程完成。

## 示例

```json
{
  "schema_version": 1,
  "wbs_external_id": "S/5818-ETO1",
  "company_code": "KT70"
}
```
