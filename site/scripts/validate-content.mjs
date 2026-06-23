import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import matter from "gray-matter";

export const MODULES = ["Common", "FI", "CO", "SD", "MM", "PP"];

export const REQUIRED_HEADINGS = {
  en: [
    "Overview",
    "Use Cases",
    "Prerequisites",
    "Usage",
    "Inputs",
    "Outputs",
    "Limitations",
    "Examples",
  ],
  "zh-CN": [
    "功能概述",
    "适用场景",
    "前置条件",
    "用法",
    "输入",
    "输出",
    "限制与注意事项",
    "示例",
  ],
};

const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

function levelTwoHeadings(body) {
  return new Set(
    [...body.matchAll(/^##\s+(.+?)\s*$/gm)].map((match) => match[1].trim()),
  );
}

function validateStringList(value, field, location) {
  if (!Array.isArray(value) || value.length === 0 || value.some((item) => typeof item !== "string" || !item.trim())) {
    return [`${location}: frontmatter '${field}' must be a non-empty string array`];
  }
  return [];
}

export function validateLocalizedDoc(markdown, locale, location = `README.${locale}.md`) {
  const errors = [];
  let parsed;
  try {
    parsed = matter(markdown);
  } catch (error) {
    return [`${location}: invalid frontmatter (${error instanceof Error ? error.message : String(error)})`];
  }

  for (const field of ["title", "summary"]) {
    if (typeof parsed.data[field] !== "string" || !parsed.data[field].trim()) {
      errors.push(`${location}: frontmatter '${field}' is required`);
    }
  }
  errors.push(...validateStringList(parsed.data.tags, "tags", location));

  for (const optionalList of ["transactions", "systems"]) {
    const value = parsed.data[optionalList];
    if (value !== undefined && (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.trim()))) {
      errors.push(`${location}: frontmatter '${optionalList}' must be a string array when present`);
    }
  }

  const headings = levelTwoHeadings(parsed.content);
  for (const heading of REQUIRED_HEADINGS[locale]) {
    if (!headings.has(heading)) {
      errors.push(`${location}: missing required heading '## ${heading}'`);
    }
  }
  return errors;
}

export function validateSkillContents({ slug, manifest, en, zh }, location = slug) {
  const errors = [];
  if (!SLUG_PATTERN.test(slug)) {
    errors.push(`${location}: skill directory must use a lowercase kebab-case slug`);
  }

  let manifestData = {};
  try {
    manifestData = matter(manifest).data;
  } catch (error) {
    errors.push(`${location}/SKILL.md: invalid frontmatter (${error instanceof Error ? error.message : String(error)})`);
  }

  if (manifestData.name !== slug) {
    errors.push(`${location}/SKILL.md: frontmatter name '${manifestData.name ?? ""}' must match directory slug '${slug}'`);
  }
  if (typeof manifestData.description !== "string" || !manifestData.description.trim()) {
    errors.push(`${location}/SKILL.md: frontmatter description is required`);
  }
  errors.push(...validateLocalizedDoc(en, "en", `${location}/README.en.md`));
  errors.push(...validateLocalizedDoc(zh, "zh-CN", `${location}/README.zh-CN.md`));
  return errors;
}

export function validateRepository(skillsRoot) {
  const errors = [];
  const slugs = new Map();

  if (!existsSync(skillsRoot)) {
    return { errors: [`Skills root does not exist: ${skillsRoot}`], skillCount: 0 };
  }

  const topLevelDirectories = readdirSync(skillsRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  for (const entry of topLevelDirectories) {
    if (!MODULES.includes(entry.name)) {
      errors.push(`skills/${entry.name}: unsupported module directory`);
    }
  }

  let skillCount = 0;
  for (const moduleName of MODULES) {
    const modulePath = path.join(skillsRoot, moduleName);
    if (!existsSync(modulePath)) {
      errors.push(`skills/${moduleName}: required module directory is missing`);
      continue;
    }

    const skillDirectories = readdirSync(modulePath, { withFileTypes: true }).filter((entry) => entry.isDirectory());
    for (const directory of skillDirectories) {
      const slug = directory.name;
      const relativeLocation = `skills/${moduleName}/${slug}`;
      if (slugs.has(slug)) {
        errors.push(`${relativeLocation}: duplicate slug also used by ${slugs.get(slug)}`);
      } else {
        slugs.set(slug, relativeLocation);
      }

      const files = {
        manifest: path.join(modulePath, slug, "SKILL.md"),
        en: path.join(modulePath, slug, "README.en.md"),
        zh: path.join(modulePath, slug, "README.zh-CN.md"),
      };

      for (const [key, filePath] of Object.entries(files)) {
        if (!existsSync(filePath)) {
          errors.push(`${relativeLocation}: missing ${path.basename(filePath)}`);
          files[key] = null;
        }
      }
      if (Object.values(files).some((filePath) => filePath === null)) continue;

      skillCount += 1;
      errors.push(
        ...validateSkillContents(
          {
            slug,
            manifest: readFileSync(files.manifest, "utf8"),
            en: readFileSync(files.en, "utf8"),
            zh: readFileSync(files.zh, "utf8"),
          },
          relativeLocation,
        ),
      );
    }
  }

  return { errors, skillCount };
}

function runCli() {
  const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
  const skillsRoot = path.resolve(scriptDirectory, "..", "..", "skills");
  const result = validateRepository(skillsRoot);
  if (result.errors.length > 0) {
    console.error(`Skill content validation failed with ${result.errors.length} error(s):`);
    for (const error of result.errors) console.error(`- ${error}`);
    process.exitCode = 1;
    return;
  }
  console.log(`Validated ${result.skillCount} skill(s) across ${MODULES.length} SAP modules.`);
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  runCli();
}
