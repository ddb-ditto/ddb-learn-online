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
 * Say it.
 *
 * Slower than the default, which is a conversational pace — too quick to copy
 * when the whole exercise is copying it. 0.9 is still natural; below about
 * 0.75 the synthesiser starts to distort the vowels, which defeats the object.
 */
export const RATE = 0.9;

export function speak(text: string, voice: SpeechSynthesisVoice): void {
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  // Set alongside the voice: some engines consult `lang` for prosody even when
  // a voice is named, and a mismatch between the two is read as a conflict.
  u.lang = voice.lang;
  u.rate = RATE;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(u);
}
