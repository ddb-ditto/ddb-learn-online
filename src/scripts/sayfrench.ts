/**
 * A speaker beside every bit of French the page already declares as French.
 *
 * The pack pages mark their French with `lang="fr"` — the word tables, the
 * countries, the numbers, the five answers, the spellings. That attribute is
 * there for screen readers and it happens to be exactly the right hook: it is
 * a statement, in the markup, that this text is French, made by whoever wrote
 * the template. So there is nothing to guess and nothing to list.
 *
 * It also draws the line round the Italian course for free. Nothing under
 * `/italian/` carries `lang="fr"`, so nothing under `/italian/` gets a
 * speaker, and this module could be loaded there without doing anything.
 *
 * Three things are deliberately *not* marked `lang="fr"` in the templates and
 * so are silent here, each for a reason:
 *
 *   - The pronunciation column — “ko-koo”, “ah”, “bay”. That is English
 *     spelling describing a French sound. Read as French it is nonsense.
 *   - The alphabet's sounds, for the same reason.
 *   - The misspellings in the tricky-spellings pack. Only the correct
 *     spelling is printed, and only the correct spelling speaks.
 *
 * If a future template marks something `lang="fr"` that is not French, it
 * will start speaking. That is the trade for not keeping a list, and
 * `check_site.py` counts the speakers per page so a jump shows up.
 */
import {
  currentVoice, frenchVoices, needsNetwork, onVoicesReady, remember,
  setSpeed, speaker, speedId, SPEEDS, spoken,
} from "./speech";

/**
 * Where a speaker must never go, even inside something marked as French.
 *
 * A heading or a table header is furniture. An input is his to type in. And a
 * nested `lang="fr"` would otherwise get a second speaker from its parent, so
 * only the outermost one is taken.
 */
const NEVER = "h1, h2, h3, h4, th, input, textarea, button, .say, .sayit";

export function attachSpeakers(root: ParentNode = document): number {
  const marked = Array.from(root.querySelectorAll<HTMLElement>('[lang="fr"]'));
  let made = 0;

  for (const node of marked) {
    if (node.matches(NEVER)) continue;
    if (node.closest(NEVER)) continue;
    // Only the outermost French element in a nest: a speaker on both a
    // sentence and a word inside it reads the sentence twice.
    if (marked.some((other) => other !== node && other.contains(node))) continue;
    // Nothing to say.
    const text = spoken(node.innerHTML);
    if (!text) continue;

    node.appendChild(speaker(() => spoken(node.innerHTML), text.slice(0, 40)));
    made++;
  }
  return made;
}

/**
 * Fill in and switch on the audio controls, once it is known there is a voice.
 *
 * The row is hidden in the markup and only appears here, so a device with no
 * French voice never sees a speed control for audio that will not play — the
 * same rule the speakers themselves follow. The voice half appears only where
 * there is more than one to choose between.
 */
function attachControls(): void {
  const row = document.getElementById("fraudio");
  const speed = document.getElementById("fr-speed") as HTMLSelectElement | null;
  if (!row || !speed) return;

  let built = false;
  onVoicesReady(() => {
    const voices = frenchVoices();
    if (!voices.length) return;                  // nothing speaks; nothing to set
    // Told again every time the voice list changes, so this has to be safe to
    // run twice: without the guard a second announcement would append a second
    // set of options to both menus.
    if (built) return;
    built = true;

    for (const s of SPEEDS) {
      const o = document.createElement("option");
      o.value = s.id;
      o.textContent = s.label;
      o.selected = s.id === speedId();
      speed.appendChild(o);
    }
    speed.addEventListener("change", () => {
      setSpeed(speed.value);
      // Say something in the new speed, so choosing is also hearing.
      const voice = currentVoice();
      const sample = document.querySelector<HTMLElement>('[lang="fr"]');
      if (voice && sample) {
        import("./speech").then((m) => m.speak(spoken(sample.innerHTML), voice));
      }
    });

    const wrap = document.getElementById("fr-voicewrap");
    const pick = document.getElementById("fr-voice") as HTMLSelectElement | null;
    if (wrap && pick && voices.length > 1) {
      const chosen = currentVoice();
      for (const v of voices) {
        const o = document.createElement("option");
        o.value = v.name;
        o.textContent = v.name + (needsNetwork(v) ? " (needs wi-fi)" : "");
        o.selected = chosen !== null && v.name === chosen.name;
        pick.appendChild(o);
      }
      pick.addEventListener("change", () => {
        remember(pick.value);
        const voice = currentVoice();
        const sample = document.querySelector<HTMLElement>('[lang="fr"]');
        if (voice && sample) {
          import("./speech").then((m) => m.speak(spoken(sample.innerHTML), voice));
        }
      });
      wrap.hidden = false;
    }

    row.hidden = false;
  });
}

attachSpeakers();
attachControls();
