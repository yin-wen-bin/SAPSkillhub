import { defineConfig } from "astro/config";

const isDevelopment = process.env.NODE_ENV === "development";
const siteOrigin = process.env.PUBLIC_SITE_ORIGIN ?? "https://example.github.io";
const productionBase = process.env.PUBLIC_SITE_BASE ?? "/SAPSkillhub";

export default defineConfig({
  site: siteOrigin,
  base: isDevelopment ? "/" : productionBase,
  output: "static",
  trailingSlash: "always",
});
