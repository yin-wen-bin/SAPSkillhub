import type { Locale, SapModule } from "./types";
import { repositoryBranch, repositoryUrl } from "./siteConfig";

export function withBase(base: string, ...segments: string[]): string {
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const suffix = segments
    .filter(Boolean)
    .map((segment) => segment.replace(/^\/+|\/+$/g, ""))
    .join("/");
  return suffix ? `${normalizedBase}${suffix}/` : normalizedBase;
}

export function homePath(base: string, locale: Locale): string {
  return withBase(base, locale);
}

export function skillPath(base: string, locale: Locale, moduleName: SapModule, slug: string): string {
  return withBase(base, locale, "skills", moduleName, slug);
}

export function sourceUrl(moduleName: SapModule, slug: string): string {
  return `${repositoryUrl}/tree/${repositoryBranch}/skills/${moduleName}/${slug}`;
}
