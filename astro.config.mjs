// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

/**
 * A GitHub project page is served from a path named after the repository:
 * rename the repository and the URL moves with it. So the base is read from
 * the repository rather than written down here — otherwise a rename would
 * leave every stylesheet and script pointing at a path that no longer exists,
 * and the site would come back unstyled with nothing in the build to explain
 * why.
 *
 * GITHUB_REPOSITORY is "owner/name", set by Actions. Locally there is no such
 * variable, so the fallback is the directory the repository is checked out
 * into — which is its name in every ordinary case. BASE_PATH overrides both,
 * for anyone serving it from somewhere else entirely.
 */
import path from "node:path";

const repo =
  process.env.GITHUB_REPOSITORY?.split("/")[1] ?? path.basename(process.cwd());
const base = process.env.BASE_PATH ?? `/${repo}`;

export default defineConfig({
  site: "https://ddb-ditto.github.io",
  base,
  trailingSlash: "ignore",
  integrations: [mdx()],
  build: { format: "directory" },
});
