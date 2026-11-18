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
      });
    }
    for (const c of p.countries) {
      cards.push({ d: "Saying “in”", t: "rule", f: `in ${c.en}`, m: c.in });
    }
  }

  if (p.numbers) {
    // French on the front, the digit on the back — and reversible, because
    // writing the number down from a digit is what the writing test wants.
    for (const [n, word] of p.numbers) {
      cards.push({ d: "Numbers", t: "word", f: word, m: String(n) });
    }
  }

  if (p.alphabet) {
    for (const [letter, sound] of p.alphabet) {
      cards.push({ d: "The alphabet", t: "rule", f: letter, m: `“${sound}”` });
    }
  }

  if (p.answers) {
    // A rule card, never reversed: the question leads to the answer and going
    // back the other way is not a thing anybody has to do.
    for (const a of p.answers) {
      cards.push({ d: "The five answers", t: "rule", f: tight(a.q), m: `${tight(a.a)} — ${a.en}` });
    }
  }

  if (p.sounds) {
    for (const s of p.sounds) {
      cards.push({ d: "Saying it", t: "rule", f: s.fr, m: `“${s.say}” — ${s.why}` });
    }
  }

  if (p.corrections) {
    // A misspelling on the front, and spotting it is the skill — the writing
    // test's last task is exactly this. The card is phrased about the word,
    // never about who got it wrong: a deck that keeps telling a child what he
    // got wrong is a deck he stops opening.
    for (const c of p.corrections) {
      cards.push({
        d: "Spot the slip",
        t: "rule",
        f: `What is wrong with <em>${c.wrong[0]}</em>?`,
        m: tight(c.right),
      });
    }
  }

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
