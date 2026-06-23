# SAP Skill Hub

SAP Skill Hub is a bilingual, static catalog for reusable SAP operation skills. The public site is generated directly from the repository's `skills` directory and is designed for GitHub Pages.

SAP Skill Hub 是一个用于整理和展示 SAP 操作类 Skill 的中英文静态目录站。主页、详情页和搜索索引都由仓库内的 `skills` 目录自动生成。

## Repository structure

```text
skills/
  Common/
  FI/
  CO/
  SD/
  MM/
  PP/
site/
tests/
```

Each skill must use this contract:

```text
skills/<module>/<slug>/
  SKILL.md
  README.zh-CN.md
  README.en.md
  agents/       # optional
  references/   # optional
  scripts/      # optional
```

Supported modules are `Common`, `FI`, `CO`, `SD`, `MM`, and `PP`. The directory slug must match the `name` in `SKILL.md`.

## Documentation requirements

Both localized README files require `title`, `summary`, and `tags` frontmatter. `transactions` and `systems` are optional.

Chinese documentation must contain:

- 功能概述
- 适用场景
- 前置条件
- 用法
- 输入
- 输出
- 限制与注意事项
- 示例

English documentation must contain:

- Overview
- Use Cases
- Prerequisites
- Usage
- Inputs
- Outputs
- Limitations
- Examples

The validation command fails when required content is incomplete, so invalid skills cannot be published.

## Local development

```powershell
cd site
npm install
npm run validate
npm test
npm run dev
```

The development server uses `/` as its base path. Production builds use `/SAPSkillhub/` for GitHub Pages:

```powershell
npm run check
npm run build
npm run preview
```

## Add a skill

1. Choose one supported SAP module.
2. Create `skills/<module>/<slug>/`.
3. Add `SKILL.md`, `README.zh-CN.md`, and `README.en.md`.
4. Run `npm run validate` and `npm test` from `site/`.
5. Open both localized pages locally and verify search terms, links, tables, and code blocks.

No central homepage index needs to be edited.

## Deployment

GitHub Actions validates the Python skill tests and website content on pull requests. A successful build on `main` deploys `site/dist` through GitHub Pages.

Expected public URL: <https://yin-wen-bin.github.io/SAPSkillhub/>
