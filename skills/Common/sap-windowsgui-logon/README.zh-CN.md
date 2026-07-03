---
title: SAP Windows GUI 自动登录
summary: 优先使用 SAP GUI Scripting 登录，并在提交凭据前不可用时自动回退到 SAP Shortcut。
tags:
  - SAP GUI
  - 自动登录
  - Windows
  - PowerShell
  - Python
  - SAP Shortcut
systems:
  - SAP ERP
  - SAP S/4HANA
  - SAP GUI for Windows
---

## 功能概述

本 Skill 从本地 JSON 配置读取 SAP 环境 Description、Client、User、Password 和 Logon Language，并按顺序使用两种方式登录：首先通过 pywin32 和 SAP GUI Scripting 登录；如果 Scripting 在提交凭据前不可用，则自动回退到 `sapshcut.exe`。

Scripting 方式通过 SAP 技术控件 ID 操作并验证 Client 和已认证用户。SAP Shortcut 方式不依赖 GUI Scripting，但因为无法读取会话，只能确认启动请求被接受，不能确认认证成功。

登录过程中如遇到 SAP GUI Scripting 的标准安全提示，本 Skill 仅在识别到已知安全提示文本和标准 `OK` 控件时自动确认；多重登录、改密码、许可证和其他二次业务对话框仍会停止并交给人工处理。

## 适用场景

- 使用固定的 SAP Logon 环境配置自动登录本机 SAP GUI。
- 在后续 SAP GUI 自动化开始前建立已认证会话。
- 检查登录配置文件的字段和格式是否正确。
- SAP Logon 安装在非标准路径时显式指定 `saplogon.exe`。
- 目标服务器禁用 SAP GUI Scripting 时通过 SAP Shortcut 尝试登录。

## 前置条件

- Windows 操作系统，并已安装 SAP GUI for Windows。
- Python 3.11 或更高版本，并安装 `pywin32>=311`。
- 优先方式需要 SAP 客户端和服务器端均启用 SAP GUI Scripting；回退方式需要 `sapshcut.exe`。
- SAP Logon 中已存在与 `Description` 完全一致的连接条目。
- SAP Shortcut 回退需要能从 `SAPUILandscape.xml` 将 Description 映射到 System ID，或在配置中提供可选的 `System`。
- 当前账号有权登录目标 SAP Client。
- 使用 Windows PowerShell 5.1 或更高版本运行脚本。

## 依赖版本策略

`scripts/requirements.txt` 保留已测试通过的精确版本：

```text
pywin32==311
```

登录脚本接受当前环境中满足最低要求的更高版本，并先运行原有的 `-ValidateOnly` 或登录流程。如果流程成功，不要求更新或降级当前环境。如果流程失败，且当前 `pywin32` 版本与已测试基线不同，脚本会同时报告当前版本和已测试基线，并建议先用 `scripts/requirements.txt` 复现。

## 用法

先将示例配置复制到默认的用户配置目录：

```powershell
$configDirectory = Join-Path $env:USERPROFILE ".sap-windowsgui-logon"
New-Item -ItemType Directory -Path $configDirectory -Force | Out-Null
Copy-Item "assets\config.example.json" (Join-Path $configDirectory "config.json")
```

在本机编辑 `config.json`，不要在聊天、日志或命令行中粘贴密码。首次使用先执行离线校验：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -ValidateOnly
```

校验通过后自动登录：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1"
```

使用其他配置文件时传入路径：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -ConfigPath "<LOCAL_CONFIG_PATH>\sap-logon.json"
```

## 输入

配置文件必须是 UTF-8 JSON，所有字段都必须是字符串：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `Description` | 是 | SAP Logon 中连接条目的精确 Description。 |
| `Client` | 是 | 三位 Client，例如 `100`；前导零不能省略。 |
| `User` | 是 | SAP 用户名。 |
| `Password` | 是 | SAP 密码；脚本不会输出该字段。 |
| `LogonLanguage` | 是 | 两位登录语言，例如 `EN`、`DE` 或 `ZH`。 |
| `System` | 否 | 三位 SAP System ID；仅在无法从本机 Landscape 映射时提供。 |

可选命令行参数：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-ConfigPath` | `%USERPROFILE%\.sap-windowsgui-logon\config.json` | 本地配置文件路径。 |
| `-TimeoutSeconds` | `60` | 等待 SAP 启动和登录完成的总秒数。 |
| `-SapLogonPath` | 自动发现 | 非标准安装时指定 `saplogon.exe` 完整路径。 |
| `-SapShcutPath` | 自动发现 | 非标准安装时指定 `sapshcut.exe` 完整路径。 |
| `-DisableSapshcutFallback` | 关闭 | 禁止 SAP Shortcut 回退，避免密码进入子进程命令行。 |
| `-ValidateOnly` | 关闭 | 只校验配置，不启动或操作 SAP。 |

## 输出

- Scripting 成功：返回码为 `0`，保留已登录的 SAP GUI 会话，并输出方法、Description 和 Client；认证已验证。
- SAP Shortcut 启动成功：返回码为 `0`，输出方法、System ID 和 Client；认证状态无法验证。
- 失败：返回码为 `1`，输出不包含密码的错误原因，并保留 SAP 窗口供人工检查。
- 配置校验：只确认 Description、Client 和 Logon Language，不输出 User 或 Password。

## 限制与注意事项

- 配置文件包含明文密码，必须放在仓库外，并使用 NTFS 权限限制为指定 Windows 用户可读。
- SAP Shortcut 需要通过子进程命令行传递密码。密码可能在进程运行期间被同机高权限进程读取；不接受该风险时使用 `-DisableSapshcutFallback`。
- 不支持 SAP GUI for HTML、SAP Fiori、SAP Business Client 网页内容或非 Windows 平台。
- `Description` 必须与 SAP Logon 中已有连接条目完全一致。
- 自动回退只发生在提交凭据之前。错误密码、已提交后的错误和二次对话框不会触发第二次尝试。
- Scripting 被服务器禁用时无法验证 SAP Shortcut 是否真正认证成功。
- 只自动确认两类 SAP GUI Scripting 安全提示：`A script is attempting to access SAP GUI.` 和 `A script is opening a connection to system:`。
- 遇到多重登录、修改密码、许可证或其他第二个对话框时会停止，不自动选择任何选项。
- 登录被拒绝后不会自动重试，避免重复错误密码导致账号锁定。
- 使用 SSO、SNC 或其他不显示标准登录字段的环境时，本脚本不会绕过现有认证流程。

## 示例

示例配置：

```json
{
  "Description": "QAS - Quality",
  "Client": "200",
  "User": "YOUR_SAP_USER",
  "Password": "YOUR_SAP_PASSWORD",
  "LogonLanguage": "ZH"
}
```

SAP Logon 无法自动发现时：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -SapLogonPath "<SAP_GUI_INSTALL_PATH>\saplogon.exe"
```

如果公司策略禁止密码进入进程命令行，可关闭回退：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File "scripts\logon.ps1" `
  -DisableSapshcutFallback
```
