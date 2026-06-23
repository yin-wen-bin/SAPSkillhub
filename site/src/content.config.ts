import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const stringList = z.array(z.string().min(1));

const skillDocs = defineCollection({
  loader: glob({
    pattern: "**/README.{en,zh-CN}.md",
    base: "../skills",
  }),
  schema: z.object({
    title: z.string().min(1),
    summary: z.string().min(1),
    tags: stringList.min(1),
    transactions: stringList.optional().default([]),
    systems: stringList.optional().default([]),
  }),
});

const skillManifests = defineCollection({
  loader: glob({
    pattern: "**/SKILL.md",
    base: "../skills",
  }),
  schema: z.object({
    name: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/),
    description: z.string().min(1),
  }),
});

export const collections = { skillDocs, skillManifests };
