import { defineConfig } from "astro/config";

const isDevelopment = process.env.NODE_ENV === "development";

export default defineConfig({
  site: "https://yin-wen-bin.github.io",
  base: isDevelopment ? "/" : "/SAPSkillhub",
  output: "static",
  trailingSlash: "always",
});
