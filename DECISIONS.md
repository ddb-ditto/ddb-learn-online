# Decisions taken while building the site, and why

Recorded here because a future session that knows only *what* was decided will
re-open the argument.

## The repository owns the content

A lesson is an `.mdx` file in `src/content/` with checked frontmatter, and the
flashcards are one JSON file. Not a page of markup, and not a copy of anything
kept elsewhere: there is one place a session exists, and the site is built from
it. Everything else follows — the unit page, the session page, the deck page and
the record sheet are all generated, so adding a session is adding a file.

## One stylesheet, imported once

Every page goes through `src/layouts/Base.astro`, which imports the house
stylesheet. It is bundled once and cached, so a page costs its own markup and
nothing else, and there is exactly one place a colour or a margin is decided.

## The lessons are public and need no account

A sign-in wall in front of a lesson is friction with nothing behind it. Anyone
given the URL can read all of it, on any device, with nothing to install and
nothing to sign up for. That is a property worth protecting, not a stage on the
way to something gated.

## Progress is recorded on paper

The record is a printed sheet: a tick box per session and per unit's can-do
list, one sheet per child, filled in by hand.

The alternative was an account per family and a database behind it. That buys
synchronised ticks and costs a login, a service to keep running and a privacy
surface — for a record two people already keep in the same room. On-screen
checkboxes with no account are worse still: state that vanishes when the tab
closes looks like a record and is not one, so the boxes on `/progress/` are
printed squares.

The sheets are generated from the content, so they cannot drift from the course,
and they carry only what the syllabus turns on: the sessions worked through, and
the can-do statements that decide whether to move on. No marks, no scores, no
minutes — a number there would be invented.

## The template owns the shape of a page; content supplies the material

A unit file's body is its introduction. Its can-do list, the one can-do to
insist on and what to do if the unit goes badly are frontmatter, and the unit
page places them. That is not tidiness: while both sides owned the shape, Unit 1
rendered its can-do list, that heading and its note twice, and the note was
Unit 1's opinion of Unit 1 sitting in the template where every later unit would
have inherited it. A unit now supplies material and gets the same page as every
other unit, for free.

## A deck is a file

`src/data/decks/01-2.json` is the deck for `src/content/sessions/01-2.mdx` —
same name, so the pair is obvious in a directory listing and the id comes from
the filename. One file for the whole course would have been a quarter of a
megabyte by Unit 14 that every session edit had to touch and every merge had to
reconcile.

## Nothing is dated, and nobody is counted

The course does not start in a particular September, so its timelines run
Year 1 · autumn to Year 2 · May/June rather than naming years that are wrong for
everyone who starts later. For the same reason nothing assumes how many children
are being taught: the material says "a child" or "them", the sheets are one per
learner, and the places that need more than one say "if you are teaching more
than one".

## Navigation is on the page, not in the footer

Every page below the contents carries a trail — Contents › Unit 01 › Session 2 ›
Flashcards — pinned to the top of the window. A session page runs four screens on
a phone, and a link that only exists at the bottom of that is not navigation.

## The vocabulary is checked against the specification, not chosen by ear

The syllabus decides what is learned; the teaching is written here. That split
is fine for pedagogy and dangerous for vocabulary, because plausible Italian is
easy to produce and impossible to spot afterwards — a child can drill a word for
a term before anyone notices the exam will never ask for it. So every word a
deck teaches is checked against Appendix 3 by `tools/check_vocab.py`, and a word
that is not on it must be declared in `src/data/off-syllabus.json` with a
reason.

It earns its place: on its first run it found the stress deck teaching *medico*,
which is not on the list, where *musica* makes the same point and is.

Reading the list is a parser, `tools/vocab.py`, rather than a regular
expression, because the first regular expression was wrong in three ways at
once — it read the gender of *camera da letto (f)* as belonging to *letto*, it
truncated every noun that begins with an article so *lavagna* was filed under
*vagna*, and it ate the leading *e* of *età*. None of that was visible in the
output; it simply produced a plausible table. It has a self-test that asserts
genders nobody disputes, for the same reason the site has a browser check. The
specification itself stays out of the repository — Pearson's copyright — so this
is an authoring check rather than a CI one, run while a unit is being written,
which is the only point at which it can change anything.

## A unit is read before it ships, and the tools do not replace that

The checks cover what is mechanical: a word that is not on the examined list, an
article that disagrees with the gender, a standfirst that has drifted from its
deck, double-encoded text, a stress guide that contradicts its own card. Every
one of those was added because it had already gone wrong.

None of them catches a page that contradicts another page. Units 1 and 2 passed
everything and shipped, and reading them afterwards found nine problems the
tools had no opinion about — a claim in Session 1 disproved by Session 2, a
promise in the introduction disproved by Session 4, a rule that did not cover
words the unit itself taught, and four words taught in prose that no card ever
drilled. So the reading is a step, it is written down in CLAUDE.md as a list of
the things that actually went wrong, and it happens before the unit ships.

Where a class of error can be made mechanical it is moved out of that list and
into a tool. That is what happened to the stress guides, and it is the reason
the list is short: everything left on it is there because automating it would
mean guessing.

## Can-dos, not coverage

A unit's frontmatter carries its can-do list and the unit page says to move on
when they are true, not when the material has been covered. It is the same list
on the record sheet, and it is tested cold, on a different day from the last
session. This is the one piece of assessment in the whole design, and making it
the *only* one is deliberate.

## Nobody real appears in the course

Where a lesson needs a name it is an invented Italian one, or a role. The
greetings dialogue in Unit 1 runs between *You* and *Child*, and the single slot
where a name belongs is written `[name]` for whoever is at the table to fill in
aloud. A worked example is better for it — a page that names one child is a page
the other one is not in.

That is a convention, not a check. Earlier versions of this repository scanned
every file for a list of real names, which made sense while a folder of private
material was being copied in and stopped making sense the moment the course was
written here instead: a real name can now only arrive if someone types it on
purpose, and a grep is not what stops that.

`tools/check_text.py` remains, and checks one thing — a local file path pasted
into a file, which names whoever owns the machine and is permanent once the
repository is public. That one is a genuine slip, so it is worth a net.

## Published by GitHub Actions, not by pointing Pages at a folder

It costs a workflow file and buys a gate: the privacy check runs before the
build, and a failing check publishes nothing. Pages serves the artifact the
workflow uploads, so there is no built output committed to the repository and
nothing to keep in step by hand.

## The flashcard app is written once

`src/scripts/flashcards.ts` is one module, bundled once, reading its cards from
JSON in the page. The behaviour was argued over and is fixed in the file's own
comment: it opens on deck one, card one, unshuffled — the cards are in teaching
order and that order is the point — deck buttons switch rather than filter,
arrows wrap, and there are no self-marking "got it" buttons, because a
nine-year-old grading themselves is not data.

## Every deck page prints as fold-over cards

Eight to an A4 sheet, folded down the middle and cut along the solid lines. The
screen app is for drilling in the room; paper is for the ten minutes in the car.
Both come from the same deck, so they cannot disagree.

## Claims about marks come from the mark schemes

The specification, the papers and the mark schemes answer three different
questions, and only the third one is about marks. Unit 2 shipped telling a
reader that the apostrophe in *un'amica* "is one mark on paper". There is no
such mark — no writing question awards anything for an article — and the same
mark scheme lists article and gender errors, by name, among the errors that do
not affect meaning. The claim was plausible, useful-sounding, and had never been
near a grid.

So the reference pages now carry the grids' own three-way ranking of errors, and
the teaching plan says plainly that agreement is the cheapest error in the
qualification while verb person, tense and mother-tongue interference are the
expensive ones. That is the opposite of what feels urgent to drill, which is
exactly why it is written down.

Gender is still taught with the noun from Unit 2 onwards. The reason is that it
is cheap to learn early, expensive to retrofit, and needed by the plurals and
the agreement that follow — not that it scores.

## Formal register stays at Unit 12

It was worth asking, because the formal question is 28 of 60 marks on the Higher
writing paper and Unit 12 is late — twelve units of *tu* before the register that
half the paper is set in.

The mark schemes answered it. Register is one bullet of four in the communication
and content grid, and it appears in no accuracy grid at all, so getting it wrong
holds down the larger grid on a question rather than capping the paper. That is a
real cost and not a cliff. Against it, *Lei* needs the third person of the verb
and the possessive to be secure first, and pulling it forward would mean teaching
it twice.

So it stays where it is. Every session involving speaking to someone still marks
which register it is using, from Unit 1 — the unit is where the distinction is
taught, not where it starts being noticed.

## The French section is dated; the Italian course is not

The Italian course carries no calendar years, because it does not start in a
particular September and a real year would be wrong for everyone who began in a
different one. `check_text.py` enforces that over `src/`.

A Year 7 French section cannot work that way. It is revision for two tests, on
two named Wednesdays, and a countdown is the most useful thing on the page. So
the rule is scoped rather than weakened: `src/pages/french` and the countdown
component are exempt, the dates live in the test data where they can be edited
without touching a template, and everything else is still held to the old rule.

Two rules, for two different things, each written down. The alternative — a
single rule loose enough to admit both — would have let a calendar year back
into the Italian course, which is the thing worth preventing.

## Nothing is stored, in the French section either — except which cards are hard

The brief allowed browser storage for ticks and scores "if the site already
uses it". It does not: progress is recorded on paper and nothing on this site
counts anybody. So the exercises mark in memory and forget everything when the
tab closes.

That is not a limitation worked around. A score that silently resets is worse
than no score, and the person who needs to know how the revision went is the one
testing him.

**Amended, after an audit of the site against how children actually learn.**
That paragraph was right about scores and wrong to take spaced repetition down
with it. Spacing is the best-evidenced thing anybody knows about learning
vocabulary, and the decks had none: every visit reset, so the word known for a
fortnight came up as often as the one that catches him every time.

The flashcards now keep a Leitner box, and the distinction is the one the
original decision was reaching for. **Which box a card is in is a fact about the
word. A score is a fact about the child.** The first is stored — a word and a
number from one to three, in his browser, keyed on the pack so moving the site
cannot lose it. The second still is not: no score, no count, no dates, no
streak, nothing that leaves the device. The exercises still forget everything
when the tab closes.

The Italian decks are unchanged. They are drilled with the teacher in the room,
where self-marking is not needed and a nine-year-old grading themselves is still
not data.

## French flashcards are derived, not written

The Italian decks are hand-written files, because a card there teaches something
the word list does not: how to say it, a rule, a trap. The French cards *are* the
word list, so `src/lib/packcards.ts` builds them from the pack. Writing them out
a second time would only create something that could disagree with the first —
which is exactly the bug the deck-size check exists to catch.

A consequence worth knowing: a pack with nothing to drill has no cards page, and
its pack page offers no cards link. That is right rather than missing — reading
skills and culture facts are not flashcard material.

## Only declared names appear

The brief that started this section was explicit: no real name, school, village,
birthday or family member on the site. It matches the rule the Italian course
already had, and it is held the same way — by an allowlist, not a denylist.

`src/data/french/names.json` names every invented person and every real place
used, with a reason for each, and `check_french.py` fails on any proper noun
that is not in it. A list of forbidden words would have had to contain the real
name, which is the thing being kept out of the repository.

## Marking is strict about French and forgiving about keyboards

The writing test marks spelling, so the typed exercises do too: accents,
capitals and hyphens all count, and `tres` is wrong. Two things are forgiven,
because both are about the keyboard rather than the language — a curly
apostrophe where a straight one was written, and the space French puts before
`?` and `!`. Phones and laptops disagree about both, and marking him down for
his keyboard would be noise drowning the signal.

A wrong answer shows the correct version with the difference picked out, rather
than only saying no. He has just proved he cannot see the difference unaided.

## The front page is a choice, not a contents list

Two people use this site for two unrelated things. Stacking both on one page
made each of them scroll past the other, and made the site look like an Italian
course with a French appendix rather than two things that happen to share a
layout.

So `/` is two doors and nothing else, and what used to be on it moved to
`/italian/` unchanged. The counts on each door are read from the content, so a
door never advertises something that is not behind it, and the French door
carries the next test's countdown because that is the thing most likely to be
why somebody opened the site at all.

## The URL follows the repository's name

A GitHub project page is served from a path named after the repository, so the
two cannot disagree — and if the base path is written down in the config, a
rename silently breaks every stylesheet and script on the site. It does not fail
the build. The pages come back unstyled.

So the base is derived from `GITHUB_REPOSITORY` and `check_site.py` reads it
back out of the build. Renaming the repository is now the whole operation, and
nothing in the code needs editing when it happens.

## Going back is allowed; answering twice is not

Every exercise that shows one item at a time shipped with a Next and no Back.
On the speaking practice that was plainly wrong — nothing there is marked, the
whole point is saying a question again until it comes out cleanly, and there
was no way to return to one.

Back exists everywhere now, but it does not mean the same thing in both kinds.
The speaking practice wraps at both ends, like the flashcards, because there is
no score to protect. The marked exercises stop at the first and last, and an
item already answered comes back read-only: what he typed, how it was marked,
and no way to answer it again. Letting him re-answer would make the count at
the end meaningless, and a count that cannot be trusted is worse than none —
the same reasoning as recording progress on paper.

A button that is not available keeps its space rather than disappearing, so the
counter between the two does not slide about as he steps through.

## Mixing is offered separately, not imposed

Each pack drills its own words, and the flashcards run a deck at a time in
teaching order — which is right for meeting material and wrong for revising it.
Practising one topic at a time feels fluent and holds worse, because the test
asks you to work out which rule applies before you can use it.

Rather than shuffle the packs together and take the ordered run away, there is a
separate mixed deck drawing on all ten, reached from the hub and recommended
after a pack rather than instead of one. The page says plainly that it will feel
harder, because it will, and a child who is not told that concludes he has gone
backwards.

## One picture, where a picture does work

The site has no illustrations and this did not change that. An audit said dual
coding was missing; looking at what the packs actually teach, almost none of it
is picturable — greetings, numbers, verb phrases and rules do not illustrate.

Countries do. A flag is a second, independent route to the same fact and most of
these are already in his head, so the countries carry one and nothing else does.
Adding pictures to the rest would have been decoration answering an audit rather
than teaching anybody anything.

## A pack says what is hard, not who got it wrong

Pack 10 shipped as "His own mistakes, next to what they should have been" —
twelve lines, each one something a twelve-year-old had actually written down
wrongly, assembled into a page with his name all over it in everything but the
literal word.

It came from a good instinct. Practising the errors somebody actually makes
beats practising a generic list, and the content was right. The framing was
not. A revision pack is opened by the person it was written for, often alone,
and one that opens by telling him what he gets wrong says that to him every
single time — which is both unkind and a reason to stop opening it.

The words did not change. The page now says what is hard about the French: an
accent missing, a hyphen gone, two letters the wrong way round. Which is also
simply more useful, because it names the kind of slip rather than the incident.

`check_french.py` enforces it, because this is the sort of thing that creeps
back in one well-meant sentence at a time. It fails on he, him or his anywhere
a learner reads, with the honest uses — French has gendered pronouns to teach,
and Louis Pasteur gave his name to pasteurisation — listed as exceptions. Notes
explicitly marked for the parent are exempt, because the page says on its face
who those are for.

The code comments went the same way. The repository is public and the child is
real; "mistakes from his own book" sitting in a checker is the same disclosure
with fewer readers.

## The commentary is switched off, not written out

A pack carries three kinds of writing: the words, the rule that holds them
together, and the asides explaining why the rule is the way it is. Measured
across the ten packs, that third kind is about 400 of 1,100 words — a third of
the prose, and on the fifth time through it is in the way.

The fix is a switch rather than a rewrite, because the same sentence is useful
the first time and noise the fifth, and because the parent and the child want
different pages. Notes for the parent disappear; notes for the learner fold to
their heading and stay one tap from open; the rules, the words and the practice
are untouched. Off by default, so the first person to open a pack sees all of
it.

**What it deliberately does not hide.** Each exercise opens with a line like
"Tap the tiles in the right order. Tap one you have placed to take it back."
Those read like prose and are nothing of the kind — they are how to work the
thing. Folding them would have made the page shorter and the exercises harder,
which is the opposite of the point. Measuring them was what settled it: every
intro is eight to twenty-five words and most are instructions.

It is honest about its size. A pack page runs 220 to 330 words with the switch
on, of which the majority is the vocabulary he came to learn. The switch takes
about fifty words off a page — real, and not a transformation. If the pages
still read as too long, the next lever is the order of the page rather than
more hiding, and that is worth measuring before building.

## The wrong spelling appears once, where it is being asked about

Pack 10 showed each misspelling struck through beside the right one. That was
the brief's own design and the argument for it is real: the writing test's last
task is spotting a wrong spelling, so recognising one is examined.

Against it: seeing a misspelling makes it fractionally more familiar, and
familiarity is what somebody reaches for when they are unsure. The evidence is
mixed rather than settled, but it points one way and the column was the most
passive form of the exposure — read past, every visit, learning nothing.

So the page shows only the spelling that counts. Recognising a wrong one
happens in **Spot the mistake**, where it is a question with an answer and the
right version appears a second later, and in the punctuation drill, where a
stripped-down prompt is the task rather than something on display.

The flashcards went too, which was not asked for but follows. A card is seen
over and over, and the Leitner box shows the ones that keep going wrong *more*
often — so a deck of misspellings would have put them in front of him most
where he was weakest. Pack 10 now has no cards; its drilling is the exercises.

`check_french.py` holds the line: a wrong spelling may appear in those two
drills and nowhere else.

## Two marks, one site

The site has its own logo now — the DDB wordmark — and it goes on the front
door, which is the only page belonging to the whole site rather than to one
subject. The GCSE Italian roundel stays on the Italian contents page, because
it says "GCSE Italian" on its face and that is still true there.

Keeping both was not indecision. One brands a site that teaches two things; the
other brands one of them.

## Three colour settings, not two

The site followed the device and offered nothing, so reading it in daylight
meant changing the whole phone. There is a switch at the foot of every page
now: Light, Dark, or Match my device.

Three states rather than two, and matching the device is the default. A plain
light/dark toggle has no way back to following the device once it has been
touched, and a child who taps it on a whim should be able to undo that without
knowing what they changed.

Matching the device means *no* attribute on the page, not a third stored value,
so a browser with no JavaScript still gets the media query and still follows
the device. The choice is applied by an inline script in the head rather than
from the bundle: a moment later and a page set to dark arrives white and turns,
which is worse than not offering the choice at all.

The cost is that the dark tokens are now written twice, because CSS cannot
share one declaration between a media query and a selector. Two copies drift,
so they are compared by behaviour rather than trusted: the site is loaded on a
dark device with no override and on a light device with the switch forced to
dark, and all seventeen tokens have to match. That caught the drift when it was
tried deliberately.

## Still open

- Custom domain, or the `ddb-ditto.github.io/<repo-name>/` path? No `CNAME` file yet.
- Whether the record sheet should also carry a listening or speaking column once
  Stage 1 reaches the units that need it. Not until there is something to tick.
