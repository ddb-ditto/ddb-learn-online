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
  card teaches something real. Here the source is the class's own work, and once
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
- **No progress is stored.** Exercises mark in memory and forget: there is no
  account and no score that outlives the tab. Four things are kept in
  `localStorage`, each a setting rather than a judgement, each a deliberate
  exception written down here — the colour theme, the reading switch
  (`fr7:plain`), which Leitner box a French card is in, and which voice reads
  the French aloud (`fr7:voice`). Nothing that describes how he did is stored,
  and nothing stored leaves the device. Anything new in there needs a line in
  this list or it is a mistake.
- **Flashcards are derived, never written.** `src/lib/packcards.ts` builds them
  from the pack's word list. Add a word to a pack and its card appears.
- **A wrong answer is highlighted only when the highlight points at
  something.** The character diff is for a missing accent or a dropped hyphen.
  Given an answer nowhere near the right one it finds whatever letters happen
  to coincide and marks up everything else, so the correct version comes back
  in fragments with holes in it — which reads as a bug, and was reported as
  one. `similarity()` in `marking.ts` gates it: under a half, print the answer
  plain. Measured on the real pack data, genuine near misses score 0.71 and
  above and nonsense scores under 0.15.
- **"Just what I need" takes prose, never material.** `ReadingMode.astro` is
  a switch, remembered across the French section, that hides the notes written
  for the parent and folds the ones written for the learner down to their
  heading. It must never touch a word table, a rule, an exercise or an
  exercise's instructions — those are what he came for, and an exercise intro
  is how to play it, not commentary. `check_site.py` asserts that by
  visibility, not by counting elements: `display: none` leaves them in the DOM.
  It is off by default, because a parent opening a pack should see all of it.
- **A pack never says what the learner got wrong.** It is read by the person
  it was written for, so a page saying "twelve things he has actually got
  wrong" tells him that about himself every time he opens it — and the words
  are worth drilling whoever first misspelled them. Say what is hard about the
  French. `check_french.py` fails on `he`, `him` or `his` in any learner-facing
  pack text, with the honest uses (French gendered pronouns, Louis Pasteur)
  exempted. The same goes for comments: this repository is public and the
  child is real.
- **Every proper noun is declared** in `src/data/french/names.json`, with a
  reason. The check fails on any that is not. It is an allowlist on purpose:
  a list of forbidden names would have to contain the real one.
- **Every one-at-a-time exercise steps both ways.** `stepper()` in
  `exercises.ts` builds the bar, so the four kinds agree. The unmarked kind
  (speaking practice) wraps at both ends like the flashcards; the marked ones
  do not, and an item already answered comes back read-only — re-answering it
  would double-count the score underneath. All four shipped with a Next and no
  Back.
- **The French cards have a Leitner box; the Italian ones do not.** Three
  boxes, in `leitner.ts`, turned on per page with `practise` on `Flashcards`.
  It stores **only which box each card is in** — never a score, a count, a
  date or anything that leaves the device — keyed on the pack's slug rather
  than the URL so moving the site does not lose it, and written to be lost
  safely: an empty box is just a deck starting at the beginning. The Italian
  decks stay as they were, because the teacher is in the room there.
- **Marking is strict on accents, capitals and hyphens**, and forgiving of a
  curly apostrophe and the space before `?` and `!`. Those two are keyboards,
  not French. `src/scripts/marking.ts` is the only place that decides this, and
  `check_site.py` drives it both ways in a browser.
- **The voice is the device's, and silence beats an English accent.** The
  audio is the browser's own synthesiser, so the only voices available are the
  ones already installed — a static site cannot ship one. `speech.ts` is the
  only place that decides which: French voices only, a named Apple, Google or
  Microsoft voice preferred over the device default, `rate` 0.9 because the
  default pace is too quick to copy, and a picker rendered only where the
  device has more than one.

  **`utterance.lang` is a hint, not a guarantee.** It does not make a device
  find a French voice, and the old code asked only whether the browser had a
  speech API at all — true everywhere — so the ♪ Hear it button appeared on
  machines that read the French in an English accent and on machines with no
  voices at all, where pressing it did nothing. Both were invisible to
  reading: the DOM is identical either way. `check_site.py` now replaces the
  voice list before the page's scripts run and drives the button against nine
  shapes of device, including a list that arrives late, which is what Chrome
  really does — `getVoices()` is empty on the first call and announced by
  `voiceschanged`.

  If pre-recorded audio is ever added, this becomes the fallback rather than
  the main event, and a missing clip is what it falls back to.
- **`lang="fr"` is what makes something speakable, and that is the whole
  rule.** A speaker appears beside every element the markup declares as
  French — `sayfrench.ts` walks `[lang="fr"]` — so there is no list of
  selectors to keep in step with the templates, and the Italian course is
  excluded for free because nothing in it carries that attribute. Marking
  something `lang="fr"` that is not French will make it speak, which is the
  trade for not keeping a list: `check_site.py` counts the speakers per page
  so a jump shows up. The pronunciation column, the alphabet's respellings and
  the English glosses are deliberately unmarked — "ko-koo" and "bay" are
  English spelling describing a French sound, and a French voice reading them
  teaches the error the column exists to prevent.
- **Audio never reads French that is wrong on purpose.** *Spot the mistake*
  prompts with a misspelling and *Put the punctuation back* prompts with the
  punctuation stripped out. Spoken, both are **identical to the correct
  sentence** — the final *-s* of *appelles* is silent — so the audio teaches
  nothing and implies the spoken form is what is being marked. Exercises name
  their French fields in `speak`; it is a declaration because "is this
  French?" is not a question the code can answer. Same reasoning as
  `packcards.ts` not making flashcards out of misspellings.
- **Audio never reaches an answer before he has committed to one.** The
  covered-answer rule is the spine of the exercises, and a speaker on a
  hidden answer would undo it by sound instead of sight. The gap-fill will
  not read the passage until Check has been pressed, because the filled
  passage *is* the answers; `type` and `order` attach their speaker when the
  answer is marked, not when it is built.
- **A revealed answer is green only where nothing is being marked.** The
  three unmarked reveals print their answer in the green block, like the
  model answer in the speaking practice: one colour, one meaning, "this is
  the right one". They used to print it in `var(--accent)`, which is this
  section's colour for *wrong*. Everything that marks — `type`, `order`,
  `gapfill`, `truefalse`, the quiz — shows its answer **because he got it
  wrong**, so green there would put the "you were right" colour on a failed
  attempt beside a red input in the same exercise. Those stay neutral.

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

There are three marks, and each belongs to one page — the front page of what
it names, and nothing below it.

`public/logo-site.png` is the DDB wordmark. It is the site's, so it goes on the
front door. `public/logo.png` is the Italian GCSE wordmark, which says so on
its face, so it stays on `/italian/`. `public/logo-french.png` is the Year 7 French
wordmark and stays on `/french/year-7/`. None of them goes above a lesson, a
pack, a test or a deck, where it would compete with the material rather than
introduce it. `Base.astro` takes `logo="site"`, `"italian"` or `"french"`;
anything else gets none.

**The front door has no heading, so its mark carries the h1.** The eyebrow,
the heading and the standfirst were taken off that page: the mark says the
site's name better than a line of type, and the two doors say the rest. Two
things had to change with them. The masthead rendered only when there was a
heading, so removing the words would have removed the mark too — a front page
with no branding at all, and nothing in the build to say so. And a page needs
an h1, so when there is no heading the mark goes *inside* one and its alt text
becomes the page's accessible name. A front page with no h1 looks perfectly
fine in the markup and gives anybody arriving by search or by screen reader a
page with no name.

**The heading under a mark says something the mark does not.** "Which one?"
sits under the site wordmark and "Italian at home" under the Italian one. The
French page's heading was "Year 7 French" above a mark reading YEAR 7 FRENCH,
and its eyebrow said it a third time, so the heading is now "French at school"
— which is also the true distinction between the two sections, one taught at
home and one revised for school. `check_site.py` fails if a heading matches
its mark's alt text.

**A supplied cut-out is not a cut-out until it has been looked at.** The DDB
wordmark arrived as a PNG with an alpha channel already set, and the alpha was
wrong: strictly binary, 0 or 255 with nothing between, and whole patches of
the green card left opaque — a circle bottom left, another bottom right, a
patch above the second D. They read as olive smudges on cream and holes on
navy. Corner alpha would never have found them, because the corners were
already clear. `dechroma()` keys the card out on two tests, because neither
catches the other's case: any pixel where green beats both other channels,
and any pixel within 100 in RGB of the card's own colour, which finds the
blended edge pixels whose green no longer dominates. Then it clamps green to
the larger of the other two channels, which removes the keyed-image rim and
touches nothing else — in red, blue, yellow, black and white, green is always
the middle channel or the smallest.

**"Is it green?" is not the test; "is it *that* green?" is.** The first
version of the check failed a correct file 424 times. Yellow blended with
blue makes green, this artwork has yellow shapes against blue ones, and every
downscale averages the boundary. The check measures distance from the card's
sampled colour instead.

**Quantise the alpha with the colour, not beside it.** `quantise()` used to
split the alpha off and put a full eight-bit channel back afterwards. On flat
artwork that costs nothing; on comic halftone, where every dot is its own
island of alpha, it cost five times the file — 256 KB against 49 KB for
output that differs by a mean of three parts in 255 over either theme. On the
page everybody loads first.

**Pillow's `resize` already handles alpha.** The usual advice is that it
averages the colour behind transparent pixels into the ones beside them and
that you must premultiply by hand. A hand-rolled premultiply was written,
measured against a plain `thumbnail` and found byte-for-byte identical, so it
was taken back out. A guard that prevents nothing, with a comment saying it
prevents something, is worse than no guard.

**Both wordmarks are keyed, not flooded.** The French mark arrived on white
to begin with and was flooded out from the border; its replacement arrives on
the same green card as the DDB one, with the same bad binary alpha, so both
now go through `dechroma`. `brand/french.png` and `brand/wordmark.png`, both
PNG because both carry an alpha channel that cannot be trusted but cannot be
thrown away either.

**A check written for one mark has to be written for all of them.** The
reserved-size check lived inside the site logo's block, so replacing the
French artwork with one of a different shape sailed straight past it. It is
`mark_reserves_right_space()` now and both marks are put through it. When a
third mark appears, put it through too.

**A wordmark drawn on white has to have the white cut away**, or it is a
glaring rectangle on the dark theme — and that is invisible while you work in
the light one. `make_icons.transparent()` floods inward from the border and
stops at the artwork, so enclosed white survives: the French mark's own white
lettering, the word YEAR, is ringed by a dark outline and comes through the
cut intact. `check_site.py` reads the served PNG's corner alpha in the browser.
It also reads `naturalWidth`, because an `<img>` that failed to load still
lays out at its `width` and `height` attributes — the box measures right and
the page is empty where the mark should be.

A third place carries the mark: the breadcrumb bar, as the drawn D at 20px.
It is the only branding on a lesson or a pack, where the wordmark would
compete with the material. It goes *inside* the centred `.crumbrow`, not
before it — the row is narrower than the body and has its own centring, so a
mark outside it pins itself to the window's edge and drags the crumbs out of
line. `check_site.py` measures the row's centring and the mark's position at
two widths.

The artwork both are cut from lives in `brand/`, outside `public/` because it
is a source rather than something the site serves. `tools/make_icons.py`
regenerates everything from it and needs Pillow.

Neither mark survives being shrunk to a favicon, so 32px and 16px are a drawn
D in the brand's yellow on its navy — one shape, the right first letter, and no
dependency on a font. Build it from masks: the first attempt painted the bowl
over the stem and squared the left edge off afterwards, which erased the stem
and produced something that read as a C.

**The comic wordmark is not an icon, and was tried.** `brand/wordmark.png`
was offered as a favicon, squared off to 512px. At 32px it is coloured mush
beside the drawn D — four colours, a halftone texture, an outline and a
tagline inside 32 pixels — and at 16px there is nothing at all. As a
home-screen icon it is no better: its content is 432x255, a wide mark on a
square canvas, so it leaves empty bands top and bottom and its letters come
out about half the size of `brand/appicon.jpg`'s, which is composed for a
square. Rendered side by side at 180, 96, 64, 32 and 16 and decided by
looking. The icons stay as they are.

**The app icons are upscaled and should not be.** `brand/appicon.jpg` is
272x271, so `icon-512.png` is a 1.88x enlargement of it. 192 and 180 are
downscales and fine. If a square-composed mark ever arrives at 512px or more
— letters filling the frame, no tagline — it fixes that and can take every
size above 64px. The two smallest stay drawn whatever arrives.

**The manifest is generated**, at `src/pages/manifest.webmanifest.ts`. As a
static file in `public/` it hard-coded the old repository name in `start_url`,
`scope` and every icon path, so the rename broke the installed app and nothing
said a word — no build error, no console message. Anything carrying the base
path has to be generated.
`tools/make_icons.py` derives every icon from it and needs Pillow.

**All three marks are generated now, and all three go through `dechroma`.**
The Italian one used to be a circular roundel committed straight to `public/`
with no source in `brand/` at all, so nothing regenerated it and nothing
checked it. It is `brand/italian.png` and `make_icons.py` builds it like the
others.

That also emptied the stylesheet's default. `.logomark` was the roundel —
150px wide and pulled 0.35rem left to take up the air inside its ring — with
the two wordmarks overriding it. All three are wide wordmarks now, so there
is one rule and no exceptions. If a roundel ever comes back it needs its own
class, not a change to the default.

**`transparent()` is still there and is now used by nothing.** It flood-fills
white inward from the border, which is right for artwork on a white card and
wrong for these, which arrive on green with an alpha channel that has to be
ignored. Left in place because the next piece of artwork may well arrive on
white again.

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
- **`[hidden]` is the weakest rule in CSS.** Any class that sets `display`
  beats the browser's own `[hidden] { display: none }`, so an element whose
  `hidden` property is perfectly true sits there on screen — and the DOM looks
  right, which is why it survives review. `house.css` now forces it globally.
  Assert the computed `display`, not the attribute.
- **`:global()` is Astro `<style>` syntax, not CSS.** `src/styles/house.css` is
  imported as a plain global stylesheet, so a rule written
  `.exercise :global(.exbtn)` there is invalid and the browser drops the whole
  rule. It does not look dropped: the element falls back to the browser's own
  grey button, which is why an assertion that only asked "is anything painted?"
  passed against the bug. Assert the actual value — the computed background
  against `--accent` — and prove it fails before calling it done.
- **The dark tokens exist twice, and the duplication is checked.** Once under
  `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`,
  which is what a browser with no JavaScript gets, and once under
  `:root[data-theme="dark"]`, which is what the colour switch sets. CSS cannot
  share one declaration between a media query and a selector, so the two
  copies drift — `check_site.py` loads the site on a dark device with no
  override and on a light device with the switch forced to dark, and fails if
  any of the seventeen tokens differ. Add a token and add it to both blocks
  and to that list.
- **The saved theme is applied inline in `<head>`.** From the bundle it would
  run after the first paint, so a page set to dark arrives white and then
  turns. "Match my device" means no attribute at all, not a third value.
- **Text on a solid accent block uses `--on-accent`, never `#fff`.** The light
  theme's accent is a dark red and the dark theme's is a light salmon; white
  serves the first and fails the second at 2.7:1. `check_site.py` measures it
  in both themes and was proved against the bug.
- **Some browser globals cannot be assigned over, and fail silently.**
  `window.speechSynthesis` is a read-only accessor on `Window.prototype`, so
  `window.speechSynthesis = stub` in a non-strict script does nothing at all
  and throws nothing either. The voice checks appeared to find eight real
  failures before this was spotted — the test harness, not the site, was
  broken. Use `Object.defineProperty(window, name, { value, configurable: true })`,
  and have the stub assert it installed, so a harness that failed says so
  instead of reporting the page as broken.
- **An assertion gated on something optional may never run.** The wi-fi
  warning on the voice picker was checked only when a picker existed, and the
  case it was written for had a single voice, so no picker rendered and the
  check was dead code — it passed against a build with the warning removed.
  Proving an assertion against its bug catches this and nothing else does.
- **"None of X" passes for free on a page with no X.** "No speaker on the
  pronunciation column" was asserted against the greetings pack, which has no
  pronunciation column — only the speaking-answers pack does. It passed with
  both of its guards deliberately removed. Any check of the form *none of
  these are wrong* has to assert first that there was something to be wrong:
  count the cells, fail if the count is zero, and say that the check is
  passing vacuously.
- **A guard worth having twice is a guard that needs both halves removed to
  prove the check.** That same column is kept silent by the template not
  marking it and by `sayfrench.ts` refusing `.say` outright. Removing either
  one alone leaves the other holding, and the check correctly stays green —
  which looks exactly like a dead assertion. Remove both to prove it fires,
  then put both back.
- **A runner can quietly ignore a field the schema allows.** `runReveal` never
  rendered `ex.text`, so *A text you have not been taught* shipped asking the
  reader to find words in a French passage that was in the page as JSON and
  never on the screen. Nothing failed: the data was valid, the exercise
  rendered, the questions appeared. If the schema offers a field, something
  has to assert that the page shows it.
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

`check_site.py` catches a crash and reports it as a finding rather than dying
on it. A step that throws — a selector timing out because the thing it drives
is gone — used to end the run and take every finding made before it with it.
If you add a step that drives something, guard it the way the Back-button
checks do: a missing control is a finding, not an exception.

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
