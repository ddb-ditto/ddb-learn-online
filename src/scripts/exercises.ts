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
import { diff, isCorrect, pick, shuffled, type Run } from "./marking";

type Part = "speaking" | "reading" | "writing";

interface Base { id: string; part: Part; title: string; intro?: string; shuffle: boolean; ask?: number; }
interface PromptEx extends Base { kind: "prompt"; speakLang?: string; items: { prompt: string; answer: string; en?: string }[]; }
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
  const speak = button("♪ Hear it", "exbtn quiet");
  const reveal = button("Show the model answer");
  const answer = el("div", "exanswer");
  answer.hidden = true;
  const nav = el("div", "exnav");
  const pos = el("span", "expos");
  const next = button("Next →");

  const show = () => {
    const it = items[i]!;
    q.innerHTML = tight(it.prompt);
    answer.innerHTML = "";
    say(answer, "p", "fr", it.answer);
    if (it.en) say(answer, "p", "en", it.en);
    answer.hidden = true;
    reveal.hidden = false;
    pos.textContent = `${i + 1} of ${items.length}`;
  };

  reveal.addEventListener("click", () => {
    answer.hidden = false;
    reveal.hidden = true;
  });

  // Browsers without French speech simply do not offer the button, rather
  // than offering one that reads it in English.
  const canSpeak = ex.speakLang !== undefined && "speechSynthesis" in window;
  if (canSpeak) {
    speak.addEventListener("click", () => {
      const u = new SpeechSynthesisUtterance(items[i]!.prompt);
      u.lang = ex.speakLang!;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    });
  } else {
    speak.hidden = true;
  }

  next.addEventListener("click", () => {
    i = (i + 1) % items.length;
    show();
  });

  const row = el("div", "exrow");
  row.append(speak, reveal);
  stage.append(row, answer);
  nav.append(pos, next);
  root.append(stage, nav);
  show();
}

/* ------------------------------------------------------------------- reveal */

/** Think, then turn it over. Unmarked — only he knows whether he had it. */
function runReveal(ex: RevealEx, root: HTMLElement): void {
  const items = ex.shuffle ? shuffled(ex.items) : ex.items.slice();
  const list = el("ol", "exreveal");

  for (const it of items) {
    const li = el("li");
    if (it.prompt) say(li, "p", "fr", it.prompt);
    if (it.question) say(li, "p", "exq", it.question);
    const a = el("p", "exanswer");
    a.innerHTML = tight(it.answer);
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
  for (const w of shuffled(ex.bank)) bank.appendChild(el("span", "extile", tight(w)));

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
  });

  root.append(bank, para, check, result);
}

/* ---------------------------------------------------------------- true/false */

function runTrueFalse(ex: TrueFalseEx, root: HTMLElement): void {
  if (ex.text) say(root, "p", "extext fr", ex.text);

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

/** A quiz. Tapping an option is the commitment, so it marks there and then. */
function runChoice(ex: ChoiceEx, root: HTMLElement): void {
  const items = pick(ex.shuffle ? shuffled(ex.items) : ex.items.slice(), ex.ask);
  let i = 0;
  let got = 0;
  let answered = false;

  const q = el("p", "exq");
  const options = el("div", "exoptions");
  const result = el("p", "exresult");
  const nav = el("div", "exnav");
  const pos = el("span", "expos");
  const next = button("Next →");
  next.hidden = true;

  const show = () => {
    const it = items[i]!;
    answered = false;
    q.innerHTML = tight(it.q);
    options.innerHTML = "";
    result.textContent = "";
    next.hidden = true;
    it.options.forEach((label, n) => {
      const b = button(tight(label), "exbtn option");
      b.addEventListener("click", () => {
        if (answered) return;
        answered = true;
        const right = n === it.answer;
        if (right) got++;
        b.classList.add(right ? "right" : "wrong");
        if (!right) {
          (options.children[it.answer] as HTMLElement).classList.add("right");
        }
        next.hidden = i === items.length - 1;
        if (i === items.length - 1) result.textContent = `Finished — ${verdict(got, items.length)}`;
      });
      options.appendChild(b);
    });
    pos.textContent = `${i + 1} of ${items.length}`;
  };

  next.addEventListener("click", () => {
    i++;
    show();
  });

  nav.append(pos, next);
  root.append(q, options, result, nav);
  show();
}

/* --------------------------------------------------------------------- type */

/** Draw a wrong answer as the right one, with what he missed picked out. */
const renderDiff = (runs: Run[]): string =>
  runs.map((r) => (r.same ? tight(r.text) : `<mark>${tight(r.text)}</mark>`)).join("");

/**
 * Type the French. One at a time, marked strictly, and a wrong answer shows
 * the correct version rather than only saying "no" — he has already proved he
 * cannot see the difference unaided.
 */
function runType(ex: TypeEx, root: HTMLElement): void {
  const items = pick(ex.shuffle ? shuffled(ex.items) : ex.items.slice(), ex.ask);
  let i = 0;
  let got = 0;
  let marked = false;

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
  const next = button("Next →");
  next.hidden = true;
  const result = el("p", "exresult");
  const nav = el("div", "exnav");
  const pos = el("span", "expos");

  // Focus moves to the input when he asks for the next question, never on
  // load: a pack page carries several exercises, and the last one to boot
  // would otherwise take the focus and scroll the page past the vocabulary
  // the page exists to show.
  const show = (focus = true) => {
    const it = items[i]!;
    marked = false;
    prompt.innerHTML = tight(it.prompt);
    input.value = "";
    input.className = "exinput";
    input.disabled = false;
    result.innerHTML = "";
    check.hidden = false;
    next.hidden = true;
    pos.textContent = `${i + 1} of ${items.length}`;
    if (focus) input.focus();
  };

  const mark = () => {
    if (marked) return;
    marked = true;
    const it = items[i]!;
    const right = isCorrect(input.value, it.answer);
    if (right) got++;
    input.classList.add(right ? "right" : "wrong");
    input.disabled = true;
    check.hidden = true;
    result.innerHTML = right
      ? "Correct."
      : `<span class="exlabel">The answer is</span> <span class="fr">${renderDiff(diff(input.value, it.answer))}</span>`;
    if (i === items.length - 1) {
      result.innerHTML += `<span class="exfinal">Finished — ${verdict(got, items.length)}</span>`;
    } else {
      next.hidden = false;
      next.focus({ preventScroll: true });
    }
  };

  check.addEventListener("click", mark);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      mark();
    }
  });
  next.addEventListener("click", () => {
    i++;
    show();
  });

  const row = el("div", "exrow");
  row.append(check, next);
  nav.appendChild(pos);
  root.append(prompt, input, row, result, nav);
  show(false);
}

/* -------------------------------------------------------------------- order */

/** Tiles into a line. Tapping a placed tile takes it back. */
function runOrder(ex: OrderEx, root: HTMLElement): void {
  const items = ex.shuffle ? shuffled(ex.items) : ex.items.slice();
  let i = 0;
  let got = 0;

  const line = el("div", "exline");
  const pool = el("div", "expool");
  const check = button("Check");
  const next = button("Next →");
  next.hidden = true;
  const result = el("p", "exresult");
  const nav = el("div", "exnav");
  const pos = el("span", "expos");
  let placed: string[] = [];

  const draw = () => {
    const it = items[i]!;
    line.innerHTML = "";
    placed.forEach((word, n) => {
      const t = button(tight(word), "extile placed");
      t.addEventListener("click", () => {
        placed.splice(n, 1);
        draw();
      });
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
      t.addEventListener("click", () => {
        placed.push(word);
        draw();
      });
      pool.appendChild(t);
    }
    check.disabled = left.length > 0;
  };

  const show = () => {
    placed = [];
    const it = items[i]!;
    it.tiles = shuffled(it.tiles);
    result.innerHTML = "";
    check.hidden = false;
    next.hidden = true;
    pos.textContent = `${i + 1} of ${items.length}`;
    draw();
  };

  check.addEventListener("click", () => {
    const it = items[i]!;
    // The tiles carry no punctuation beyond what is written on them, so the
    // sentence they make is compared with the commas and full stops removed —
    // the task is the word order, and W-D is where punctuation is marked.
    const bare = (s: string) => s.replace(/[.,]/g, "").replace(/\s+/g, " ").trim();
    const right = isCorrect(bare(placed.join(" ")), bare(it.answer));
    if (right) got++;
    check.hidden = true;
    result.innerHTML = right
      ? `Correct. <span class="fr">${tight(it.answer)}</span>`
      : `<span class="exlabel">Not quite. It is</span> <span class="fr">${tight(it.answer)}</span>`;
    line.querySelectorAll<HTMLElement>(".placed").forEach((t) => t.classList.add(right ? "right" : "wrong"));
    if (i === items.length - 1) {
      result.innerHTML += `<span class="exfinal">Finished — ${verdict(got, items.length)}</span>`;
    } else {
      next.hidden = false;
    }
  });

  next.addEventListener("click", () => {
    i++;
    show();
  });

  const row = el("div", "exrow");
  row.append(check, next);
  nav.appendChild(pos);
  root.append(line, pool, row, result, nav);
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
