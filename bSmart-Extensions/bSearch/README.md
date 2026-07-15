# bSmart Extension: bSearch

```yaml
name: bSearch
status: bundled_optional_extension
source_root: /workspace/bSmart-System/bSmart-Extensions/bSearch
install_root: /workspace/bSmart-Extensions/bSearch
license: MIT
purpose: Optional AI-driven knowledge-search add-on for bSmart.
```

## What bSearch is
bSearch is an optional bSmart extension that can periodically search for interesting knowledge, tools, repositories, videos, posts, software, and related discoveries, then curate a smaller set for the user.

Core behavior:
- run on a configurable schedule
- search a larger candidate pool
- deliver a smaller curated shortlist
- maintain a short editable user-interest profile
- learn from explicit user ratings from 1 to 5
- automatically refresh the user-interest profile when a full evaluation round is completed
- preserve prior items as a searchable knowledge repository
- accept flexible natural-language commands as long as they begin with `bSearch`
- current runtime implementation performs multisource live discovery for `bSearch run` across GitHub, RSS/news/blog feeds, arXiv, and YouTube-oriented feed results
- when building a live candidate pool, source choice is randomized per slot to reduce systematic source bias
- scheduled/manual `bSearch run` must first refuse a new run if the most recent delivered run still has unhandled items

## Initialization should ask for
- Search schedule
- Candidate pool size
- Delivered item count
- Exploration strength
- Source preferences
- Initial user-interest profile review/edit
- Whether scheduled runs should be pinned to `openai-codex / gpt-5.4`

## Recommended exploration formula
bSearch should use a softened exploration bonus so randomness helps surface novelty without making exploration disappear entirely.

```text
exploration_multiplier = exploration_strength * rank_progress * (0.5 + 0.5 * random())
final_score = predicted_interest + (5 - predicted_interest) * exploration_multiplier
```

Where:
- `predicted_interest` is the estimated user-interest score before exploration
- `exploration_strength` is between 0 and 1
- `rank_progress = a / b`
- `a` is the candidate item's position in the full candidate pool, starting at 1
- `b` is the full candidate pool size
- `random()` returns a normalized random value between 0 and 1

Why this version:
- later-ranked items get more exploration weight
- randomness modulates the bonus without collapsing it to near-zero too often
- the score remains capped at 5 because the exploration multiplier stays within `[0, 1]`

## Files expected in an installed copy
- `README.md`
- `project.md`
- `data/configuration-notes.md`
- `data/user-interest-profile.initial.md`
- `COMMAND_HANDLER_SPEC.md`
- `bsearch_handler.py`
- `tests/test_bsearch_handler.py`
- optional future implementation files such as storage schemas, prompts, scripts, and cron templates

## bSearch command catalog
All user commands must begin with `bSearch`. After that prefix, bSearch should interpret flexible natural language rather than requiring rigid syntax.

### 1. Insert / add
Purpose:
- manually store an item and score it immediately
- resolve it like a normal discovery item so it can participate in later learning

Examples:
- `bSearch insert https://github.com/Graphify-Labs/graphify 5`
- `bSearch add https://github.com/Graphify-Labs/graphify 5`
- `bSearch insert Graphify 5`

Behavior:
1. Detect insert/add intent from the text after `bSearch`.
2. Extract the likely item reference and score.
3. Resolve the item as if bSearch had discovered it normally:
   - identify title
   - identify source type
   - infer or assign category
   - gather a short description and useful links when possible
4. If the reference is ambiguous, ask a short clarification question.
5. If it is clear enough, add it to the stored pool/history with the given score.
6. Let manual inserts influence future learning just like discovered items.

### 2. List / browse categories and items
Purpose:
- browse categories
- browse items inside a category
- allow score/alpha sorting and limit/all views

Examples:
- `bSearch list`
- `bSearch list categories`
- `bSearch list score`
- `bSearch list score categories`
- `bSearch list alpha`
- `bSearch list alpha categories`
- `bSearch list 6`
- `bSearch list score 6`
- `bSearch list score 6 categories`
- `bSearch list all`
- `bSearch list AI`
- `bSearch list AI 4`
- `bSearch list 3`
- `bSearch list category 3`
- `bSearch list category 3 4`

Behavior:
1. `bSearch list` defaults to a numbered category list with current category scores.
2. `bSearch list categories` explicitly requests the same numbered category view.
3. Default sort is by score.
4. `score` means sort by score; `alpha` means alphabetical sorting.
5. A numeric argument used before category resolution acts as a display limit `N`; default limit is `10`.
6. `all` means show all items in the selected sorted view.
7. Therefore `bSearch list 6`, `bSearch list score 6`, and `bSearch list score 6 categories` all mean: show the first 6 categories sorted by score.
8. `bSearch list <category name>` shows a numbered list of items in that category with their scores.
9. If a category label/name is present, a following number is the item display limit for that category view. So `bSearch list AI 4` means: show the first 4 items in category AI.
10. Immediately after a numbered category list, `bSearch list <number>` may refer to that category by its list position when the intent is an immediate contextual follow-up.
11. To avoid ambiguity when both a category index and a limit are needed, prefer `bSearch list category 3 4` or `bSearch list category 3 limit 4`.
12. A bare two-number form like `bSearch list 3 4` is ambiguous and should trigger a short clarification rather than a guess.
13. Numeric category references are short-lived context helpers, not stable long-term IDs.

### 3. Planned next command families
These are not fully specified yet, but fit the agreed bSearch direction:
- `bSearch run` / `bSearch search now`
- `bSearch review pending` to reopen the latest unhandled delivered run for scoring/archive handling
- `bSearch rate ...` / `bSearch score ...`
- `bSearch show ...`
- `bSearch search memory ...`
- `bSearch show profile` / `bSearch update profile`
- `bSearch settings` / `bSearch set ...`
- `bSearch remove ...` / `bSearch archive ...`

### UX rule
Use numbered lists for categories and category item lists so the user can continue either by name or by index. Category names are the safer long-term reference; numeric references are convenience shortcuts for immediate follow-up. Sorting keywords (`score`, `alpha`) and view limits (`N`, `all`) should work for both category lists and category item lists.
