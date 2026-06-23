import path from "node:path";
import { describe, expect, it } from "vitest";
// The validator is plain ESM so CI and local users can run it directly with Node.
import {
  validateLocalizedDoc,
  validateRepository,
  validateSkillContents,
} from "../scripts/validate-content.mjs";

const completeEnglish = `---
title: Example
summary: Example summary
tags: [example]
---
## Overview
## Use Cases
## Prerequisites
## Usage
## Inputs
## Outputs
## Limitations
## Examples
`;

const completeChinese = `---
title: 示例
summary: 示例说明
tags: [示例]
---
## 功能概述
## 适用场景
## 前置条件
## 用法
## 输入
## 输出
## 限制与注意事项
## 示例
`;

describe("skill content contract", () => {
  it("validates the real repository", () => {
    const skillsRoot = path.resolve(import.meta.dirname, "..", "..", "skills");
    const result = validateRepository(skillsRoot);
    expect(result.errors).toEqual([]);
    expect(result.skillCount).toBe(1);
  });

  it("rejects a missing localized section", () => {
    const errors = validateLocalizedDoc(completeEnglish.replace("## Outputs\n", ""), "en");
    expect(errors).toContain("README.en.md: missing required heading '## Outputs'");
  });

  it("requires SKILL.md name to match the directory slug", () => {
    const errors = validateSkillContents({
      slug: "example-skill",
      manifest: "---\nname: wrong-name\ndescription: Example\n---\n",
      en: completeEnglish,
      zh: completeChinese,
    });
    expect(errors.some((error: string) => error.includes("must match directory slug"))).toBe(true);
  });
});
