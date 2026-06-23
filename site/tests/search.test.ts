import { describe, expect, it } from "vitest";
import { searchSkills } from "../src/lib/search";
import type { SkillSearchItem } from "../src/lib/types";

const records: SkillSearchItem[] = [
  {
    id: "MM/sap-mb5b-export",
    slug: "sap-mb5b-export",
    module: "MM",
    title: "SAP MB5B Export and Merge",
    summary: "Export inventory workbooks and merge them by plant.",
    tags: ["inventory", "Excel"],
    transactions: ["MB5B"],
    systems: ["SAP GUI for Windows"],
    searchText: "plant storage location posting date",
    href: "/SAPSkillhub/en/skills/MM/sap-mb5b-export/",
  },
  {
    id: "FI/example-fi",
    slug: "example-fi",
    module: "FI",
    title: "Financial document example",
    summary: "Display a financial document.",
    tags: ["document"],
    transactions: ["FB03"],
    systems: ["SAP ERP"],
    searchText: "accounting document",
    href: "/SAPSkillhub/en/skills/FI/example-fi/",
  },
];

describe("catalog search", () => {
  it("finds a skill by transaction code", () => {
    expect(searchSkills(records, "MB5B").map((record) => record.slug)).toEqual(["sap-mb5b-export"]);
  });

  it("finds a skill by full-text content", () => {
    expect(searchSkills(records, "storage location")[0]?.slug).toBe("sap-mb5b-export");
  });

  it("applies the module filter", () => {
    expect(searchSkills(records, "", "FI").map((record) => record.module)).toEqual(["FI"]);
    expect(searchSkills(records, "MB5B", "FI")).toEqual([]);
  });
});
