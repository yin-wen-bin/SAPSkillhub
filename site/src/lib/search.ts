import Fuse from "fuse.js";
import type { IFuseOptions } from "fuse.js";
import type { SapModule, SkillSearchItem } from "./types";

const FUSE_OPTIONS: IFuseOptions<SkillSearchItem> = {
  threshold: 0.32,
  ignoreLocation: true,
  minMatchCharLength: 2,
  keys: [
    { name: "title", weight: 0.3 },
    { name: "transactions", weight: 0.2 },
    { name: "tags", weight: 0.16 },
    { name: "summary", weight: 0.14 },
    { name: "slug", weight: 0.1 },
    { name: "module", weight: 0.05 },
    { name: "searchText", weight: 0.05 },
  ],
};

export function searchSkills(
  records: SkillSearchItem[],
  query: string,
  moduleName: SapModule | "all" = "all",
): SkillSearchItem[] {
  const moduleRecords = moduleName === "all" ? records : records.filter((record) => record.module === moduleName);
  const normalizedQuery = query.trim();
  if (!normalizedQuery) return moduleRecords;
  return new Fuse(moduleRecords, FUSE_OPTIONS).search(normalizedQuery).map((result) => result.item);
}
