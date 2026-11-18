/**
 * A Leitner box: the cards you keep getting wrong come round sooner.
 *
 * Spaced retrieval is the best-evidenced thing anybody knows about learning
 * vocabulary, and the site had none of it. Every deck reset on every visit, so
 * the word he has known for a fortnight came up exactly as often as the one
 * that catches him every time. Three boxes fix most of that for very little
 * machinery: a card he gets right moves up a box and is shown less; a card he
 * gets wrong goes straight back to box one.
 *
 * WHAT IS STORED, AND WHAT DELIBERATELY IS NOT
 *
 * Only which box each card is in — a word and a number from 1 to 3, in this
 * browser. Not a score, not how many he got right, not when he studied, not
 * how long for, and nothing that leaves the device. The site's rule is that
 * nobody is counted and progress is recorded on paper, and that rule is about
 * *the child*. Which cards are hard is a fact about the words.
 *
 * It is also written to be lost safely. Private windows, cleared site data and
 * a different device all give an empty box, and an empty box is just a deck
 * that starts at the beginning — which is what the site did before this
 * existed. So every read and write is wrapped, and nothing here is ever the
 * only copy of anything that matters.
 */

/** Box 1 is "still learning"; box 3 is "known for now". */
export type Box = 1 | 2 | 3;
export const BOXES: Box[] = [1, 2, 3];

/** How often a box is drawn from, relative to the others. */
const WEIGHT: Record<Box, number> = { 1: 6, 2: 3, 3: 1 };

export class Leitner {
  private readonly key: string;
  private box = new Map<string, Box>();

  constructor(scope: string) {
    this.key = `leitner:${scope}`;
    this.load();
  }

  private load(): void {
    try {
      const raw = window.localStorage.getItem(this.key);
      if (!raw) return;
      const saved = JSON.parse(raw) as Record<string, number>;
      for (const [card, n] of Object.entries(saved)) {
        if (n === 1 || n === 2 || n === 3) this.box.set(card, n);
      }
    } catch {
      // No storage, or something else wrote nonsense here. Start fresh; the
      // deck works perfectly well without a memory.
      this.box.clear();
    }
  }

  private save(): void {
    try {
      window.localStorage.setItem(
        this.key, JSON.stringify(Object.fromEntries(this.box)));
    } catch {
      // Out of quota, or storage refused. The boxes still work for this
      // sitting; they are simply forgotten when the tab closes.
    }
  }

  at(card: string): Box {
    return this.box.get(card) ?? 1;
  }

  /** Right: up a box, to a maximum of three. */
  up(card: string): void {
    this.box.set(card, Math.min(3, this.at(card) + 1) as Box);
    this.save();
  }

  /**
   * Wrong: all the way back to box one, not down one.
   *
   * Demoting by a single step lets a card he has never really known drift
   * upwards on lucky guesses. Back to the start is the whole point of the
   * method.
   */
  down(card: string): void {
    this.box.set(card, 1);
    this.save();
  }

  forget(): void {
    this.box.clear();
    try {
      window.localStorage.removeItem(this.key);
    } catch {
      /* nothing to do: it was never written */
    }
  }

  /** How many of these cards sit in each box. */
  tally(cards: readonly string[]): Record<Box, number> {
    const out: Record<Box, number> = { 1: 0, 2: 0, 3: 0 };
    for (const c of cards) out[this.at(c)]++;
    return out;
  }

  /**
   * The order to show these cards in.
   *
   * Not simply "box one first": working through every hard card and then every
   * easy one is just two blocked runs, and blocking is the thing spacing is
   * meant to break up. Instead each card gets a random draw weighted by its
   * box, so box one comes up about six times as often as box three while the
   * rest stay in the mix.
   */
  order<T>(cards: readonly T[], front: (c: T) => string): T[] {
    return cards
      .map((card) => ({ card, r: Math.random() / WEIGHT[this.at(front(card))] }))
      .sort((a, b) => a.r - b.r)
      .map(({ card }) => card);
  }
}

/**
 * Whether this browser will remember anything at all.
 *
 * Checked by writing, because Safari in a private window has a localStorage
 * object that throws the moment you use it — reading `window.localStorage`
 * and finding it present proves nothing.
 */
export function storageWorks(): boolean {
  try {
    const probe = "leitner:probe";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
    return true;
  } catch {
    return false;
  }
}
