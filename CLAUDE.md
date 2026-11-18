# Working on this repository

Two things, published as one static Astro site through GitHub Pages: a two-year
Edexcel GCSE Italian (1IN0) course taught at home, and a Year 7 French revision
section for school tests. `README.md` says how to run and publish it;
`DECISIONS.md` says why it is the way it is and is worth reading before arguing
with it. This file is the part that is easy to get wrong.

**Most of this file is about the Italian course.** Where a rule is about one
subject and not the other it says so — the examined-vocabulary rule and the
specification rules below are Italian's, and the undated rule is Italian's too.
The French section has its own section at the end.

## The shape of the work

Adding to the course is adding files. A session is
`src/content/sessions/<uu>-<n>.mdx` and its deck is
`src/data/decks/<uu>-<n>.json` — the same name, and a session is not finished
until its deck exists. A unit adds `src/content/units/unit-<uu>.mdx`. Nothing
central needs editing: the unit page, session page, deck page, record sheet and
navigation are all generated.

**The template owns the shape of a page.** A unit file's body is its
introduction and nothing else — the can-do list, the `insist` note and the
`contingency` list are frontmatter, and `src/pages/units/[unit]/index.astro`
decides where they go. Do not write a can-do list, a "Can-do check" heading, a
session list or a contingency section into a unit's body: the template already
renders all four, and doing both is how Unit 1 ended up printing its can-dos
twice.

## Building a unit

The brief for every unit already exists: the Stage 1 units page gives its
grammar, language field, can-do and task, and the grammar checklist gives the
points in teaching order. Neither says how to teach it — that is the writing.

**Always check the examined vocabulary list.** Every Italian word a unit teaches
is either on Appendix 3 of the specification or a deliberate exception with a
reason. Not "mostly", and not by eye: fluent, plausible Italian is exactly what
gets written when nobody checks, and a child drilling a word that is not on the
list is spending their time on something the exam will not ask for.

The list is Pearson's copyright and is not in this repository. Produce it once,
per machine, from the specification PDF:

```
python3 tools/check_vocab.py path/to/specification-....pdf
python3 tools/vocab.py --selftest    # the parser still reads it correctly
```

Point it at the PDF and it extracts the text itself, caching it as
`tools/spec.txt` so later runs are instant. It needs `pdftotext` on PATH
(poppler) and says how to get one if it is missing.

`tools/spec.txt` is gitignored. Without it the check exits non-zero and says so
rather than passing quietly — a vocabulary check with no vocabulary list looks
exactly like one that found nothing.

It reports four things. Words on the list; inflected forms of listed words
(*chiamo* → *chiamare / chiamarsi*), shown so you can see they were understood;
words named in Appendix 2, the grammar list, which is where the articles,
pronouns and prepositions live — Unit 2 teaches *il* and *lo*, and neither is
vocabulary; and words on none of those footings, which fail the run.

It also checks that any card teaching an article with its noun agrees with the
list: gender, and the *lo/uno* rule, and *l\'* before a vowel. A unit about
gender that shipped *la libro* would be teaching the mistake it exists to
prevent, and re-reading does not catch that reliably.

`tools/vocab.py` does the parsing and has a `--selftest` that asserts known
genders and refuses parsing debris. Run it whenever the specification is
re-extracted. It is not decoration: the first version of it read the gender in
*camera da letto (f)* as belonging to *letto*, and separately truncated every
noun beginning with an article — *lavagna* became *vagna* — so that a unit about
gender would have been built on a table that was quietly wrong.
An off-list word is not automatically wrong — Unit 1 teaches *gnocchi* and
*spaghetti* for their sound in a unit that says not to teach their meaning — but
it has to be a decision, so each one goes in `src/data/off-syllabus.json` with a
reason. Prefer fixing to declaring: the check found the stress deck teaching
*medico*, which is not on the list, where *musica* makes the identical point and
is.

## Working practice

These predate the website and were nearly lost with the folder it replaced.
They are the project's rules, not the site's.

- **One unit at a time.** Build the next unit only after the previous one has
  been taught, or at least started, so it can be calibrated to how it landed.
  Do not batch-produce units nobody has tried. This is the rule most likely to
  be broken by enthusiasm, and it was broken once already — Unit 2 was built
  without anyone asking whether Unit 1 had been taught.
- **Ask before assuming prior knowledge.** If it is unclear whether something
  has been covered, ask rather than guess.
- **Say when something cannot be done.** Access limits, blocked deletions,
  format constraints — say so plainly rather than working around them quietly.
- **Push back where the plan looks wrong.** Sitting this qualification this
  young is ambitious. If evidence starts to suggest it is not working, say so
  rather than producing the next unit on schedule.
- **No progress inflation.** If work is weak, say it is weak and say what to do.
- **Write decisions down as they are made.** A convention that lives only in a
  conversation is lost when the session ends.

## What the specification requires

Check these against the specification, a past paper or a mark scheme, never
from memory. For anything about *marks* the mark scheme outranks the other two:
the specification says what is on the course, the paper shows what is asked, and
only the grid says what is rewarded.

- **Mark the tier of every grammar point** — F, H, or receptive-only (R). The
  Foundation-to-Higher receptive/productive shift is the most important
  distinction in the grammar appendix; preserve it. It is also the top band:
  the writing mark scheme defines Higher "complex language" as, first on its
  list, the grammar specific to Higher tier.
- **Two Foundation limits that catch people out.** The imperfect is productive
  only for *avere*, *essere*, *stare* and *fare*. The conditional at Foundation
  means *vorrei* and *mi piacerebbe* and nothing else.
- **Register is examined.** Build it into every session involving speaking to
  someone. The formal writing question is 28 of 60 marks on Higher and 16 of 60
  on Foundation. Register is a bullet in the communication and content grid — it
  holds down the larger of the two grids, it does not cap the paper, and saying
  it caps the paper is the kind of overstatement this list exists to prevent.
- **Justified opinion.** The grids define *straightforward* language partly as
  opinions stated without justification, and straightforward is the band below
  the top ones. From Unit 8 onwards, no opinion without a reason.
- **Past, present and future are all required** in the picture task, at both
  tiers, and handling all three accurately is what the accuracy grid uses to
  describe its top bands.
- **Know which errors are cheap.** The writing mark schemes rank errors in three
  named bands, identically at both tiers, and the ranking is not the intuitive
  one:
  1. *Do not hinder clarity* — gender, adjective agreement, and the definite and
     indefinite articles, named explicitly. The top band is reachable with them.
  2. *Hinder clarity* — tense and time-frame confusion, a possessive mismatched
     to its subject, and any error frequent enough to distract.
  3. *Prevent meaning* — the wrong message, the wrong person of the verb,
     Anglicisms and mother-tongue interference.

  So never write that an article or an agreement is "worth a mark" — Unit 2 said
  exactly that and it was wrong. Teach gender with the noun because it is cheap
  early and expensive to retrofit, and because plurals and agreement need it, and
  say that rather than inventing a mark for it. Where teaching time is scarce it
  comes off agreement and goes to verb person, tense, and translation into
  Italian.
- **Do not reproduce the vocabulary appendix.** Reference it, structure work
  around it, quote only what a task needs. It is Pearson's material. The mark
  grid descriptors are too: paraphrase them, never paste them.

## Read the unit before it ships

**A unit is not finished when the checks pass. It is finished when it has been
read end to end, against this list, and the reading is done before it ships and
not after.**

That is not a general exhortation to be careful. Units 1 and 2 passed every
check and were shipped, and reading them afterwards found nine problems, of
which the tools had caught none — including the stress deck's first card
teaching the opposite of its own rule. These are the classes that only reading
finds, each one written here because it actually happened:

1. **Check every claim against the rest of the course, not the page.** Session 1
   said there are no silent letters in Italian; Session 2 teaches two of them.
2. **Check every promise the introduction makes against the sessions.** The unit
   intro said a dozen rules let you pronounce any word on sight; Session 4
   spends half an hour showing that unmarked stress does not work that way.
3. **Trace every fact about the exam to a source, and prefer a real paper to
   the specification.** "Handwriting is examined in two of the four papers" was
   asserted twice, weakened because the specification never says what language
   Paper 3's answers are in, and then restored because the June 2025 paper
   shows Section B answered in Italian — and then corrected a third time, and
   this is the settled version: Paper 4 is the only paper that requires
   *producing* written Italian. The specification says outright that Paper 1
   needs none. Paper 3 Section B is set and answered in Italian, but at
   Foundation that is a word-box gap-fill — the June 2025 paper's question 7
   supplies the words and the candidate copies one into each gap — and only
   Higher has a short open response there. Say "Paper 4 is written in Italian
   throughout" and stop.

   The specification describes the qualification; the papers show what it does;
   the mark schemes show what it pays for. Unit 2 shipped saying the *un'amica*
   apostrophe "is one mark on paper". There is no such mark, and the same mark
   scheme names article errors as the kind that do not affect meaning — a claim
   about marks that had never been near a mark scheme.
4. **Every rule must cover every word the unit teaches.** Session 1's gender
   rule handled -o, -a and -e; Session 3 drilled *lo sport* and *lo yogurt*,
   which are none of those.
5. **Every word taught in prose or in the notebook needs a card.** *il cane*,
   *la classe* and *un amico* were each taught and never drilled — the last is
   half of the trap its session turns on. `check_vocab.py` lists the candidates
   under "on no card in that unit"; it does not decide, because some are meant
   to be uncarded.
6. **Read every pronunciation guide as an English speaker would read it.**
   *STAI* reads as "stay", *e TOO* wants to be "eh TOO".
7. **Measure every number.** "Six nouns in ten" was really seven, which made the
   rule sound weaker than it is. `tools/vocab.py` can count.

## The Year 7 French section

Revision for two school tests, which is a different job from a designed course
and so a different shape: ten packs, two test pages, and no units or sessions.
`src/data/french/` holds all of it and `tools/check_french.py` checks it.

- **There is no specification to check against.** The Italian course has
  Pearson's published vocabulary list, so `check_vocab.py` can say whether a
  card teaches something real. Here the source is his exercise book, and once
  it has been typed in nothing outside the repository can confirm it. So
  `check_french.py` checks the files against *each other* — that a test lists
  the packs that claim it and no others, that every answer he is marked against
  is spelled the way some pack spells it, that known accents and hyphens are
  present. That catches drift between files, which is how most of it would go
  wrong. **It does not catch a word that was typed in wrongly from the start.**
  Say so rather than implying the checks mean more than they do.
- **Dates belong here and only here.** `src/pages/french` and
  `Countdown.astro` are exempt from the no-calendar-years rule; everything else
  in `src/` still is. Keep the dates in the test data, not in a template.
- **Nothing is stored.** No localStorage, in either section. Exercises mark in
  memory and forget.
- **Flashcards are derived, never written.** `src/lib/packcards.ts` builds them
  from the pack's word list. Add a word to a pack and its card appears.
- **Every proper noun is declared** in `src/data/french/names.json`, with a
  reason. The check fails on any that is not. It is an allowlist on purpose:
  a list of forbidden names would have to contain the real one.
- **Marking is strict on accents, capitals and hyphens**, and forgiving of a
  curly apostrophe and the space before `?` and `!`. Those two are keyboards,
  not French. `src/scripts/marking.ts` is the only place that decides this, and
  `check_site.py` drives it both ways in a browser.

## House rules for content

- **Nobody real appears.** Where a lesson needs a name it is invented and
  Italian, or a role. The Unit 1 dialogue runs between *You* and *Child*, and
  the slot where a name belongs is written `[name]`. Never a real name.
- **Nothing is dated.** Timelines are `Year 1 · autumn` … `Year 2 · May/June`.
  No calendar years — the course does not start in a particular September. If
  an external deadline must be described, say what it *has* been and tell the
  reader to check their own year.
- **Do not assume how many children.** "A child", "them", "each learner". Where
  it genuinely matters, "if you are teaching more than one".
- **No pointing outside the site.** No local folders, no "see the tracker", no
  "in this folder". A reader has a browser and nothing else.
- **Check a claim against the rest of the page.** "Nothing but a recorder and
  these pages" sat directly above a box demanding a notebook for every session.

## The logo

`public/logo.png` is the mark. It reads "GCSE Italian", so it belongs to the
Italian course: it appears on `/italian/` and nowhere else. Not on the front
door, where it would brand a French page Italian; not above a lesson, where it
competes with the material rather than introducing it.
`tools/make_icons.py` derives every icon from it and needs Pillow.

It is a circular mark with a ring, three lines of text and a drawing inside it.
That reads down to about 64px and no further: at 32px only the word "Italian"
survives and at 16px it is a smear, so the two small favicons are a drawn serif
I in the logo's own navy on its own cream rather than the logo shrunk. If the
logo is replaced, look at `favicon-32.png` before assuming the new one scales.

The file arrived as RGB on white, which renders as a glaring square on the dark
palette. `make_icons.transparent()` cuts the background by filling inward from
the border, which stops at the ring and so leaves the cream inside it intact.

## House rules for code

- **Scoped styles do not reach elements JavaScript creates.** Astro scopes a
  component's CSS with a `data-astro-cid-*` attribute that only elements written
  in the file receive. `document.createElement("button")` gets no such
  attribute, so `.chip { … }` in `Flashcards.astro` compiled to a selector that
  could never match and the deck chips rendered as bare boxes reading
  "Vowels5". Hang such rules off a static ancestor — `.decks :global(.chip)` —
  which is in the markup and does carry the attribute.
- **Inline HTML in a prop needs `set:html`.** `lead`, `insist` and
  `contingency` items carry `<em>` and `<strong>`. Rendering them as `{value}`
  prints the tags.
- **MDX is JSX.** Void tags self-close, a list item must be on one line, and a
  bare `<` in prose is read as a tag.
- **`:global()` is Astro `<style>` syntax, not CSS.** `src/styles/house.css` is
  imported as a plain global stylesheet, so a rule written
  `.exercise :global(.exbtn)` there is invalid and the browser drops the whole
  rule. It does not look dropped: the element falls back to the browser's own
  grey button, which is why an assertion that only asked "is anything painted?"
  passed against the bug. Assert the actual value — the computed background
  against `--accent` — and prove it fails before calling it done.
- **Text on a solid accent block uses `--on-accent`, never `#fff`.** The light
  theme's accent is a dark red and the dark theme's is a light salmon; white
  serves the first and fails the second at 2.7:1. `check_site.py` measures it
  in both themes and was proved against the bug.
- **Always name the encoding.** `read_text()` and `write_text()` without
  `encoding="utf-8"` are how the decks came to say *cittÃ* and *â* instead of
  *città* and an em dash — text already in UTF-8, decoded as Latin-1 and
  encoded again. It survived a month because nothing throws.

## Before committing

```
npm run build
python3 tools/check_all.py
```

`check_all.py` runs five checks now; `check_french.py` needs nothing and so
runs everywhere, CI included.

Then read the unit, against the list above. That runs all five and says which
of them did not run — a skipped check and a
passing check look identical otherwise. `check_site.py` needs a build and a
browser; the two vocabulary checks need `tools/spec.txt`. CI has neither the
specification nor a browser, so it runs `check_text.py` alone and the rest are
yours to run before you push.

`check_site.py` is not decoration. Every failure this project has shipped was
silent — nothing threw, the page just looked wrong — so it asserts computed
styles and positions, not only text. **When you fix a bug of that kind, add the
assertion that would have caught it, and prove the assertion fails against the
bug before you call it done.** Every guard in these tools was verified that way,
against the actual defect it exists for.

**Verify in the browser, not by grepping the HTML.** Astro's entity encoding
does not match what you expect, and a `grep` that returns 0 will convince you a
working feature is broken. It has already happened once.

## Publishing

Push to `main`. The workflow checks, builds and deploys.

**The base path follows the repository's name and is never written down.** A
GitHub project page is served from `/<repo>/`, so `astro.config.mjs` reads it
from `GITHUB_REPOSITORY` (falling back to the checkout directory, overridable
with `BASE_PATH`), and `check_site.py` reads it back out of the build. Hard-code
it in either place and a rename leaves every stylesheet pointing at a path that
no longer exists — the site comes back unstyled with nothing in the build log to
say why. Renaming the repository is the only way to change the URL, and the
workflow must be re-run afterwards so the pages are rebuilt. Ref deletions and general outbound HTTPS are
blocked from the agent sandbox, so deleting a branch or opening the live URL is
a job for whoever is at a real machine.
