export const MODULES = ["Common", "FI", "CO", "SD", "MM", "PP"] as const;

export type SapModule = (typeof MODULES)[number];
export type Locale = "zh" | "en";

export interface SkillSearchItem {
  id: string;
  slug: string;
  module: SapModule;
  title: string;
  summary: string;
  tags: string[];
  transactions: string[];
  systems: string[];
  searchText: string;
  href: string;
}
