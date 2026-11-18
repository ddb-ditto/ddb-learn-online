/**
 * Marking a typed French answer.
 *
 * The writing test marks spelling, so this does too: accents, capitals and
 * hyphens all count, and a near miss is wrong. Being lenient here would teach
 * him that `tres` is fine, which is the one thing the pack exists to prevent.
 *
 * Two things are forgiven, both because they are about the keyboard rather
 * than about French:
 *
 *   - The apostrophe. A phone types a curly ’ and a laptop a straight ', and
 *     French uses them interchangeably in print. Marking him down for his
 *     keyboard's choice is noise.
 *   - The space before ? and !. French convention puts one there, his booklet
 *     writes a plain space, and most keyboards make it a nuisance. Either way
 *     round is accepted — the mark is for the question mark being there.
 *
 * Nothing else is. `Ca va ?` is wrong, and so is `ça va ?` at the start of a
 * sentence.
 */

/** Straight and curly apostrophes, and the prime that sometimes sneaks in. */
const APOSTROPHES = /[’ʼ´′]/g;
/** Every space French might put before a ? or a ! — including the thin ones. */
const SPACE_BEFORE = /[\s   ]+([?!;:])/g;
/** Ellipsis, typed as three dots or as the single character. */
const ELLIPSIS = /…/g;

/**
 * What two answers have to agree on. Everything this strips is a keyboard
 * difference; everything it leaves is French.
 */
export function normalise(s: string): string {
  return s
    .replace(APOSTROPHES, "'")
    .replace(ELLIPSIS, "...")
    .replace(SPACE_BEFORE, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

export function isCorrect(typed: string, expected: string): boolean {
  return normalise(typed) === normalise(expected);
}

/**
 * Where a wrong answer went wrong, as runs of characters that match or do not.
 *
 * Showing the correct answer on its own leaves him to spot the difference,
 * which is the very thing he just failed to do. A plain longest-common-
 * subsequence diff over characters is enough to put the missing accent in red,
 * and the answers are one line long so the cost does not matter.
 */
export interface Run { text: string; same: boolean; }

export function diff(typed: string, expected: string): Run[] {
  const a = normalise(typed);
  const b = normalise(expected);
  const n = a.length;
  const m = b.length;

  // lcs[i][j] = length of the longest common subsequence of a[i…] and b[j…]
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i]![j] = a[i] === b[j]
        ? lcs[i + 1]![j + 1]! + 1
        : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!);
    }
  }

  // Walk the table, collecting what `expected` says and marking which of it
  // he got. Characters he typed that are not in the answer are not shown:
  // the point is the correct version, with his gaps visible in it.
  const runs: Run[] = [];
  const push = (text: string, same: boolean) => {
    const last = runs[runs.length - 1];
    if (last && last.same === same) last.text += text;
    else runs.push({ text, same });
  };

  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      push(b[j]!, true);
      i++;
      j++;
    } else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) {
      i++;                                  // he typed something extra
    } else {
      push(b[j]!, false);                   // he left this out
      j++;
    }
  }
  while (j < m) push(b[j++]!, false);
  return runs;
}

/**
 * How much of the expected answer he actually got, from 0 to 1.
 *
 * The highlight is for pointing at a small difference — a missing accent, a
 * dropped hyphen. When the answer is nowhere near, there is no small
 * difference to point at, and marking up everything-but-the-incidental-letter
 * produces something that reads as a bug: a child typed gibberish, the diff
 * found the one `a` in it, and the correct answer came back chopped into two
 * highlighted blocks with a hole in the middle.
 *
 * Measured over the real pack data, genuine near misses score 0.71 and above
 * and nonsense scores under 0.15, so anything under a half gets the answer
 * printed plainly instead.
 */
export function similarity(typed: string, expected: string): number {
  const want = normalise(expected);
  if (!want) return 1;
  const matched = diff(typed, expected)
    .filter((run) => run.same)
    .reduce((n, run) => n + run.text.length, 0);
  return matched / want.length;
}

/** Below this, show the answer rather than trying to point at a difference. */
export const NEAR_ENOUGH = 0.5;

/** Fisher–Yates, so a shuffled set is actually shuffled. */
export function shuffled<T>(items: readonly T[]): T[] {
  const out = items.slice();
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

/**
 * Pick `n` items, honouring a weight. A weight of 2 puts an item in the hat
 * twice, which is how Pack 10's words come up more often than the rest — but
 * it is picked at most once, because asking the same question twice in one run
 * looks like a bug.
 */
export function pick<T extends { weight?: number }>(items: readonly T[], n?: number): T[] {
  // Asking for everything returns everything, in the order it arrived.
  // Shuffling is the caller's decision and it has already been made: an
  // exercise that says `shuffle: false` means it, and w-d and w-e are written
  // to run from the easiest to the hardest. This used to shuffle regardless,
  // which quietly threw that order away.
  if (n === undefined || n >= items.length) return items.slice();
  const hat: T[] = [];
  for (const it of items) for (let k = 0; k < (it.weight ?? 1); k++) hat.push(it);

  const out: T[] = [];
  const seen = new Set<T>();
  for (const candidate of shuffled(hat)) {
    if (seen.has(candidate)) continue;
    seen.add(candidate);
    out.push(candidate);
    if (out.length === n) break;
  }
  return out;
}
