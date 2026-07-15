# bSearch configuration notes

## User-facing parameters
- Search schedule
  - How often bSearch runs
  - Optionally preferred day/time
- Candidate pool size
  - How many items bSearch collects before ranking
- Delivered item count
  - How many items bSearch keeps and presents to the user
- Exploration strength
  - How strongly bSearch boosts less-certain items to preserve novelty
  - Range: 0 to 1
  - Default: 0.5
- Source preferences
  - Relative emphasis on YouTube, GitHub, blogs/posts, tools/software, research, and broader web content
- User-interest profile
  - Short editable list of the user's current interests and preference patterns
- Preferred execution model
  - Pin scheduled runs to `openai-codex / gpt-5.4`

## Internal scoring notes
- predicted interest = prior estimated score before exploration
- candidate pool size = prior `X`
- delivered item count = prior `Y`
- exploration strength = prior `B`
- user interest rating = prior `FS`
- rank progress = `a / b`
- softened random modulation = `0.5 + 0.5 * random()`
