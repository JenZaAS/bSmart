# bTeach

bTeach explains one thing at the user's level and checks that it landed. On
request it can also run a short course over several sessions.

Status: draft, optional. User-invoked only; an agent never starts it on its
own. Works with or without a project.

## Files

| File | Purpose |
|---|---|
| `teach.md` | The teaching rules for both modes. |
| `templates/course.template.md` | Blank course file: goal, level, sources, progress. |
| `templates/lesson.template.md` | Blank lesson: one short sitting, one win. |

## Use

- "Teach me <area, concept, or term>", "explain <thing> at my level", or
  "bTeach <topic>": one explanation, then one check question.
- "Start a course on <topic>": a course of short markdown lessons, kept
  outside the product repo.

## bTeach, bAsk, and plain answers

- **Plain answers** (`response_style` in `bSmart.md`) already explain jargon
  in a few words. bTeach is for when the user wants to understand something,
  not just get the answer.
- **bAsk** asks the user questions to sharpen a decision. bTeach explains and
  asks one question to check understanding.

## Credits

Inspired by Matt Pocock's /teach skill ([aihero.dev](https://www.aihero.dev/)).
