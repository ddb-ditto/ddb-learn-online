# Lessons and flashcards

Two things live here.

**A two-year Pearson Edexcel GCSE Italian (1IN0) course** taught at home. A unit
is a lesson plan, a set of flashcards per session, and a printable sheet for
recording what has actually been done.

**A Year 7 French revision section**, for two class tests at school. Ten short
packs — the words, the rule behind them, flashcards, and practice that marks
itself — and a page per test saying which packs to revise and in what order.

The front page is a choice between the two; each has its own contents page
underneath. They share the layout, the stylesheet, the flashcard app and the
checks, and nothing else. The Italian course is a designed sequence with no dates in it; the
French section is revision for a test on a named Wednesday. That difference is
why they are shaped differently rather than forced into one mould.

It is a static [Astro](https://astro.build) site, published to GitHub Pages by
GitHub Actions. A project page is served from a path named after the
repository, so **the URL follows the repository's name**: `astro.config.mjs`
reads it from `GITHUB_REPOSITORY` rather than hard-coding it, and renaming the
repository moves the site with no code change. Re-run the workflow afterwards
so the pages are rebuilt against the new path. `BASE_PATH` overrides it. There is no server, no database and no account: everything opens
in a browser, and anyone given the URL can read all of it.

## Running it

```
npm install
npm run dev       # http://localhost:4321/<repo-name>/
npm run build     # into dist/
npm run preview   # serve dist/ as it will be served
```

Node 22 or newer.

## Layout

```
src/
  content/
    units/       one file per unit: why it exists, and its can-do checks
    sessions/    one file per session — a single sitting
    reference/   teaching plan, the Stage 1 unit list, grammar checklist
  data/
    stage1.json  the fourteen units of Stage 1, built or not
    decks/       one file per session's deck, named for that session
    off-syllabus.json  words taught anyway, and why
    french/
      packs/     one file per revision pack: the words, the rules, the exercises
      tests/     one file per test: its date, its format, the packs it needs
      exercises/ one file per practice exercise, shaped by what it asks for
      names.json every invented person and place used, and why
  components/    the blocks the lessons are written out of
  layouts/       the one layout
  pages/         routes; the unit, session, pack and test pages are generated
                 from content. `/` is the two-door front page, `/italian/` the
                 Italian contents, `/french/year-7/` the French hub.
  lib/           a pack's flashcards, worked out from the pack's word list
  scripts/       the flashcard app and the exercise runner, bundled once
  styles/        the house stylesheet, loaded once
brand/           the logo artwork the icons are cut from, not served
tools/
  check_all.py       all of the below, reporting what could not run
  check_text.py      local paths, calendar years, encoding — run by CI
  check_french.py    packs, tests and exercises agree with each other
  check_vocab.py     every taught word is on the examined list
  vocab.py           reads the specification's vocabulary appendix
  check_site.py      open the built site in a browser and use it
  make_icons.py      icons, from brand/ — needs Pillow
```

Content is data. A session is an `.mdx` file with frontmatter; its schema is in
`src/content.config.ts` and the build fails if a field is missing. Adding a
session adds a page, a row on its unit's contents list, and a line on that
unit's record sheet — with no change to any template.

## Adding a session

1. Write `src/content/sessions/<unit>-<n>.mdx`. Copy an existing one: the
   frontmatter is checked, so a mistake is a build error rather than a bad page.
2. Write its deck at `src/data/decks/<unit>-<n>.json` — same name as the
   session. A session is not finished until its deck exists.
3. `python3 tools/check_vocab.py <specification>.pdf` — every Italian word it
   teaches is on the specification's vocabulary list, or declared in
   `src/data/off-syllabus.json` with a reason. Point it at Pearson's PDF and it
   reads the list itself; see `CLAUDE.md`.
4. `npm run build`, then `python3 tools/check_site.py`.

### Adding to the French section

A pack is `src/data/french/packs/<nn>-<slug>.json`; a practice exercise is
`src/data/french/exercises/<id>.json`; a test is
`src/data/french/tests/<slug>.json`. All three are checked by the schema in
`src/content.config.ts`, and `tools/check_french.py` then checks them against
each other — that a test lists the packs that claim it and no others, that
every answer a pack is marked against is spelled the way the pack spells it,
and that no proper noun appears that is not declared in `names.json`.

Flashcards are not written. `src/lib/packcards.ts` derives them from the pack's
own word list, so they cannot fall out of step with it; a pack with nothing to
drill simply has no cards page.

### A new unit

A new unit is the same as a session, plus `src/content/units/unit-<nn>.mdx`. Its body is the
introduction only: the can-do list, the one to insist on and what to do if it
goes badly are frontmatter, because the template decides where those go so
every unit's page reads the same way. Units listed in `stage1.json` with no
content show as *not built yet*, which is the honest state.

## Progress

`/progress/` prints a record sheet per child per unit: a tick box for each
session and a tick box for each of that unit's can-dos. It is paper by design —
nothing is stored on the site and there is no sign-in, so the sheet is filled in
by hand. The sheets are generated from the content, so a unit built later gets
its sheet for free.

## Publishing

Every push runs the checks; the default branch is published if they pass.

**One-time setup, and only the repository owner can do it:** in
**Settings → Pages**, set *Source* to **GitHub Actions**. Until then the checks
run and pass but the publish step fails with `Get Pages site failed` — there is
nowhere to publish to. Letting the workflow enable Pages itself was tried and
does not work: `GITHUB_TOKEN` is refused when it tries to create the site.

The site is then at `https://ddb-ditto.github.io/<repo-name>/`. That path is
the repository's name and nothing else, so **renaming the repository moves the
site**. No code changes when it does — `astro.config.mjs` reads the name from
`GITHUB_REPOSITORY` — but the workflow has to be re-run afterwards, because a
rename does not rebuild the pages and they still point at the old path.

## Who can see it

The repository must be **public**. Pages from a private repository needs a paid
plan for *the account that owns the repository* — a personal account on Free
gets an upgrade prompt regardless of what other plans you hold elsewhere.

Public is the intended end state, not a workaround: the site is meant to be
read by anyone given the link.

## Before publishing

`python3 tools/check_text.py` scans every text file for the two things that get
in without anyone meaning them to: a local file path, which names whoever owns
the machine and is permanent once the repository is public, and double-encoded
UTF-8, which shipped a deck reading "cittA" for a month of nobody noticing. CI
runs it before the build.

Where a lesson needs a name it uses an invented Italian one, or a role: the
dialogue in Unit 1 is between *You* and *Child*, and the one slot for a name is
written `[name]`.

## Checking it before you trust it

```
python3 tools/check_text.py                   # run by CI
npm run build && python3 tools/check_site.py   # opens it and uses it
```

`check_site.py` drives a real browser at phone width: the contents page, the
reference pages, a unit, a lesson, the breadcrumb trail on each, the progress
sheets, and the flashcard app — that it opens on card one unshuffled, flips,
wraps at both ends, switches decks and builds its print sheets. It asserts
computed styles as well as text, because the failures that matter here are
silent: nothing throws, the page just looks wrong.

## Where it is up to

**Built:** Unit 1 in full — an introduction, five session pages, five decks and
89 cards — the teaching plan, the Stage 1 unit list, the grammar checklist, and
record sheets for everything built. Units 2–14 show as not built yet.
