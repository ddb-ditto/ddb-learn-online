/**
 * Choosing the voice that reads the French aloud.
 *
 * The browser's speech synthesiser reads with whatever voices the *device*
 * has. A static site cannot ship a voice, so all this module can do is pick
 * the best of what is there — and, just as importantly, refuse to speak when
 * what is there is not French.
 *
 * That refusal is the point. `utterance.lang = "fr-FR"` is a hint, not a
 * guarantee: a device with English voices and no French one will happily read
 * *Comment tu t'appelles ?* in an English accent, which is worse than silence
 * in a pronunciation drill. The old code checked only whether the browser had
 * a speech API at all — true in every modern browser — so it offered the
 * button on a machine with no voices whatsoever, where pressing it did
 * nothing at all. That was verified in a browser with none installed: the
 * button rendered, visible, `display: block`, and silent.
 *
 * Nothing here is a judgement about his progress and nothing leaves the
 * device. The one thing stored is which voice was chosen, under the same
 * `fr7:` prefix as the reading switch, and losing it just means the device
 * default again.
 */

/** Only a voice the device labels as French will ever be used. */
const isFrench = (v: SpeechSynthesisVoice): boolean =>
  v.lang.toLowerCase().replace("_", "-").startsWith("fr");

/**
 * Voices worth preferring over the device default, best first.
 *
 * Matched as a substring of the voice name, because the same voice is
 * labelled differently across versions — "Thomas" is "Thomas" on one macOS
 * and "Thomas (Enhanced)" on another. Everything here is a named French
 * voice shipped by Apple, Google or Microsoft; a device with none of them
 * still gets its own French default, which is the next line down.
 */
const PREFERRED = [
  // Apple: iOS, iPadOS and macOS. The enhanced variants are markedly better
  // than the compact ones and carry the same first name, so a substring match
  // picks up whichever is installed.
  "Thomas", "Amélie", "Amelie", "Audrey", "Aurélie", "Aurelie", "Marie",
  // Android, and Chrome on the desktop. Needs the network — see `needsNetwork`.
  "Google français", "Google francais",
  // Windows.
  "Microsoft Denise", "Microsoft Henri", "Microsoft Julie",
  "Microsoft Paul", "Microsoft Hortense",
];

/** Every French voice the device has, preferred ones first. */
export function frenchVoices(): SpeechSynthesisVoice[] {
  if (!("speechSynthesis" in window)) return [];
  const all = window.speechSynthesis.getVoices().filter(isFrench);
  const rank = (v: SpeechSynthesisVoice): number => {
    const i = PREFERRED.findIndex((name) => v.name.includes(name));
    return i === -1 ? PREFERRED.length : i;
  };
  return all.sort((a, b) => rank(a) - rank(b));
}

/**
 * A voice that is not on the device has to be fetched to speak, so it is
 * silent on a train. Worth saying out loud rather than looking broken.
 */
export const needsNetwork = (v: SpeechSynthesisVoice): boolean => !v.localService;

/** The `fr7:` key holding the chosen voice's name. Only a name is stored. */
const KEY = "fr7:voice";

const remembered = (): string | null => {
  try { return window.localStorage.getItem(KEY); } catch { return null; }
};

export const remember = (name: string): void => {
  try { window.localStorage.setItem(KEY, name); } catch { /* holds for this page */ }
};

/** The voice to use: the remembered one if it is still installed, else the best. */
export function chosenVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  if (!voices.length) return null;
  const name = remembered();
  return (name && voices.find((v) => v.name === name)) || voices[0]!;
}

/**
 * Run `ready` once the voice list is populated, or once it is clear there is
 * nothing coming.
 *
 * `getVoices()` returns an empty array on the first call in Chrome and fills
 * in later, announced by `voiceschanged`. A browser with genuinely no voices
 * never fires that event, and so would leave a caller waiting forever — hence
 * the timeout, after which an empty list is the honest answer and the button
 * stays hidden.
 */
export function whenVoicesReady(ready: () => void, waitMs = 1500): void {
  if (!("speechSynthesis" in window)) { ready(); return; }
  if (window.speechSynthesis.getVoices().length) { ready(); return; }

  let done = false;
  const once = () => {
    if (done) return;
    done = true;
    window.speechSynthesis.removeEventListener("voiceschanged", once);
    ready();
  };
  window.speechSynthesis.addEventListener("voiceschanged", once);
  window.setTimeout(once, waitMs);
}

/**
 * How fast it reads, as a setting rather than a number chosen here.
 *
 * It used to be a constant at 0.9, with a comment saying that below about
 * 0.75 the synthesiser starts to distort the vowels. That comment was written
 * from general knowledge and never tested — it could not be, since the
 * machine these tools run on has no speech voices at all — so it has been
 * taken out rather than left standing as though it were measured.
 *
 * Which is also the argument for a control instead of a better guess. The
 * right speed depends on the voice the device happens to have and on how much
 * French the listener already knows, and neither is knowable from here. Three
 * steps, because a slider invites fiddling and the difference between 0.70
 * and 0.72 is not a difference anybody can hear.
 */
export const SPEEDS = [
  { id: "normal", label: "Normal", rate: 0.9 },
  { id: "slow", label: "Slower", rate: 0.75 },
  { id: "slowest", label: "Slowest", rate: 0.6 },
] as const;

/** Slower is the default: it is what was asked for, and it is easier to
 *  follow a word you already know at a crawl than to miss one at speed. */
const DEFAULT_SPEED = "slow";
const RATE_KEY = "fr7:rate";

export function speedId(): string {
  let stored: string | null = null;
  try { stored = window.localStorage.getItem(RATE_KEY); } catch { /* no storage */ }
  return SPEEDS.some((s) => s.id === stored) ? stored! : DEFAULT_SPEED;
}

export function setSpeed(id: string): void {
  if (!SPEEDS.some((s) => s.id === id)) return;
  try { window.localStorage.setItem(RATE_KEY, id); } catch { /* holds for this page */ }
}

/** The rate to speak at now, read at the press so a change takes effect at once. */
export const rate = (): number =>
  (SPEEDS.find((s) => s.id === speedId()) ?? SPEEDS[1]).rate;

export function speak(text: string, voice: SpeechSynthesisVoice): void {
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  // Set alongside the voice: some engines consult `lang` for prosody even when
  // a voice is named, and a mismatch between the two is read as a conflict.
  u.lang = voice.lang;
  u.rate = rate();
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}

/* -------------------------------------------------------------- the speakers */

/**
 * One wait, shared.
 *
 * A pack page can carry fifty French words, each with its own speaker. Each
 * one calling `whenVoicesReady` would attach fifty `voiceschanged` listeners
 * and set fifty timers for the same answer, so the wait happens once and
 * everybody is told.
 */
let waiting: (() => void)[] | null = [];

export function onVoicesReady(fn: () => void): void {
  if (waiting === null) { fn(); return; }        // already settled
  waiting.push(fn);
  if (waiting.length > 1) return;                // somebody is already waiting
  whenVoicesReady(() => {
    const queue = waiting!;
    waiting = null;
    for (const f of queue) f();
  });
}

/**
 * The voice everything on the page speaks with, re-read each time so that
 * choosing one in the picker changes every speaker at once rather than only
 * the exercise the picker happens to sit in.
 */
export const currentVoice = (): SpeechSynthesisVoice | null => chosenVoice(frenchVoices());

/**
 * A speaker, drawn rather than written.
 *
 * It replaces a button reading "♪ Hear it". That wording was fine beside one
 * question and wrong everywhere else: the point is to hear *this* word, and a
 * sentence of English instruction beside each of fifty French words is noise
 * in a section whose reading switch exists precisely to remove noise. So the
 * label is for screen readers and the sighted reader gets a glyph.
 *
 * Inline SVG rather than 🔊, which is a different drawing on every platform,
 * is coloured whatever the vendor chose, and cannot be dimmed to sit quietly
 * beside the word it belongs to.
 *
 * `text` is read at the moment of the press, not when the button is made, so
 * a speaker attached to something that changes — the card on screen, the
 * answer just revealed — says what is there now.
 */
const GLYPH = `<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
<path d="M8.6 2.3 4.9 5.2H2.4v5.6h2.5l3.7 2.9z" fill="currentColor"/>
<path d="M11 5.8a3.1 3.1 0 0 1 0 4.4" fill="none" stroke="currentColor"
      stroke-width="1.4" stroke-linecap="round"/>
<path d="M12.9 3.7a5.6 5.6 0 0 1 0 8.6" fill="none" stroke="currentColor"
      stroke-width="1.4" stroke-linecap="round"/></svg>`;

export function speaker(text: () => string, what?: string): HTMLButtonElement {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "sayit";
  b.innerHTML = GLYPH;
  // A page of these needs each one to say what it reads, or a screen reader
  // gets fifty buttons all called "Hear it".
  b.setAttribute("aria-label", what ? `Hear “${what}” in French` : "Hear it in French");
  // Hidden until there is a French voice to say it with, and hidden for good
  // if there is not. Same rule as the button it replaces: silence beats an
  // English accent.
  b.hidden = true;
  onVoicesReady(() => {
    const voice = currentVoice();
    if (!voice) return;
    b.hidden = false;
  });
  b.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();                         // never turn the card over
    const voice = currentVoice();
    const say = text().trim();
    if (voice && say) speak(say, voice);
  });
  return b;
}

/**
 * Strip what is on the page for the eye but not for the ear.
 *
 * Pack text carries `<em>` and `<strong>`; the reading-practice answers join
 * their words with a middle dot, which a synthesiser either names or stumbles
 * over. The flag on a country is decoration. None of it is French.
 */
export function spoken(html: string): string {
  const box = document.createElement("div");
  box.innerHTML = html;
  for (const n of box.querySelectorAll("[aria-hidden='true'], .flag, .sayit")) n.remove();
  return (box.textContent ?? "")
    .replace(/[·•]/g, ", ")
    .replace(/ | /g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
