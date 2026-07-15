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

## Command notes and catalog
- All user commands should begin with `bSearch`.
- bSearch should interpret flexible natural language after the prefix rather than forcing rigid syntax.

### Insert / add
- `insert` and `add` should be treated as equivalent when the user is trying to store an item.
- The item may be provided as a URL, repository name, project name, or other short reference.
- If the item reference is ambiguous, ask a short clarification question before storing it.
- If the item reference is clear enough, resolve it similarly to a normal discovery item and store it with the provided score.

### List / browse
- `list` should support category browsing as a first-class command.
- `bSearch list` and `bSearch list categories` should show a numbered category list with category scores.
- Default list sorting should be by score; `alpha` should request alphabetical sorting.
- A numeric argument may act as a display limit `N`; the default display limit is `10`.
- `all` may be used instead of `N` to request the full sorted list.
- `bSearch list <category name>` should show numbered items in that category with scores.
- If a category label/name is present, a following number should be treated as the item display limit for that category view.
- Immediately after a category list, `bSearch list <number>` may refer to the numbered category from that most recent list.
- Numeric references should be treated as short-lived context helpers, not stable long-term IDs.
- If both a category index and a limit are needed, prefer `bSearch list category <index> <limit>`.
- A bare two-number form like `bSearch list 3 4` is ambiguous and should trigger a clarification question rather than a guess.

### Planned next command families
- `bSearch run` / `bSearch search now`
- `bSearch rate ...` / `bSearch score ...`
- `bSearch show ...`
- `bSearch search memory ...`
- `bSearch show profile` / `bSearch update profile`
- `bSearch settings` / `bSearch set ...`
- `bSearch remove ...` / `bSearch archive ...`
