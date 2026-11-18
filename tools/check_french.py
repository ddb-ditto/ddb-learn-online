#!/usr/bin/env python3
"""The Year 7 French section, checked against itself.

    python3 tools/check_french.py

The Italian course has the specification to check against: a published list of
every examined word, so `check_vocab.py` can say whether a card teaches
something real. There is no such document here. The source is the class's own
work, and once it has been typed into `src/data/french/` nothing outside the
repository can confirm it.

So these checks are internal-consistency checks, and they are worth more than
they sound. Almost every way this section can go wrong is a disagreement
between two files that were written at different moments:

  - an exercise that marks an answer the vocabulary spells differently,
  - a test that lists a pack which does not say it is for that test,
  - a pack that teaches a word no exercise ever asks for,
  - a French string that has lost an accent or a hyphen somewhere in editing.

The last one is the reason this file exists at all. The writing test marks
spelling. A pack that teaches `tres` would be teaching the mistake it was
written to prevent, and nothing else in the toolchain would notice.
"""
import json
import pathlib
import re
import sys
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
FRENCH = REPO / "src/data/french"
PACKS = FRENCH / "packs"
TESTS = FRENCH / "tests"
EXERCISES = FRENCH / "exercises"

PARTS = ("speaking", "reading", "writing")

# Keyboard differences, not French ones — the same two the marking forgives.
APOSTROPHES = re.compile(r"[’ʼ´′]")
SPACE_BEFORE = re.compile(r"[\s   ]+([?!;:])")


def load(folder: pathlib.Path) -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(folder.glob("*.json"))}


def normalise(s: str) -> str:
    """What two spellings have to agree on. Mirrors `normalise` in marking.ts."""
    s = APOSTROPHES.sub("'", s).replace("…", "...")
    s = SPACE_BEFORE.sub(r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_markup(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


# ---------------------------------------------------------------- typography

# Words that are spelled with an accent and are easy to type without one.
# Each is a spelling the pack teaches, or one step away from it.
ACCENTED = {
    "tres": "très", "ca": "ça", "age": "âge", "ecosse": "Écosse",
    "espagne": None, "soeur": "sœur", "annee": "année", "visite": "visité",
    "cote": "Côte", "edimbourg": "Édimbourg", "chloe": "Chloé",
}
# Words that must carry a hyphen.
HYPHENATED = ("dix-sept", "dix-huit", "dix-neuf", "vingt-et-un", "trente-et-un",
              "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq",
              "vingt-six", "vingt-sept", "vingt-huit", "vingt-neuf",
              "as-tu", "t'appelles-tu", "habites-tu", "voudrais-tu",
              "Grande-Bretagne")
UNHYPHENATED = re.compile(
    r"\b(dix (?:sept|huit|neuf)|vingt (?:et un|deux|trois|quatre|cinq|six|sept|huit|neuf)"
    r"|trente et un|as tu|Grande Bretagne)\b", re.I)


def typography(strings: list[tuple[str, str]]) -> list[str]:
    """Accents and hyphens that have gone missing, and spaces doubled up."""
    bad = []
    for where, s in strings:
        plain = strip_markup(s)

        missing = UNHYPHENATED.search(plain)
        if missing:
            bad.append(f"{where}: {missing.group(0)!r} has lost its hyphen")

        for word in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’]+", plain):
            flat = "".join(
                c for c in unicodedata.normalize("NFD", word.lower())
                if unicodedata.category(c) != "Mn"
            ).replace("œ", "oe")
            right = ACCENTED.get(flat)
            if right and word != right and word.lower() != right.lower():
                # `ca` is also a perfectly good start to an English word, so
                # only flag it where the surrounding text is French.
                bad.append(f"{where}: {word!r} should be {right!r}")

        if "  " in plain:
            bad.append(f"{where}: two spaces in a row")
        if plain != plain.strip():
            bad.append(f"{where}: leading or trailing space")
    return bad


# ------------------------------------------------------------------ the data

def french_strings(packs: dict, exercises: dict) -> list[tuple[str, str]]:
    """Every string on the site that is meant to be French."""
    out: list[tuple[str, str]] = []
    for name, p in packs.items():
        for v in p.get("vocab", []):
            out.append((f"packs/{name} vocab", v["fr"]))
            if v.get("alt"):
                out.append((f"packs/{name} vocab alt", v["alt"]))
        for c in p.get("countries", []):
            out.append((f"packs/{name} countries", c["fr"]))
            out.append((f"packs/{name} countries", c["in"]))
        for _, word in p.get("numbers", []):
            out.append((f"packs/{name} numbers", word))
        for a in p.get("answers", []):
            out.append((f"packs/{name} answers", a["q"]))
            out.append((f"packs/{name} answers", a["a"]))
        for c in p.get("corrections", []):
            out.append((f"packs/{name} corrections", c["right"]))

    for name, e in exercises.items():
        kind = e["kind"]
        if kind in ("prompt", "type"):
            for it in e["items"]:
                # A "type" prompt is English and its answer is French; a
                # "prompt" exercise is the other way round.
                out.append((f"exercises/{name}", it["answer" if kind == "type" else "prompt"]))
        if kind == "order":
            for it in e["items"]:
                out.append((f"exercises/{name}", it["answer"]))
        if kind == "gapfill":
            for piece in e["text"]:
                if isinstance(piece, str):
                    # Edge spaces are load-bearing here: these fragments sit
                    # either side of an input, so they are stripped before the
                    # whitespace rule sees them.
                    out.append((f"exercises/{name} text", piece.strip()))
                else:
                    out.append((f"exercises/{name} gap", piece["gap"]))
            for w in e["bank"]:
                out.append((f"exercises/{name} bank", w))
        if kind == "truefalse" and e.get("text"):
            out.append((f"exercises/{name} text", e["text"]))
        if kind == "reveal" and e.get("text"):
            out.append((f"exercises/{name} text", e["text"]))
    return out


def mapping(packs: dict, tests: dict) -> list[str]:
    """Each test lists the packs that say they are for it, and no others."""
    bad = []
    by_slug = {p["slug"]: p for p in packs.values()}

    for name, t in tests.items():
        listed = list(t["packOrder"])
        if len(listed) != len(set(listed)):
            bad.append(f"tests/{name}: a pack is listed twice in packOrder")
        for slug in listed:
            pack = by_slug.get(slug)
            if pack is None:
                bad.append(f"tests/{name}: packOrder names {slug!r}, which is not a pack")
                continue
            if not set(pack["tests"]) & set(t["parts"]):
                bad.append(f"tests/{name}: lists pack {slug!r}, which is not for "
                           f"{' or '.join(t['parts'])}")
        # and the other way round, which is the half that gets forgotten
        for slug, pack in by_slug.items():
            if set(pack["tests"]) & set(t["parts"]) and slug not in listed:
                bad.append(f"tests/{name}: pack {slug!r} says it is for this test "
                           f"but the test does not list it")

    for name, p in packs.items():
        if f"{p['number']:02d}-{p['slug']}" != name:
            bad.append(f"packs/{name}: filename does not match number {p['number']} "
                       f"and slug {p['slug']!r}")
        for part in p["tests"]:
            if part not in PARTS:
                bad.append(f"packs/{name}: unknown test part {part!r}")
        for part in p.get("testNotes", {}):
            if part not in p["tests"]:
                bad.append(f"packs/{name}: a note for {part!r}, which it is not for")
    return bad


def exercise_links(packs: dict, tests: dict, exercises: dict) -> list[str]:
    """Every exercise named by a pack or a test exists, and every one is used."""
    bad = []
    known = set(exercises)
    used: set[str] = set()

    for name, p in packs.items():
        for ex in p.get("exercises", []):
            used.add(ex)
            if ex not in known:
                bad.append(f"packs/{name}: names exercise {ex!r}, which does not exist")
    for name, t in tests.items():
        for ex in t["practice"]:
            used.add(ex)
            if ex not in known:
                bad.append(f"tests/{name}: practice names {ex!r}, which does not exist")
        if len(t["practice"]) != len(set(t["practice"])):
            bad.append(f"tests/{name}: an exercise is listed twice in practice")

    for ex in sorted(known - used):
        bad.append(f"exercises/{ex}: written, but no pack or test offers it")

    for name, e in exercises.items():
        if e["id"] != name:
            bad.append(f"exercises/{name}: id says {e['id']!r}")
        if e["kind"] == "choice":
            for n, it in enumerate(e["items"], 1):
                if not 0 <= it["answer"] < len(it["options"]):
                    bad.append(f"exercises/{name} q{n}: answer {it['answer']} is not an option")
                if len(set(it["options"])) != len(it["options"]):
                    bad.append(f"exercises/{name} q{n}: two options are the same")
        if e["kind"] == "gapfill":
            gaps = [p["gap"] for p in e["text"] if isinstance(p, dict)]
            for g in gaps:
                if g not in e["bank"]:
                    bad.append(f"exercises/{name}: gap {g!r} is not in the word bank")
            for w in e["bank"]:
                if w not in gaps:
                    bad.append(f"exercises/{name}: bank word {w!r} fills no gap")
        if e["kind"] == "order":
            for n, it in enumerate(e["items"], 1):
                tiles = sorted(x.lower() for x in it["tiles"])
                words = sorted(re.sub(r"[.,]", "", it["answer"]).lower().split())
                if tiles != words:
                    bad.append(f"exercises/{name} {n}: tiles {tiles} do not make "
                               f"the answer {words}")
        if e.get("ask") and e["kind"] in ("type", "choice") and e["ask"] > len(e["items"]):
            bad.append(f"exercises/{name}: asks for {e['ask']} of {len(e['items'])} items")
    return bad


def declared_names() -> tuple[set[str], list[str]]:
    """The invented people and the places, each one written down on purpose.

    The brief that set this section going was explicit: no real name, school,
    village, birthday or family member goes on the site. The way to hold that
    line is not a list of forbidden words — writing the real name into a
    checker would put it in the repository, which is the thing being avoided.
    It is a list of the permitted ones. Anything else trips the check and a
    person decides.
    """
    f = FRENCH / "names.json"
    if not f.exists():
        return set(), [f"{f.relative_to(REPO)} is missing — every proper noun "
                       "used in the section has to be declared there"]
    declared = json.loads(f.read_text(encoding="utf-8"))
    allowed = set()
    bad = []
    for entry in declared:
        if not entry.get("why"):
            bad.append(f"names.json: {entry.get('name')!r} has no reason")
        allowed.add(entry["name"].lower())
    return allowed, bad


def answers_are_taught(packs: dict, exercises: dict, allowed: set[str]) -> list[str]:
    """A typed answer has to be spelled the way a pack spells it.

    This is the check that matters most. An exercise answer and a pack's
    vocabulary are the same fact written twice, and the second one is where a
    letter goes missing — so every French answer he is marked against must
    appear somewhere he could have learned it.
    """
    taught: set[str] = set()
    for p in packs.values():
        for v in p.get("vocab", []):
            taught.add(normalise(v["fr"]))
        for c in p.get("countries", []):
            taught.update({normalise(c["fr"]), normalise(c["in"])})
        for _, word in p.get("numbers", []):
            taught.add(normalise(word))
        for a in p.get("answers", []):
            taught.update({normalise(a["q"]), normalise(a["a"])})
        for c in p.get("corrections", []):
            taught.add(normalise(c["right"]))

    # Every word of every taught phrase, so a sentence built from taught words
    # counts as taught even when the whole sentence is new.
    words = {w for phrase in taught for w in re.findall(r"[\w'’À-ÖØ-öø-ÿ-]+", phrase.lower())}

    bad = []
    for name, e in exercises.items():
        if e["kind"] not in ("type", "order"):
            continue
        for it in e["items"]:
            answer = normalise(it["answer"])
            if answer in taught:
                continue
            unknown = [
                w for w in re.findall(r"[\w'’À-ÖØ-öø-ÿ-]+", answer.lower())
                if w not in words and w not in allowed
            ]
            if unknown:
                bad.append(f"exercises/{name}: {it['answer']!r} uses "
                           f"{', '.join(repr(u) for u in unknown)}, which no pack teaches")
    return bad


def undrilled(packs: dict, exercises: dict) -> list[str]:
    """Words taught and never asked for. A report, not a failure.

    The Italian course has the same report for the same reason: some things are
    meant to be read rather than drilled, so a person decides.
    """
    asked = set()
    for e in exercises.values():
        if e["kind"] in ("type", "order"):
            for it in e["items"]:
                asked.add(normalise(it["answer"]))
        if e["kind"] == "gapfill":
            asked.update(normalise(w) for w in e["bank"])

    loose = []
    for name, p in sorted(packs.items()):
        if "writing" not in p["tests"]:
            continue                     # only the writing test spells things
        for v in p.get("vocab", []):
            if normalise(v["fr"]) not in asked:
                loose.append(f"{p['slug']}: {v['fr']}")
        for c in p.get("countries", []):
            if normalise(c["in"]) not in asked:
                loose.append(f"{p['slug']}: {c['in']}")
    return loose


# Words that make a sentence about the learner rather than about French.
ABOUT_HIM = re.compile(r"\b(he|him|his)\b", re.I)
# Where "he" is doing honest work: French has gendered pronouns to teach, and
# a fact about Louis Pasteur is a fact about Louis Pasteur.
NOT_ABOUT_HIM = re.compile(
    r"\b(he|she) is called\b|\bhe / she\b|\(she: elle\)|"
    r"\bgave his name\b|\bwould he like\b|\bhe lives in\b|\bhe is… years\b|"
    r"\bbrought it with him\b", re.I)


def about_the_learner(packs: dict, exercises: dict) -> list[str]:
    """Nothing a child reads should be about what that child got wrong.

    A revision pack is opened by the person it was written for. A page that
    says "twelve things he has actually got wrong" tells him something about
    himself every time he opens it, which is both unkind and a reason to stop
    opening it — and the words are worth drilling whoever first misspelled
    them. So the learner-facing text talks about French, not about him.

    Notes explicitly marked for the parent are exempt: those are addressed to
    somebody else and say so on the page.
    """
    bad = []
    for name, p in sorted(packs.items()):
        fields: list[tuple[str, str]] = [
            ("standfirst", p["standfirst"]), ("summary", p["summary"])]
        for note in p.get("notes", []):
            if note.get("audience") == "parent":
                continue
            fields += [("note lead", note["lead"]), ("note body", note["body"])]
        for rule in p.get("rules", []):
            fields += [("rule lead", rule["lead"]), ("rule body", rule["body"])]
        for part, note in (p.get("testNotes") or {}).items():
            fields.append((f"testNote {part}", note))

        for where, text in fields:
            plain = NOT_ABOUT_HIM.sub("", strip_markup(text))
            hit = ABOUT_HIM.search(plain)
            if hit:
                bad.append(f"packs/{name} {where}: {hit.group(0)!r} — a pack is read "
                           f"by the learner, so it says what is hard about the French, "
                           f"not what he got wrong: {text[:60]!r}")

    for name, e in sorted(exercises.items()):
        for where, text in (("title", e["title"]), ("intro", e.get("intro") or "")):
            plain = NOT_ABOUT_HIM.sub("", strip_markup(text))
            hit = ABOUT_HIM.search(plain)
            if hit:
                bad.append(f"exercises/{name} {where}: {hit.group(0)!r} — "
                           f"about the learner rather than the French: {text[:60]!r}")
    return bad


def main() -> int:
    if not PACKS.is_dir():
        print("no src/data/french — nothing to check")
        return 0

    packs = load(PACKS)
    tests = load(TESTS)
    exercises = load(EXERCISES)
    print(f"{len(packs)} pack(s), {len(tests)} test(s), {len(exercises)} exercise(s)")

    allowed, bad = declared_names()
    bad += typography(french_strings(packs, exercises))
    bad += mapping(packs, tests)
    bad += exercise_links(packs, tests, exercises)
    bad += answers_are_taught(packs, exercises, allowed)
    bad += about_the_learner(packs, exercises)

    loose = undrilled(packs, exercises)
    if loose:
        print(f"\nTaught but never asked for ({len(loose)}) — a decision, not a failure:")
        for w in loose:
            print(f"  {w}")

    if bad:
        print(f"\nFAILED — {len(bad)} problem(s):")
        for b in bad:
            print(f"  {b}")
        return 1
    print("\nevery pack, test and exercise agrees with the others.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
