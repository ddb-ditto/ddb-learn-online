/**
 * One question at a time, from every pack, until he has got them all right.
 *
 * The pack pages and *Mix it up* give him a page of exercises and let him work
 * down it. This is the other shape: a single card on screen, marked the
 * instant he answers, and a bar that only moves when he is right. A question
 * he gets wrong goes to the back of the queue and comes round again, so the
 * run ends when every question in it has been answered correctly rather than
 * when he reaches the bottom of a list. That is the whole mechanic, and it is
 * worth the duplication with `exercises.ts`: those are exercises you finish,
 * this is a thing you clear.
 *
 * Three rules from CLAUDE.md shape what is below, and none of them is
 * negotiable:
 *
 *   - **Nothing is stored.** No streak, no best score, no history. The tally
 *     lives in this closure and dies with the tab, exactly as the exercises
 *     do. Nothing here writes to `localStorage`.
 *   - **No French is invented.** Every string comes out of `runqueue.ts`,
 *     which takes it from a pack. The multiple-choice wrong answers are other
 *     real items' real glosses, picked from the same group so the question
 *     cannot be answered by elimination alone.
 *   - **Audio never reaches an answer first, and never reads French that is
 *     wrong on purpose.** A speaker goes on a French *prompt* only when that
 *     prompt is the pack's own French; on an answer only once it is marked.
 *     The punctuation prompt and the misspelling prompt get neither.
 *
 * Speaking is the one thing this cannot mark. A synthesiser can read the
 * French out, but nothing in a browser can tell him whether what he said was
 * any good — so those cards say outright that a person has to listen, and
 * they are not scored. Pretending to mark them would be worse than not
 * having them.
 */
import { diff, isCorrect, NEAR_ENOUGH, shuffled, similarity } from "./marking";
import { speaker, spoken } from "./speech";

/* ------------------------------------------------------------------ the pool */

type Group = "word" | "number" | "country";
interface Item { fr: string; en: string; group: Group; pack: string; tiles?: string[]; bare?: string; }
interface Mistake { wrong: string; right: string; pack: string; }
interface Say { q: string; a: string; en: string; pack: string; }
interface Pool { items: Item[]; mistakes: Mistake[]; say: Say[]; }

/* ------------------------------------------------------------- the questions */

interface Base { id: string; pack: string; }
type Question =
  /** French on screen, four English meanings, one of them right. */
  | (Base & { k: "choose"; fr: string; options: string[]; answer: number })
  /** Something to type. `french` says whether the prompt may be read aloud. */
  | (Base & { k: "type"; how: string; prompt: string; french: boolean; answer: string })
  /** Tiles to put in order. */
  | (Base & { k: "order"; en: string; tiles: string[]; answer: string })
  /** Out loud. Nothing here marks it. */
  | (Base & { k: "say"; q: string; a: string; en: string });

/** How many markable questions a run holds. About ten minutes of work. */
const LENGTH = 14;
/** How many out-loud cards get mixed in. */
const SPOKEN = 2;
/** How many real misspellings to include. Pack 10 is the only source. */
const MISSPELT = 2;
/** A multiple choice needs three wrong answers, so a group needs four members. */
const CHOICES = 4;

const esc = (s: string): string =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/**
 * Three wrong answers for `item`, taken from other real items.
 *
 * From its own group first — other numbers for a number, other countries for
 * a country — because a question whose wrong answers are all obviously the
 * wrong *kind* of thing is a question about English. Falls back to the whole
 * pool if a group is too small, and gives up if even that cannot fill it,
 * in which case the item is asked some other way.
 */
function distractors(item: Item, pool: Item[]): string[] | null {
  const other = (from: Item[]): string[] => {
    const seen = new Set([item.en]);
    const out: string[] = [];
    for (const c of shuffled(from)) {
      if (seen.has(c.en)) continue;
      seen.add(c.en);
      out.push(c.en);
      if (out.length === CHOICES - 1) break;
    }
    return out;
  };
  const sameKind = other(pool.filter((i) => i.group === item.group));
  if (sameKind.length === CHOICES - 1) return sameKind;
  const anything = other(pool);
  return anything.length === CHOICES - 1 ? anything : null;
}

/** Every way this item could be asked, as questions ready to run. */
function waysToAsk(item: Item, at: number, pool: Item[]): Question[] {
  const id = `i${at}`;
  const out: Question[] = [];

  const wrong = distractors(item, pool);
  if (wrong) {
    const options = shuffled([item.en, ...wrong]);
    out.push({
      k: "choose", id, pack: item.pack, fr: item.fr,
      options, answer: options.indexOf(item.en),
    });
  }

  out.push({
    k: "type", id, pack: item.pack,
    how: item.tiles ? "Write it in French" : "Spell it in French",
    prompt: item.en, french: false, answer: item.fr,
  });

  if (item.tiles) {
    out.push({
      k: "order", id, pack: item.pack,
      en: item.en, tiles: item.tiles, answer: item.fr,
    });
  }

  if (item.bare) {
    out.push({
      k: "type", id, pack: item.pack,
      how: "Put the capitals, accents and marks back",
      // French with its marks stripped off: wrong on purpose, so never spoken.
      prompt: item.bare, french: true, answer: item.fr,
    });
  }

  return out;
}

/**
 * Build one run: a shuffled set of questions, no item asked twice, with the
 * out-loud cards spread through it rather than bunched at one end.
 */
function buildRun(pool: Pool): Question[] {
  const asked: Question[] = [];

  // The real misspellings first, because there are only ever a handful of
  // them and they would otherwise be squeezed out by the hundred-odd words.
  // They cannot be derived — see CLAUDE.md — so what pack 10 holds is all
  // there is.
  for (const [at, m] of shuffled(pool.mistakes.map((x, n) => [n, x] as const)).slice(0, MISSPELT)) {
    asked.push({
      k: "type", id: `m${at}`, pack: m.pack,
      how: "Something is wrong with this. Type it out correctly",
      prompt: m.wrong, french: true, answer: m.right,
    });
  }

  // Then every item, in a random order, asked a random one of the ways it
  // can be asked, until the run is full.
  for (const [at, item] of shuffled(pool.items.map((i, n) => [n, i] as const))) {
    if (asked.length >= LENGTH) break;
    const ways = waysToAsk(item, at, pool.items);
    if (ways.length) asked.push(shuffled(ways)[0]!);
  }

  const marked = shuffled(asked);

  const aloud = shuffled(pool.say.map((s, n) => [n, s] as const)).slice(0, SPOKEN)
    .map(([at, s]): Question => ({
      k: "say", id: `s${at}`, pack: s.pack, q: s.q, a: s.a, en: s.en,
    }));

  // Spread rather than shuffle, so the unmarked cards are breathing spaces
  // through the run instead of landing two in a row at the end.
  const out = [...marked];
  for (const [n, spokenCard] of aloud.entries()) {
    out.splice(Math.round(((n + 1) * out.length) / (aloud.length + 1)), 0, spokenCard);
  }
  return out;
}

/* ----------------------------------------------------------------- the stage */

const stage = document.getElementById("run-stage");
const fill = document.getElementById("run-fill");
const tally = document.getElementById("run-tally");
const data = document.getElementById("run-pool");

if (stage && fill && tally && data) {
  const pool = JSON.parse(data.textContent ?? "{}") as Pool;
  start();

  function start(): void {
    const queue = buildRun(pool);
    const total = queue.filter((q) => q.k !== "say").length;
    const done = new Set<string>();
    let first = 0;               // got right at the first time of asking
    let at = 0;

    const progress = (): void => {
      const pc = total ? Math.round((done.size / total) * 100) : 100;
      fill!.style.width = `${pc}%`;
      // Both, or the count is read against the default maximum of 100 and a
      // cleared run of fourteen is announced as fourteen per cent.
      const bar = fill!.parentElement;
      bar?.setAttribute("aria-valuemax", String(total));
      bar?.setAttribute("aria-valuenow", String(done.size));
      tally!.textContent = `${done.size} of ${total}`;
    };

    /** Move on. A question answered wrongly has already been pushed to the back. */
    const next = (): void => {
      at++;
      if (at >= queue.length) return finish();
      show(queue[at]!);
    };

    const finish = (): void => {
      stage!.innerHTML = `<div class="runend">
        <h2>That is the lot.</h2>
        <p>You cleared all ${total}, and got ${first} of them right first time.</p>
        <p class="runnote">Nothing here is saved. Close the tab and it is gone —
        the next run picks a different set and asks it in a different way.</p>
        <button type="button" class="exbtn" id="run-again">Go again</button>
      </div>`;
      document.getElementById("run-again")?.addEventListener("click", start);
      progress();
    };

    /**
     * Mark one markable question.
     *
     * `again` is whether this is a repeat, which is what keeps the first-time
     * count honest: a question got right on its third showing has still been
     * got right, and the bar moves, but it was not right first time.
     */
    const mark = (q: Question, right: boolean, again: boolean): void => {
      if (right) {
        if (!done.has(q.id)) {
          done.add(q.id);
          if (!again) first++;
        }
      } else {
        queue.push({ ...q });
      }
      progress();
    };

    const card = (inner: string): HTMLElement => {
      stage!.innerHTML = `<div class="runcard">${inner}</div>`;
      return stage!.firstElementChild as HTMLElement;
    };

    /**
     * The classes below are `exercises.ts`'s own — `.exbtn`, `.exinput`,
     * `.extile`, `.exline`, `.exprompt`, `.exanswer`, `.right`, `.wrong`.
     * They are all scoped under `.exercise` in `house.css`, which is why the
     * stage sits inside an element carrying that class. A parallel set of
     * `.run*` rules saying the same things would have drifted from them by
     * the second change, and a drill here should look like a drill there.
     */

    /** The button that moves on, added once the question has been answered. */
    const onward = (box: HTMLElement, label = "Next"): void => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "exbtn runnext";
      b.textContent = label;
      b.addEventListener("click", next);
      box.appendChild(b);
      b.focus();
    };

    /**
     * The right answer, with a speaker on it.
     *
     * Deliberately *not* the green block. Green in this section means "this
     * is the right one" and is kept for the reveals that mark nothing; here
     * something is being marked, and the same block has to carry both a
     * correct answer and a failed one. Colouring it green would put the "you
     * were right" colour on a wrong attempt every other time it appeared. The
     * marking is on the input and the options, where it already is.
     */
    const reveal = (box: HTMLElement, french: string, lead: string): void => {
      const p = document.createElement("p");
      p.className = "exanswer";
      p.innerHTML = `<span class="runlead">${esc(lead)}</span> `
        + `<span lang="fr" class="fr">${esc(french)}</span>`;
      box.appendChild(p);
      const fr = p.querySelector<HTMLElement>(".fr")!;
      fr.appendChild(speaker(() => spoken(fr.innerHTML), french.slice(0, 40)));
    };

    function show(q: Question): void {
      const again = done.has(q.id) === false && at > 0
        && queue.slice(0, at).some((e) => e.id === q.id);

      if (q.k === "say") return showSay(q);
      if (q.k === "choose") return showChoose(q, again);
      if (q.k === "order") return showOrder(q, again);
      return showType(q, again);
    }

    /* --------------------------------------------------------- choose */

    function showChoose(q: Extract<Question, { k: "choose" }>, again: boolean): void {
      const box = card(`
        <p class="exintro">What does this mean?</p>
        <p class="exprompt"><span lang="fr" class="fr">${esc(q.fr)}</span></p>
        <div class="exrow runoptions"></div>`);
      const ask = box.querySelector<HTMLElement>(".fr")!;
      // The prompt is the pack's own French and is not the answer, so it can
      // be read aloud straight away.
      ask.appendChild(speaker(() => spoken(ask.innerHTML), q.fr));

      const options = box.querySelector<HTMLElement>(".runoptions")!;
      const buttons: HTMLButtonElement[] = [];
      q.options.forEach((label, n) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "exbtn option";
        b.textContent = label;
        b.addEventListener("click", () => {
          for (const other of buttons) other.disabled = true;
          const right = n === q.answer;
          b.classList.add(right ? "right" : "wrong");
          if (!right) buttons[q.answer]!.classList.add("right");
          mark(q, right, again);
          onward(box);
        });
        buttons.push(b);
        options.appendChild(b);
      });
    }

    /* ----------------------------------------------------------- type */

    function showType(q: Extract<Question, { k: "type" }>, again: boolean): void {
      // `.fr` is the section's italic for French and nothing more — it is
      // not what makes a thing speakable, and these two prompts are French
      // with something deliberately wrong with it, so no speaker is attached
      // to them anywhere below.
      const prompt = q.french
        ? `<span lang="fr" class="fr">${esc(q.prompt)}</span>`
        : esc(q.prompt);
      const box = card(`
        <p class="exintro">${esc(q.how)}</p>
        <p class="exprompt">${prompt}</p>
        <input type="text" class="exinput" autocomplete="off" autocapitalize="off"
               autocorrect="off" spellcheck="false" lang="fr"
               aria-label="Your answer in French">
        <button type="button" class="exbtn runcheck">Check</button>`);
      // No speaker on the prompt: where it is French at all it is French with
      // something deliberately wrong with it, and reading it aloud would both
      // teach the error and give the answer away — spoken, a missing accent
      // and a missing final -s sound exactly like the right answer.
      const input = box.querySelector<HTMLInputElement>("input")!;
      const check = box.querySelector<HTMLButtonElement>(".runcheck")!;

      const submit = (): void => {
        const typed = input.value.trim();
        if (!typed) return input.focus();
        const right = isCorrect(typed, q.answer);
        input.disabled = true;
        check.remove();
        input.classList.add(right ? "right" : "wrong");
        if (right) {
          reveal(box, q.answer, "Yes —");
        } else if (similarity(typed, q.answer) >= NEAR_ENOUGH) {
          // Close enough that marking up the difference points at something.
          const marks = diff(typed, q.answer)
            .map((r) => (r.same ? esc(r.text) : `<mark>${esc(r.text)}</mark>`)).join("");
          const p = document.createElement("p");
          p.className = "exanswer";
          p.innerHTML = `<span class="runlead">Nearly —</span> `
            + `<span lang="fr" class="fr">${marks}</span>`;
          box.appendChild(p);
          const fr = p.querySelector<HTMLElement>(".fr")!;
          fr.appendChild(speaker(() => spoken(fr.innerHTML), q.answer.slice(0, 40)));
        } else {
          reveal(box, q.answer, "It is");
        }
        mark(q, right, again);
        onward(box);
      };

      check.addEventListener("click", submit);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
      input.focus();
    }

    /* ---------------------------------------------------------- order */

    function showOrder(q: Extract<Question, { k: "order" }>, again: boolean): void {
      const box = card(`
        <p class="exintro">Put the words in order</p>
        <p class="exprompt">${esc(q.en)}</p>
        <p class="exline runline" aria-live="polite"></p>
        <div class="expool"></div>
        <button type="button" class="exbtn runcheck">Check</button>`);
      const line = box.querySelector<HTMLElement>(".runline")!;
      const tray = box.querySelector<HTMLElement>(".expool")!;
      const check = box.querySelector<HTMLButtonElement>(".runcheck")!;
      const placed: string[] = [];

      /**
       * The tiles carry no punctuation — `runqueue.ts` splits a sentence on
       * its own spaces and drops the commas and full stops — so a sentence
       * that ends in one can never be rebuilt from them character for
       * character. Compare with those taken off both sides, exactly as the
       * pack pages' ordering drill does: the task here is the word order,
       * and putting the marks back is its own card.
       *
       * Without this the run cannot be finished. A question got wrong goes
       * to the back of the queue, so an order card that can never be right
       * comes round for ever and the bar stops one short. That is why the
       * check plays a whole run instead of looking at one card: nothing
       * about the card itself looks wrong.
       */
      const unmarked = (t: string) => t.replace(/[.,]/g, "").replace(/\s+/g, " ").trim();

      const draw = (): void => {
        line.textContent = placed.join(" ") || " ";
        // Same rule as the pack pages: nothing to check until every tile is
        // down, so a half-built sentence cannot be marked wrong.
        check.disabled = placed.length < q.tiles.length;
      };
      // No speaker on the tiles: they are the answer's own words, and hearing
      // them is most of the way to hearing the answer.
      for (const word of shuffled(q.tiles)) {
        const t = document.createElement("button");
        t.type = "button";
        t.className = "extile";
        t.textContent = word;
        t.setAttribute("lang", "fr");
        t.addEventListener("click", () => {
          if (t.classList.toggle("placed")) placed.push(word);
          else placed.splice(placed.lastIndexOf(word), 1);
          draw();
        });
        tray.appendChild(t);
      }
      draw();

      check.addEventListener("click", () => {
        if (placed.length < q.tiles.length) return;
        const right = isCorrect(unmarked(placed.join(" ")), unmarked(q.answer));
        for (const t of tray.querySelectorAll("button")) t.disabled = true;
        check.remove();
        line.classList.add(right ? "right" : "wrong");
        reveal(box, q.answer, right ? "Yes —" : "It is");
        mark(q, right, again);
        onward(box);
      });
    }

    /* ------------------------------------------------------------ say */

    /**
     * The one card nothing here can mark.
     *
     * A browser can read the French out, where the device has a French voice,
     * but it cannot hear him back — so this asks for the answer out loud,
     * says plainly that a grown-up has to be the judge of it, and does not
     * touch the score either way. An exercise that marked this by asking him
     * whether he got it right would be a score he awarded himself, which is
     * worth nothing and would quietly sit in the tally as though it were not.
     */
    function showSay(q: Extract<Question, { k: "say" }>): void {
      const box = card(`
        <p class="exintro">Out loud — someone has to listen to this one</p>
        <p class="exprompt"><span lang="fr" class="fr">${esc(q.q)}</span></p>
        <p class="en rungloss">${esc(q.en)}</p>
        <p class="runappraise">Say your answer out loud, in French, before you
        look. Nothing on this page can tell you whether it was any good: a
        teacher or a parent needs to hear it and say so. Ask them whether it
        was understandable, and whether it had the accents and the endings in
        the right places.</p>
        <button type="button" class="exbtn runcheck">Show one way to say it</button>`);
      const ask = box.querySelector<HTMLElement>(".fr")!;
      ask.appendChild(speaker(() => spoken(ask.innerHTML), q.q));

      const check = box.querySelector<HTMLButtonElement>(".runcheck")!;
      check.addEventListener("click", () => {
        check.remove();
        reveal(box, q.a, "One way:");
        // It moves the run on but never the score: see above.
        onward(box, "Next");
      });
    }

    progress();
    show(queue[0]!);
  }
}
