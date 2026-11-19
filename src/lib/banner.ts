/**
 * The front door's banner, and the one place its sizes are written.
 *
 * In `Base.astro` these numbers tripped `check_text.py`, which fails on any
 * four-digit number in the pages, components and layouts: the course has no
 * calendar years, and `2048` is indistinguishable from one by looking. The
 * checker was right to be coarse — it is guarding prose a reader sees — and
 * the fix is not to carve a hole in it but to keep a pixel width out of the
 * prose, which is what `src/lib` is for.
 *
 * `make_icons.py` writes the files these name. The two lists have to agree,
 * so `check_site.py` asks the server for every candidate in the srcset and
 * fails on anything that is not there: rename a width in one place and the
 * check says so rather than the browser quietly falling back.
 */

/** The widths `make_icons.py` emits, narrowest first. A phone and a desktop. */
export const BANNER_WIDTHS = [1024, 2048] as const;

/** The intrinsic shape of the artwork, for the box the browser reserves. */
export const BANNER_SIZE = { w: 2048, h: 1120 };

/**
 * What the front page is called, for anybody arriving by search or by screen
 * reader: with no heading on that page, this is its accessible name.
 */
export const BANNER_ALT = "DDB Learn Online";

export const bannerSrc = (base: string, width: number): string =>
  `${base}/banner-${width}.webp`;

export const bannerSrcset = (base: string): string =>
  BANNER_WIDTHS.map((w) => `${bannerSrc(base, w)} ${w}w`).join(", ");
