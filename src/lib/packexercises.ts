/**
 * A pack's own practice, worked out from the pack itself.
 *
 * The same thing `packcards.ts` does for flashcards, and for the same reason.
 * *Spell it* was one file of 59 items shared by seven packs and *What does it
 * mean?* one file of 15 shared by six, so a pack's "test yourself" asked about
 * words from every other pack and asked the identical questions each time.
 * Working through pack 3 after pack 2 set exactly the same questions.
 *
 * **Nothing here invents French.** Every prompt and every answer is a string
 * already in the pack — its own vocabulary, its own countries, its own
 * numbers, written as the notebook writes them. That is the whole point: the
 * source is the class's work and this file may rearrange it but may not add
 * to it. A drill that needed a word the pack does not have would be a drill
 * this file must not generate.
 *
 * Which is why a pack with nothing of its own gets nothing here, and keeps
 * whatever shared exercise it was given. `reading-skills` and `culture` have
 * no word list at all; `tricky-spellings` has only its misspellings, which
 * make one exercise and not the other two.
 */
import type { CollectionEntry } from "astro:content";

type Pack = CollectionEntry<"frenchPacks">["data"];
type Exercise = CollectionEntry<"frenchExercises">["data"];

/** French keeps a space before ? and !; it must not be where a line breaks. */
const tight = (s: string) => s.replace(/ ([?!;:])/g, " $1");

/** One French-to-English pair drawn from the pack, however it stores them. */
interface Pair { fr: string; en: string; }

/**
 * Everything in the pack that is a French word with an English meaning.
 *
 * The three shapes a pack stores words in, and nothing else. `answers` are
 * whole spoken sentences and `sounds` are pronunciation notes — neither is a
 * translation pair, and pack 7 has its own speaking exercise for them.
 * `corrections` are misspellings, which feed a different drill below.
 */
function pairs(p: Pack): Pair[] {
  const out: Pair[] = [];
  for (const v of p.vocab ?? []) out.push({ fr: tight(v.fr), en: v.en });
  for (const c of p.countries ?? []) out.push({ fr: c.fr, en: c.en });
  // A number's "meaning" is its digit, which is as true as any gloss and is
  // exactly what the writing test asks for in reverse.
  for (const [n, word] of p.numbers ?? []) out.push({ fr: word, en: String(n) });
  return out;
}

/** Shared by every derived exercise, so they cannot drift apart. */
const base = (p: Pack) => ({ shuffle: true, ask: undefined as number | undefined });

/**
 * The practice this pack can set from its own material.
 *
 * Empty when the pack has nothing to set it from, and the page then falls
 * back to whatever shared exercise the pack lists.
 */
export function ownExercises(p: Pack): Exercise[] {
  const out: Exercise[] = [];
  const words = pairs(p);

  // Four is thin, but four of his own words beats fifteen of everybody's.
  if (words.length >= 4) {
    out.push({
      ...base(p),
      id: "own-meaning",
      kind: "reveal",
      part: "reading",
      title: "What does it mean?",
      intro: "Every word on this page, French side up. Say what it means before "
        + "you turn it over.",
      speak: ["prompt"],
      items: words.map((w) => ({ prompt: w.fr, answer: w.en })),
    } as Exercise);

    out.push({
      ...base(p),
      id: "own-spell",
      kind: "type",
      part: "writing",
      title: "Spell it",
      intro: "English on screen, French typed in. Accents and capitals count — "
        + "that is the point of this one.",
      speak: ["answer"],
      items: words.map((w) => ({ prompt: w.en, answer: w.fr, weight: 1 })),
    } as Exercise);
  }

  // Only where the pack holds misspellings of its own. Generating them would
  // mean inventing French that is wrong on purpose, which is further from the
  // notebook than inventing French that is right.
  const wrong = (p.corrections ?? []).flatMap((c) =>
    c.wrong.map((w) => ({ prompt: w, answer: c.right, weight: 1 })));
  if (wrong.length >= 4) {
    out.push({
      ...base(p),
      id: "own-mistake",
      kind: "type",
      part: "writing",
      title: "Spot the mistake",
      intro: "Each one has something wrong with it. Type it out correctly.",
      // The prompt is French misspelled on purpose: silent, because spoken it
      // is identical to the right answer. See the audio rules in CLAUDE.md.
      speak: ["answer"],
      items: wrong,
    } as Exercise);
  }

  return out;
}

/** Which derived exercises a pack can offer, by id. */
export const ownIds = (p: Pack): string[] => ownExercises(p).map((e) => e.id);
