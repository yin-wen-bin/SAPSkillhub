---
title: SAP F.05 日志与测试运行导出
summary: 通过 SAP GUI 导出现有 F.05 运行日志或非过账测试运行证据。
tags: [F.05, 外币评估, 测试运行, SAP GUI 自动化]
transactions: [F.05]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## 功能概述

Skill 默认查看并导出现有日志，也支持严格非过账的 F.05 测试运行。输出运行元数据、警告/错误、逐币种评估合计、引用凭证和文件哈希。

## 适用场景

- 导出现有外币评估运行证据。
- 在不更新、不记账的前提下执行 F.05 测试。
- 保存与语言无关的 ALV/list 或 spool 证据。

## 前置条件

需要 Windows、已登录 SAP GUI、启用 Scripting、Python 3.12、`pywin32` 和 `openpyxl`。必须在目标系统中验证复制后的技术控件 profile。

## 用法

```powershell
python scripts\f05_log_export.py --mode existing-log --run-id 20260801-001 --output-dir C:\Exports --profile .\validated-profile.json
```

## 输入

模式；现有日志的运行 ID，或测试运行的公司代码和评估关键日；可选评估范围/方法、变式、system/client、输出名、profile 和覆盖许可。

## 输出

技术字段表头 XLSX、CSV、日志，以及包含 SAP 身份、实际选择、作业/运行状态、警告/错误、逐币种合计、时间戳、凭证引用和 SHA-256 的 manifest。

## 限制与注意事项

仓库内 profile 明确标记为未验证。不同版本和客户变式的 F.05/spool 控件不同。Skill 永不启用更新或过账，也不会创建会计凭证。

## 示例

只有 profile 验证后才执行非过账测试：

```powershell
python scripts\f05_log_export.py --mode test-run --company-code 1000 --valuation-key-date 2026-08-01 --valuation-method Z001 --output-dir C:\Exports --profile .\validated-profile.json
```
