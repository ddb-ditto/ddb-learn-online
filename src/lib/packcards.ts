/**
 * A pack's flashcards, worked out from the pack itself.
 *
 * The cards are not a second copy of the vocabulary. The Italian decks are
 * hand-written files because the cards there teach something the word list
 * does not — pronunciation, a rule, a trap. Here the cards *are* the word
 * list, so writing them out again would only create something to fall out of
 * step with it, which is the bug the deck-size check exists to catch.
 *
 * What each pack turns into is a judgement, not a rule, so it is written out
 * per shape below.
 */
import type { CollectionEntry } from "astro:content";
import type { Card } from "../scripts/flashcards";

type Pack = CollectionEntry<"frenchPacks">["data"];

/** French keeps a space before ? and !; it must not be where a line breaks. */
const tight = (s: string) => s.replace(/ ([?!;:])/g, " $1");

export function cardsFor(p: Pack): Card[] {
  const cards: Card[] = [];

  if (p.vocab) {
    for (const v of p.vocab) {
      // The front is the one phrasing he has to produce. A second way of
      // saying it goes on the back, where knowing it costs nothing — on the
      // front it would be two questions on one card.
      cards.push({
        d: p.title, t: "word", f: tight(v.fr),
        m: v.alt ? `${v.en} — or <em>${tight(v.alt)}</em>` : v.en,
        // The back is the English meaning, and where there is a second way of
        // saying it the French sits inside that English sentence — so only the
        // front is read aloud, and the second phrasing is spoken on its own
        // card in the pack's word table.
        fr: { f: tight(v.fr) },
      });
    }
  }

  if (p.countries) {
    // Two jobs, so two decks. Reading a country's name is one thing; producing
    // "au" or "en" in front of it is the thing the test actually asks for, and
    // a single card that showed both would let him read the answer off the
    // front.
    for (const c of p.countries) {
      // The flag goes on the back, with the English. On the front it would
      // answer the question before it had been asked.
      cards.push({
        d: "The country", t: "word", f: c.fr,
        m: c.flag ? `${c.flag}  ${c.en}` : c.en,
        fr: { f: c.fr },
      });
    }
    for (const c of p.countries) {
      // The one deck whose French is on the back: the front asks in English
      // ("in Italy") and the French is the answer. A side flag alone would
      // have had a French voice read "in Italy" aloud.
      cards.push({
        d: "Saying “in”", t: "rule", f: `in ${c.en}`, m: c.in,
        fr: { m: `${c.in} ${c.fr}` },
      });
    }
  }

  if (p.numbers) {
    // French on the front, the digit on the back — and reversible, because
    // writing the number down from a digit is what the writing test wants.
    for (const [n, word] of p.numbers) {
      cards.push({ d: "Numbers", t: "word", f: word, m: String(n), fr: { f: word } });
    }
  }

  if (p.alphabet) {
    for (const [letter, sound] of p.alphabet) {
      // Neither side is read aloud. The front is a bare letter, which a
      // synthesiser says as a letter name of its own choosing, and the back is
      // an English respelling of the French name — "ah", "bay". Speaking
      // either would teach the sound this deck exists to correct.
      cards.push({ d: "The alphabet", t: "rule", f: letter, m: `“${sound}”` });
    }
  }

  if (p.answers) {
    // A rule card, never reversed: the question leads to the answer and going
    // back the other way is not a thing anybody has to do.
    for (const a of p.answers) {
      // Both sides are French, and the back carries the English gloss after a
      // dash. What is spoken is named outright rather than cut out of the
      // back at play time, so nothing depends on the dash staying put.
      cards.push({
        d: "The five answers", t: "rule", f: tight(a.q),
        m: `${tight(a.a)} — ${a.en}`,
        fr: { f: a.q, m: a.a },
      });
    }
  }

  if (p.sounds) {
    for (const s of p.sounds) {
      // The back is an English respelling and the reason for it, so the front
      // alone speaks.
      cards.push({
        d: "Saying it", t: "rule", f: s.fr, m: `“${s.say}” — ${s.why}`,
        fr: { f: s.fr },
      });
    }
  }

  // `corrections` deliberately makes no cards.
  //
  // It used to: a misspelling on the front, the right spelling on the back.
  // But a flashcard is seen over and over, and the Leitner box shows the ones
  // that keep going wrong *more* often — so the deck's effect was to put the
  // misspelling in front of him repeatedly, which is the opposite of what a
  // spelling pack is for. Seeing a wrong spelling makes it fractionally more
  // familiar, and familiarity is what a speller reaches for.
  //
  // Recognising a wrong spelling is still worth practising, because the
  // writing test's last task is exactly that. It happens in the "Spot the
  // mistake" exercise, once, where getting it wrong costs nothing and the
  // correct version is shown immediately afterwards.

  return cards;
}

/**
 * Decks where "English first" is switched off.
 *
 * The app offers it when a deck's backs are distinct translations. That holds
 * for the vocabulary decks and not for the numbers one, whose backs are digits
 * — "18 → dix-huit" is a fair question, and it is the one the reversal already
 * asks, so nothing is turned off here. Rule cards never reverse anyway.
 */
export const noReverseFor = (_p: Pack): string[] => [];

/** How many cards a pack has, for the link that offers them. */
export const cardCountFor = (p: Pack): number => cardsFor(p).length;
