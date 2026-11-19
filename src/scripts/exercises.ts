/**
 * The practice exercises.
 *
 * One module for every kind, bundled once, driven by the JSON each exercise
 * puts on the page — the same arrangement as the flashcards, and for the same
 * reason: adding an exercise should be adding a file.
 *
 * Nothing is stored. There is no account on this site and no localStorage
 * anywhere in it, so a score lives as long as the tab and no longer. That is
 * deliberate: a number that quietly resets is worse than no number, and the
 * person who needs to know how it went is the one in the room.
 *
 * Answers stay hidden until he has committed to one. Every kind here either
 * takes an answer first and then marks it, or has a button he has to press to
 * turn the card over — never both at once.
 */
import { NEAR_ENOUGH, diff, isCorrect, pick, shuffled, similarity } from "./marking";
import { speaker, spoken } from "./speech";

type Part = "speaking" | "reading" | "writing";

/**
 * `speak` names the fields of this exercise that hold French worth hearing.
 * See the schema for why it is declared rather than detected — two exercises
 * prompt with French that is wrong on purpose.
 */
type Speakable =
  | "prompt" | "question" | "answer" | "text" | "bank" | "tiles"
  | "statement" | "because" | "q" | "options";

interface Base {
  id: string; part: Part; title: string; intro?: string;
  shuffle: boolean; ask?: number; speak: Speakable[];
}
interface PromptEx extends Base { kind: "prompt"; items: { prompt: string; enPrompt?: string; answer: string; en?: string }[]; }
interface RevealEx extends Base { kind: "reveal"; text?: string; items: { prompt?: string; question?: string; answer: string }[]; }
interface GapEx extends Base { kind: "gapfill"; bank: string[]; text: (string | { gap: string })[]; }
interface TrueFalseEx extends Base { kind: "truefalse"; text?: string; items: { statement: string; answer: boolean; because?: string }[]; }
interface ChoiceEx extends Base { kind: "choice"; items: { q: string; options: string[]; answer: number }[]; }
interface TypeEx extends Base { kind: "type"; items: { prompt: string; answer: string; weight: number }[]; }
interface OrderEx extends Base { kind: "order"; items: { tiles: string[]; answer: string }[]; }
type Exercise = PromptEx | RevealEx | GapEx | TrueFalseEx | ChoiceEx | TypeEx | OrderEx;

/* ------------------------------------------------------------------ helpers */

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K, cls?: string, html?: string,
): HTMLElementTagNameMap[K] => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (html !== undefined) node.innerHTML = html;
  return node;
};

/**
 * French puts a space before ? ! ; and :, and a line that breaks there reads
 * as though the mark belongs to the next sentence. The data keeps the plain
 * space the booklet uses; this makes it unbreakable on the way to the screen.
 */
const tight = (s: string): string => s.replace(/ ([?!;:])/g, " $1");

/** Text from the data, with the inline markup the packs use left intact. */
const say = (parent: HTMLElement, tag: "p" | "span" | "div", cls: string, text: string) => {
  const node = el(tag, cls, tight(text));
  parent.appendChild(node);
  return node;
};

const button = (label: string, cls = "exbtn"): HTMLButtonElement => {
  const b = el("button", cls, label);
  b.type = "button";
  return b;
};

/** A score line that appears once, at the end, and says nothing clever. */
const verdict = (got: number, total: number): string =>
  `${got} out of ${total}` + (got === total ? " — all of them." : "");

/**
 * Put a speaker on something, if this exercise says that field is French.
 *
 * The element's own text is what gets spoken, read at the press rather than
 * now, so a speaker attached to a node that is later rewritten — the question
 * on screen, the answer just marked — says what it currently shows. `spoken`
 * strips the markup, the flags and the middle dots the data uses to separate
 * words, none of which are French.
 *
 * Two rules hold everywhere this is used, and the browser checks both:
 *
 *   - Nothing speaks a field the exercise has not declared. The declaration
 *     exists because *Spot the mistake* and *Put the punctuation back* prompt
 *     with French that is deliberately wrong.
 *   - Nothing speaks an answer before he has committed to one. Audio is a
 *     back door onto the answer otherwise: the whole design keeps answers
 *     covered until there is an attempt to compare them with, and a speaker
 *     that reads the covered answer aloud would undo that quietly.
 */
function withSpeaker(ex: Base, field: Speakable, node: HTMLElement): HTMLElement {
  if (!ex.speak.includes(field)) return node;
  const text = () => spoken(node.innerHTML);
  node.appendChild(speaker(text, spoken(node.innerHTML).slice(0, 40)));
  return node;
}

/**
 * The bar under a one-at-a-time exercise: back, where you are, forward.
 *
 * Every kind that shows one item at a time had a Next and no Back, which left
 * no way to look again at the one you just did — on the speaking practice,
 * where nothing is marked and the whole point is repeating a question until it
 * comes out cleanly, that was simply wrong.
 *
 * The unmarked kinds wrap at both ends, like the flashcards. The marked ones
 * do not: wrapping past the last answer into the first would invite answering
 * everything twice, and the count underneath would stop meaning anything.
 */
function stepper(
  total: () => number,
  at: () => number,
  go: (to: number) => void,
  { wrap = false }: { wrap?: boolean } = {},
): { nav: HTMLElement; next: HTMLButtonElement; refresh: (canGoOn: boolean) => void } {
  const nav = el("div", "exnav");
  const prev = button("← Back", "exbtn quiet");
  const pos = el("span", "expos");
  const next = button("Next →");

  prev.addEventListener("click", () => {
    const n = at() - 1;
    go(n < 0 ? (wrap ? total() - 1 : 0) : n);
  });
  next.addEventListener("click", () => {
    const n = at() + 1;
    go(n >= total() ? (wrap ? 0 : total() - 1) : n);
  });

  // A button that is not available keeps its space rather than collapsing:
  // removing it slid the counter across the bar every time the first or last
  // item came up, which reads as the page twitching. `visibility` also takes
  // it out of the tab order, so it cannot be reached while it is off.
  const avail = (b: HTMLButtonElement, yes: boolean) => {
    b.classList.toggle("gone", !yes);
    b.disabled = !yes;
  };

  const refresh = (canGoOn: boolean) => {
    pos.textContent = `${at() + 1} of ${total()}`;
    avail(prev, wrap || at() > 0);
    avail(next, canGoOn && (wrap || at() < total() - 1));
  };

  nav.append(prev, pos, next);
  return { nav, next, refresh };
}

/* ----------------------------------------------------------------- speaking */

/**
 * Say it aloud, then look. The reveal is a button rather than a hover or a
 * tap anywhere, because the whole value is in having tried first and it is
 * too easy to uncover an answer by accident.
 */
function runPrompt(ex: PromptEx, root: HTMLElement): void {
  const items = ex.shuffle ? shuffled(ex.items) : ex.items.slice();
  let i = 0;

  const stage = el("div", "exstage");
  const q = say(stage, "p", "exq", "");
  const reveal = button("Show the model answer");
  const answer = el("div", "exanswer");
  answer.hidden = true;

  const step = stepper(() => items.length, () => i, (to) => { i = to; show(); },
                       { wrap: true });

  const show = () => {
    const it = items[i]!;
    q.innerHTML = tight(it.prompt);
    // The question carries its own speaker, so hearing it is a press on the
    // question rather than a separate button labelled in English.
    withSpeaker(ex, "prompt", q);
    answer.innerHTML = "";

    // Both halves: what was asked, and what to say. The French question is at
    // the top of the card on its own, so somebody who is not sure what it
    // means gets nothing from the answer alone. The two blocks are tinted
    // differently so a glance tells you which half you are looking at.
    const asked = el("div", "exblock asked");
    withSpeaker(ex, "prompt", say(asked, "p", "fr", it.prompt));
    if (it.enPrompt) say(asked, "p", "en", it.enPrompt);

    const said = el("div", "exblock said");
    withSpeaker(ex, "answer", say(said, "p", "fr", it.answer));
    if (it.en) say(said, "p", "en", it.en);

    answer.append(asked, said);
    answer.hidden = true;
    reveal.hidden = false;
    step.refresh(true);
  };

  reveal.addEventListener("click", () => {
    answer.hidden = false;
    reveal.hidden = true;
  });

  // Nothing here takes typing, so the arrow keys are free to do what they do
  // in the flashcard app.
  root.tabIndex = -1;
  root.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") { i = (i + 1) % items.length; show(); }
    if (e.key === "ArrowLeft") { i = (i - 1 + items.length) % items.length; show(); }
  });

  const row = el("div", "exrow");
  row.append(reveal);
  stage.append(row, answer);
  root.append(stage, step.nav);
  show();
}

/* ------------------------------------------------------------------- reveal */

/** Think, then turn it over. Unmarked — only he knows whether he had it. */
function runReveal(ex: RevealEx, root: HTMLElement): void {
  const items = ex.shuffle ? shuffled(ex.items) : ex.items.slice();
  const list = el("ol", "exreveal");

  if (ex.text) withSpeaker(ex, "text", say(root, "p", "extext fr", ex.text));

  for (const it of items) {
    const li = el("li");
    if (it.prompt) withSpeaker(ex, "prompt", say(li, "p", "fr", it.prompt));
    if (it.question) withSpeaker(ex, "question", say(li, "p", "exq", it.question));
    const a = el("p", "exanswer");
    a.innerHTML = tight(it.answer);
    // The speaker goes on after the text, so `spoken()` reads the answer and
    // not the glyph. It is inside the hidden answer, so it cannot be pressed
    // — and therefore cannot leak the answer — until Show has been pressed.
    withSpeaker(ex, "answer", a);
    a.hidden = true;
    const b = button("Show");
    b.addEventListener("click", () => {
      a.hidden = false;
      b.hidden = true;
    });
    li.append(b, a);
    list.appendChild(li);
  }

  const all = button("Show every answer", "exbtn quiet");
  all.addEventListener("click", () => {
    list.querySelectorAll<HTMLElement>(".exanswer").forEach((a) => (a.hidden = false));
    list.querySelectorAll<HTMLButtonElement>("button").forEach((b) => (b.hidden = true));
    all.hidden = true;
  });

  root.append(list, all);
}

/* ------------------------------------------------------------------ gapfill */

function runGap(ex: GapEx, root: HTMLElement): void {
  const bank = el("div", "exbank");
  for (const w of shuffled(ex.bank)) {
    bank.appendChild(withSpeaker(ex, "bank", el("span", "extile", tight(w))));
  }

  const para = el("p", "extext");
  const gaps: { input: HTMLInputElement; answer: string }[] = [];
  for (const piece of ex.text) {
    if (typeof piece === "string") {
      para.appendChild(document.createTextNode(tight(piece)));
    } else {
      const input = el("input", "exgap");
      input.type = "text";
      input.autocapitalize = "off";
      input.autocomplete = "off";
      input.spellcheck = false;
      input.size = Math.max(piece.gap.length, 4);
      input.setAttribute("aria-label", `gap ${gaps.length + 1}`);
      para.appendChild(input);
      gaps.push({ input, answer: piece.gap });
    }
  }

  const check = button("Check");
  const result = el("p", "exresult");
  /** Holds the whole-passage speaker, once there is a filled passage to read. */
  const passage = el("p", "expassage");
  check.addEventListener("click", () => {
    let got = 0;
    for (const g of gaps) {
      const right = isCorrect(g.input.value, g.answer);
      g.input.classList.toggle("right", right);
      g.input.classList.toggle("wrong", !right);
      if (right) got++;
      else g.input.value = g.answer;      // the correct word, in its gap
    }
    result.textContent = verdict(got, gaps.length) +
      (got === gaps.length ? "" : " The right words are in the gaps now.");
    // The whole passage, now that every gap holds the right word — and only
    // now. A speaker on it beforehand would read the answers out before he
    // had filled anything in, which is the covered-answer rule the rest of
    // this file is built on, broken by sound instead of sight.
    if (ex.speak.includes("text") && !passage.hasChildNodes()) {
      const whole = ex.text
        .map((piece) => (typeof piece === "string" ? piece : piece.gap))
        .join("");
      passage.append(
        el("span", "exlabel", "Hear the whole thing"),
        speaker(() => spoken(whole), "the passage"),
      );
    }
  });

  root.append(bank, para, check, result, passage);
}

/* ---------------------------------------------------------------- true/false */

function runTrueFalse(ex: TrueFalseEx, root: HTMLElement): void {
  if (ex.text) withSpeaker(ex, "text", say(root, "p", "extext fr", ex.text));

  const list = el("ol", "extf");
  const rows = ex.items.map((it) => {
    const li = el("li");
    say(li, "span", "exstatement", it.statement);
    const yes = button("True", "exbtn pick");
    const no = button("False", "exbtn pick");
    const why = el("span", "exwhy");
    why.hidden = true;
    let chose: boolean | undefined;
    for (const [b, value] of [[yes, true], [no, false]] as const) {
      b.addEventListener("click", () => {
        chose = value;
        yes.setAttribute("aria-pressed", String(value));
        no.setAttribute("aria-pressed", String(!value));
      });
    }
    const buttons = el("span", "exbuttons");
    buttons.append(yes, no);
    li.append(buttons, why);
    list.appendChild(li);
    return { it, yes, no, why, chosen: () => chose };
  });

  const check = button("Check");
  const result = el("p", "exresult");
  check.addEventListener("click", () => {
    let got = 0;
    for (const r of rows) {
      const right = r.chosen() === r.it.answer;
      if (right) got++;
      const correct = r.it.answer ? r.yes : r.no;
      correct.classList.add("right");
      (r.it.answer ? r.no : r.yes).classList.toggle("wrong", r.chosen() === !r.it.answer);
      if (!right) {
        r.why.hidden = false;
        r.why.innerHTML = r.it.because
          ? `${r.it.answer ? "True" : "False"} — ${tight(r.it.because)}`
          : r.it.answer ? "True" : "False";
      }
    }
    result.textContent = verdict(got, rows.length);
  });

  root.append(list, check, result);
}

/* ------------------------------------------------------------------- choice */

/**
 * A quiz. Tapping an option is the commitment, so it marks there and then.
 *
 * What he picked is remembered, so going back shows the question as he left
 * it — the right answer still highlighted — rather than offering it again. An
 * answered question cannot be answered twice, which is what keeps the count
 * at the end honest.
 */
function runChoice(ex: ChoiceEx, root: HTMLElement): void {
  const items = pick(ex.shuffle ? shuffled(ex.items) : ex.items.slice(), ex.ask);
  const chose: (number | undefined)[] = [];
  let i = 0;

  const q = el("p", "exq");
  const options = el("div", "exoptions");
  const result = el("p", "exresult");
  const step = stepper(() => items.length, () => i, (to) => { i = to; show(); });

  const score = () =>
    chose.reduce<number>((n, pickedAt, at) => n + (pickedAt === items[at]!.answer ? 1 : 0), 0);
  const allDone = () => items.every((_, at) => chose[at] !== undefined);

  const show = () => {
    const it = items[i]!;
    const picked = chose[i];
    q.innerHTML = tight(it.q);
    withSpeaker(ex, "q", q);
    options.innerHTML = "";

    it.options.forEach((label, n) => {
      const b = button(tight(label), "exbtn option");
      if (picked !== undefined) {
        // Already answered: show how it went, and take no more clicks.
        if (n === it.answer) b.classList.add("right");
        if (n === picked && picked !== it.answer) b.classList.add("wrong");
        b.disabled = true;
      } else {
        b.addEventListener("click", () => {
          chose[i] = n;
          show();
        });
      }
      options.appendChild(b);
    });

    result.textContent = allDone() ? `Finished — ${verdict(score(), items.length)}` : "";
    step.refresh(picked !== undefined);
  };

  root.append(q, options, result, step.nav);
  show();
}

/* --------------------------------------------------------------------- type */

/**
 * The right answer, with what was missed picked out — but only when picking it
 * out means something.
 *
 * A highlight says "look here". If the answer was nowhere near, there is no
 * "here" to look at and the markup only makes the correct version harder to
 * read, so it is printed plain. The same goes for an answer that differs only
 * by something he typed *extra*: nothing is missing from the correct version,
 * so there is nothing to mark, and a run of markup with no holes in it would
 * just be a red box round the whole line.
 */
function answerWith(typed: string, expected: string): string {
  const runs = diff(typed, expected);
  const worth = similarity(typed, expected) >= NEAR_ENOUGH
    && runs.some((r) => !r.same)
    && runs.some((r) => r.same);
  if (!worth) return tight(expected);
  return runs.map((r) => (r.same ? tight(r.text) : `<mark>${tight(r.text)}</mark>`)).join("");
}

/**
 * Type the French. One at a time, marked strictly, and a wrong answer shows
 * the correct version rather than only saying "no": somebody who could see the
 * difference unaided would not have typed it that way.
 */
function runType(ex: TypeEx, root: HTMLElement): void {
  const items = pick(ex.shuffle ? shuffled(ex.items) : ex.items.slice(), ex.ask);
  /** What he typed for each one, once marked. Going back shows it again. */
  const typed: (string | undefined)[] = [];
  let i = 0;

  const prompt = el("p", "exprompt");
  const input = el("input", "exinput");
  input.type = "text";
  input.autocapitalize = "off";
  input.autocomplete = "off";
  input.autocorrect = "off";
  input.spellcheck = false;
  input.lang = "fr";
  input.setAttribute("aria-label", "Your answer in French");

  const check = button("Check");
  const result = el("p", "exresult");
  const step = stepper(() => items.length, () => i,
                       (to) => { i = to; show(typed[to] === undefined); });

  const right = (at: number) =>
    typed[at] !== undefined && isCorrect(typed[at]!, items[at]!.answer);
  const score = () => items.reduce<number>((n, _, at) => n + (right(at) ? 1 : 0), 0);
  const allDone = () => items.every((_, at) => typed[at] !== undefined);

  // Focus moves to the input when he asks for the next question, never on
  // load: a pack page carries several exercises, and the last one to boot
  // would otherwise take the focus and scroll the page past the vocabulary
  // the page exists to show. Nor when stepping back to one already answered,
  // where there is nothing to type.
  const show = (focus = true) => {
    const it = items[i]!;
    const said = typed[i];
    prompt.innerHTML = tight(it.prompt);
    input.value = said ?? "";
    input.className = "exinput";
    input.disabled = said !== undefined;
    check.hidden = said !== undefined;
    result.innerHTML = "";

    if (said !== undefined) {
      input.classList.add(right(i) ? "right" : "wrong");
      result.innerHTML = right(i)
        ? "Correct."
        : `<span class="exlabel">The answer is</span> <span class="fr">${answerWith(said, it.answer)}</span>`;
      // A speaker on the answer, but only now it has been marked — before
      // that there is nothing on screen to attach it to, which is the point.
      // It reads `it.answer` rather than the span, because the span carries
      // <mark> round the letters he missed and the marks are not French.
      const fr = result.querySelector<HTMLElement>(".fr");
      if (fr && ex.speak.includes("answer")) {
        fr.appendChild(speaker(() => spoken(tight(it.answer)), spoken(it.answer)));
      }
    }
    if (allDone()) {
      result.innerHTML += `<span class="exfinal">Finished — ${verdict(score(), items.length)}</span>`;
    }

    step.refresh(said !== undefined);
    if (focus && said === undefined) input.focus();
  };

  const mark = () => {
    if (typed[i] !== undefined) return;       // already answered; not twice
    typed[i] = input.value;
    show(false);
    if (!step.next.hidden) step.next.focus({ preventScroll: true });
  };

  check.addEventListener("click", mark);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      mark();
    }
  });

  const row = el("div", "exrow");
  row.append(check);
  root.append(prompt, input, row, result, step.nav);
  show(false);
}

/* -------------------------------------------------------------------- order */

/** Tiles into a line. Tapping a placed tile takes it back. */
function runOrder(ex: OrderEx, root: HTMLElement): void {
  const items = ex.shuffle ? shuffled(ex.items) : ex.items.slice();
  /** The order he settled on, once checked. Going back shows it again. */
  const settled: (string[] | undefined)[] = [];
  let i = 0;
  let placed: string[] = [];

  const line = el("div", "exline");
  const pool = el("div", "expool");
  const check = button("Check");
  const result = el("p", "exresult");
  const step = stepper(() => items.length, () => i, (to) => { i = to; show(); });

  // The tiles carry no punctuation beyond what is written on them, so the
  // sentence they make is compared with the commas and full stops removed —
  // the task is the word order, and W-D is where punctuation is marked.
  const bare = (t: string) => t.replace(/[.,]/g, "").replace(/\s+/g, " ").trim();
  const right = (at: number) =>
    settled[at] !== undefined &&
    isCorrect(bare(settled[at]!.join(" ")), bare(items[at]!.answer));
  const score = () => items.reduce<number>((n, _, at) => n + (right(at) ? 1 : 0), 0);
  const allDone = () => items.every((_, at) => settled[at] !== undefined);

  const draw = () => {
    const it = items[i]!;
    const done = settled[i] !== undefined;

    line.innerHTML = "";
    placed.forEach((word, n) => {
      const t = button(tight(word), "extile placed");
      if (done) {
        t.classList.add(right(i) ? "right" : "wrong");
        t.disabled = true;
      } else {
        t.addEventListener("click", () => {
          placed.splice(n, 1);
          draw();
        });
      }
      line.appendChild(t);
    });
    if (placed.length === 0) line.appendChild(el("span", "exempty", "Tap the words in order"));

    pool.innerHTML = "";
    const left = it.tiles.slice();
    for (const word of placed) {
      const at = left.indexOf(word);
      if (at >= 0) left.splice(at, 1);
    }
    for (const word of left) {
      const t = button(tight(word), "extile");
      if (done) t.disabled = true;
      else {
        t.addEventListener("click", () => {
          placed.push(word);
          draw();
        });
      }
      // One tile is one word, so hearing it gives nothing away about the
      // order — which is the thing being asked.
      if (ex.speak.includes("tiles")) {
        const s = speaker(() => spoken(word), spoken(word));
        s.classList.add("ontile");
        pool.append(t, s);
      } else {
        pool.appendChild(t);
      }
    }
    check.disabled = left.length > 0;
  };

  /** Which items have had their tiles shuffled. See below. */
  const shuffledOnce = new Set<number>();

  const show = () => {
    const it = items[i]!;
    const done = settled[i];
    // The tiles are shuffled once, the first time this item is reached. A
    // reshuffle on the way back would make a sentence he has already put in
    // order look like a different question.
    placed = done ? done.slice() : [];
    if (done === undefined && !shuffledOnce.has(i)) {
      it.tiles = shuffled(it.tiles);
      shuffledOnce.add(i);
    }

    result.innerHTML = done
      ? (right(i)
          ? `Correct. <span class="fr">${tight(it.answer)}</span>`
          : `<span class="exlabel">Not quite. It is</span> <span class="fr">${tight(it.answer)}</span>`)
      : "";
    if (done) {
      const fr = result.querySelector<HTMLElement>(".fr");
      if (fr && ex.speak.includes("answer")) {
        fr.appendChild(speaker(() => spoken(tight(it.answer)), spoken(it.answer)));
      }
    }
    if (allDone()) {
      result.innerHTML += `<span class="exfinal">Finished — ${verdict(score(), items.length)}</span>`;
    }
    check.hidden = done !== undefined;
    step.refresh(done !== undefined);
    draw();
  };

  check.addEventListener("click", () => {
    if (settled[i] !== undefined) return;     // already checked; not twice
    settled[i] = placed.slice();
    show();
  });

  const row = el("div", "exrow");
  row.append(check);
  root.append(line, pool, row, result, step.nav);
  show();
}

/* --------------------------------------------------------------------- boot */

const RUNNERS = {
  prompt: runPrompt, reveal: runReveal, gapfill: runGap, truefalse: runTrueFalse,
  choice: runChoice, type: runType, order: runOrder,
} as const;

for (const host of document.querySelectorAll<HTMLElement>("[data-exercise]")) {
  const script = host.querySelector<HTMLScriptElement>("script.ex-data");
  const body = host.querySelector<HTMLElement>(".ex-body");
  if (!script?.textContent || !body) continue;
  const ex = JSON.parse(script.textContent) as Exercise;
  // Typed as a union on `kind`; the cast is the one place the dispatch table
  // and the union have to be taken on trust.
  (RUNNERS[ex.kind] as (e: Exercise, root: HTMLElement) => void)(ex, body);
  host.classList.add("ready");
}
