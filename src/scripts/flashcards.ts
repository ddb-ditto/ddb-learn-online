/**
 * The flashcard app.
 *
 * Written once and bundled once, rather than pasted into every deck page. The
 * behaviour is deliberate and was argued over, so it is worth stating:
 *
 *   - It opens on deck one, card one, unshuffled. Never a shuffle of
 *     everything: the cards are in teaching order and that order is the point.
 *   - Deck buttons switch, they do not filter. One deck at a time, and
 *     switching resets to its first card.
 *   - Arrows wrap at both ends, and the left and right keys do the same.
 *   - The Italian decks have no self-marking "got it" buttons. The teacher is
 *     in the room, and a nine-year-old grading themselves is not data.
 *   - The French decks do, because the position is different: a twelve-year-old
 *     revising for a test next week is usually alone, and "did I just produce
 *     *très* or not?" is a verifiable yes or no against the back of the card,
 *     not the kind of self-assessment children are bad at. Without some signal
 *     there can be no spacing at all, and spacing is worth more here than the
 *     purity of refusing it. It is off unless a page asks for it.
 */

import { Leitner, storageWorks } from "./leitner";

export interface Card {
  /** Deck name. Decks appear in the order they first occur. */
  d: string;
  /** "word" reverses under English-first; "rule" never does. */
  t: "word" | "rule";
  /** Front: the prompt. */
  f: string;
  /** How to say it. */
  s?: string;
  /** Back: the answer. */
  m: string;
}

const data = document.getElementById("cards-data");
const off = document.getElementById("no-reverse");
const practise = document.getElementById("practise");
const scope = document.getElementById("deck-scope");
if (data?.textContent) {
  start(
    JSON.parse(data.textContent) as Card[],
    off?.textContent ? (JSON.parse(off.textContent) as string[]) : [],
    practise?.textContent === "true",
    scope?.textContent ? (JSON.parse(scope.textContent) as string) : "",
  );
}

function start(CARDS: Card[], NO_REVERSE: string[], PRACTISE: boolean,
               SCOPE: string): void {
  const DECKS: string[] = [];
  for (const c of CARDS) if (!DECKS.includes(c.d)) DECKS.push(c.d);

  const el = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const elDecks = el("decks");
  const elCard = el("card");
  const elFace = el("face");
  const elDeckTag = el("decktag");
  const elHint = el("hint");
  const elPosition = el("position");

  let cards: Card[] = [];
  let deck = DECKS[0]!;
  let canReverse = false;
  let idx = 0;
  let showingBack = false;
  let reverse = false;

  // One box per deck, named by the content rather than the URL so that moving
  // the site does not throw away what the boxes know.
  const boxes = PRACTISE ? new Leitner(SCOPE || location.pathname) : null;
  const remembers = PRACTISE && storageWorks();

  /**
   * Whether "English first" means anything for a deck.
   *
   * It is for vocabulary recall — given the English, produce the Italian — so
   * it needs cards whose back is a translation. A deck of rule cards has no
   * such side, and Unit 1's stress deck answers five different words with the
   * same sentence, which reversed gives five identical prompts. Both used to
   * leave a checkbox that did nothing when ticked, which reads as broken.
   */
  function reversible(name: string): boolean {
    if (NO_REVERSE.includes(name)) return false;   // switched off in the deck
    const words = CARDS.filter((c) => c.d === name && c.t === "word");
    const meanings = words.map((c) => c.m);
    const distinct = words.filter(
      (c) => meanings.indexOf(c.m) === meanings.lastIndexOf(c.m),
    );
    return distinct.length >= 2;
  }

  const esc = (s: string) =>
    s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

  function drawDecks(): void {
    elDecks.replaceChildren(
      ...DECKS.map((d) => {
        const n = CARDS.filter((c) => c.d === d).length;
        const b = document.createElement("button");
        b.className = "chip";
        b.type = "button";
        b.setAttribute("aria-pressed", String(d === deck));
        b.innerHTML = `${esc(d)}<span class="n">${n}</span>`;
        b.addEventListener("click", () => selectDeck(d));
        return b;
      }),
    );
  }

  function selectDeck(d: string): void {
    deck = d;
    cards = CARDS.filter((c) => c.d === deck);
    if (boxes) cards = boxes.order(cards, (c) => c.f);
    idx = 0;
    showingBack = false;
    canReverse = reversible(deck);

    // Hide the control rather than disable it: a checkbox that is present and
    // inert is what made this look broken in the first place.
    const control = el("reversewrap");
    control.hidden = !canReverse;
    if (!canReverse) {
      reverse = false;
      el<HTMLInputElement>("reverse").checked = false;
    }

    drawDecks();
    render();
  }

  function step(delta: number): void {
    if (!cards.length) return;
    idx = (idx + delta + cards.length) % cards.length;
    showingBack = false;
    render();
  }

  function shuffle(): void {
    for (let i = cards.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [cards[i], cards[j]] = [cards[j]!, cards[i]!];
    }
    idx = 0;
    showingBack = false;
    render();
  }

  function render(): void {
    const card = cards[idx];
    if (!card) return;

    elDeckTag.textContent = card.d;
    elPosition.innerHTML = `${idx + 1} <span class="of">/ ${cards.length}</span>`;

    if (boxes) {
      const marks = document.getElementById("marks");
      if (marks) marks.hidden = !showingBack;
      const left = document.getElementById("stillto");
      if (left) {
        const tally = boxes.tally(cards.map((c) => c.f));
        // A count of the words, not of him: how much of this deck is still
        // coming round often. It goes down as the deck is learned.
        left.textContent = tally[1] === 0
          ? "Every card in this deck is settled."
          : `${tally[1]} of ${cards.length} still coming round often`;
      }
    }

    // English first only applies to word cards. A rule card asks a question,
    // so reversing it would show the answer and ask for the question.
    const flipped = reverse && canReverse && card.t === "word";
    const say = card.s ? `<p class="say">${esc(card.s)}</p>` : "";

    if (!showingBack) {
      elHint.textContent = "Tap, click or press space to turn over";
      elFace.innerHTML = flipped
        ? `<p class="term q">${esc(card.m)}</p>`
        : `<p class="term${card.t === "rule" ? " q" : ""}">${esc(card.f)}</p>`;
      return;
    }

    elHint.textContent = boxes
      ? "Did you get it?"
      : "Arrows for the next card";
    if (flipped) {
      elFace.innerHTML = `<div class="answer"><p class="term">${esc(card.f)}</p>${say}</div>`;
    } else if (card.t === "rule") {
      elFace.innerHTML = `<div class="answer"><p class="meaning">${esc(card.m)}</p></div>`;
    } else {
      elFace.innerHTML = `<div class="answer">${say}<p class="meaning">${esc(card.m)}</p></div>`;
    }
  }

  /**
   * Mark the card he is looking at, then move on.
   *
   * Only reachable once the card is face up — grading a card you have not
   * turned over is not retrieval practice, it is clicking.
   */
  function mark(knew: boolean): void {
    const card = cards[idx];
    if (!boxes || !card || !showingBack) return;
    if (knew) boxes.up(card.f);
    else boxes.down(card.f);
    // Re-order on every mark, so a card just sent back to box one can return
    // within the same sitting rather than waiting for a reload.
    const here = card.f;
    cards = boxes.order(cards, (c) => c.f);
    const was = cards.findIndex((c) => c.f === here);
    idx = (was + 1) % cards.length;
    showingBack = false;
    render();
  }

  const flip = () => {
    showingBack = !showingBack;
    render();
  };

  elCard.addEventListener("click", flip);
  elCard.addEventListener("keydown", (e) => {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      flip();
    }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement)?.tagName === "INPUT") return;
    if (e.key === " ") { e.preventDefault(); flip(); }
    if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
    if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
  });

  el("next").addEventListener("click", () => step(1));
  el("prev").addEventListener("click", () => step(-1));
  el("shuffle").addEventListener("click", shuffle);

  if (boxes) {
    document.getElementById("knew")?.addEventListener("click", () => mark(true));
    document.getElementById("missed")?.addEventListener("click", () => mark(false));
    document.getElementById("forget")?.addEventListener("click", () => {
      boxes.forget();
      selectDeck(deck);
    });
    const warn = document.getElementById("nomemory");
    if (warn) warn.hidden = remembers;
  }
  el("printit").addEventListener("click", () => window.print());
  el<HTMLInputElement>("reverse").addEventListener("change", function () {
    reverse = this.checked;
    showingBack = false;
    render();
  });

  buildPrintSheets(CARDS, esc);
  selectDeck(DECKS[0]!);
}

/**
 * Fold-over cards, 8 to an A4 sheet: fold down the dashed centre line, cut
 * along the 8 solid lines. Backs read correctly because the fold is vertical,
 * so nothing needs rotating.
 */
function buildPrintSheets(CARDS: Card[], esc: (s: string) => string): void {
  const host = document.getElementById("printsheets");
  if (!host) return;

  let html = "";
  for (let i = 0; i < CARDS.length; i += 8) {
    html += '<div class="sheet">';
    for (const c of CARDS.slice(i, i + 8)) {
      const front =
        `<div class="pcell pfront"><div class="pdeck">${esc(c.d)}</div>` +
        `<div class="pterm${c.t === "rule" ? " q" : ""}">${esc(c.f)}</div></div>`;
      const back =
        '<div class="pcell pback">' +
        (c.s ? `<div class="psay">${esc(c.s)}</div>` : "") +
        `<div class="pmeaning">${esc(c.m)}</div></div>`;
      html += `<div class="prow">${front}${back}</div>`;
    }
    html += "</div>";
  }
  host.innerHTML = html;
}
