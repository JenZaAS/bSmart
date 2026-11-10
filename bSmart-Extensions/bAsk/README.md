# bAsk

bAsk is a short interview that sharpens an idea. The agent asks one plain
question at a time until the idea is clear, then sums up what was decided.

Status: draft, optional. Works on its own for any idea, with or without a map.
bMap uses it for explore tickets.

## Files

| File | Purpose |
|---|---|
| `interview.md` | The interview rules. |

## Use

Say "bAsk me about <idea>", or "ask me questions about this". The agent reads
`interview.md` and starts.

## bAsk, bQAbuild, and bMap

- **bAsk**: a quick talk to sharpen an idea. Nothing to set up; the result is
  a short list of decisions.
- **bQAbuild**: a fixed list of questions, stored answers, and a build brief.
  Use it when the result must be a formal brief.
- **bMap**: work too big for one session. Each explore ticket is one bAsk.

## Credits

Based on the `grill-me` and `grilling` skills by Matt Pocock,
https://github.com/mattpocock/skills (MIT), rewritten in our own words. bAsk
asks one question at a time instead of a round of questions.
