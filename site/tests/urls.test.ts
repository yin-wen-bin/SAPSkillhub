import { describe, expect, it } from "vitest";
import { homePath, skillPath, withBase } from "../src/lib/urls";

describe("GitHub Pages routes", () => {
  it("prefixes internal links with the repository base", () => {
    expect(withBase("/SAPSkillhub", "zh")).toBe("/SAPSkillhub/zh/");
    expect(homePath("/SAPSkillhub/", "en")).toBe("/SAPSkillhub/en/");
    expect(skillPath("/SAPSkillhub/", "zh", "MM", "sap-mb5b-export")).toBe(
      "/SAPSkillhub/zh/skills/MM/sap-mb5b-export/",
    );
  });
});
