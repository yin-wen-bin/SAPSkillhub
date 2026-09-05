---
title: SAP AR 历史催收证据
summary: 从已验证的只读来源读取指定业务日期前、有界且已执行的客户催收事件。
tags: [sap, fi, 应收账款, 催收, 只读]
systems: [SAP S/4HANA]
---

## 功能概述

本 Skill 按公司代码、1–50个客户和截止日期读取已经执行的AR催收事件。当前目标系统存在发布视图 `I_DunningEntryItem`，但 ADT Data Preview 无法可靠投影完整项目键，因此已验证的来源Profile使用经实时DDIC检查的 `MHNK/MHND` 只读回退。

它不修改SAP，不重建任意历史日期的客户催收主数据快照，也不把空结果表述为“从未催收”。

## 适用场景

用于历史应收分析，明确区分已经执行的催收事件证据与当前客户催收主数据。

## 前置条件

- 固定来源Profile已通过目标系统验证并启用。
- SAPSkillhub能够访问已批准的ADT Data Preview和DDIC源码端点。
- TLS校验和仓库管理的连接Profile保持启用。

## 用法

输入和输出必须放在仓库忽略目录：

```powershell
python run.py --input ..\..\..\.artifacts\ar-dunning\input.json --output ..\..\..\.artifacts\ar-dunning\output.json
```

## 输入

严格Schema只接受公司代码、1–50个不重复客户、包含边界的截止日期和可选催收区域。调用方不能指定连接、表、字段、SQL、凭据、TLS或分页参数。

## 输出

公开投影包含公司代码、客户、催收区域、运行编号与日期、FI凭证键、催收级别、Decimal金额文本、币种和事件顺序状态。受限来源字段单独返回，由平台加密保存。

## 完整性

来源、分页和证据完整性分别报告。完整空结果只表示在请求范围及截止日前没有找到已执行催收事件。同日事件顺序无法证明时保持明确的歧义状态。

## 隐私

公开字段和受限字段通过声明式Schema分流。受限行必须由调用平台加密，不得提供给Agent Runtime、公开制品、日志或SSE事件。

## 限制与注意事项

本Skill不重建历史客户主数据设置，因此 `historical_dunning_master_status` 固定为 `not_assessed`。当日期、时间或经验证的业务序号不足时，也不会根据运行编号推断业务先后。

## 示例

```json
{
  "schema_version": 1,
  "company_code": "1710",
  "customers": ["1000001", "1000002"],
  "as_of": "2023-11-30"
}
```
