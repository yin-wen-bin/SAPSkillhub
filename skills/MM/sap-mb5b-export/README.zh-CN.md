---
title: SAP MB5B 导出与合并
summary: 按工厂和库存地点批量执行 MB5B，补充库存地点列，并将成功导出的工作簿按工厂合并。
tags:
  - MB5B
  - 库存
  - Excel
  - SAP GUI 自动化
transactions:
  - MB5B
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## 功能概述

本 Skill 用于自动操作 Windows 版 SAP GUI 中的 MB5B 事务。它从 Excel 工作簿读取工厂和库存地点组合，逐个执行导出，在导出数据中补充库存地点，并将成功结果按工厂合并为一个工作簿。

执行逻辑使用 SAP 技术控件 ID 和 Windows 控件结构，不依赖界面翻译文字或固定屏幕坐标。

运行中如遇到 SAP GUI Scripting 的标准安全提示，本 Skill 仅在识别到已知安全提示文本和标准 `OK` 控件时自动确认；业务弹窗、覆盖确认和其他多按钮对话框仍按安全规则停止或由原状态机处理。

## 适用场景

- 批量导出多个工厂和库存地点组合的过账日期库存。
- 为库存核对或后续报表生成命名一致的工作簿。
- 在合并多个 MB5B 导出前补充库存地点字段。
- SAP GUI 语言、主题、版本或 Windows 缩放发生变化后验证兼容性。
- 在不操作 SAP 的情况下，通过 dry run 检查目标和输出路径。

## 前置条件

- Windows 操作系统，并已安装 Windows 版 SAP GUI。
- SAP 客户端和服务器端均已启用 SAP GUI Scripting。
- 已登录 SAP，且账号具备执行 MB5B 和导出结果的权限。
- Python 环境已安装 `scripts/requirements.txt` 中的依赖。
- 输入 Excel 的前两列分别包含工厂和库存地点。
- 首次在一台电脑运行，或 SAP GUI、Windows 升级后，先阅读 `references/environment.md`。

## 依赖版本策略

`scripts/requirements.txt` 保留已测试通过的精确版本：

```text
openpyxl==3.1.5
pywin32==311
pywinauto==0.6.9
```

`scripts/check_environment.py` 接受当前环境中满足最低要求的更高版本，并先运行环境检查、输入检查和可选 SAP 会话检查。如果检查成功，不要求更新或降级当前环境。如果检查失败，且当前依赖版本与已测试基线不同，脚本会同时报告当前版本和已测试基线，并建议先用 `scripts/requirements.txt` 复现。

## 用法

首先检查本机环境：

```powershell
python scripts/check_environment.py `
  --input "<LOCAL_WORKSPACE>\库存地点.xlsx" `
  --require-sap
```

在不操作 SAP 的情况下预览全部目标和输出路径：

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\库存地点.xlsx" `
  --date 2026-02-28 `
  --dry-run
```

在新的 SAP GUI 环境中，先执行一个真实目标：

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\库存地点.xlsx" `
  --date 2026-02-28 `
  --limit 1
```

确认输出文件名和 `Data!D1` 表头正确后，移除 `--limit` 执行完整批次。

## 输入

| 输入项 | 必填 | 说明 |
| --- | --- | --- |
| `--input` | 是 | 包含工厂和库存地点组合的 Excel 工作簿。 |
| `--date` | 是 | `YYYY-MM-DD` 格式的过账日期。 |
| `--output-dir` | 否 | 个别导出、合并文件、日志和诊断文件的输出目录。 |
| `--limit` | 否 | 只处理前 N 个目标；首次真实验证使用 `1`。 |
| `--dry-run` | 否 | 仅验证目标与路径，不控制 SAP。 |
| `--overwrite` | 否 | 覆盖已有输出；只有在用户明确许可时使用。 |
| `--inspect-ui` | 否 | 被动捕获不支持对话框的界面诊断，不执行点击。 |

## 输出

| 输出项 | 命名规则 | 说明 |
| --- | --- | --- |
| 单个工作簿 | `MB5B_<工厂>_<库存地点>_<YYYYMMDD>.xlsx` | 每个成功工厂/库存地点目标的增强导出。 |
| 工厂合并工作簿 | `MB5B_<工厂>_<YYYYMMDD>.xlsx` | 按输入顺序合并成功文件，并仅保留一行表头。 |
| 库存地点列 | `Data!D:D` | 必要时插入 D 列，`D1` 写入配置表头，数据行写入目标库存地点。 |
| 运行日志 | 本地输出目录 | 记录已处理目标与失败信息，不提交到仓库。 |
| 界面诊断 | 诊断目录 | 使用 `--inspect-ui` 时生成截图和控件树 JSON。 |

进程返回码：`0` 表示全部成功，`1` 表示预检或启动失败，`2` 表示部分导出或合并失败。

## 限制与注意事项

- 仅支持 Windows 版 SAP GUI，不自动操作 SAP GUI for HTML 或 SAP Fiori 应用。
- 执行依赖技术控件 ID，不使用窗口标题、翻译后的按钮文字、OCR 或固定坐标。
- 只自动确认两类 SAP GUI Scripting 安全提示：`A script is attempting to access SAP GUI.` 和 `A script is opening a connection to system:`。
- 遇到含义不明确的多按钮对话框时立即停止，不猜测“允许”“保存”或“覆盖”等操作。
- 除非明确传入 `--overwrite`，否则保留已有输出文件。
- dry run 和单目标验证均成功后，才应启动完整真实批次。

## 示例

将完整结果导出到独立测试目录：

```powershell
python scripts/mb5b_export.py `
  --input "<LOCAL_WORKSPACE>\库存地点.xlsx" `
  --date 2026-02-28 `
  --output-dir "<LOCAL_WORKSPACE>\mb5b-test"
```

如果返回码为 `2`，应保留已经成功的工作簿，并从日志中定位失败的工厂/库存地点组合。除非确实需要替换文件，否则不要用 `--overwrite` 重跑成功目标。
