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
import traceback
import unicodedata

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parent.parent
DIST = REPO / "dist"

if not (DIST / "index.html").exists():
    sys.exit("dist/ is not built — run `npm run build` first")

# The base path is whatever the build used, read back out of the build rather
# than written down twice. It follows the repository's name, so a rename moves
# it — and a checker that insisted on the old one would fail everything and
# say nothing useful about why.
_asset = re.search(r'href="(/[^"]*?)/_astro/', (DIST / "index.html").read_text(encoding="utf-8"))
BASE = _asset.group(1) if _asset else ""

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
    # A step that throws — a selector that times out because the thing it
    # drives is gone — used to end the run on a stack trace, losing every
    # finding made before it and saying nothing useful about the one that
    # mattered. A crash is a finding too, so it is caught and reported with
    # the rest.
    try:

        def wide() -> int:
            return page.evaluate("document.body.scrollWidth")

        # --- the front door ----------------------------------------------------
        # Two choices and nothing else. Both have to be here and both have to go
        # somewhere: a door that 404s is worse than no door.
        page.goto(f"{ROOT}/")
        notes.append(f"front page h1: {page.locator('h1').first.inner_text()!r}")
        doors = page.locator(".doors .door")
        notes.append(f"doors: {doors.count()} — {doors.all_inner_texts()!r}"[:120])
        if doors.count() != 2:
            fails.append(f"the front page offers {doors.count()} doors, expected 2")
        for n in range(doors.count()):
            href = doors.nth(n).get_attribute("href")
            got = page.request.get(f"http://127.0.0.1:{httpd.server_address[1]}{href}")
            if got.status != 200:
                fails.append(f"door {n + 1} goes to {href}, which is {got.status}")
        if wide() > 390:
            fails.append(f"front page scrolls sideways at 390px ({wide()}px)")
        if page.locator("a[href*='.pdf']").count():
            fails.append("PDF link on the front page")

        # --- the Italian contents, where the front page used to be -------------
        page.goto(f"{ROOT}/italian/")
        notes.append(f"italian contents cards: {page.locator('.cardlink').count()}")
        if page.locator(".cardlink").count() < 15:
            fails.append("the Italian contents page lost its cards")
        if not page.locator("a[href$='/progress/']").count():
            fails.append("no link to the progress page from the Italian contents")
        if wide() > 390:
            fails.append(f"the Italian contents scroll sideways at 390px ({wide()}px)")

        # Two marks, each on the one page it belongs to. The DDB wordmark is
        # the site's, so it goes on the front door; the GCSE Italian roundel
        # says so on its face, so it stays on the Italian contents page. Above
        # a lesson either would compete with the material.
        page.goto(f"{ROOT}/")
        site_mark = page.locator(".logomark.is-site")
        if site_mark.count() != 1:
            fails.append(f"the front door has {site_mark.count()} site logos, expected 1")
        else:
            box = site_mark.bounding_box()
            notes.append(f"site logo: {round(box['width'])}x{round(box['height'])}px, "
                         f"alt {site_mark.get_attribute('alt')!r}")
            if box["width"] < 120:
                fails.append(f"the site logo renders at {round(box['width'])}px wide")
            if "italian" in (site_mark.get_attribute("alt") or "").lower():
                fails.append("the site logo's alt text still names one subject")

        # The manifest used to be a static file carrying the old repository
        # name, so a rename broke the installed app and nothing said a word.
        manifest = page.request.get(
            f"http://127.0.0.1:{httpd.server_address[1]}{BASE}/manifest.webmanifest")
        if manifest.status != 200:
            fails.append(f"the manifest is {manifest.status}")
        else:
            data = json.loads(manifest.text())
            notes.append(f"manifest start_url: {data['start_url']!r}")
            for field in ("start_url", "scope"):
                if not data[field].startswith(BASE):
                    fails.append(f"the manifest's {field} is {data[field]!r}, "
                                 f"not under {BASE}")
            for ico in data["icons"]:
                got = page.request.get(
                    f"http://127.0.0.1:{httpd.server_address[1]}{ico['src']}")
                if got.status != 200:
                    fails.append(f"the manifest names {ico['src']}, which is {got.status}")

        page.goto(f"{ROOT}/italian/")
        mark = page.locator(".logomark")
        if mark.count() != 1:
            fails.append(f"the Italian contents page has {mark.count()} logos, expected 1")
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
            ("/italian/", "Home › Italian"),
            ("/units/1/", "Home › Italian › Unit 01"),
            ("/units/1/sessions/2/", "Home › Italian › Unit 01 › Session 2"),
            ("/units/1/sessions/2/cards/", "Home › Italian › Unit 01 › Session 2 › Flashcards"),
            ("/progress/", "Home › Italian › Progress"),
            ("/reference/teaching-plan/", "Home › Italian › Teaching plan"),
            ("/french/year-7/", "Home › Year 7 French"),
            ("/french/year-7/packs/countries/", "Home › Year 7 French › Pack 5"),
            ("/french/year-7/packs/countries/cards/",
             "Home › Year 7 French › Pack 5 › Flashcards"),
            ("/french/year-7/tests/writing/", "Home › Year 7 French › Writing"),
        ):
            page.goto(f"{ROOT}{path}")
            crumbs = page.locator(".crumbs li")
            got = " › ".join(crumbs.all_inner_texts())
            if got != expected:
                fails.append(f"{path} trail is {got!r}, expected {expected!r}")
        notes.append(f"breadcrumb trails checked on 10 pages, last: {got!r}")

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
        # The pack grid, not every link on the page — the hub also offers the
        # mixed deck, and counting all of them made that look like an 11th pack.
        packs = page.locator("#packs .cardlink").count()
        notes.append(f"french hub: {tests} test card(s), {packs} pack card(s)")
        if tests != 2:
            fails.append(f"the French hub shows {tests} tests, expected 2")
        if packs != 10:
            fails.append(f"the French hub shows {packs} packs, expected 10")
        if page.locator("a[href$='/mix/']").count() == 0:
            fails.append("the French hub does not offer the mixed deck")
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

        # Every exercise that shows one item at a time can go back as well as
        # forward. All four shipped with a Next and no Back, which on the speaking
        # practice — where nothing is marked and the point is repeating a question
        # until it comes out cleanly — left no way to hear it again.
        #
        # The unmarked kind wraps; the marked ones do not, and a question already
        # answered comes back read-only so the count at the end stays honest.
        page.goto(f"{ROOT}/french/year-7/packs/speaking-answers/")
        sp = page.locator("#ex-speaking-practice")
        back = sp.get_by_text("← Back")
        if back.count() == 0:
            fails.append("the speaking practice has no Back button")
        elif not back.is_visible():
            fails.append("the speaking practice offers no Back on its first "
                         "question — nothing here is marked, so it should wrap "
                         "round to the last")
        else:
            start = sp.locator(".expos").inner_text()
            back.click()
            wrapped = sp.locator(".expos").inner_text()
            notes.append(f"speaking practice: Back from {start!r} goes to {wrapped!r}")
            if wrapped == start:
                fails.append("Back on the speaking practice does nothing")
            if not wrapped.startswith("5 of"):
                fails.append(f"Back from the first question should wrap to the last, got {wrapped!r}")
            sp.get_by_text("Show the model answer").click()
            sp.get_by_text("Next →").click()
            if sp.locator(".exanswer").is_visible():
                fails.append("the model answer stays uncovered when the question changes")

        page.goto(f"{ROOT}/french/year-7/packs/greetings/")
        wd = page.locator("#ex-w-d")
        answers = page.evaluate("""() => JSON.parse(
            document.querySelector('#ex-w-d .ex-data').textContent).items""")
        if wd.get_by_text("← Back").count() == 0:
            fails.append("the typed drill has no Back button")
            answers = []                       # nothing below can be driven
        elif wd.get_by_text("← Back").is_visible():
            fails.append("the typed drill offers Back on its first question")
        if answers:
            wd.locator(".exinput").fill(answers[0]["answer"])
            wd.get_by_text("Check").click()
            wd.get_by_text("Next →").click()
            wd.locator(".exinput").fill("not the answer")
            wd.get_by_text("Check").click()
            wd.get_by_text("← Back").click()
            was = wd.locator(".exinput").input_value()
            notes.append(f"typed drill: Back shows {was!r}, "
                         f"read-only {wd.locator('.exinput').is_disabled()}")
            if was != answers[0]["answer"]:
                fails.append(f"Back on the typed drill shows {was!r}, not what he typed")
            if not wd.locator(".exinput").is_disabled():
                fails.append("a question already answered can be answered again — "
                             "the score would double-count")
            if wd.get_by_text("Check").is_visible():
                fails.append("an answered question still offers Check")

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

            # ----------------------------------------------------------------------
        # "Just what I need"
        # ----------------------------------------------------------------------
        #
        # Three things have to hold: it starts off, it actually removes the
        # commentary, and it never touches the material. The last is the one
        # worth guarding — a switch that quietly hid the vocabulary would be a
        # disaster that looked like a feature.
        page.goto(f"{ROOT}/french/year-7/packs/speaking-answers/")
        switch = page.locator("#plainmode")
        if switch.count() == 0:
            fails.append("no reading-mode switch on a pack page")
        else:
            if switch.is_checked():
                fails.append("the reading-mode switch starts on; a parent should see everything")
            if not page.locator(".note.forparent").is_visible():
                fails.append("a note for the parent is hidden before the switch is used")
            words = lambda: len(page.inner_text("main").split())
            before, answers, drills = words(), page.locator(".qa li").count(), page.locator(".exercise").count()

            switch.check()
            after = words()
            notes.append(f"reading mode: {before} words → {after} ({before - after} fewer)")
            if page.locator(".note.forparent").is_visible():
                fails.append("the parent's note survives the switch")
            if after >= before:
                fails.append(f"the switch removes nothing ({before} → {after} words)")
            if page.locator(".qa li").count() != answers:
                fails.append("the switch removed some of the answers — it must only take prose")
            if page.locator(".exercise").count() != drills:
                fails.append("the switch removed an exercise")
            # Visibility, not presence. `display: none` leaves the element in
            # the DOM, so counting it proves nothing — the same trap as the
            # `hidden` attribute, met twice now.
            for keep, what in ((".words", "a word table"),
                               (".exintro", "an exercise's instructions"),
                               (".qa", "the model answers")):
                shown = page.locator(keep).count() and page.locator(keep).first.is_visible()
                if page.locator(keep).count() and not shown:
                    fails.append(f"the switch hides {what} — it must only take prose")

            # It has to survive the walk to the next pack, or it is set per page.
            page.goto(f"{ROOT}/french/year-7/packs/countries/")
            if not page.locator("#plainmode").is_checked():
                fails.append("the reading-mode choice is forgotten between pages")
            if not page.evaluate("document.documentElement.hasAttribute('data-plain')"):
                fails.append("reading mode is applied late — the notes would flash up first")
            folded = page.locator("details.note.aside")
            if folded.count() == 0:
                fails.append("a learner's note cannot fold")
            elif folded.first.evaluate("e => e.open"):
                fails.append("a learner's note stays open with the switch on")
            elif not folded.first.locator("summary").is_visible():
                fails.append("a folded note hides its heading too — it should be one tap from open")

            # And wherever the switch is offered it must do something.
            for path in ("/french/year-7/", "/french/year-7/tests/writing/"):
                page.goto(f"{ROOT}{path}")
                if page.locator("#plainmode").count() == 0:
                    continue
                if page.locator("details.note.aside, .note.forparent").count() == 0:
                    fails.append(f"{path} offers the switch with nothing for it to act on")

            page.goto(f"{ROOT}/french/year-7/packs/countries/")
            page.locator("#plainmode").uncheck()
            if not page.locator("details.note.aside").first.evaluate("e => e.open"):
                fails.append("switching off does not unfold the notes again")

        # ----------------------------------------------------------------------
        # The Leitner box
        # ----------------------------------------------------------------------
        #
        # Spacing is the point of it, so what matters is that a card can be marked,
        # that the marking survives a reload, and that only box numbers are stored
        # — not a score. And that the Italian decks did not quietly grow buttons.
        page.goto(f"{ROOT}/french/year-7/packs/greetings/cards/")
        if page.locator("#marks").count() == 0:
            fails.append("the French cards have no Leitner box")
        else:
            # `hidden` has to mean hidden. The browser's own [hidden] rule is the
            # weakest there is, so `.marks { display: flex }` beat it and the two
            # buttons sat under a card that had not been turned over — with the
            # element's hidden property true the whole time, so nothing in the DOM
            # looked wrong. Checked with a computed style, not the attribute.
            shown = page.locator("#marks").evaluate("e => getComputedStyle(e).display")
            notes.append(f"marks before the card is turned: display {shown}")
            if shown != "none":
                fails.append(f"the mark buttons show under an unturned card (display {shown})")

            page.locator("#card").click()
            if not page.locator("#marks").is_visible():
                fails.append("the mark buttons do not appear once the card is face up")

            start = page.locator("#stillto").inner_text()
            page.locator("#knew").click()
            moved = page.locator("#stillto").inner_text()
            notes.append(f"box tally: {start!r} → {moved!r}")
            if start == moved:
                fails.append("marking a card right does not move it up a box")
            if page.locator("#marks").is_visible():
                fails.append("the mark buttons stay up after marking")

            page.reload()
            if page.locator("#stillto").inner_text() != moved:
                fails.append("the boxes do not survive a reload")

            stored = page.evaluate("""() => {
              const keys = Object.keys(localStorage).filter((k) => k.startsWith('leitner:'));
              const values = keys.flatMap((k) => Object.values(JSON.parse(localStorage.getItem(k))));
              return { keys, values: [...new Set(values)] };
            }""")
            notes.append(f"stored: {stored['keys']} holding {sorted(stored['values'])}")
            if any(v not in (1, 2, 3) for v in stored["values"]):
                fails.append(f"something other than a box number is stored: {stored['values']}")
            if any("/" in k for k in stored["keys"]):
                fails.append(f"the boxes are keyed on a URL, so moving the site loses them: {stored['keys']}")

            page.locator("#forget").click()
            if page.locator("#stillto").inner_text() == moved:
                fails.append("starting the boxes again does not clear them")

        page.goto(f"{ROOT}/units/2/sessions/1/cards/")
        if page.locator("#marks").count():
            fails.append("an Italian deck has self-marking buttons — the teacher is in the room")

    # A test page lists its packs in its own order, not in number order.
        page.goto(f"{ROOT}/french/year-7/tests/writing/")
        first = page.locator(".cardlink .t").first.inner_text()
        notes.append(f"writing test, first pack: {first!r}")
        if "Tricky" not in first:
            fails.append(f"the writing test opens with {first!r}, not the tricky spellings")

        # ----------------------------------------------------------------------
        # Light, dark, or the device
        # ----------------------------------------------------------------------
        #
        # The dark tokens are written twice — once under the media query, for a
        # browser with no JavaScript, and once under [data-theme="dark"], for
        # the switch — because CSS cannot share one declaration between a media
        # query and a selector. Two copies drift, so they are compared by what
        # the browser actually computes rather than by reading the stylesheet.
        TOKENS = """() => {
          const s = getComputedStyle(document.documentElement);
          const names = ['--accent','--accent-soft','--accent-line','--ink',
            '--ink-soft','--ink-faint','--paper','--card','--rule','--note-bg',
            '--note-line','--answer-bg','--answer-line','--on-accent','--pen',
            '--pen-bg','--pen-line'];
          return Object.fromEntries(names.map((n) => [n, s.getPropertyValue(n).trim()]));
        }"""
        THEMED = f"{ROOT}/units/1/sessions/1/"        # uses the notebook tokens too

        dark_device = b.new_page(color_scheme="dark")
        dark_device.goto(THEMED)
        by_device = dark_device.evaluate(TOKENS)
        dark_device.close()

        light_device = b.new_page(color_scheme="light")
        light_device.goto(THEMED)
        if light_device.locator("#theme").count() == 0:
            fails.append("no colour switch on a lesson page")
            light_device.close()
        else:
            light_device.select_option("#theme", "dark")
            by_switch = light_device.evaluate(TOKENS)
            drifted = {k: (by_device[k], by_switch[k])
                       for k in by_device if by_device[k] != by_switch[k]}
            notes.append(f"theme tokens compared: {len(by_device)}, drifted: {len(drifted)}")
            for name, (device, switch) in drifted.items():
                fails.append(f"{name} is {device} on a dark device but {switch} when "
                             f"the switch forces dark — the two dark blocks have drifted")
            light_device.close()

            # Light has to win on a dark device, or the switch is one-way.
            forced = b.new_page(color_scheme="dark")
            forced.goto(THEMED)
            forced.select_option("#theme", "light")
            paper = forced.evaluate(TOKENS)["--paper"].lower()
            notes.append(f"light forced on a dark device: --paper {paper}")
            if paper != "#fbf9f7":
                fails.append(f"forcing light on a dark device leaves --paper {paper}")

            # Remembered, and applied before anything paints: set by the inline
            # script in the head, so the attribute is already there on load.
            forced.reload()
            if forced.evaluate("document.documentElement.getAttribute('data-theme')") != "light":
                fails.append("the colour choice is not applied on the next load")
            if forced.locator("#theme").input_value() != "light":
                fails.append("the colour switch does not show the saved choice")
            if forced.evaluate(TOKENS)["--paper"].lower() != "#fbf9f7":
                fails.append("the saved light choice does not survive a reload")

            # And there is a way back to following the device.
            forced.select_option("#theme", "auto")
            if forced.evaluate("document.documentElement.hasAttribute('data-theme')"):
                fails.append("'Match my device' leaves an override in place")
            if forced.evaluate(TOKENS)["--paper"].lower() != "#171615":
                fails.append("'Match my device' does not hand back to a dark device")
            forced.close()

        # ----------------------------------------------------------------------
        # Text on a solid accent block, in both themes
        # ----------------------------------------------------------------------
        #
        # The light theme's accent is a dark red and the dark theme's is a light
        # salmon, so one colour of text cannot serve both. White on the salmon
        # measured 2.7:1 — readable to someone who already knows what it says, and
        # not to a twelve-year-old glancing at a phone. `--on-accent` flips it, and
        # this is here so nobody flips it back by writing `color: #fff` again.
        CONTRAST = """(sel) => {
          const e = document.querySelector(sel);
          if (!e) return null;
          const s = getComputedStyle(e);
          const lum = (c) => {
            const [r, g, b] = c.match(/\\d+/g).map(Number).map((v) => {
              v /= 255;
              return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            });
            return 0.2126 * r + 0.7152 * g + 0.0722 * b;
          };
          const a = lum(s.color), b = lum(s.backgroundColor);
          const [hi, lo] = a > b ? [a, b] : [b, a];
          return Math.round(((hi + 0.05) / (lo + 0.05)) * 10) / 10;
        }"""

        ON_ACCENT = (
            ("/", ".door .flag", "the next-test flag on the front page"),
            ("/french/year-7/packs/greetings/", ".exercise .exbtn", "an exercise button"),
            ("/french/year-7/packs/countries/cards/", '.chip[aria-pressed="true"]',
             "the selected deck chip"),
            ("/reference/grammar-checklist/", ".badge.f", "a Foundation grammar badge"),
        )
        for scheme in ("light", "dark"):
            themed = b.new_page(viewport={"width": 900, "height": 800}, color_scheme=scheme)
            worst = None
            for path, sel, what in ON_ACCENT:
                themed.goto(f"{ROOT}{path}")
                ratio = themed.evaluate(CONTRAST, sel)
                if ratio is None:
                    fails.append(f"{what} is missing from {path}")
                    continue
                if worst is None or ratio < worst[0]:
                    worst = (ratio, what)
                if ratio < 4.5:
                    fails.append(f"{scheme} theme: {what} is {ratio}:1, below 4.5:1")
            if worst:
                notes.append(f"{scheme} theme, worst accent contrast: {worst[0]}:1 ({worst[1]})")
            themed.close()

        # The logo belongs to one page.
        for path, why in (("/units/1/sessions/2/", "a lesson page"),
                          ("/french/year-7/", "a French page"),
                          ("/french/year-7/packs/greetings/", "a French pack")):
            page.goto(f"{ROOT}{path}")
            if page.locator(".logomark").count():
                fails.append(f"a logo is on {why}, where it competes with the material")
        page.goto(f"{ROOT}/")
        if page.locator(".logomark.is-italian").count():
            fails.append("the Italian mark is on the front door, branding the site one subject")

    except Exception as crash:
        # The deepest frame is inside Playwright and says nothing useful. The
        # deepest frame in *this* file is the step that actually broke.
        here = [f for f in traceback.extract_tb(crash.__traceback__)
                if f.filename == __file__]
        where = here[-1] if here else traceback.extract_tb(crash.__traceback__)[-1]
        first = str(crash).splitlines()[0]
        fails.append(f"a check threw at line {where.lineno}, {where.line!r}: {first}")

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
