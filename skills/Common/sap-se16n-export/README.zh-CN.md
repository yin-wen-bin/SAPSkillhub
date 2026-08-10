---
title: SAP SE16N 安全表导出
summary: 通过 SAP GUI for Windows 筛选、验证、分块、合并并留存 SE16N 导出证据。
tags: [SE16N, 表数据, 分块导出, Excel, SAP GUI 自动化]
transactions: [SE16N]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## 功能概述

Python 主入口接受 JSON 或重复 CLI 条件，默认以 100 行做验证；正式模式用 50,001 行探测溢出，再递归拆分为不超过 50,000 行的成功块。最终生成标准 XLSX、CSV、manifest 和 SHA-256。VBS 仅保留为旧调用转发器。

## 适用场景

- 低影响验证表名和筛选条件。
- 按审核策略导出有明确边界的大表。
- 留存选择条件、行数、分块、合并和哈希证据。

## 前置条件

需要 Windows、已登录的 SAP GUI、启用 GUI Scripting、Python 3.12、`openpyxl==3.1.5` 和 `pywin32`。首次运行前阅读 `references/environment.md`；目标系统控件不同时，先被动检查再调整 `references/control-profile.json`。

## 用法

```powershell
python scripts\se16n_export.py --table BSIK --selection-file .\bsik.json --mode full --output-dir C:\Exports --file bsik
```

不指定模式时默认验证：

```powershell
python scripts\se16n_export.py --table MARA --where "MATNR=10000001,10000002" --exclude "MTART=DIEN" --output-dir C:\Exports
```

## 输入

版本 1 JSON 支持 `filters`、`columns`、`sort`、可选 `chunk` 和 `key_fields`。条件支持 `EQ/NE/BT/NB/GE/GT/LE/LT/CP/NP`。同字段包含条件为 OR，排除条件从命中结果扣除，不同字段之间为 AND。CLI 支持单值、`low..high` 和逗号多值。

BSEG、BSIK、BSIS 要求公司代码和会计年度；EKBE 要求过账日期边界。未知表必须明确提供分块字段、类型、上下限和完整业务键。

## 输出

生成 `<name>.part-NNNN.xlsx`、`<name>.xlsx`、`<name>.csv`、`<name>.manifest.json` 以及溢出探测工作簿。Manifest 记录 SAP 身份、请求和实际选择条件、分块范围与行数、布局、时间、状态和文件哈希。

## 限制与注意事项

仅支持 SAP GUI for Windows。不同 SAP 版本和客户增强可能改变控件 ID。没有可证明的分块范围和完整键时拒绝正式大表导出。失败时保留证据，但不会声明完整。超过单表容量时 XLSX 自动使用多个工作表。

## 示例

```json
{"schema_version": 1, "filters": [{"field": "BUKRS", "sign": "I", "option": "EQ", "low": "1710"}, {"field": "GJAHR", "sign": "I", "option": "EQ", "low": "2026"}, {"field": "BELNR", "sign": "I", "option": "BT", "low": "0000000001", "high": "9999999999"}], "sort": ["BUKRS", "GJAHR", "BELNR", "BUZEI"]}
```
