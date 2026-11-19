/**
 * A pack's own practice, worked out from the pack itself.
 *
 * The same thing `packcards.ts` does for flashcards, and for the same reason.
 * *Spell it* was one file of 59 items shared by seven packs and *What does it
 * mean?* one of 15 shared by six, so a pack's practice asked about words from
 * every other pack and asked the identical questions each time.
 *
 * **Nothing here invents French.** Every prompt and every answer is a string
 * already in the pack — its own vocabulary, its own countries, its own
 * numbers, written as the notebook writes them — or a mechanical
 * transformation of one: split on its spaces, or stripped of its accents and
 * marks. Rearranging the notebook is allowed; adding to it is not. A drill
 * that needed a word the pack does not have is a drill this file must not
 * generate, which is why *Spot the mistake* exists only where there are real
 * misspellings to use. `check_site.py` reads every built page and looks each
 * string up in that pack's own data.
 *
 * Testing across all ten packs at once is still there, on *Mix it up*, which
 * is where the shared files now live.
 */
import type { CollectionEntry } from "astro:content";

type Pack = CollectionEntry<"frenchPacks">["data"];
type Exercise = CollectionEntry<"frenchExercises">["data"];

/** French keeps a space before ? and !; it must not be where a line breaks. */
const tight = (s: string) => s.replace(/ ([?!;:])/g, " $1");
const flat = (s: string) => s.replace(/ /g, " ");

/** One French-to-English pair drawn from the pack, however it stores them. */
interface Pair { fr: string; en: string; }

/**
 * The words of a sentence, as tiles to put back in order.
 *
 * Split on the spaces that are already there and drop the full stops and
 * commas, which the order exercise ignores when it marks. French puts a space
 * before `?` and `!`, so those arrive as their own tile without any help.
 */
const tiles = (fr: string): string[] =>
  flat(fr).split(/\s+/).map((t) => t.replace(/[.,]/g, "").trim()).filter(Boolean);

/**
 * The same sentence with everything a keyboard makes you think about taken
 * off: capitals, accents, apostrophes, hyphens and the marks at the end.
 *
 * This is a transformation of the pack's own sentence, not a new one. What is
 * left is what somebody types in a hurry, and putting it all back is the
 * drill. Note the prompt is therefore French that is deliberately wrong, so
 * it is never spoken — see the audio rules in CLAUDE.md.
 */
function bare(fr: string): string {
  const noMarks = flat(fr).toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "");
  return noMarks.replace(/['’]/g, "")
    .replace(/[^a-z0-9 ]/g, " ")
    .split(/\s+/).filter(Boolean).join(" ");
}

/**
 * Everything in the pack that is a French word with an English meaning.
 *
 * The three shapes a pack stores words in, and nothing else. `answers` are
 * whole spoken sentences and `sounds` are pronunciation notes — neither is a
 * translation pair, and pack 7 has its own speaking exercise for them.
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

/** Under four items a drill is not worth its heading. */
const ENOUGH = 4;
/** Over this many, ask a random handful rather than all of them. */
const ask = (n: number) => (n > 15 ? 12 : undefined);

export function ownExercises(p: Pack): Exercise[] {
  const out: Exercise[] = [];
  const words = pairs(p);

  // A sentence is something with enough words to put in an order. Everything
  // shorter is a word to spell. The two sets do not overlap, so nothing on the
  // page is drilled twice under two headings.
  const sentences = words.filter((w) => tiles(w.fr).length >= 3);
  const singles = words.filter((w) => tiles(w.fr).length < 3);

  if (words.length >= ENOUGH) {
    out.push({
      shuffle: true, id: "own-meaning", kind: "reveal", part: "reading",
      title: "What does it mean?",
      intro: "Every word on this page, French side up. Say what it means before "
        + "you turn it over.",
      speak: ["prompt"],
      items: words.map((w) => ({ prompt: w.fr, answer: w.en })),
    } as Exercise);
  }

  if (singles.length >= ENOUGH) {
    out.push({
      shuffle: true, ask: ask(singles.length),
      id: "own-spell", kind: "type", part: "writing",
      title: "Spell it",
      intro: "English on screen, French typed in. Accents and capitals count — "
        + "that is the point of this one.",
      speak: ["answer"],
      items: singles.map((w) => ({ prompt: w.en, answer: w.fr, weight: 1 })),
    } as Exercise);
  }

  if (sentences.length >= ENOUGH) {
    out.push({
      shuffle: true, ask: ask(sentences.length),
      id: "own-translate", kind: "type", part: "writing",
      title: "Translate into French",
      intro: "Whole sentences this time, from this page. Punctuation and all.",
      speak: ["answer"],
      items: sentences.map((w) => ({ prompt: w.en, answer: w.fr, weight: 1 })),
    } as Exercise);

    out.push({
      shuffle: true,
      id: "own-order", kind: "order", part: "writing",
      title: "Put the words in order",
      intro: "Tap the tiles in the right order. Tap one you have placed to take "
        + "it back.",
      speak: ["tiles", "answer"],
      items: sentences.map((w) => ({ tiles: tiles(w.fr), answer: w.fr })),
    } as Exercise);
  }

  // Only where stripping actually takes something off — a bare word with no
  // accent, apostrophe or hyphen would make a prompt identical to its answer.
  //
  // The correct spellings from a corrections list count as a source too, and
  // for the tricky-spellings pack they are the only one: it holds no
  // vocabulary of its own, and without them its single accented words — très,
  // ça va, j'habite — would have nothing to drill against. A lone word is
  // skipped from the word list, where its accent is already covered by
  // spelling it from the English, and kept here, where the accent *is* the
  // question.
  const spellings = (p.corrections ?? []).map((c) => ({ fr: c.right, en: "" }));
  const marked = [
    ...words.filter((w) =>
      bare(w.fr) !== flat(w.fr) && (tiles(w.fr).length >= 2 || w.fr.includes("-"))),
    ...spellings.filter((w) => bare(w.fr) !== flat(w.fr)),
  ];
  if (marked.length >= ENOUGH) {
    out.push({
      shuffle: true, ask: ask(marked.length),
      id: "own-punctuation", kind: "type", part: "writing",
      title: "Put the punctuation back",
      intro: "Capitals, accents, apostrophes, hyphens and the marks at the end. "
        + "Everything else is already there.",
      // The prompt is this pack's French with its marks taken off: French that
      // is wrong on purpose, so it is never read aloud.
      speak: ["answer"],
      items: marked.map((w) => ({ prompt: bare(w.fr), answer: w.fr, weight: 1 })),
    } as Exercise);
  }

  // Misspellings cannot be derived — making them up would be inventing French
  // that is wrong on purpose, which is further from the notebook than
  // inventing French that is right.
  const wrong = (p.corrections ?? []).flatMap((c) =>
    c.wrong.map((w) => ({ prompt: w, answer: c.right, weight: 1 })));
  if (wrong.length >= ENOUGH) {
    out.push({
      shuffle: true, ask: ask(wrong.length),
      id: "own-mistake", kind: "type", part: "writing",
      title: "Spot the mistake",
      intro: "Each one has something wrong with it. Type it out correctly.",
      speak: ["answer"],
      items: wrong,
    } as Exercise);
  }

  return out;
}

/** Which derived exercises a pack can offer, by id. */
export const ownIds = (p: Pack): string[] => ownExercises(p).map((e) => e.id);
