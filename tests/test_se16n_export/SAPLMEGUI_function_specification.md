# SAPLMEGUI Function Specification

生成日期：2026-07-06  
分析对象：`SAPLMEGUI` 及其递归 INCLUDE  
导出目录：`D:\Skills\sap-se38-export\20260706`

## 1. 目的与业务定位

`SAPLMEGUI` 是 SAP Enjoy Purchasing GUI 的核心 Function Group/GUI 编排层。它不直接承载全部采购业务规则，而是把采购单、采购申请、分配/处理申请、外部/框架类采购对象的业务模型、屏幕页签、树形工作区、命令按钮、消息和增强点组织到一个可交互的 SAP GUI 事务体验中。

从导出的源码看，该程序主要支持以下业务场景：

- 采购订单显示/修改/创建流程，包括从外部入口跳转到 `ME22N`、`ME23N`。
- 采购申请处理流程，包括从 EBAN/EBKN 数据创建申请聚合并进入维护界面。
- 采购订单项目、抬头、明细、历史、文本、交货计划、服务、条件、合作伙伴、地址、Incoterms、柔性工作流、产品合规等页签维护。
- 申请项目的物料、数量、估价、供货源、外部寻源、历史、增强限制、联系人、文本等页签维护。
- 外部/outline/central contract 类采购对象的抬头、项目概览和项目明细页签。
- 通过 Enhancement Point、BAdI、行业开关和自定义字段容器扩展标准采购 GUI。

本规格说明偏重业务功能描述，技术细节仅用于解释业务行为和系统边界。

## 2. 分析范围

本次导出和递归解析完成以下范围：

| 指标 | 数量 |
|---|---:|
| 程序节点 | 203 |
| INCLUDE 关系 | 207 |
| 最大 INCLUDE 深度 | 4 |
| ABAP 源码行数 | 80,032 |
| 函数模块 | 18 |
| 类定义 | 154 |
| 类实现 | 147 |
| FORM | 31 |
| PBO/PAI Module | 54 |
| 导出失败 | 0 |

配套文件：

- Include 层级 Excel：`D:\Skills\sap-se38-export\20260706\SAPLMEGUI_include_hierarchy.xlsx`
- 代码清单：`D:\Skills\sap-se38-export\20260706\SAPLMEGUI_code_inventory.md`
- 机器可读图谱：`D:\Skills\sap-se38-export\20260706\include_graph.json`

## 3. 主要用户与业务角色

| 角色 | 典型诉求 | SAPLMEGUI 支持点 |
|---|---|---|
| 采购员 | 创建、修改、检查、保存采购订单 | PO transaction、header/item plugin、保存/检查/消息处理 |
| 采购申请处理人员 | 从采购申请生成采购订单或维护采购申请 | PR transaction、requisition plugin、source of supply、assign/process requisitions |
| 采购主管/审批相关用户 | 查看状态、输出、柔性工作流、释放/审批相关信息 | Header status、Flexible Workflow、PF-Status 排除逻辑 |
| 行业业务用户 | Oil/TSW、Fashion、Mill、NFM、Retail、ILE 等行业字段维护 | 行业 include、外部 dynpro、增强页签 |
| 扩展开发/实施顾问 | 增加客户字段、附加页签、布局控制、字段目录增强 | `MEPOBADI_LAYOUT`、customer include、EEW structures、enhancement points |

## 4. 高层业务流程

### 4.1 外部打开采购订单

函数模块 `MEPO_CALL` 接收采购订单号、项目号、事务类型和可选 Datablade：

1. 校验事务类型只允许显示或修改。
2. 按事务类型选择 `ME23N` 或 `ME22N`。
3. 执行事务码权限检查。
4. 设置参数 ID `BES`、`BSP`，把订单号和项目号传给后续事务。
5. 如有 Datablade，则写入 memory connector，进入事务后释放。
6. 调用目标事务。

业务含义：外部程序可用统一接口打开采购订单，并保留项目定位和跨事务上下文。

### 4.2 初始化维护界面

函数模块 `MEGUI_MAINTAIN` 是维护界面的主装配入口：

1. 获取 View Factory 和 Datablade Factory。
2. 初始化采购 GUI 框架、环境函数、个人化设置和工作清单设置。
3. 配置采购消息处理器。
4. 注册 MFS/metafield 服务和 proposer，用于 PO header、PO item、PR 等对象的字段默认与 X-structure 变化追踪。
5. 创建默认窗口、Document View、命令处理器和控制器。
6. 创建左侧工作清单/查询树并绑定双击事件。
7. 创建 `lcl_application`，把 Document View、树和 View Factory 交给应用对象管理。
8. 读取/写入个性化设置和 Datablade memory。

业务含义：用户看到的 Enjoy Purchasing 画面不是静态屏幕，而是按当前业务对象动态组装出的视图树、页签、命令和模型绑定。

### 4.3 应用和事务生命周期

`lcl_application` 管理当前业务会话：

- 读取上次序列化状态，恢复采购订单或采购申请的 process、单号、事务类型和激活状态。
- 根据文档类型选择 process：PO、PR、APR、OUT。
- 调用 `lcl_transaction_mgr` 打开对应 transaction。
- 通过 `lcl_plugin_mgr` 激活对应 GUI plugin。
- 根据 initiator 定位具体项目、字段或页签焦点。
- 在保存、检查、取消/反取消、切换显示/修改时委托当前 transaction 执行业务动作。

`lcl_transaction_mgr` 按 process 创建事务对象：

- `lcl_transaction_po`：采购订单。
- `lcl_transaction_req`：采购申请。
- `lcl_transaction_apr`：APR/申请分配相关流程。
- `lcl_transaction_out`：外部/outline/central contract 类采购对象。

业务含义：界面层允许同一框架承载不同采购对象，但每种对象的打开、保存、检查和可用命令由专门 transaction 类控制。

## 5. GUI 插件架构

### 5.1 插件管理

`lcl_plugin_mgr` 是插件工厂和缓存：

- 按 process 创建 PO、PR、APR、OUT plugin。
- 缓存已创建的 plugin，避免重复构建。
- 激活新 plugin 时清空旧模型、停用旧视图，再启用新视图。

### 5.2 插件基类行为

`lcl_plugin_basic` 控制通用布局和可见性：

- 跟踪 header、item detail、item overview 的激活变化。
- 根据当前屏幕布局决定哪些区域展开或收起。
- 避免互斥视图同时可编辑，例如供应商地址和项目交货地址、付款页签和服务/限制页签等。
- 根据焦点模型和 metafield 找到需要聚焦的子视图。

业务含义：用户切换页签、展开抬头/项目明细、从消息跳转到字段时，系统会自动调整可见区域并定位焦点。

## 6. 采购订单功能范围

### 6.1 PO 顶部区域

`MEGUI_BUILD_TOPLINE_PLUGIN` 构建采购订单顶部区域：

- 显示/维护单据类型、单号、供应商/供货工厂、单据日期等核心信息。
- 创建购物篮/工作区图形区域，支持采购文档和申请对象拖拽或工作清单交互。
- 调用 `MEPOBADI_LAYOUT`，允许实施方在 `TOPLINE` 元素上追加布局扩展。

### 6.2 PO 抬头页签

`MEGUI_BUILD_PO_HEADER_PLUGIN` 构建采购订单抬头明细，包括：

- 交货和付款条件。
- 供应商地址。
- 通讯数据。
- 抬头文本。
- 合作伙伴。
- 抬头状态。
- 抬头条件。
- 组织数据。
- 其他抬头数据。
- Incoterms。
- 柔性工作流。
- 产品合规。
- 自定义字段容器 `EKKO_INCL_EEW_PS`。
- 客户自定义抬头页签和 BAdI 动态订阅页签。
- Fashion order scheduling、Oil header extension、ILE annex/package、PTFM 等行业/本地化页签。

业务含义：采购订单抬头区域覆盖供应商、组织、付款、文本、合规、工作流和增强字段，是订单级决策和控制信息的主维护区。

### 6.3 PO 项目概览

`MEGUI_BUILD_PO_ITEMOV_PLUGIN` 构建项目概览表：

- 绑定结构 `MEPO1211` 和 table control `tc_1211`。
- 设置默认定位字段为物料号。
- 提供项目级 controller，用于项目选择、表格事件、命令处理。
- 可与 grid/table 两种项目展示方式切换。

业务含义：项目概览是采购订单行项目维护的入口，承载批量行项目浏览和快速编辑。

### 6.4 PO 项目明细页签

`MEGUI_BUILD_PO_ITEM_PLUGIN` 构建项目明细和导航，覆盖以下业务页签：

- 服务和限制。
- 交货、收货、催交相关数据。
- 项目自定义字段 `EKPO_INCL_EEW_PS`。
- 发票/付款控制。
- 物料数据、MPN/制造商料号、货号/HTN。
- 数量单位转换、重量/体积。
- 交货计划。
- 项目条件/价格。
- 项目文本。
- 变式、SLS 项目、Spec2000/子承包、外部链接。
- 交货地址、发运数据。
- 确认和外部确认，含 ALV 确认 grid。
- Retail、价格控制、Brazil/India/Italy 等本地化页签。
- 项目历史、冻结/阻止原因。
- 项目 Incoterms、增强限制、产品合规。
- 客户项目页签、BAdI 动态页签。
- ILE annex/package、Oil/TSW、Oil fee、Retail dateline 等行业扩展。

业务含义：项目明细是采购订单履约、价格、交货、服务、合规和行业字段的主维护区。

### 6.5 PO 保存、检查和命令控制

`lcl_transaction_po` 控制采购订单事务行为：

- 打开订单时按单号读取数据库，或为创建模式准备新订单。
- 支持从采购申请展开生成采购订单项目。
- 按事务模式和开关设置 PF-Status，例如显示模式下隐藏保存、检查、批量修改、取消等功能。
- 保存时先判断是否有变更，再执行 `po_check`。
- 对错误、警告、park/hold 场景弹出确认，允许用户保存、暂存、保持或取消。
- 执行 `po_post` 后刷新状态、序列化新单据、必要时打开下一张新建单据。
- 支持取消/反取消、打印/输出相关按钮控制、BRF+ 输出预览按钮控制。

业务含义：界面层确保用户只能在合适的事务状态下执行命令，并把保存前校验、消息展示和后续界面刷新串起来。

## 7. 采购申请功能范围

### 7.1 从申请数据进入维护

`MEGUI_ASSIGN_AND_PROCESS_REQS` 从传入的 table manager 读取 `EBAN`，创建 requisition aggregate、header 和 item，再调用 `MEGUI_MAINTAIN`。

业务含义：系统可以从外部申请列表或分配场景进入 GUI，并把申请数据转换成可维护的模型结构。

### 7.2 PR 顶部和抬头

`MEGUI_BUILD_REQ_TOPLINE_PLUGIN` 和 `MEGUI_BUILD_REQ_HEADER_PLUGIN` 构建申请顶部和抬头区域：

- 顶部区域绑定 `MEREQ_TOPLINE`，默认字段为申请号。
- 提供 PR 购物篮/工作区图形区域。
- 抬头页签主要包含申请抬头文本和可扩展的附加视图。

### 7.3 PR 项目明细

`MEGUI_BUILD_REQ_ITEM_PLUGIN` 构建采购申请项目明细，包括：

- 服务和限制。
- 物料。
- 数量。
- 估价。
- 自定义字段 `EBAN_INCL_EEW_PS`。
- 供货源、供货源 grid、供货源 toggle/composite。
- Brazil 本地化。
- 项目文本。
- 增强限制。
- 联系人。
- 外部寻源。
- 历史记录。
- 客户自定义项目页签。
- Spec2000/子承包页签。
- 交货地址。

业务含义：申请项目维护侧重需求描述、数量/估价、供货源选择、寻源和后续采购处理所需信息。

### 7.4 PR 项目表和 Catalog

`lcl_req_item_table`、`lcl_req_item_grid`、`lcl_catalog` 等类实现申请项目表格和 catalog 交互：

- 支持申请项目表格显示和 grid 显示。
- 支持字段目录增强、catalog 值映射和文本 ID 确定。
- Fashion 季节字段、主题、系列等字段会在申请表格中参与映射和屏幕修改。

业务含义：采购申请项目可以通过表格、catalog 和增强字段进行高效批量维护。

## 8. OUT / Outline / Central Contract 类流程

OUT process 由 `MEGUI_BUILD_OUT_TOPLINE_PLUGIN`、`MEGUI_BUILD_OUT_HEADER_PLUGIN`、`MEGUI_BUILD_OUT_ITEMOV_PLUGIN`、`MEGUI_BUILD_OUT_ITEM_PLUGIN` 组装：

- 顶部区域绑定 `MEOUT_TOPLINE`。
- 抬头页签包含 basic data for central contract、抬头文本和 BAdI 动态页签。
- 项目概览绑定 `MEOUT1410`。
- 项目明细包含项目文本、服务、物料、MPN/HTN、项目历史和 BAdI 动态页签。

业务含义：同一 GUI 框架可承载中心合同/outline 类采购对象，复用文档、项目和文本维护模式。

## 9. 消息、校验与错误处理

系统使用 `cl_message_handler_mm` 统一处理采购消息：

- 初始化时调用 `set_config_for_mepo` 配置采购消息行为。
- 保存前执行业务对象的 `po_check` 或对应 transaction check。
- 错误时显示消息并可根据 park/hold 权限提供替代处理。
- 警告时弹出确认，用户可继续或取消。
- 应用层 `display_all_events` 负责把消息事件反馈到界面。
- 从消息定位字段时，通过 plugin 的 `get_view_for_focus` 找到对应模型视图和 metafield。

业务含义：用户看到的错误、警告和字段定位由 GUI 框架统一协调，但业务规则由底层采购对象和增强实现决定。

## 10. 权限和安全控制

源码中体现的主要权限/安全控制：

- `MEPO_CALL` 在跳转 `ME22N`/`ME23N` 前调用 `AUTHORITY_CHECK_TCODE`。
- Spot-buy 供应商帮助读取 `TSUPP_SB` 与 `LFA1` 后，按供应商权限组检查 `F_LFA1_BEK` 的 F4 或显示权限。
- 事务命令可用性受事务类型、显示/修改模式、业务开关、输出管理状态和 BAdI 激活状态控制。
- 删除、取消、反取消、保存、park/hold、批量修改等按钮会按业务状态从 PF-Status 排除。

业务含义：界面不会只靠后端失败来控制权限，很多按钮和入口会在 GUI 层提前收敛。

## 11. 扩展点与行业增强

### 11.1 通用扩展

- `MEPOBADI_LAYOUT`：允许按 application/element/subscriber 动态添加自定义屏幕页签。
- `MEPOBADI_CONFIRMATION`：控制确认相关功能是否激活。
- EEW customer fields：PO header `EKKO_INCL_EEW_PS`、PO item `EKPO_INCL_EEW_PS`、PR item `EBAN_INCL_EEW_PS`。
- `MEGUI_GRID_ENHANCEMENT` 等 BAdI：增强 grid 字段目录和字段映射。
- 多个 `ENHANCEMENT-POINT` 和 `ENHANCEMENT-SECTION`：用于行业包和客户增强插入标准流程。

### 11.2 行业和本地化增强

| 增强域 | 主要业务内容 |
|---|---|
| Fashion / FSH | Order scheduling、VAS、deallocation、季节/系列/主题字段、PR season F4 |
| Oil / TSW | TSW 细节、nomination、carrier point、laycan/layout、screen 配置、fee、header/item extension |
| NFM | 非铁金属/原料计价相关默认值、item raw material charging、header defaults |
| ILE | Annex 和 package annex 的 header/item 页签 |
| Mill / SAPMP | Fast data entry、characteristic extension、CE 数据、原批次/材料特性相关增强 |
| Retail / WRF | Dateline / transportation chain 相关页签 |
| PTFM | PO header 本地化字段 |
| Brazil/India/Italy | 项目级本地化字段和校验，例如 Brazil、GST India、Italy CUP/CIG |
| Spec2000 / MPN | A&D Spec2000、子承包和制造商料号相关页签 |

业务含义：`SAPLMEGUI` 是标准采购 GUI 与行业解决方案共同挂接的枢纽，很多页签只有在开关、配置或 BAdI 激活时才显示。

## 12. 关键数据对象和模型

| 对象/结构 | 用途 |
|---|---|
| `MEPO_DOCUMENT` | 传入维护界面的文档上下文，含 process、doc type、key、transaction type、initiator |
| `MEPOHEADER` / `MEPOHEADERX` | PO 抬头数据及变更标记 |
| `MEPOITEM` / `MEPOITEMX` | PO 项目数据及变更标记 |
| `MEPOSCHEDULE` / `MEPOSCHEDULEX` | PO 交货计划数据及变更标记 |
| `MEREQ*` 结构 | PR 顶部、抬头、项目、供货源、历史等页签数据 |
| `MEOUT*` 结构 | OUT/central contract 类对象的抬头、项目和明细数据 |
| `MMPUR_MODELS` | 视图绑定模型列表，用于 table/grid 和 observer 交互 |
| `cl_po_header_handle_mm`、`cl_po_item_handle_mm` | PO 业务对象句柄，负责读取、校验、保存、设置数据 |
| `cl_requisition_aggregate_mm`、`cl_req_header_proxy_mm`、`cl_req_item_proxy_mm` | PR 聚合和代理对象 |
| `cl_framework_mm` | GUI 框架实例，管理 fcode、personalization、proposer、事件等 |
| `cl_message_handler_mm` | 采购消息收集、清理和显示 |

## 13. 业务流程摘要

### 13.1 创建采购订单

1. 应用层识别 create transaction type。
2. PO transaction 创建 `cl_po_header_handle_mm`。
3. 调用 `po_prepare_creation` 做创建前授权和初始化。
4. 如从申请创建，调用 `expand_from_requisitions` 把申请展开为 PO 项目。
5. 激活 PO plugin，展示顶部、抬头、项目概览、项目明细。
6. 用户维护字段、页签或增强数据。
7. 保存时执行 `po_check`，根据错误/警告/park/hold 权限引导用户。
8. 成功 `po_post` 后显示消息，必要时打开下一张新单据。

### 13.2 修改采购订单

1. 按订单号读取数据库并初始化模型。
2. 按事务状态决定可用按钮和页签。
3. 用户修改抬头、项目、交货计划、条件、文本或行业字段。
4. Observer/transport 机制把 dynpro 数据同步到模型并标记变更。
5. 保存前执行校验、警告确认和最终过账。

### 13.3 显示采购订单

1. `MEPO_CALL` 或应用初始化设置 display transaction type。
2. GUI 层隐藏保存、检查、批量修改、取消等不可用命令。
3. 用户可浏览抬头/项目/历史/文本/行业页签。
4. 如显示模式由内存标识强制，创建和切换按钮也会被隐藏。

### 13.4 处理采购申请

1. 从 EBAN/EBKN 或已保存上下文创建 PR aggregate。
2. 激活 PR plugin。
3. 用户维护申请物料、数量、估价、供货源、文本、历史、外部寻源和增强字段。
4. 可通过分配/处理功能进入采购订单或后续采购处理流程。

## 14. 非功能性说明

| 维度 | 说明 |
|---|---|
| 可配置性 | 大量页签由开关、字段选择、BAdI、行业组件和客户增强控制 |
| 可扩展性 | 标准提供动态 BAdI layout、EEW include、enhancement points 和行业 include |
| 用户体验 | 支持展开/收起区域、tabstrip、树形工作清单、grid/table、消息定位和个性化 |
| 一致性 | 数据通过 model/view observer 和 transport 方法同步，保存前统一校验 |
| 安全性 | 事务码权限、供应商权限、按钮排除和业务状态检查共同控制入口 |
| 可维护性 | 代码按 TOP、函数模块、PBO/PAI、FORM、类定义和实现拆分，但增强包较多，影响分析复杂度 |

## 15. 边界与不在本规格中的内容

- 本规格不定义采购订单定价、MRP、库存、账户分配、输出管理、审批流等后端业务规则；这些规则由被调用的业务对象、函数模块、BAdI 和配置实现。
- 本规格不说明每个 SAP 标准表字段的字段级校验；源码中大部分字段状态来自 field selection、MFS/metafield 和底层 handler。
- 本规格基于 2026-07-06 当前 SAP 系统导出的源码，行业开关和 BAdI 激活状态可能因系统配置不同而改变实际可见页签。

## 16. 结论

`SAPLMEGUI` 的业务价值在于把采购单据处理的复杂业务对象封装成统一、可扩展、可个性化的 SAP GUI 体验。它的核心不是单一业务算法，而是以下能力组合：

1. 统一入口和事务生命周期管理。
2. 动态构建 PO、PR、OUT/APR 的顶部、抬头、项目概览和项目明细插件。
3. 把用户操作、屏幕数据传输、模型变更、消息显示和保存校验串联起来。
4. 为行业解决方案、本地化和客户增强提供稳定挂接点。
5. 在显示/修改/创建、park/hold、输出管理、取消/反取消等状态下控制可用业务命令。

因此，在业务功能层面，`SAPLMEGUI` 应被理解为 SAP 采购 Enjoy GUI 的“业务交互编排器”：它把采购订单、采购申请和相关采购对象的维护功能组织成可操作的工作台，并通过标准增强机制支持不同行业和客户的差异化采购流程。
