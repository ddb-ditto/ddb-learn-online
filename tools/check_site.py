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

EVAL_WANTED = """() => {
  const d = JSON.parse(document.querySelector('#ex-w-e .ex-data').textContent);
  const p = document.querySelector('#ex-w-e .exprompt').textContent;
  const hit = d.items.find((i) => i.prompt === p);
  return hit ? hit.answer : null;
}"""

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

        # Every mark, in one place. Each entry is the page it belongs to, the
        # class that identifies it, the file it serves and how to describe it.
        #
        # One list rather than a list per check, because that is how the last
        # two were missed: the reserved-size check lived inside the site
        # logo's block and skipped the French mark entirely, and the green
        # check named two files by hand and skipped the Italian one when it
        # stopped being a hand-drawn roundel. Add a fourth mark here and every
        # check below picks it up.
        MARKS = (
            ("/", "is-site", "logo-site.png", "the site mark, on the front door"),
            ("/italian/", "is-italian", "logo.png", "the Italian mark"),
            ("/french/year-7/", "is-french", "logo-french.png", "the Year 7 French mark"),
        )

        def mark_reserves_right_space(img, what: str) -> None:
            """The width and height attributes against the file's own shape.

            Comparing the *rendered* box proves nothing: the stylesheet sets
            height:auto, so once the image has loaded the box takes the file's
            ratio whatever the attributes say. What the attributes decide is
            the space held before it loads, so a stale pair makes the page
            jump — and only on the first, uncached visit, which is the one
            visit nobody tests.

            Every mark needs this, not just the one it was first written for.
            It lived inside the site logo's block, so replacing the French
            artwork with one of a different shape sailed through.
            """
            nat = img.evaluate("e => [e.naturalWidth, e.naturalHeight, e.complete]")
            if not nat[2] or nat[0] == 0:
                fails.append(f"{what} did not load — the box is its width and height "
                             f"attributes, not the image")
                return
            attr = img.evaluate("e => [+e.getAttribute('width'), +e.getAttribute('height')]")
            if attr[0] and attr[1] and abs(attr[0] / attr[1] - nat[0] / nat[1]) > 0.02:
                fails.append(f"{what} reserves {attr[0]}x{attr[1]} for a file that is "
                             f"{nat[0]}x{nat[1]} — the page will jump as it loads")

        # --- the front door ----------------------------------------------------
        # Two choices and nothing else. Both have to be here and both have to go
        # somewhere: a door that 404s is worse than no door.
        page.goto(f"{ROOT}/")

        # The front door carries no heading, no eyebrow and no standfirst: the
        # mark says the site's name better than a line of type, and the two
        # doors say the rest. So the mark *is* the h1 here.
        #
        # Two things to hold on to. The masthead used to render only when there
        # was a heading, so taking the words out would have taken the mark with
        # them — the page would have come back with no branding and nothing
        # would have said so. And a front page with no h1 at all is the other
        # easy outcome: the markup looks fine, and anybody arriving by search
        # or by screen reader gets a page with no name.
        h1s = page.locator("h1")
        if h1s.count() != 1:
            fails.append(f"the front page has {h1s.count()} h1 elements, expected 1")
        else:
            named = page.evaluate("""() => {
                const h = document.querySelector('h1');
                const img = h.querySelector('img');
                return (h.textContent.trim() || (img && img.alt) || '').trim();
            }""")
            notes.append(f"front page h1 names the site as {named!r}")
            if not named:
                fails.append("the front page's h1 has no accessible name — no text and "
                             "no alt on the mark inside it")
        if not page.locator(".logomark").is_visible():
            fails.append("the front door shows no mark — the masthead renders only when "
                         "something is in it, and the words were taken out")

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

        # Size, alt text and reserved space are measured for all three marks
        # together, further down. The one thing that is the site mark's alone:
        # its alt text must not name a subject, because it stands for a site
        # that teaches two.
        page.goto(f"{ROOT}/")
        site_mark = page.locator(".logomark.is-site")
        if site_mark.count() == 1 and "italian" in (
                site_mark.get_attribute("alt") or "").lower():
            fails.append("the site logo's alt text still names one subject")

        # No green anywhere in either wordmark.
        #
        # The DDB artwork arrived as a PNG that had already been cut out, and
        # cut out badly: binary alpha, and whole patches of the green card it
        # was drawn on left opaque — a circle bottom left, another bottom
        # right, a patch above the second D. On the cream theme they read as
        # olive smudges and on the navy one as holes. Corners alone would
        # never have caught it, because the corners were already clear.
        #
        # The test is proximity to that specific green, not greenness.
        # "Any pixel where green beats the other two" was the first version
        # and it is unsound: yellow blended with blue makes green, this
        # artwork has yellow shapes against blue ones, and every downscale
        # averages the boundary. It reported 424 failures on a correct file,
        # all of them muted olive 90-100 away in RGB from the card's colour.
        # What matters is whether the card itself is still there.
        for _, _, name, _ in MARKS:
            got = page.request.get(
                f"http://127.0.0.1:{httpd.server_address[1]}{BASE}/{name}")
            if got.status != 200:
                fails.append(f"{name} is {got.status}")
                continue
            seen = page.evaluate("""async (bytes) => {
                const blob = new Blob([new Uint8Array(bytes)], {type: 'image/png'});
                const bmp = await createImageBitmap(blob);
                const c = new OffscreenCanvas(bmp.width, bmp.height);
                const g = c.getContext('2d');
                g.drawImage(bmp, 0, 0);
                const d = g.getImageData(0, 0, bmp.width, bmp.height).data;
                const BG = [4, 164, 74], R = 100;
                let solid = 0, edge = 0, opaque = 0;
                for (let i = 0; i < d.length; i += 4) {
                  const [r, gg, b, a] = [d[i], d[i+1], d[i+2], d[i+3]];
                  if (a < 16) continue;
                  opaque++;
                  const far = Math.hypot(r - BG[0], gg - BG[1], b - BG[2]);
                  if (far < R) { a > 200 ? solid++ : edge++; }
                }
                return {w: bmp.width, h: bmp.height, solid, edge, opaque};
            }""", list(got.body()))
            notes.append(f"{name}: {seen['solid']} background-green pixels in the "
                         f"artwork, {seen['edge']} in its edges")
            if seen["solid"]:
                fails.append(f"{name} has {seen['solid']} opaque pixel(s) of the green "
                             f"card it was drawn on — it was not fully keyed out")
            # A rim of it on the edges is the other way this goes wrong: a
            # resize that averages the colour behind transparent pixels into
            # the ones beside them. One or two is rounding; a hundred is a halo.
            if seen["edge"] > 50:
                fails.append(f"{name} has {seen['edge']} edge pixels of the background "
                             f"green — the resize bled it in from behind the "
                             f"transparency")

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
        # The site's mark in the breadcrumb bar — the one piece of branding on a
        # page that is not the front door. It lives inside the centred row: put it
        # before the row and it pins itself to the window's edge and drags the
        # crumbs out of line, which is what the first attempt did.
        for width in (1100, 390):
            page.set_viewport_size({"width": width, "height": 700})
            page.goto(f"{ROOT}/french/year-7/packs/greetings/")
            row = page.locator(".crumbrow")
            mark = page.locator(".crumbmark")
            if mark.count() == 0:
                fails.append("no site mark in the breadcrumb bar")
                break
            rb, mb = row.bounding_box(), mark.bounding_box()
            off_centre = abs(rb["x"] - (width - rb["width"] - rb["x"]))
            notes.append(f"crumb row at {width}px: x={round(rb['x'])} "
                         f"w={round(rb['width'])}, off-centre by {round(off_centre)}px")
            if off_centre > 1:
                fails.append(f"the breadcrumb row is off-centre at {width}px by "
                             f"{round(off_centre)}px — the mark is outside it")
            if mb["x"] < rb["x"] - 1:
                fails.append(f"the mark sits left of the crumb row at {width}px")
            if page.evaluate("document.body.scrollWidth") > width:
                fails.append(f"the breadcrumb bar scrolls sideways at {width}px")
        page.set_viewport_size({"width": 390, "height": 844})


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

        # Revealing shows both halves: what was asked and what to say, each in
        # French and in English. The French question sits alone at the top of the
        # card, so somebody unsure what it means gets nothing from the answer.
        page.goto(f"{ROOT}/french/year-7/packs/speaking-answers/")
        sp = page.locator("#ex-speaking-practice")
        sp.get_by_text("Show the model answer").click()
        halves = sp.locator(".exblock")
        notes.append(f"revealed halves: {halves.count()}")
        if halves.count() != 2:
            fails.append(f"the reveal shows {halves.count()} block(s), expected the "
                         f"question and the answer")
        else:
            asked = sp.locator(".exblock.asked")
            said = sp.locator(".exblock.said")
            for part, what in ((asked, "question"), (said, "answer")):
                if part.locator(".fr").count() == 0:
                    fails.append(f"the revealed {what} has no French")
                if part.locator(".en").count() == 0:
                    fails.append(f"the revealed {what} has no English")
            # The question block must actually repeat the question, not the answer.
            shown = asked.locator(".fr").inner_text()
            onCard = sp.locator(".exq").inner_text()
            if shown.replace("\u00a0", " ").strip() != onCard.replace("\u00a0", " ").strip():
                fails.append(f"the revealed question is {shown!r}, not the one asked, {onCard!r}")
            # And the two must be told apart by more than their order.
            tints = [part.evaluate("e => getComputedStyle(e).backgroundColor")
                     for part in (asked, said)]
            notes.append(f"question/answer tints: {tints}")
            if tints[0] == tints[1]:
                fails.append("the question and the answer are tinted the same")

        # --- the voice that reads the French ------------------------------------
        #
        # The ♪ Hear it button is only honest if the device has a French voice.
        # Before this was checked, the code asked `"speechSynthesis" in window`
        # — true in every modern browser whatever voices are installed — so two
        # things both happened: a machine with no voices showed a button that
        # did nothing when pressed, and a machine with English voices and no
        # French one read *Comment tu t'appelles ?* in an English accent, which
        # is worse than silence in a pronunciation drill.
        #
        # Neither is visible by reading the page: the DOM is identical either
        # way. So the voice list is replaced before the page's own scripts run
        # and the button is driven against each shape of device. `localService`
        # false marks a voice that has to be fetched, which is silent offline.
        #
        # Every case runs in its own context, because the chosen voice is
        # remembered and would otherwise leak into the next one.
        VOICE_STUB = """
        (voices, late) => {
          window.__spoken = [];
          const all = voices.map(v => ({ name: v[0], lang: v[1],
                                         localService: v[2] !== false, default: false }));
          let listeners = [];
          let ready = !late;
          const stub = {
            getVoices: () => (ready ? all : []),
            cancel: () => {},
            speak: u => window.__spoken.push({ text: u.text, voice: u.voice && u.voice.name,
                                               lang: u.lang, rate: u.rate }),
            addEventListener: (t, f) => {
              if (t !== 'voiceschanged') return;
              listeners.push(f);
              setTimeout(() => { ready = true; listeners.forEach(g => g()); }, 50);
            },
            removeEventListener: (t, f) => { listeners = listeners.filter(g => g !== f); },
          };
          // A plain assignment to window.speechSynthesis fails silently: it is a
          // read-only accessor on Window.prototype. This cost a run of eight
          // false failures before it was spotted.
          Object.defineProperty(window, 'speechSynthesis',
                                { value: stub, configurable: true });
          Object.defineProperty(window, 'SpeechSynthesisUtterance',
                                { value: function (text) { this.text = text; },
                                  configurable: true });
          window.__stubbed = window.speechSynthesis === stub;
        }
        """
        VOICE_CASES = [
            # label,                   voices,                                      late
            ("no voices at all",       [],                                          False),
            ("English voices only",    [["Daniel", "en-GB"], ["Samantha", "en-US"]], False),
            ("one French voice",       [["Marie", "fr-FR"]],                        False),
            ("French, best last",      [["Microsoft Hortense", "fr-FR"],
                                        ["Thomas", "fr-FR"]],                       False),
            ("French arriving late",   [["Thomas", "fr-FR"]],                       True),
            ("French and English",     [["Daniel", "en-GB"], ["Amélie", "fr-CA"]],  False),
            ("underscore locale",      [["Julie", "fr_FR"]],                        False),
            ("network voice alone",    [["Google français", "fr-FR", False]],       False),
            # Two voices, one of them network-only, so there is a picker for the
            # wi-fi warning to appear on. With a single voice no picker renders,
            # which made the first version of that assertion dead code — it
            # passed against a build with the warning deliberately removed.
            ("network voice listed",   [["Thomas", "fr-FR"],
                                        ["Google français", "fr-FR", False]],       False),
        ]
        is_fr = lambda lang: lang.lower().replace("_", "-").startswith("fr")
        # French puts a no-break space before "!" and "?" on screen; what is
        # spoken normalises it, so every comparison flattens both sides.
        flat = lambda t: t.replace(" ", " ").replace(" ", " ").strip()

        for label, voices, late in VOICE_CASES:
            ctx = b.new_context(viewport={"width": 390, "height": 844})
            vp = ctx.new_page()
            try:
                vp.add_init_script(f"({VOICE_STUB})({json.dumps(voices)}, "
                                   f"{json.dumps(late)})")
                vp.goto(f"{ROOT}/french/year-7/packs/speaking-answers/")
                vp.wait_for_timeout(2200)
                if not vp.evaluate("window.__stubbed === true"):
                    fails.append(f"voices [{label}]: the stub did not install, so this "
                                 f"case proved nothing")
                    continue

                french = [v[0] for v in voices if is_fr(v[1])]
                # The speaker on the question of the speaking practice. It is
                # a glyph now, not a button reading "Hear it" — see the
                # speaker rules in CLAUDE.md.
                btn = vp.locator("#ex-speaking-practice .exq .sayit")
                shown = btn.count() > 0 and btn.first.is_visible()

                if not french:
                    # The whole point. `hidden` alone is not enough to assert:
                    # any class setting `display` beats [hidden], so measure it.
                    if shown:
                        disp = btn.first.evaluate("e => getComputedStyle(e).display")
                        fails.append(f"voices [{label}]: a speaker is offered with no French "
                                     f"voice (display: {disp}) — it reads English or nothing")
                    # And none of the others on the page either: a pack marks
                    # every French word, so a leak here is fifty speakers.
                    everywhere = vp.evaluate(
                        """() => Array.from(document.querySelectorAll('.sayit'))
                             .filter(b => getComputedStyle(b).display !== 'none').length""")
                    if everywhere:
                        fails.append(f"voices [{label}]: {everywhere} speaker(s) shown on the "
                                     f"page with no French voice installed")
                    picker = vp.locator("#fr-voice")
                    if picker.count() and picker.first.is_visible():
                        fails.append(f"voices [{label}]: a voice picker with no French voice")
                    # And not the speed control either: it would set the pace
                    # of audio that cannot play.
                    row = vp.locator("#fraudio")
                    if row.count() and row.first.is_visible():
                        fails.append(f"voices [{label}]: the audio controls are shown with "
                                     f"no French voice to use them on")
                    continue

                if not shown:
                    fails.append(f"voices [{label}]: no speaker on the question though the "
                                 f"device has {french}")
                    continue                       # a finding, not an exception

                btn.first.click()
                vp.wait_for_timeout(150)
                spoken = vp.evaluate("window.__spoken || []")
                if not spoken:
                    fails.append(f"voices [{label}]: the speaker was pressed and said nothing")
                    continue
                u = spoken[-1]
                want = "Thomas" if "Thomas" in french else french[0]
                if u["voice"] != want:
                    fails.append(f"voices [{label}]: spoke with {u['voice']!r}, "
                                 f"expected {want!r}")
                if not is_fr(str(u["lang"])):
                    fails.append(f"voices [{label}]: utterance lang is {u['lang']!r}")
                # Not a fixed number any more: the speed is a setting, and
                # which number is correct is the speed checks' business. What
                # matters here is that it is deliberately below a
                # conversational pace, which is the bug this caught before —
                # the rate left at 1.
                if not (0.5 <= u["rate"] < 1.0):
                    fails.append(f"voices [{label}]: rate is {u['rate']!r} — the audio is "
                                 f"not slowed below a conversational pace")
                on_card = vp.locator("#ex-speaking-practice .exq").inner_text()
                if flat(u["text"]) != flat(on_card):
                    fails.append(f"voices [{label}]: spoke {flat(u['text'])!r} while the "
                                 f"card showed {flat(on_card)!r}")

                # The picker exists only where there is a choice. On a phone with
                # one French voice it must not be rendered at all. It lives in
                # the section's audio controls now, not inside one exercise.
                picker = vp.locator("#fr-voice")
                has_picker = picker.count() > 0 and picker.first.is_visible()
                if len(french) > 1:
                    if not has_picker:
                        fails.append(f"voices [{label}]: {len(french)} French voices and "
                                     f"no way to choose between them")
                    else:
                        if picker.first.input_value() != want:
                            fails.append(f"voices [{label}]: the picker starts on "
                                         f"{picker.first.input_value()!r}, not {want!r}")
                        other = [v for v in french if v != want][0]
                        picker.first.select_option(other)
                        vp.wait_for_timeout(150)
                        after = vp.evaluate("window.__spoken || []")[-1]
                        if after["voice"] != other:
                            fails.append(f"voices [{label}]: choosing {other!r} still "
                                         f"spoke with {after['voice']!r}")
                        kept = vp.evaluate("localStorage.getItem('fr7:voice')")
                        if kept != other:
                            fails.append(f"voices [{label}]: the chosen voice was not "
                                         f"remembered (stored {kept!r})")
                elif has_picker:
                    fails.append(f"voices [{label}]: a picker offering one voice")

                # A voice that is fetched rather than installed goes quiet on a
                # train, so it has to say so where it is chosen.
                if has_picker and any(len(v) > 2 and v[2] is False for v in voices):
                    labels = picker.first.evaluate(
                        "e => Array.from(e.options).map(o => o.textContent)")
                    if not any("wi-fi" in t for t in labels):
                        fails.append(f"voices [{label}]: a network-only voice is offered "
                                     f"without saying it needs one")
            except Exception as why:               # a crash here is a finding
                fails.append(f"voices [{label}] crashed: {str(why).splitlines()[0]}")
            finally:
                ctx.close()
        notes.append(f"voice cases driven: {len(VOICE_CASES)}")

        # --- how fast it reads ---------------------------------------------
        #
        # The speed is a setting rather than a constant because the right one
        # cannot be chosen from here: it depends on the voice the device
        # happens to have and on how much French the listener already knows,
        # and this machine has no voices to listen to at all. An earlier
        # version picked 0.9 and justified it in a comment that had never been
        # tested.
        #
        # The control appears wherever there is French and nowhere else. On a
        # page with none — the section hub, which only lists the packs — it
        # would set the pace of audio that cannot play, which is the dead
        # button all over again.
        for path, want in (("/french/year-7/packs/greetings/", True),
                           ("/french/year-7/tests/writing/", True),
                           ("/french/year-7/mix/", True),
                           ("/french/year-7/", False),
                           ("/units/1/", False)):
            ctx = b.new_context(viewport={"width": 390, "height": 844})
            vp = ctx.new_page()
            try:
                vp.add_init_script(
                    f"({VOICE_STUB})({json.dumps([['Thomas', 'fr-FR']])}, false)")
                vp.goto(f"{ROOT}{path}")
                vp.wait_for_timeout(1700)
                row = vp.locator("#fraudio")
                shown = row.count() > 0 and row.first.is_visible()
                french = vp.locator('[lang="fr"]').count()
                if shown != want:
                    fails.append(f"the audio controls are {'shown' if shown else 'absent'} "
                                 f"on {path}, which has {french} French element(s)")
                if not shown:
                    continue
                opts = vp.locator("#fr-speed option").all_inner_texts()
                notes.append(f"audio controls on {path}: speeds {opts}")
                if len(opts) < 2:
                    fails.append(f"{path}: the speed control offers {len(opts)} step(s)")
                if vp.locator("#fr-speed").input_value() != "slow":
                    fails.append(f"{path}: the speed does not start on the slower setting")
                # It has to actually reach the utterance, not just be stored.
                sayit = vp.locator(".sayit").first
                if sayit.count() == 0 or not sayit.is_visible():
                    fails.append(f"{path}: no speaker to test the speed against")
                    continue
                sayit.click()
                vp.wait_for_timeout(150)
                said = vp.evaluate("window.__spoken || []")
                if not said:
                    fails.append(f"{path}: pressing a speaker said nothing")
                elif said[-1]["rate"] != 0.75:
                    fails.append(f"{path}: spoke at {said[-1]['rate']}, not the 0.75 the "
                                 f"control is set to")
                vp.locator("#fr-speed").select_option("slowest")
                vp.wait_for_timeout(150)
                sayit.click()
                vp.wait_for_timeout(150)
                said = vp.evaluate("window.__spoken || []")
                if said and said[-1]["rate"] != 0.6:
                    fails.append(f"{path}: choosing the slowest speed still spoke at "
                                 f"{said[-1]['rate']}")
                kept = vp.evaluate("localStorage.getItem('fr7:rate')")
                if kept != "slowest":
                    fails.append(f"{path}: the speed was not remembered (stored {kept!r})")
            except Exception as why:
                fails.append(f"the speed checks crashed on {path}: "
                             f"{str(why).splitlines()[0]}")
            finally:
                ctx.close()

        # --- a speaker beside every bit of French, and beside nothing else ----
        #
        # `lang="fr"` in the markup is what puts a speaker on something, so
        # these check the two directions of that: every French thing has one,
        # and nothing that is not French has one. The second half is the one
        # that matters. A speaker on the pronunciation column would read "koo
        # koo" as though it were a French word, and a speaker on the prompts of
        # *Spot the mistake* or *Put the punctuation back* would read a
        # misspelling aloud — where the misspelling is silent, so it would
        # read the correct sentence and teach nothing while looking helpful.
        ctx = b.new_context(viewport={"width": 390, "height": 900})
        sp_page = ctx.new_page()
        try:
            sp_page.add_init_script(
                f"({VOICE_STUB})({json.dumps([['Thomas', 'fr-FR']])}, false)")

            def spoke(p):
                return p.evaluate("window.__spoken || []")

            # A pack's word table: French terms speak, the respelling and the
            # English gloss do not.
            sp_page.goto(f"{ROOT}/french/year-7/packs/greetings/")
            sp_page.wait_for_timeout(1800)
            terms = sp_page.locator("table.words td.term")
            on_terms = sp_page.locator("table.words td.term .sayit")
            notes.append(f"word-table speakers: {on_terms.count()} on {terms.count()} terms")
            if terms.count() == 0:
                fails.append("no French terms found on the greetings pack")
            elif on_terms.count() != terms.count():
                fails.append(f"{on_terms.count()} speakers on {terms.count()} French terms")
            # The English meaning, on this same page.
            n = sp_page.locator("table.words td.gloss .sayit").count()
            if n:
                fails.append(f"{n} speaker(s) on the English meaning, which is not French")
            if on_terms.count():
                on_terms.first.click()
                sp_page.wait_for_timeout(120)
                said = spoke(sp_page)
                want = flat(terms.first.inner_text())
                if not said:
                    fails.append("a word-table speaker was pressed and said nothing")
                elif flat(said[-1]["text"]) != want:
                    fails.append(f"the word table spoke {flat(said[-1]['text'])!r}, "
                                 f"not the term {want!r}")

            # The pronunciation column — "ko-koo", "ah", "bay". That is English
            # spelling describing a French sound; read as French it is noise.
            # It lives on one pack only, so the count of cells is asserted
            # first: checking "no speakers on .say" against a page that has no
            # .say cells passes for the wrong reason, and the first version of
            # this check did exactly that on the greetings pack.
            sp_page.goto(f"{ROOT}/french/year-7/packs/speaking-answers/")
            sp_page.wait_for_timeout(1800)
            says = sp_page.locator("table.words td.say")
            notes.append(f"pronunciation cells to check: {says.count()}")
            if says.count() == 0:
                fails.append("no pronunciation column found to check — this check has "
                             "nothing to assert against and is passing vacuously")
            else:
                n = sp_page.locator("table.words td.say .sayit").count()
                if n:
                    fails.append(f"{n} speaker(s) on the pronunciation respelling, which "
                                 f"is English describing a French sound")

            # Nothing in the Italian course speaks: it carries no lang="fr",
            # and the teacher is the model there.
            for url in ("/units/1/", "/italian/"):
                sp_page.goto(f"{ROOT}{url}")
                sp_page.wait_for_timeout(900)
                n = sp_page.locator(".sayit").count()
                if n:
                    fails.append(f"{n} speaker(s) on {url}, which is Italian")

            # The misspelling exercises: the prompt is French written wrong on
            # purpose and must stay silent; the marked answer may speak.
            sp_page.goto(f"{ROOT}/french/year-7/packs/tricky-spellings/")
            sp_page.wait_for_timeout(1800)
            for eid in ("ex-w-e", "ex-w-d"):
                box = sp_page.locator(f"#{eid}")
                if box.count() == 0:
                    continue                       # that pack does not carry it
                n = box.locator(".exprompt .sayit").count()
                if n:
                    fails.append(f"{eid}: {n} speaker(s) on a prompt that is "
                                 f"deliberately misspelled French")
                items = sp_page.evaluate(
                    f"""() => JSON.parse(
                        document.querySelector('#{eid} .ex-data').textContent).items""")
                box.locator(".exinput").fill("deliberately not the answer")
                box.get_by_text("Check").click()
                sp_page.wait_for_timeout(150)
                on_answer = box.locator(".exresult .fr .sayit")
                if on_answer.count() != 1:
                    fails.append(f"{eid}: the marked answer has {on_answer.count()} "
                                 f"speakers, expected 1")
                else:
                    on_answer.first.click()
                    sp_page.wait_for_timeout(120)
                    said = spoke(sp_page)
                    answers = [flat(i["answer"]) for i in items]
                    if not said:
                        fails.append(f"{eid}: the answer's speaker said nothing")
                    elif flat(said[-1]["text"]) not in answers:
                        fails.append(f"{eid}: spoke {flat(said[-1]['text'])!r}, which is "
                                     f"not one of the correct answers")

            # The reading pack: the French passage has to be on the page at all
            # (it was shipped for months as JSON that nothing rendered, so the
            # exercise asked him to find words in a text he could not see), and
            # the gap-fill must not read the passage aloud before it is filled.
            sp_page.goto(f"{ROOT}/french/year-7/packs/reading-skills/")
            sp_page.wait_for_timeout(1800)
            re_box = sp_page.locator("#ex-r-e")
            if re_box.count() == 0:
                fails.append("the unseen-text exercise is not on the reading pack")
            else:
                shown = re_box.inner_text()
                passage = sp_page.evaluate(
                    """() => JSON.parse(
                        document.querySelector('#ex-r-e .ex-data').textContent).text""")
                opening = " ".join((passage or "").split()[:5])
                if opening and opening not in " ".join(shown.split()):
                    fails.append("the unseen-text exercise does not show its passage — "
                                 "it asks for words from a text that is not on the page")
                if re_box.locator(".extext .sayit").count() != 1:
                    fails.append(f"the passage has "
                                 f"{re_box.locator('.extext .sayit').count()} speakers, "
                                 f"expected 1")

            gap = sp_page.locator("#ex-r-b")
            if gap.count():
                if gap.locator(".expassage .sayit").count():
                    fails.append("the gap-fill offers to read the whole passage before the "
                                 "gaps are filled — that is the answers, read aloud")
                bank = gap.locator(".exbank .extile")
                on_bank = gap.locator(".exbank .extile .sayit")
                if bank.count() and on_bank.count() != bank.count():
                    fails.append(f"{on_bank.count()} speakers on {bank.count()} bank words")
                gap.get_by_text("Check").click()
                sp_page.wait_for_timeout(150)
                if gap.locator(".expassage .sayit").count() != 1:
                    fails.append("after Check the gap-fill still will not read the "
                                 "completed passage")

            # The flashcards. The French side speaks; a side that is a digit,
            # an English meaning or an English respelling of a sound does not.
            sp_page.goto(f"{ROOT}/french/year-7/packs/countries/cards/")
            sp_page.wait_for_timeout(1800)
            cards = sp_page.evaluate(
                """() => JSON.parse(document.getElementById('cards-data').textContent)""")
            notes.append(f"french cards: {len(cards)}, "
                         f"declaring French: {sum(1 for c in cards if c.get('fr'))}")
            if not any(c.get("fr") for c in cards):
                fails.append("no French card declares which side is French")
            if any(c.get("fr", {}).get("m") and " — " in (c["fr"]["m"]) for c in cards):
                fails.append("a card's spoken back still carries the English gloss")
            face = sp_page.locator("#face")
            if face.locator(".sayit").count() != 1:
                fails.append(f"the card front has {face.locator('.sayit').count()} "
                             f"speakers, expected 1")
            else:
                face.locator(".sayit").first.click()
                sp_page.wait_for_timeout(120)
                said = spoke(sp_page)
                shown = flat(face.locator(".term").inner_text())
                if not said:
                    fails.append("the flashcard speaker said nothing")
                elif flat(said[-1]["text"]) != shown:
                    fails.append(f"the card spoke {flat(said[-1]['text'])!r}, "
                                 f"not the face {shown!r}")

            # The Italian decks carry no `fr`, so their cards stay silent.
            sp_page.goto(f"{ROOT}/units/1/sessions/1-1/cards/")
            sp_page.wait_for_timeout(1500)
            if sp_page.locator(".sayit").count():
                fails.append(f"{sp_page.locator('.sayit').count()} speaker(s) on an "
                             f"Italian deck")
        except Exception as why:
            fails.append(f"the speaker checks crashed: {str(why).splitlines()[0]}")
        finally:
            ctx.close()

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
        # The highlight on a wrong answer points at a small difference. Given an
        # answer nowhere near it there is no small difference, and marking
        # everything-but-the-incidental-letter chops the correct version into
        # blocks with holes in it. Reported from a screenshot: someone typed
        # "jasjsd", the diff found the one `a` in it, and the answer came back as
        # [Je m']a[ppelle Sam.]
        wanted_js = EVAL_WANTED
        for typed, what in (("jasjsd", "gibberish"), ("", "nothing at all")):
            page.goto(f"{ROOT}/french/year-7/packs/tricky-spellings/")
            we = page.locator("#ex-w-e")
            if we.count() == 0:
                fails.append("no spot-the-mistake drill to check the highlighting with")
                break
            wanted = page.evaluate(wanted_js)
            we.locator(".exinput").fill(typed)
            we.get_by_text("Check").click()
            marked = we.locator("mark").all_inner_texts()
            said = " ".join(we.locator(".exresult").inner_text().split())
            notes.append(f"answered with {what}: highlighted {marked or 'nothing'}")
            if marked:
                fails.append(f"typing {what} highlights {marked} — with nothing close "
                             f"to point at, the answer should be shown plain")
            if wanted and wanted not in said:
                fails.append(f"the correct answer is not shown in full after {what}")


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
        # Find a pack that actually carries a note for the parent rather than
        # naming one: which packs have one is content, and content moves. This
        # check was pinned to the speaking-answers pack and broke the day that
        # pack's note was rewritten for the learner — a check failing because
        # the content improved is a check in the wrong place.
        with_parent_note = None
        for slug in ("name-and-age", "numbers", "speaking-answers", "culture",
                     "greetings", "where-i-live"):
            page.goto(f"{ROOT}/french/year-7/packs/{slug}/")
            if page.locator(".note.forparent").count():
                with_parent_note = slug
                break
        if with_parent_note is None:
            fails.append("no pack carries a note for the parent, so the reading "
                         "switch cannot be checked against one")
        notes.append(f"reading mode checked on the {with_parent_note!r} pack")

        switch = page.locator("#plainmode")
        if switch.count() == 0:
            fails.append("no reading-mode switch on a pack page")
        elif with_parent_note is None:
            pass
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
            # The three tests in the three logo colours. White on the logo's
            # own blue measured 3.9:1, so the blue used here is a shade down
            # from it; these are listed so nobody puts the brighter one back.
            ("/french/year-7/packs/countries/", ".badge.part.speaking", "the Speaking badge"),
            ("/french/year-7/packs/countries/", ".badge.part.reading", "the Reading badge"),
            ("/french/year-7/packs/countries/", ".badge.part.writing", "the Writing badge"),
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

        # Each mark belongs to one page: the DDB wordmark to the front door,
        # the GCSE roundel to /italian/, the Year 7 mark to /french/year-7/.
        # Below those, a mark competes with the material rather than
        # introducing it, and the breadcrumb D is the only branding.
        for path, why in (("/units/1/sessions/2/", "a lesson page"),
                          ("/french/year-7/packs/greetings/", "a French pack"),
                          ("/french/year-7/tests/writing/", "a French test page"),
                          ("/french/year-7/packs/greetings/cards/", "a flashcard page")):
            page.goto(f"{ROOT}{path}")
            if page.locator(".logomark").count():
                fails.append(f"a logo is on {why}, where it competes with the material")

        # Each page carries its own mark and nobody else's, and each mark is
        # measured: loaded, wide enough to read, named for a screen reader, and
        # reserving the right space before it arrives.
        for path, want, _file, why in MARKS:
            page.goto(f"{ROOT}{path}")
            marks = page.locator(".logomark")
            if marks.count() != 1:
                fails.append(f"{why}: {path} has {marks.count()} marks, expected 1")
                continue
            img = marks.first
            got = img.get_attribute("class") or ""
            if want not in got:
                fails.append(f"{path} carries {got!r}, not {want}")
                continue
            box = img.bounding_box()
            notes.append(f"{why}: {round(box['width'])}x{round(box['height'])}px, "
                         f"alt {img.get_attribute('alt')!r}")
            if box["width"] < 120:
                fails.append(f"{why} renders at {round(box['width'])}px wide")
            if not (img.get_attribute("alt") or "").strip():
                fails.append(f"{why} has no alt text")
            mark_reserves_right_space(img, why)

        page.goto(f"{ROOT}/")
        if page.locator(".logomark.is-italian").count():
            fails.append("the Italian mark is on the front door, branding the site one subject")

        # The Year 7 mark, measured.
        #
        # Three ways this breaks without anything throwing. The file can fail
        # to load, and a broken <img> with width and height attributes still
        # lays out at the right size, so the box alone proves nothing —
        # naturalWidth does. The white card it was drawn on can survive the
        # cut-out, which looks fine on the light theme and is a glaring
        # rectangle on the dark one. And the heading can go back to repeating
        # what the mark already says.
        page.goto(f"{ROOT}/french/year-7/")
        fr_mark = page.locator(".logomark.is-french")
        if fr_mark.count() != 1:
            fails.append(f"the French front page has {fr_mark.count()} French marks")
        else:
            box = fr_mark.bounding_box()
            nat = fr_mark.evaluate(
                "e => [e.naturalWidth, e.naturalHeight, e.complete]")
            notes.append(f"french logo: {round(box['width'])}x{round(box['height'])}px "
                         f"from {nat[0]}x{nat[1]}, alt {fr_mark.get_attribute('alt')!r}")
            mark_reserves_right_space(fr_mark, "the French mark")
            if box["width"] < 120:
                fails.append(f"the French mark renders at {round(box['width'])}px wide")
            if not (fr_mark.get_attribute("alt") or "").strip():
                fails.append("the French mark has no alt text")
            # The heading must not simply repeat the mark. Both other marked
            # pages say something the mark does not — "Which one?" under the
            # site wordmark, "Italian at home" under the roundel.
            h1 = (page.locator(".masthead h1").inner_text() or "").strip().lower()
            alt = (fr_mark.get_attribute("alt") or "").strip().lower()
            if h1 == alt:
                fails.append(f"the heading {h1!r} repeats the mark's own words")

        # The cut-out: the corners of the served PNG must be transparent, or
        # the mark is a white rectangle on the dark theme.
        png = page.request.get(
            f"http://127.0.0.1:{httpd.server_address[1]}{BASE}/logo-french.png")
        if png.status != 200:
            fails.append(f"logo-french.png is {png.status}")
        else:
            edges = page.evaluate("""async (bytes) => {
                const blob = new Blob([new Uint8Array(bytes)], {type: 'image/png'});
                const bmp = await createImageBitmap(blob);
                const c = new OffscreenCanvas(bmp.width, bmp.height);
                const g = c.getContext('2d');
                g.drawImage(bmp, 0, 0);
                const at = (x, y) => Array.from(
                    g.getImageData(x, y, 1, 1).data);
                return {size: [bmp.width, bmp.height],
                        corners: [at(1, 1), at(bmp.width - 2, 1),
                                  at(1, bmp.height - 2),
                                  at(bmp.width - 2, bmp.height - 2)]};
            }""", list(png.body()))
            notes.append(f"french mark corners: "
                         f"{[c[3] for c in edges['corners']]} alpha")
            opaque = [c for c in edges["corners"] if c[3] > 16]
            if opaque:
                fails.append(f"the French mark's background was not cut out "
                             f"({len(opaque)} opaque corner(s)) — a white rectangle "
                             f"on the dark theme")

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
