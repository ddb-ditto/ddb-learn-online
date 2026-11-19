/**
 * The question pool for the one-at-a-time run, built from all ten packs.
 *
 * `packexercises.ts` builds a pack's own practice from that pack. This builds
 * the *cumulative* pool — everything he has met, from every pack — in the
 * shape the run needs: not finished exercises, but the raw pairs, sentences
 * and spellings, which the page then composes into questions at run time so
 * no two runs ask the same set in the same order.
 *
 * **Nothing here invents French.** Same rule, same reason, same check: every
 * French string below is a string already in a pack — its vocabulary, its
 * countries, its numbers, its spoken answers, its corrections — or a
 * mechanical transformation of one (split on its own spaces, or stripped of
 * its own accents and marks). The English is the pack's own gloss. The
 * multiple-choice wrong answers are *other packs' real glosses*, never
 * written here: a made-up wrong answer would be inventing English about
 * French he was never taught, and the pool is big enough not to need any.
 *
 * `group` is what makes that work. Distractors are drawn from the same group
 * as the answer, so a number's wrong answers are other numbers and a
 * country's are other countries. Mixing them makes the question answerable
 * without knowing any French at all.
 */
import type { CollectionEntry } from "astro:content";

type Pack = CollectionEntry<"frenchPacks">["data"];

/** French keeps a space before ? and !; it must not be where a line breaks. */
const tight = (s: string) => s.replace(/ ([?!;:])/g, " $1");
const flat = (s: string) => s.replace(/ /g, " ");

/** The words of a sentence, as tiles. Same rule as the per-pack ordering drill. */
const tiles = (fr: string): string[] =>
  flat(fr).split(/\s+/).map((t) => t.replace(/[.,]/g, "").trim()).filter(Boolean);

/** The same string with capitals, accents, apostrophes, hyphens and end marks off. */
function bare(fr: string): string {
  const noMarks = flat(fr).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  return noMarks.replace(/['’]/g, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .split(/\s+/).filter(Boolean).join(" ");
}

/** Which kind of thing this is, so a wrong answer is a plausible one. */
export type Group = "word" | "number" | "country";

export interface RunItem {
  fr: string;
  en: string;
  group: Group;
  /** The pack it came from, so the run can say where he met it. */
  pack: string;
  /** Present when it has enough words to put in an order. */
  tiles?: string[];
  /** Present when stripping the marks off actually takes something off. */
  bare?: string;
}

/** A real misspelling and its correction. These cannot be derived — see CLAUDE.md. */
export interface RunMistake { wrong: string; right: string; pack: string; }

/** A spoken answer. Nothing here can mark it, which is the whole point of it. */
export interface RunSay { q: string; a: string; en: string; pack: string; }

export interface RunPool {
  items: RunItem[];
  mistakes: RunMistake[];
  say: RunSay[];
}

export function buildPool(packs: Pack[]): RunPool {
  const items: RunItem[] = [];
  const mistakes: RunMistake[] = [];
  const say: RunSay[] = [];

  const add = (fr: string, en: string, group: Group, pack: string): void => {
    const t = tiles(fr);
    const b = bare(fr);
    items.push({
      fr, en, group, pack,
      ...(t.length >= 3 ? { tiles: t } : {}),
      // Only where stripping takes something off, and only where there is more
      // than one word or a hyphen: a lone unaccented word would give a prompt
      // identical to its answer.
      ...(b !== flat(fr) && (t.length >= 2 || fr.includes("-")) ? { bare: b } : {}),
    });
  };

  for (const p of packs) {
    for (const v of p.vocab ?? []) add(tight(v.fr), v.en, "word", p.title);
    for (const c of p.countries ?? []) add(c.fr, c.en, "country", p.title);
    // A number's meaning is its digit, which is what the writing test asks for
    // in reverse.
    for (const [n, word] of p.numbers ?? []) add(word, String(n), "number", p.title);

    for (const c of p.corrections ?? []) {
      for (const w of c.wrong) mistakes.push({ wrong: w, right: c.right, pack: p.title });
    }
    for (const a of p.answers ?? []) {
      say.push({ q: tight(a.q), a: tight(a.a), en: a.en, pack: p.title });
    }
  }

  return { items, mistakes, say };
}
