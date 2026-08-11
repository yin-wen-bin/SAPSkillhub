---
title: SAP MR11 模拟导出
summary: 仅以 MR11 模拟模式导出调整候选项和可审计证据。
tags: [MR11, GR IR, 模拟, SAP GUI 自动化]
transactions: [MR11]
systems: [SAP ERP, SAP S/4HANA, SAP GUI for Windows]
---

## 功能概述

脚本只有在确认模拟复选框已选中、过账和更新复选框均未选中后才执行 MR11，并导出候选项、排除原因、消息、币种合计、日志和哈希。

## 适用场景

- 使用 SAP 标准 MR11 逻辑获得非过账建议。
- 复核账龄或容差策略下的 GR/IR 调整候选项。
- 保存可复现的审计证据包。

## 前置条件

需要 Windows、已登录 SAP GUI、启用 Scripting、Python 3.12、`pywin32` 和 `openpyxl`。必须在目标系统中被动检查技术控件并生成已验证 profile。

## 用法

```powershell
python scripts\mr11_simulation_export.py --company-code 1000 --key-date 2026-08-01 --variant Z_MR11_AUDIT --output-dir C:\Exports --profile .\validated-profile.json
```

## 输入

公司代码、关键日期、可选 PO 范围、账龄天数、容差策略或 SAP 变式、验证/正式运行模式、system/client、profile、输出名和覆盖许可。

## 输出

技术字段表头 XLSX、CSV、日志，以及包含 SAP 身份、实际选择、行数、逐币种合计、时间戳和 SHA-256 的 manifest。

## 限制与注意事项

仓库内 profile 明确标记为未验证；不同版本和客户增强的控件 ID/ALV 字段会变化。Skill 没有过账模式；只有 SAP 数字结果计数器明确为零时才接受零结果。

## 示例

先用窄 PO 范围执行 100 行验证：

```powershell
python scripts\mr11_simulation_export.py --company-code 1000 --key-date 2026-08-01 --purchase-order-low 4500001000 --purchase-order-high 4500001099 --tolerance-policy Z01 --run-mode validate --output-dir C:\Exports --profile .\validated-profile.json
```
