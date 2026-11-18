#!/usr/bin/env python3
"""Open the built site in a browser and use it.

    npm run build
    pip install playwright && playwright install chromium
    python3 tools/check_site.py

A page that throws a JavaScript error is a broken deck, and the failure is
silent until a child hits it. So this drives the real thing at phone width: the
contents page, a lesson, the record sheets, and the flashcard app — that it
opens on card one unshuffled, flips, wraps at both ends, switches decks, and
builds its print sheets.

It serves `dist/` over HTTP under the same base path Pages uses, because that
base path is part of what can break.
"""
import functools
import http.server
import os
import pathlib
import re
import json
import socketserver
import sys
import threading
import unicodedata

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
DIST = REPO / "dist"
BASE = "/italian-gcse"

if not (DIST / "index.html").exists():
    sys.exit("dist/ is not built — run `npm run build` first")

fails: list[str] = []
notes: list[str] = []


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve dist/ as though it were at BASE, the way Pages does."""

    def translate_path(self, path: str) -> str:
        if path.startswith(BASE):
            path = path[len(BASE):] or "/"
        return super().translate_path(path)

    def log_message(self, *args) -> None:
        pass


# Threaded: the browser holds connections open, and a single-threaded server
# blocks on one of them as soon as the checks navigate more than a few times.
class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


httpd = Server(("127.0.0.1", 0), functools.partial(Handler, directory=str(DIST)))
threading.Thread(target=httpd.serve_forever, daemon=True).start()
ROOT = f"http://127.0.0.1:{httpd.server_address[1]}{BASE}"

def find_chromium() -> dict:
    """Where the browser is, if it is anywhere.

    Playwright lays its downloads out differently depending on the version and
    the platform, and a machine that has a browser but not at the path this
    guessed reports "no browser" — which the runner then counts as skipped
    rather than failed, so the site goes unchecked and nothing says so. Hence
    the list: `chrome-linux64` and `chrome-linux` have both been the layout,
    and some images put a plain executable at the root.
    """
    if os.environ.get("CHROMIUM"):
        return {"executable_path": os.environ["CHROMIUM"]}
    root = pathlib.Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    patterns = (
        "chromium*/chrome-linux64/chrome",
        "chromium*/chrome-linux/chrome",
        "chromium*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
    )
    for pattern in patterns:
        for found in sorted(root.glob(pattern), reverse=True):
            if found.is_file():
                return {"executable_path": str(found)}
    direct = root / "chromium"
    if direct.is_file() and os.access(direct, os.X_OK):
        return {"executable_path": str(direct)}
    return {}        # let Playwright try its own default, and say so if it cannot


with sync_playwright() as pw:
    try:
        b = pw.chromium.launch(**find_chromium())
    except Exception as why:                       # no browser on this machine
        print(f"No browser to drive: {str(why).splitlines()[0]}")
        print("Install one with `playwright install chromium`. Nothing was checked.")
        httpd.shutdown()
        sys.exit(2)
    page = b.new_page(viewport={"width": 390, "height": 844})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    def wide() -> int:
        return page.evaluate("document.body.scrollWidth")

    # --- contents page -----------------------------------------------------
    page.goto(f"{ROOT}/")
    notes.append(f"contents h1: {page.locator('h1').first.inner_text()!r}")
    notes.append(f"contents cards: {page.locator('.cardlink').count()}")
    if wide() > 390:
        fails.append(f"contents page scrolls sideways at 390px ({wide()}px)")
    if page.locator("a[href*='.pdf']").count():
        fails.append("PDF link on contents page")
    if not page.locator("a[href$='/progress/']").count():
        fails.append("no link to the progress page from contents")

    # The mark introduces the site once. Above a lesson it would compete with
    # the material, so it belongs to the contents page and nowhere else.
    mark = page.locator(".logomark")
    if mark.count() != 1:
        fails.append(f"contents page has {mark.count()} logos, expected 1")
    else:
        box = mark.bounding_box()
        notes.append(f"logo: {round(box['width'])}x{round(box['height'])}px")
        if not (mark.get_attribute("alt") or "").strip():
            fails.append("the logo has no alt text")
        if box["width"] < 80:
            fails.append(f"the logo renders at {round(box['width'])}px wide")

    # --- the record sheets -------------------------------------------------
    page.goto(f"{ROOT}/progress/")
    sheets = page.locator(".sheet").count()
    boxes = page.locator(".sheet .box").count()
    notes.append(f"record sheets: {sheets}, tick boxes: {boxes}")
    if sheets < 1:
        fails.append("no record sheet on the progress page")
    if boxes < 10:
        fails.append(f"only {boxes} tick boxes across the sheets")
    if page.locator(".sheet input").count():
        fails.append("the sheets have form controls — they are paper, nothing is stored")
    if wide() > 390:
        fails.append("progress page scrolls sideways at 390px")

    # every session and every can-do of unit 1 has its own box
    unit1 = page.locator("#unit-1")
    if unit1.count() and unit1.locator(".box").count() != 10:
        fails.append(f"unit 1 sheet has {unit1.locator('.box').count()} boxes, expected 10")

    # --- the reference pages -----------------------------------------------
    for slug in ("teaching-plan", "stage-1-units-1-14", "grammar-checklist"):
        page.goto(f"{ROOT}/reference/{slug}/")
        h1 = page.locator("h1").first.inner_text()
        notes.append(f"reference/{slug}: {h1!r}")
        if not h1.strip():
            fails.append(f"reference/{slug} has no heading")
        if page.locator("main").inner_text().count("<") > 2:
            fails.append(f"reference/{slug} is showing raw markup")
        if wide() > 390:
            fails.append(f"reference/{slug} scrolls sideways at 390px")

    # --- the trail, on every page below the contents ------------------------
    # The pages are long, so a link that only exists in the footer is not
    # navigation: the trail has to still be on screen once you have scrolled.
    for path, expected in (
        ("/units/1/", "Contents › Unit 01"),
        ("/units/1/sessions/2/", "Contents › Unit 01 › Session 2"),
        ("/units/1/sessions/2/cards/", "Contents › Unit 01 › Session 2 › Flashcards"),
        ("/progress/", "Contents › Progress"),
        ("/reference/teaching-plan/", "Contents › Teaching plan"),
    ):
        page.goto(f"{ROOT}{path}")
        crumbs = page.locator(".crumbs li")
        got = " › ".join(crumbs.all_inner_texts())
        if got != expected:
            fails.append(f"{path} trail is {got!r}, expected {expected!r}")
    notes.append(f"breadcrumb trails checked on 5 pages, deepest: {got!r}")

    page.goto(f"{ROOT}/units/1/sessions/2/")
    page.evaluate("window.scrollTo(0, 1400)")
    page.wait_for_timeout(200)
    stuck = page.locator(".crumbs").bounding_box()
    if not stuck or round(stuck["y"]) != 0:
        fails.append("the breadcrumb does not stay on screen when the page scrolls")
    page.locator(".crumbs a:has-text('Unit 01')").click()
    page.wait_for_load_state()
    if "sound of it" not in page.locator("h1").first.inner_text():
        fails.append("the breadcrumb's unit link does not go to the unit")

    # --- a unit, then a lesson ---------------------------------------------
    page.goto(f"{ROOT}/units/1/")
    rows = page.locator(".sessionrow").count()
    notes.append(f"unit 1 session rows: {rows}")
    if rows != 5:
        fails.append(f"unit 1 has {rows} session rows, expected 5")

    # The unit file and the template both used to render the can-do list, its
    # heading and the insist note, so the page carried each of them twice.
    headings = page.locator("main h2").all_inner_texts()
    duplicated = {h for h in headings if headings.count(h) > 1}
    notes.append(f"unit 1 sections: {len(headings)}")
    if duplicated:
        fails.append(f"unit page renders a section twice: {sorted(duplicated)}")
    candos = page.locator("main .plain li").all_inner_texts()
    repeated = {c for c in candos if candos.count(c) > 1}
    if repeated:
        fails.append(f"unit page lists the same item twice: {sorted(repeated)[:2]}")

    # The can-do heading counts to the next unit. It used to count past the end.
    units = len(json.loads((REPO / "src/data/stage1.json").read_text(encoding="utf-8")))
    for h in headings:
        m = re.search(r"BEFORE UNIT (\d+)", h.upper())
        if m and int(m.group(1)) > units:
            fails.append(f"unit page points at Unit {m.group(1)}, past the last "
                         f"unit of Stage 1 ({units})")

    page.goto(f"{ROOT}/units/1/sessions/2/")
    if "hard and soft" not in page.title():
        fails.append(f"session 2 title wrong: {page.title()!r}")
    if wide() > 390:
        fails.append("session page scrolls sideways at 390px")

    # The deck is the point of the session, so its link is above the content
    # and opens beside it rather than navigating away from the lesson.
    cue = page.locator(".deckcue")
    if not cue.count():
        fails.append("no flashcards link at the top of the session page")
    else:
        top = page.evaluate("document.querySelector('.deckcue').getBoundingClientRect().top")
        notes.append(f"deck link at y={round(top)}: {cue.inner_text()!r}")
        if top > 400:
            fails.append(f"flashcards link is not immediately visible (y={round(top)})")
        if cue.get_attribute("target") != "_blank":
            fails.append("flashcards link does not open in a new tab")

    # --- the flashcard app -------------------------------------------------
    page.goto(f"{ROOT}/units/1/sessions/1/cards/")
    page.wait_for_selector("#decks .chip")
    decks = page.locator("#decks .chip").all_inner_texts()
    notes.append(f"decks: {decks}")

    # The chips are built by the script, so they do not carry the scope
    # attribute and their styles have to be written to reach them. When that
    # breaks nothing throws — the chips just render as bare buttons reading
    # "Vowels5" — so it is asserted rather than eyeballed.
    chip = page.evaluate('''() => {
      const c = document.querySelector(".chip");
      const n = document.querySelector(".chip .n");
      const on = document.querySelector('.chip[aria-pressed="true"]');
      return {
        radius: parseFloat(getComputedStyle(c).borderRadius),
        gap: parseFloat(getComputedStyle(n).marginLeft),
        selected: getComputedStyle(on).backgroundColor,
      };
    }''')
    notes.append(f"chip: radius {chip['radius']}px, count gap {chip['gap']}px")
    if chip["radius"] < 20:
        fails.append("deck chips are not styled — scoped CSS is not reaching them")
    if chip["gap"] < 2:
        fails.append("no gap between a deck name and its count (renders as 'Vowels5')")
    if chip["selected"] in ("rgba(0, 0, 0, 0)", "transparent"):
        fails.append("the selected deck chip is not highlighted")
    first_face = page.locator("#face").inner_text()
    pos = page.locator("#position").inner_text()
    notes.append(f"opens on: {first_face!r} at {pos!r}")
    if not pos.startswith("1"):
        fails.append(f"deck does not open on card 1 ({pos})")

    page.locator("#card").click()                      # flip
    back = page.locator("#face").inner_text()
    if back == first_face:
        fails.append("card does not flip")
    notes.append(f"back of card 1: {back.splitlines()[0]!r}")

    page.locator("#next").click()
    if page.locator("#face").inner_text() == first_face:
        fails.append("forward arrow does not advance")
    page.locator("#prev").click(); page.locator("#prev").click()
    wrapped = page.locator("#position").inner_text()
    notes.append(f"wraps backwards to: {wrapped!r}")
    if not wrapped.startswith("5"):
        fails.append(f"arrows do not wrap ({wrapped})")

    page.locator("#decks .chip").nth(1).click()        # switch deck
    notes.append(f"after deck switch: {page.locator('#position').inner_text()!r}")
    if not page.locator("#position").inner_text().startswith("1"):
        fails.append("deck switch does not reset to card 1")

    total = sum(int(re.search(r"(\d+)$", d).group(1)) for d in decks)
    notes.append(f"cards in this deck page: {total}")
    if total != 15:
        fails.append(f"expected 15 cards, found {total}")

    # --- English first, where it means anything -----------------------------
    # It reverses a word card so the English is the prompt. A rule deck has no
    # such side, and a deck that answers five words with one sentence reverses
    # into five identical prompts, so the control is only offered where it
    # does something. Offering it everywhere is what made it look broken.
    page.goto(f"{ROOT}/units/2/sessions/1/cards/")
    page.wait_for_selector("#decks .chip")
    page.locator("#decks .chip").first.click()          # the rule deck
    if page.locator("#reversewrap").is_visible():
        fails.append("English first is offered on a deck of rule cards")

    page.locator("#decks .chip").nth(1).click()         # a word deck
    if not page.locator("#reversewrap").is_visible():
        fails.append("English first is not offered on a deck of word cards")
    else:
        forward = page.locator("#face").inner_text().strip()
        page.locator("#reverse").check()
        reversed_front = page.locator("#face").inner_text().strip()
        page.locator("#card").click()
        reversed_back = page.locator("#face").inner_text().splitlines()[0].strip()
        notes.append(f"English first: {forward!r} becomes {reversed_front!r}")
        if reversed_front == forward:
            fails.append("English first does not change the prompt")
        if reversed_back != forward:
            fails.append(f"English first shows {reversed_back!r} on the back, "
                         f"expected {forward!r}")
        page.locator("#decks .chip").first.click()      # back to the rule deck
        if page.locator("#reverse").is_checked():
            fails.append("English first stays ticked on a deck it cannot apply to")

    # The stress deck answers every card with the same sentence.
    page.goto(f"{ROOT}/units/1/sessions/4/cards/")
    page.wait_for_selector("#decks .chip")
    page.locator("#decks .chip:has-text('Stress')").click()
    if page.locator("#reversewrap").is_visible():
        fails.append("English first is offered on a deck whose answers are all the same")

    page.goto(f"{ROOT}/units/1/sessions/1/cards/")
    page.wait_for_selector("#decks .chip")

    # --- print view --------------------------------------------------------
    page.emulate_media(media="print")
    printed = page.locator(".printsheets .sheet").count()
    notes.append(f"print sheets: {printed}")
    if printed < 2:
        fails.append("print sheets not built")
    page.emulate_media(media="screen")

    # --- every icon and the manifest resolve under the base path ------------
    for sel in ("link[rel=manifest]", "link[rel=icon][sizes='32x32']",
                "link[rel=icon][sizes='16x16']", "link[rel=apple-touch-icon]"):
        href = page.get_attribute(sel, "href")
        if not href:
            fails.append(f"no {sel} on the page")
            continue
        got = page.request.get(f"http://127.0.0.1:{httpd.server_address[1]}{href}")
        notes.append(f"{sel.split('[')[0]} {href.rsplit('/',1)[-1]} → {got.status}")
        if got.status != 200:
            fails.append(f"{sel} does not resolve ({href})")

    # ----------------------------------------------------------------------
    # Year 7 French
    # ----------------------------------------------------------------------

    page.goto(f"{ROOT}/french/year-7/")
    tests = page.locator(".testcard").count()
    packs = page.locator(".cardlink").count()
    notes.append(f"french hub: {tests} test card(s), {packs} pack card(s)")
    if tests != 2:
        fails.append(f"the French hub shows {tests} tests, expected 2")
    if packs != 10:
        fails.append(f"the French hub shows {packs} packs, expected 10")
    if wide() > 390:
        fails.append(f"the French hub scrolls sideways at 390px ({wide()}px)")
    stamps = page.locator(".countdown time").count()
    if stamps < 2:
        fails.append("a test card has no date on it")

    page.goto(f"{ROOT}/french/year-7/packs/tricky-spellings/")
    ready = page.locator(".exercise.ready").count()
    written = page.locator(".exercise").count()
    notes.append(f"tricky spellings: {ready} of {written} exercise(s) booted")
    if written == 0:
        fails.append("the tricky spellings pack has no exercises")
    if ready != written:
        fails.append(f"{written - ready} exercise(s) did not start")

    # The exercises are built by script, so their styling hangs off .exercise
    # rather than reaching them directly — the same trap the deck chips fell
    # into. An unstyled button is not invisible, it is the browser's own grey
    # one, so this compares the paint with the site's accent rather than only
    # asking whether anything was painted. Checked both ways against the bug:
    # with the rule written as `.exercise :global(.exbtn)` — which is Astro
    # <style> syntax and not valid in a plain stylesheet — the button comes
    # back rgb(239,239,239) and this fails, as it should.
    painted = page.evaluate("""() => {
      const b = document.querySelector('.exercise .exbtn');
      if (!b) return null;
      const accent = getComputedStyle(document.documentElement)
          .getPropertyValue('--accent').trim();
      const probe = document.createElement('div');
      probe.style.color = accent;
      document.body.appendChild(probe);
      const want = getComputedStyle(probe).color;
      probe.remove();
      return { got: getComputedStyle(b).backgroundColor, want };
    }""")
    if painted is None:
        fails.append("no exercise button to check the styling of")
    else:
        notes.append(f"exercise button: {painted['got']} (accent {painted['want']})")
        if painted["got"] != painted["want"]:
            fails.append(f"exercise buttons are unstyled — {painted['got']}, "
                         f"expected the accent {painted['want']}")

    # Strict marking, driven the way he would drive it.
    #
    # The punctuation drill is the one used rather than the spelling drill,
    # because it is not shuffled: its second item is always `ca va` → `Ça va ?`
    # So the near miss below is always a real near miss. Driving the shuffled
    # drill instead meant the accent was only tested when the random pick
    # happened to produce an accented word, and a check that sometimes does
    # nothing reads exactly like one that passed.
    page.goto(f"{ROOT}/french/year-7/packs/greetings/")
    wd = page.locator("#ex-w-d")
    if wd.count() == 0:
        fails.append("the greetings pack has no punctuation drill")
    else:
        items = page.evaluate("""() => JSON.parse(
            document.querySelector('#ex-w-d .ex-data').textContent).items""")

        def drill(answer: str) -> str:
            wd.locator(".exinput").fill(answer)
            wd.get_by_text("Check").click()
            return wd.locator(".exresult").inner_text()

        said = drill(items[0]["answer"])
        notes.append(f"punctuation drill: {items[0]['answer']!r} → {said.splitlines()[0]!r}")
        if "Correct" not in said:
            fails.append(f"the right answer {items[0]['answer']!r} was marked wrong: {said!r}")

        wd.get_by_text("Next").click()
        want = items[1]["answer"]                       # "Ça va ?"
        flat = (unicodedata.normalize("NFD", want)
                .encode("ascii", "ignore").decode("ascii"))
        if flat == want:
            fails.append(f"the near-miss item {want!r} has no accent to drop — "
                         "this check is no longer checking anything")
        else:
            said = drill(flat)
            notes.append(f"near miss: {flat!r} → {said.splitlines()[0]!r}")
            if "Correct" in said:
                fails.append(f"{flat!r} was accepted — the writing test marks accents")
            marks = wd.locator("mark").all_inner_texts()
            notes.append(f"marked as missing: {marks}")
            if not marks:
                fails.append("a wrong answer does not show what was missing")

        # And the two things that are forgiven, because they are the keyboard
        # rather than the French.
        page.reload()
        wd = page.locator("#ex-w-d")
        forgiving = items[0]["answer"].replace("'", "\u2019").replace(" !", "!")
        if forgiving != items[0]["answer"]:
            wd.locator(".exinput").fill(forgiving)
            wd.get_by_text("Check").click()
            said = wd.locator(".exresult").inner_text()
            notes.append(f"curly apostrophe: {forgiving!r} → {said.splitlines()[0]!r}")
            if "Correct" not in said:
                fails.append(f"{forgiving!r} was rejected — a curly apostrophe and "
                             "a missing space before ! are keyboard differences")

    # A pack's cards are worked out from its word list, so they cannot drift
    # from it — but they do have to arrive.
    page.goto(f"{ROOT}/french/year-7/packs/countries/cards/")
    chips = page.locator(".chip").count()
    notes.append(f"countries deck chips: {chips}")
    if chips != 2:
        fails.append(f"the countries pack shows {chips} decks, expected 2")
    face = page.locator("#face").inner_text()
    page.locator("#card").click()
    if page.locator("#face").inner_text() == face:
        fails.append("a French card does not turn over")
    if page.locator("#printsheets .sheet").count() == 0:
        fails.append("the French cards build no print sheets")

    # A test page lists its packs in its own order, not in number order.
    page.goto(f"{ROOT}/french/year-7/tests/writing/")
    first = page.locator(".cardlink .t").first.inner_text()
    notes.append(f"writing test, first pack: {first!r}")
    if "Tricky" not in first:
        fails.append(f"the writing test opens with {first!r}, not the tricky spellings")

    # The logo belongs to one page.
    page.goto(f"{ROOT}/units/1/sessions/2/")
    if page.locator(".logomark").count():
        fails.append("the logo is on a lesson page, not just the contents page")

    b.close()

httpd.shutdown()

print("\n".join("  " + n for n in notes))
if errors:
    print("\nCONSOLE / PAGE ERRORS:")
    for e in errors:
        print("  " + e)
    fails.append(f"{len(errors)} JavaScript error(s)")
print()
if fails:
    print("FAILED:")
    for f in fails:
        print("  ✗ " + f)
    sys.exit(1)
print("all checks passed")
