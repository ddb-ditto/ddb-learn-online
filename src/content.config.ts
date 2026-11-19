import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

/**
 * The course, as data.
 *
 * A unit is a chunk of material, not a length of time, and it is split into
 * sessions of one sitting each. Every session has a matching deck; a session
 * is not finished until its deck exists, which is why `deck` is required and
 * the decks are a collection in their own right rather than a loose file.
 */

const units = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/units" }),
  schema: z.object({
    number: z.number().int().positive(),
    title: z.string(),
    /** One line under the title: what this unit is for. */
    standfirst: z.string(),
    /** Move on when these are true, not when the material has been covered. */
    canDos: z.array(z.string()).min(1),
    /**
     * The can-do to hold the line on, if one of them carries the unit. Written
     * per unit because it is about that unit's material — a note in the
     * template would be Unit 1's opinion printed on Unit 14.
     */
    insist: z.string().optional(),
    /**
     * What to do when the unit goes badly. Inline HTML, like the leads: the
     * template decides where it goes so every unit's page reads the same way.
     */
    contingency: z.array(z.string()).optional(),
  }),
});

const sessions = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/sessions" }),
  schema: z.object({
    unit: z.number().int().positive(),
    number: z.number().int().positive(),
    title: z.string(),
    standfirst: z.string(),
    /** How it reads on the unit's contents list. */
    summary: z.string(),
    /** One sitting. Longer than 40 on paper means it should be two sessions. */
    minutes: z.number().int().min(15).max(45),
    /** What the deck page says about itself. */
    deckStandfirst: z.string(),
  }),
});

const decks = defineCollection({
  /**
   * One file per session, named to match the session it belongs to — 01-2.json
   * is the deck for src/content/sessions/01-2.mdx. The id comes from the
   * filename, so a new deck is a new file and nothing central has to be edited.
   */
  loader: glob({ pattern: "**/*.json", base: "./src/data/decks" }),
  schema: z.object({
    unit: z.number().int().positive(),
    session: z.number().int().positive(),
    /**
     * Notes shown above the deck, collapsed. Every deck says what it cannot
     * do: anything resting on hearing or producing a sound cannot be tested by
     * a card, and the teacher needs to know which decks need them in the room.
     */
    notes: z.array(z.object({ lead: z.string(), body: z.string() })),
    /**
     * Decks where "English first" is switched off by hand. It is offered where
     * the backs are distinct translations, which is the right default — but
     * Unit 1's backs are instructions rather than glosses, and reversing them
     * asks "which word does this describe?" rather than testing vocabulary.
     */
    noReverse: z.array(z.string()).optional(),
    cards: z.array(
      z.object({
        /** Deck name. Decks run in teaching order, most fundamental first. */
        d: z.string(),
        /** A rule card is a question and is never reversed. */
        t: z.enum(["word", "rule"]),
        f: z.string(),
        s: z.string().optional(),
        m: z.string(),
      }),
    ).min(1),
  }),
});

const reference = defineCollection({
  loader: glob({ pattern: "**/*.mdx", base: "./src/content/reference" }),
  schema: z.object({
    title: z.string(),
    standfirst: z.string(),
    /** Position on the contents page. */
    order: z.number().int(),
    /** The one-word label on its card. */
    kind: z.string(),
    blurb: z.string(),
  }),
});

/* ---------------------------------------------------------------------------
 * Year 7 French.
 *
 * A different shape from the Italian course, because it is a different job.
 * The Italian course is a designed two-year sequence of units and sessions.
 * This is revision for two school tests on fixed dates: ten packs, and a page
 * per test saying which packs it needs and in what order. Dates are real here
 * and absent there, and that is the difference between a course someone starts
 * whenever they like and a test on a Wednesday.
 * ------------------------------------------------------------------------- */

/** Which of the three school tests a pack feeds. */
const part = z.enum(["speaking", "reading", "writing"]);

/**
 * A lead and a body, as the Note and Warn components take them, plus who it
 * is talking to.
 *
 * The Italian course does not need this: every word of it is addressed to
 * whoever is teaching, and the child never opens it. A revision pack is used
 * by a twelve-year-old on his own, and four of the ten carried a note written
 * about him in the third person — "if his class answers differ, use his" —
 * with nothing to say it was not meant for him. So the audience is declared
 * and the page shows it.
 *
 * This is deliberately not the Note component's `child` flag, which means
 * something else: an aside to the teacher about handling one child
 * differently.
 */
const aside = z.object({
  lead: z.string(),
  body: z.string(),
  audience: z.enum(["learner", "parent"]).default("learner"),
});

const frenchPacks = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/data/french/packs" }),
  schema: z.object({
    number: z.number().int().positive(),
    /** The URL segment, and how tests refer to the pack. */
    slug: z.string(),
    title: z.string(),
    standfirst: z.string(),
    /** How it reads on a card in the hub and on a test page. */
    summary: z.string(),
    /**
     * One sitting, in minutes. The Italian sessions have carried this from the
     * start and the packs shipped without it — which left a child with no idea
     * whether he was starting a five-minute job or a forty-minute one, and
     * nothing to stop a pack quietly growing past what one sitting holds.
     */
    minutes: z.number().int().min(5).max(40),
    tests: z.array(part).min(1),
    /**
     * Why a pack is only partly needed, e.g. numbers for the speaking test.
     * An object with three optional keys rather than a record over the enum,
     * because a record over an enum demands every key.
     */
    testNotes: z.object({
      speaking: z.string().optional(),
      reading: z.string().optional(),
      writing: z.string().optional(),
    }).optional(),

    /* A pack carries whichever of these its material needs; the template
       renders the ones that are there and skips the rest. */
    vocab: z.array(z.object({
      fr: z.string(),
      en: z.string(),
      /**
       * A second way of saying the same thing — the inversion, or the
       * feminine. It is shown on the page and never drilled: one phrase has
       * to be the one he produces, or a spelling drill has two right answers
       * and marks one of them wrong.
       */
      alt: z.string().optional(),
    })).optional(),
    countries: z.array(z.object({
      fr: z.string(), en: z.string(), in: z.string(), gender: z.enum(["m", "f"]),
      /**
       * The country's flag, as a character.
       *
       * The only picture anywhere in these packs, because it is the only place
       * a picture does real work: a flag is a second, independent route to the
       * same fact, and most of these are already in his head. Nothing else
       * here is a concrete noun — greetings, numbers and verb phrases do not
       * illustrate, and decorating them would be decoration.
       *
       * Wales, England and Scotland are tag sequences rather than ordinary
       * flag emoji. They draw correctly in current browsers — checked by
       * rendering each one and comparing the pixels with the plain black flag
       * — but older Android and some Windows builds fall back to that black
       * flag. That is a shrug, not a break: the country's name is next to it.
       */
      flag: z.string().optional(),
    })).optional(),
    numbers: z.array(z.tuple([z.number().int(), z.string()])).optional(),
    alphabet: z.array(z.tuple([z.string(), z.string()])).optional(),
    answers: z.array(z.object({ q: z.string(), a: z.string(), en: z.string() })).optional(),
    sounds: z.array(z.object({ fr: z.string(), say: z.string(), why: z.string() })).optional(),
    facts: z.array(z.string()).optional(),
    corrections: z.array(z.object({
      wrong: z.array(z.string()).min(1), right: z.string(),
    })).optional(),

    rules: z.array(aside).optional(),
    notes: z.array(aside).optional(),
    /** Exercise ids this pack offers, in the order they should be worked. */
    exercises: z.array(z.string()).default([]),
  }),
});

const frenchTests = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/data/french/tests" }),
  schema: z.object({
    slug: z.string(),
    order: z.number().int(),
    title: z.string(),
    /** The real date. A test is on a Wednesday, so this one is dated. */
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    parts: z.array(part).min(1),
    standfirst: z.string(),
    sections: z.array(z.object({
      part,
      title: z.string(),
      format: z.array(z.string()).min(1),
      questions: z.array(z.string()).optional(),
      advice: z.string().optional(),
      howToScore: z.object({ lead: z.string(), items: z.array(z.string()) }).optional(),
    })).min(1),
    /** Pack slugs, most urgent first. */
    packOrder: z.array(z.string()).min(1),
    /** Exercise ids the practice run works through. */
    practice: z.array(z.string()).min(1),
  }),
});

/**
 * Practice exercises, one file each, shaped by what they ask the learner to do.
 *
 * They are a union rather than one loose object because the marking differs:
 * a typed answer is compared character by character, a choice is an index, and
 * a reveal is not marked at all. A schema that allowed all of it everywhere
 * would let a "type" exercise ship with no answer to type against.
 */
const exerciseBase = {
  id: z.string(),
  part,
  title: z.string(),
  intro: z.string().optional(),
  text: z.string().optional(),
  shuffle: z.boolean().default(false),
  /** Ask this many of the items, picked at random. All of them if absent. */
  ask: z.number().int().positive().optional(),
};

const frenchExercises = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/data/french/exercises" }),
  schema: z.discriminatedUnion("kind", [
    /* Say it aloud, then reveal. Nothing is marked: only the person in the
       room can hear whether it was right. */
    z.object({
      ...exerciseBase, kind: z.literal("prompt"),
      speakLang: z.string().optional(),
      items: z.array(z.object({
        prompt: z.string(),
        /**
         * The question in English, shown beside it when the model answer is
         * revealed. The French question sits alone at the top of the card, so
         * somebody unsure what was being *asked* gets no help from an answer.
         */
        enPrompt: z.string().optional(),
        answer: z.string(), en: z.string().optional(),
      })).min(1),
    }),
    /* Think, then turn over. Also unmarked. */
    z.object({
      ...exerciseBase, kind: z.literal("reveal"),
      items: z.array(z.object({
        prompt: z.string().optional(),
        question: z.string().optional(),
        answer: z.string(),
      })).min(1),
    }),
    /* A run of text with holes in it and a bank of words to fill them. */
    z.object({
      ...exerciseBase, kind: z.literal("gapfill"),
      bank: z.array(z.string()).min(1),
      text: z.array(z.union([z.string(), z.object({ gap: z.string() })])).min(1),
    }),
    z.object({
      ...exerciseBase, kind: z.literal("truefalse"),
      items: z.array(z.object({
        statement: z.string(), answer: z.boolean(), because: z.string().optional(),
      })).min(1),
    }),
    z.object({
      ...exerciseBase, kind: z.literal("choice"),
      items: z.array(z.object({
        q: z.string(),
        options: z.array(z.string()).min(2),
        answer: z.number().int().nonnegative(),
      })).min(1),
    }),
    /* Typed, and marked strictly. `weight` makes an item come up more often. */
    z.object({
      ...exerciseBase, kind: z.literal("type"),
      items: z.array(z.object({
        prompt: z.string(), answer: z.string(),
        weight: z.number().int().positive().default(1),
      })).min(1),
    }),
    /* Tiles put back into order. */
    z.object({
      ...exerciseBase, kind: z.literal("order"),
      items: z.array(z.object({
        tiles: z.array(z.string()).min(2), answer: z.string(),
      })).min(1),
    }),
  ]),
});

export const collections = {
  units, sessions, decks, reference,
  frenchPacks, frenchTests, frenchExercises,
};
