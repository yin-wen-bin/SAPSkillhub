# SAP Skill Hub

[中文](#中文) | [English](#english)

SAP Skill Hub 是一个面向 SAP 操作场景的开源双语 Skill 目录。站点会直接扫描仓库中的 `skills` 目录，自动生成模块导航、全文搜索和中英文详情页。

SAP Skill Hub is an open-source, bilingual catalog for reusable SAP operation skills. The website scans the repository's `skills` directory and automatically generates module navigation, full-text search, and localized detail pages.

**在线站点 / Live site:** <https://yin-wen-bin.github.io/SAPSkillhub/>

---

## 中文

### 项目功能

- 按 `Common`、`FI`、`CO`、`SD`、`MM`、`PP` 模块管理 SAP Skill。
- 自动发现仓库中的 Skill，无需手工维护主页索引。
- 支持按名称、事务码、说明、标签和正文搜索。
- 支持模块筛选、URL 查询参数和键盘快捷键 `/`、`Ctrl+K`。
- 根据浏览器语言选择中文或英文，并支持手动切换。
- 为每个 Skill 生成独立详情页，展示用途、用法、输入、输出、限制和示例。
- 提供 GitHub 源码入口和代码块复制功能。
- 通过 GitHub Actions 自动校验、构建并发布到 GitHub Pages。

### 仓库结构

```text
skills/
  Common/
  FI/
  CO/
  SD/
  MM/
  PP/
site/       # Astro 静态站点
tests/      # Skill 测试
```

每个 Skill 必须遵守以下目录契约：

```text
skills/<模块>/<skill-slug>/
  SKILL.md
  README.zh-CN.md
  README.en.md
  agents/       # 可选
  references/   # 可选
  scripts/      # 可选
```

- `<模块>` 只能是 `Common`、`FI`、`CO`、`SD`、`MM` 或 `PP`。
- `<skill-slug>` 使用小写 kebab-case，并且必须与 `SKILL.md` frontmatter 中的 `name` 一致。
- `SKILL.md` 保存给 Agent 使用的执行说明。
- `README.zh-CN.md` 和 `README.en.md` 保存站点展示的双语公开说明。

### 双语文档规范

两份本地化 README 都必须包含以下 frontmatter：

```yaml
---
title: Skill 显示名称
summary: 一句话功能说明
tags:
  - 标签
transactions:  # 可选
  - MB5B
systems:       # 可选
  - SAP S/4HANA
---
```

中文文档必须包含：

- 功能概述
- 适用场景
- 前置条件
- 用法
- 输入
- 输出
- 限制与注意事项
- 示例

英文文档必须包含对应的 `Overview`、`Use Cases`、`Prerequisites`、`Usage`、`Inputs`、`Outputs`、`Limitations` 和 `Examples`。

如果缺少语言文件、frontmatter、必填章节，或者目录名称不符合规范，构建会失败，从而阻止不完整内容发布。

### 运行依赖版本策略

带 `scripts/requirements.txt` 或运行时依赖的 Skill 必须区分“已测试基线”和“最低可接受版本”：

- `requirements.txt` 继续保留精确 pin，作为可复现的已测试基线。
- 环境检查脚本应显式声明 `MINIMUM_DEPENDENCIES` 和 `TESTED_DEPENDENCIES`。
- 当前环境版本满足 `>= minimum` 时，不应直接失败，应先运行原有环境检查、输入检查和必要的轻量运行检查。
- 如果检查成功，即使当前版本高于已测试基线，也不要求用户更新或降级。
- 如果检查失败且当前版本与已测试基线不同，应在错误信息中同时报告 tested baseline 和 current environment，并建议先用 `scripts/requirements.txt` 复现后再继续诊断。
- 如果当前版本低于最低要求，环境检查应直接失败并说明最低版本要求。

### 本地开发

环境要求：

- Node.js 22 或更高版本
- npm
- Python 3.12（运行现有 Python Skill 测试时使用）

安装依赖并启动开发服务器：

```powershell
cd site
npm install
npm run validate
npm test
npm run dev
```

默认开发地址为 <http://localhost:4321/>。

从仓库根目录执行完整检查和生产构建：

```powershell
python -m unittest discover -s tests

cd site
npm run validate
npm test
npm run check
npm run build
npm run preview
```

生产构建使用 `/SAPSkillhub/` 作为 GitHub Pages base path。

### 添加新的 Skill

1. 确认 Skill 所属模块。
2. 创建 `skills/<模块>/<skill-slug>/`。
3. 添加 `SKILL.md`、`README.zh-CN.md` 和 `README.en.md`。
4. 根据需要添加 `agents`、`references` 或 `scripts`。
5. 如果 Skill 带运行依赖，添加 pinned `scripts/requirements.txt`，并在环境检查中实现已测试基线与最低版本策略。
6. 在 `site` 目录运行 `npm run validate` 和 `npm test`。
7. 本地检查中英文主页、详情页、搜索关键词、表格、链接和代码块。
8. 提交 Pull Request；合并到 `main` 后站点会自动发布。

不需要修改中央索引或主页代码。

### 自动部署

`.github/workflows/pages.yml` 会在 Pull Request 和 `main` 分支更新时运行：

1. 执行 Python Skill 测试。
2. 校验所有 Skill 的目录和双语文档。
3. 执行 Vitest 和 Astro 类型检查。
4. 构建静态站点。
5. 在 `main` 分支构建成功后发布 GitHub Pages。

---

## English

### Features

- Organizes SAP skills by `Common`, `FI`, `CO`, `SD`, `MM`, and `PP` modules.
- Automatically discovers skills from the repository; no handwritten homepage index is required.
- Searches names, transaction codes, summaries, tags, and full documentation text.
- Supports module filters, shareable URL parameters, and `/` or `Ctrl+K` keyboard shortcuts.
- Selects Chinese or English from the browser language and provides a manual language switch.
- Generates a detail page for every skill with purpose, usage, inputs, outputs, limitations, and examples.
- Provides GitHub source links and copy buttons for code blocks.
- Uses GitHub Actions to validate, build, and deploy the website to GitHub Pages.

### Repository structure

```text
skills/
  Common/
  FI/
  CO/
  SD/
  MM/
  PP/
site/       # Astro static website
tests/      # Skill tests
```

Every skill must follow this directory contract:

```text
skills/<module>/<skill-slug>/
  SKILL.md
  README.zh-CN.md
  README.en.md
  agents/       # optional
  references/   # optional
  scripts/      # optional
```

- `<module>` must be `Common`, `FI`, `CO`, `SD`, `MM`, or `PP`.
- `<skill-slug>` must use lowercase kebab-case and match the `name` field in the `SKILL.md` frontmatter.
- `SKILL.md` contains the execution instructions used by an agent.
- `README.zh-CN.md` and `README.en.md` contain the public localized documentation rendered by the website.

### Bilingual documentation contract

Both localized README files require this frontmatter:

```yaml
---
title: Skill display name
summary: One-sentence description
tags:
  - tag
transactions:  # optional
  - MB5B
systems:       # optional
  - SAP S/4HANA
---
```

English documentation must contain:

- Overview
- Use Cases
- Prerequisites
- Usage
- Inputs
- Outputs
- Limitations
- Examples

Chinese documentation must contain the corresponding `功能概述`, `适用场景`, `前置条件`, `用法`, `输入`, `输出`, `限制与注意事项`, and `示例` sections.

The build fails when a language file, required frontmatter, mandatory section, or valid directory name is missing. Incomplete skills therefore cannot be published.

### Runtime dependency version policy

Skills with `scripts/requirements.txt` or runtime dependencies must distinguish a tested baseline from the minimum acceptable versions:

- Keep exact pins in `requirements.txt` as the reproducible tested baseline.
- Environment check scripts should declare `MINIMUM_DEPENDENCIES` and `TESTED_DEPENDENCIES` explicitly.
- When the current environment satisfies `>= minimum`, do not fail immediately. Run the existing environment, input, and necessary lightweight runtime checks first.
- If those checks pass, do not require a package update or downgrade, even when the installed version is newer than the tested baseline.
- If those checks fail while the installed versions differ from the tested baseline, report both the tested baseline and the current environment in the error output, and recommend reproducing with `scripts/requirements.txt` before further diagnosis.
- If an installed version is below the minimum requirement, fail the environment check and state the required minimum version.

### Local development

Requirements:

- Node.js 22 or later
- npm
- Python 3.12 for the existing Python skill tests

Install dependencies and start the development server:

```powershell
cd site
npm install
npm run validate
npm test
npm run dev
```

The default development URL is <http://localhost:4321/>.

Run the complete validation and production build from the repository root:

```powershell
python -m unittest discover -s tests

cd site
npm run validate
npm test
npm run check
npm run build
npm run preview
```

Production builds use `/SAPSkillhub/` as the GitHub Pages base path.

### Add a new skill

1. Choose the SAP module that owns the skill.
2. Create `skills/<module>/<skill-slug>/`.
3. Add `SKILL.md`, `README.zh-CN.md`, and `README.en.md`.
4. Add `agents`, `references`, or `scripts` when needed.
5. If the skill has runtime dependencies, add a pinned `scripts/requirements.txt` and implement the tested-baseline/minimum-version policy in the environment check.
6. Run `npm run validate` and `npm test` from `site/`.
7. Review both localized homepages and detail pages, including search terms, tables, links, and code blocks.
8. Open a pull request; merging to `main` publishes the website automatically.

No central index or homepage code needs to be edited.

### Automated deployment

`.github/workflows/pages.yml` runs for pull requests and updates to `main`:

1. Runs the Python skill tests.
2. Validates every skill directory and localized document.
3. Runs Vitest and the Astro type checker.
4. Builds the static website.
5. Deploys GitHub Pages after a successful build on `main`.
