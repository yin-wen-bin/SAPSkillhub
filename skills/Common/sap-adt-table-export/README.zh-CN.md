---
title: SAP ADT 表与 CDS 证据导出
summary: 通过 SAP ADT Data Preview 执行严格只读、明确有界的表或 CDS 证据查询。
tags: [sap, adt, 只读, 证据, 导出]
systems: [SAP S/4HANA, SAP NetWeaver AS ABAP]
---

## 功能概述

本 Skill 用 SAP ADT Data Preview 填补明确有界的证据缺口。它只接收结构化查询意图，使用内部配置的默认连接，在内部生成 SELECT，并输出规范 JSON 与 SHA-256 manifest。动态模式不维护表、读取字段或过滤字段白名单，而是以目标系统实时 ADT/DDIC 元数据为准。

## 适用场景

仅当发布的 API 或 OData 无法提供所需字段时使用，并排在 GUI SE16N 之前。适合查询实时 DDIC 可确认的表或 CDS 字段，且筛选明确有界。不适合作为通用 SQL、开发、激活或传输工具。

## 前置条件

- SAP 用户仅具备目标 ADT Data Preview 只读权限。
- `/sap/bc/adt/datapreview/freestyle` 已通过 HTTPS 启用。
- 证书链可信，禁止关闭 TLS 校验。
- 从 `.env.example` 复制得到的、已被 Git 忽略的 Skill 自有 `.env`，以及仓库外的受保护 profile 文件。profile 文件声明内部 `default_profile`，调用方不能选择或覆盖；动态模式通过实时 DDIC 确认对象、字段、递归展开的 include 结构、类型和真实稳定键。如果活动透明表、DDIC View 或 include 源端点没有发布，可通过有界的活动版本 DD02L/DD03L 读取重建相同字段/键契约；该补充路径不用于 CDS。include 循环、过深嵌套或继承字段冲突会安全失败。
- Python 3.10+，并安装 `scripts/requirements.txt` 中已测试的 `requests==2.34.2`（最低接受版本为 2.31.0）。

## 用法

在本 Skill 目录执行：

```powershell
python scripts/check_environment.py
Copy-Item .env.example .env
# 编辑已忽略的 .env 和仓库外的受保护 profile。
python run.py --input input.json --output .artifacts\adt-table-export\output.json
```

首次真机运行必须遵循 `references/live-validation.md`，任务和结果文件均保存在被 Git 忽略的运行目录中。

## 输入

输入契约见 `references/input.schema.json`。任务只能包含 `table` 或 `cds`、对象与字段、类型化筛选、与实时 DDIC 稳定键完全一致的升序和有界 `max_rows`。任何实时存在的字段都可用于读取或筛选，但至少要有一个包含式 EQ、BT 或 IN 筛选；`max_rows` 最大为 30,000。profile 名、原始 SQL、URL、账号密码、SAP client、端点和 TLS 开关都会被拒绝。

## 输出

输出遵循 `references/output.schema.json`，包括运行标识、脱敏后的来源、精确范围、行、行数、完整性、截断、闭集错误码、时间戳和哈希。`source.stable_key` 显示实时稳定键，返回行包含这些可审计支持键，`scope.returned_fields` 声明实际行结构。内部 profile 名、SAP URL、client、凭证和连接路径不会输出。`complete` 只表示这一精确有界选择完整；`partial` 的 `source_complete` 必为 `false`；`failed` 不返回行。

## 限制与注意事项

仅实现指向唯一 Data Preview 端点的 GET 和只读 POST 兼容回退。分页必须使用实时 DDIC 声明的真实稳定键和升序 keyset。运行时不能证明 `max_rows` 之外的完整性，不能猜测键、绕过权限、接受重定向或降低 TLS 强度。达到 30,000 行或任务声明的更小上限时必须返回 `partial/row_limit_reached`。CDS 访问控制可能合法地减少返回行。

## 示例

```json
{
  "schema_version": 1,
  "source_type": "table",
  "object": "TSTC",
  "fields": ["TCODE", "PGMNA"],
  "filters": [{"field": "TCODE", "operator": "eq", "value": "SE16N"}],
  "order_by": [{"field": "TCODE", "direction": "asc"}],
  "max_rows": 2
}
```

若结果为一行、无验证问题且 `source_complete=true`，只能证明 `TCODE = SE16N` 这一精确选择完成。
