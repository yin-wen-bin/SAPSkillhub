---
title: SAP ADT 表与 CDS 证据导出
summary: 通过 SAP ADT Data Preview 执行严格只读、明确有界的表或 CDS 证据查询。
tags: [sap, adt, 只读, 证据, 导出]
systems: [SAP S/4HANA, SAP NetWeaver AS ABAP]
---

## 功能概述

本 Skill 用 SAP ADT Data Preview 填补小范围证据缺口。它只接收结构化查询意图，从受保护的可信 profile 解析连接和白名单，在内部生成 SELECT，并输出规范 JSON 与 SHA-256 manifest。

## 适用场景

仅当发布的 API 或 OData 无法提供所需字段时使用，并排在 GUI SE16N 之前。适合查询经过审核的表或 CDS 字段，且范围小、筛选明确有界。不适合作为通用 SQL、批量取数、开发、激活或传输工具。

## 前置条件

- SAP 用户仅具备目标 ADT Data Preview 只读权限。
- `/sap/bc/adt/datapreview/freestyle` 已通过 HTTPS 启用。
- 证书链可信，禁止关闭 TLS 校验。
- 仓库外的受保护 profile 文件已审核对象、字段、类型、有界筛选字段和真实稳定键，可参考 `references/profiles.example.json`。
- Python 3.10+，并安装 `scripts/requirements.txt` 中已测试的 `requests==2.34.2`（最低接受版本为 2.31.0）。

## 用法

在本 Skill 目录执行：

```powershell
python scripts/check_environment.py
$env:SAP_ADT_PROFILES_FILE = "C:\protected\adt-profiles.json"
python run.py --input input.json --output .artifacts\adt-table-export\output.json
```

首次真机运行必须遵循 `references/live-validation.md`，任务和结果文件均保存在被 Git 忽略的运行目录中。

## 输入

输入契约见 `references/input.schema.json`。任务只能包含可信 profile 名、`table` 或 `cds`、白名单对象与字段、类型化筛选、与稳定键完全一致的升序和有界 `max_rows`。至少包含一个经审核的 EQ、BT 或 IN 有界筛选。原始 SQL、URL、账号密码、SAP client、端点和 TLS 开关都会被拒绝。

## 输出

输出遵循 `references/output.schema.json`，包括运行与来源标识、精确范围、行、行数、完整性、截断、闭集错误码、时间戳和哈希。`complete` 只表示这一精确有界选择完整；`partial` 的 `source_complete` 必为 `false`；`failed` 不返回行。

## 限制与注意事项

仅实现指向唯一 Data Preview 端点的 GET 和只读 POST 兼容回退。分页必须使用经审核的真实稳定键和升序 keyset。运行时不能证明 `max_rows` 之外的完整性，不能猜测键、发现或扩展白名单、绕过权限、接受重定向或降低 TLS 强度。CDS 访问控制可能合法地减少返回行。

## 示例

```json
{
  "schema_version": 1,
  "connection_profile": "quality-readonly",
  "source_type": "table",
  "object": "TSTC",
  "fields": ["TCODE", "PGMNA"],
  "filters": [{"field": "TCODE", "operator": "eq", "value": "SE16N"}],
  "order_by": [{"field": "TCODE", "direction": "asc"}],
  "max_rows": 2
}
```

若结果为一行、无验证问题且 `source_complete=true`，只能证明 `TCODE = SE16N` 这一精确选择完成。
