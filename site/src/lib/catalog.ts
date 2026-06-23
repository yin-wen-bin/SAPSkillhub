import { getCollection, type CollectionEntry } from "astro:content";
import { MODULES, type Locale, type SapModule } from "./types";

type DocEntry = CollectionEntry<"skillDocs">;

export interface LocalizedSkill {
  entry: DocEntry;
  title: string;
  summary: string;
  tags: string[];
  transactions: string[];
  systems: string[];
  searchText: string;
}

export interface SkillRecord {
  id: string;
  slug: string;
  module: SapModule;
  manifestDescription: string;
  locales: Record<Locale, LocalizedSkill>;
}

interface DraftSkillRecord {
  id: string;
  slug: string;
  module: SapModule;
  manifestDescription: string;
  locales: Partial<Record<Locale, LocalizedSkill>>;
}

function normalizedId(id: string): string {
  return id.replaceAll("\\", "/").replace(/\.md$/i, "");
}

function parseDocId(id: string): { module: SapModule; slug: string; locale: Locale } | null {
  const match = normalizedId(id).match(/^([^/]+)\/([^/]+)\/readme\.?(en|zh-cn)$/i);
  const moduleName = match && MODULES.find((candidate) => candidate.toLowerCase() === match[1].toLowerCase());
  if (!match || !moduleName) return null;
  return {
    module: moduleName,
    slug: match[2],
    locale: match[3].toLowerCase() === "zh-cn" ? "zh" : "en",
  };
}

function parseManifestId(id: string): { module: SapModule; slug: string } | null {
  const match = normalizedId(id).match(/^([^/]+)\/([^/]+)\/skill$/i);
  const moduleName = match && MODULES.find((candidate) => candidate.toLowerCase() === match[1].toLowerCase());
  if (!match || !moduleName) return null;
  return { module: moduleName, slug: match[2] };
}

function plainText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/[|>*_~-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export async function loadCatalog(): Promise<SkillRecord[]> {
  const [manifestEntries, docEntries] = await Promise.all([
    getCollection("skillManifests"),
    getCollection("skillDocs"),
  ]);

  const records = new Map<string, DraftSkillRecord>();

  for (const manifest of manifestEntries) {
    const parsed = parseManifestId(manifest.id);
    if (!parsed) throw new Error(`Unsupported SKILL.md path: ${manifest.id}`);
    const id = `${parsed.module}/${parsed.slug}`;
    if (manifest.data.name !== parsed.slug) {
      throw new Error(`${manifest.id}: name '${manifest.data.name}' must match '${parsed.slug}'`);
    }
    records.set(id, {
      id,
      slug: parsed.slug,
      module: parsed.module,
      manifestDescription: manifest.data.description,
      locales: {},
    });
  }

  for (const entry of docEntries) {
    const parsed = parseDocId(entry.id);
    if (!parsed) throw new Error(`Unsupported localized README path: ${entry.id}`);
    const id = `${parsed.module}/${parsed.slug}`;
    const record = records.get(id);
    if (!record) throw new Error(`${entry.id}: matching SKILL.md is missing`);
    record.locales[parsed.locale] = {
      entry,
      title: entry.data.title,
      summary: entry.data.summary,
      tags: entry.data.tags,
      transactions: entry.data.transactions,
      systems: entry.data.systems,
      searchText: plainText(entry.body ?? ""),
    };
  }

  const result: SkillRecord[] = [];
  for (const [id, record] of records) {
    if (!record.locales.en || !record.locales.zh) {
      throw new Error(`${id}: both README.en.md and README.zh-CN.md are required`);
    }
    result.push(record as SkillRecord);
  }

  return result.sort((a, b) => {
    const moduleOrder = MODULES.indexOf(a.module) - MODULES.indexOf(b.module);
    return moduleOrder || a.slug.localeCompare(b.slug);
  });
}

export function moduleCounts(records: SkillRecord[]): Record<SapModule, number> {
  const counts = Object.fromEntries(MODULES.map((moduleName) => [moduleName, 0])) as Record<SapModule, number>;
  for (const record of records) counts[record.module] += 1;
  return counts;
}
