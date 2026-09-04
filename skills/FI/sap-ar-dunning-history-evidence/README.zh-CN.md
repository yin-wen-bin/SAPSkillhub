# SAP AR 历史催收证据

该 Skill 按公司代码、1–50个客户和截止日期读取已经执行的催收事件。当前目标系统存在发布视图 `I_DunningEntryItem`，但 ADT Data Preview 无法可靠投影完整项目键，因此使用经实时 DDIC 验证的 `MHNK/MHND` 只读回退。

它不修改 SAP，不重建任意历史日期的客户催收主数据快照，也不把空结果表述为“从未催收”。
