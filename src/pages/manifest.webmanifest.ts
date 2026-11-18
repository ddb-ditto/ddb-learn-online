/**
 * The web app manifest, generated rather than kept in `public/`.
 *
 * As a static file it carried `/italian-gcse/` in its `start_url`, its `scope`
 * and every icon path — so when the repository was renamed it went on pointing
 * at a path that no longer exists, and the installed-app behaviour broke
 * silently. Nothing fetches a manifest and complains out loud.
 *
 * Generated, it reads the same base as everything else, so the next rename
 * takes it along.
 */
import type { APIRoute } from "astro";

export const GET: APIRoute = () => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return new Response(JSON.stringify({
    name: "ddb-learn-online",
    short_name: "DDB Learn",
    description:
      "Lesson pages, flashcards and printable sheets: a two-year GCSE Italian " +
      "course taught at home, and Year 7 French revision.",
    start_url: `${base}/`,
    scope: `${base}/`,
    display: "standalone",
    orientation: "any",
    background_color: "#fbf9f7",
    theme_color: "#021229",
    icons: [
      { src: `${base}/icon-192.png`, sizes: "192x192", type: "image/png", purpose: "any" },
      { src: `${base}/icon-512.png`, sizes: "512x512", type: "image/png", purpose: "any" },
    ],
  }, null, 2), {
    headers: { "content-type": "application/manifest+json; charset=utf-8" },
  });
};
