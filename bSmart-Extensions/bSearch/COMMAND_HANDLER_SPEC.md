# bSearch command handler spec

```yaml
name: bSearch command handler spec
status: design_ready_for_implementation
scope: chat-driven bSearch command parsing, storage updates, and retrieval behavior
canonical_root: /workspace/bSmart-Extensions/bSearch
created_utc: 2026-07-15
```

## Goal
Define a concrete handler contract for `bSearch ...` commands so the later runtime implementation can act on real files already present in the installed extension.

## Canonical installed paths
Use the installed extension copy as the runtime source of truth:
- root: `/workspace/bSmart-Extensions/bSearch`
- config: `/workspace/bSmart-Extensions/bSearch/config.yaml`
- state: `/workspace/bSmart-Extensions/bSearch/state.yaml`
- user profile: `/workspace/bSmart-Extensions/bSearch/user-interest-profile.md`
- candidate pool history: `/workspace/bSmart-Extensions/bSearch/runs/candidate-pool-history.jsonl`
- delivered history: `/workspace/bSmart-Extensions/bSearch/runs/delivered-history.jsonl`
- feedback history: `/workspace/bSmart-Extensions/bSearch/data/feedback-history.jsonl`
- category stats: `/workspace/bSmart-Extensions/bSearch/data/category-stats.json`

## Handler entry condition
A message should be treated as a bSearch command only if it begins with the prefix `bSearch`.

Anything after the prefix should be parsed flexibly from natural language.

## Parsing pipeline
1. Confirm the `bSearch` prefix.
2. Normalize the remainder:
   - trim whitespace
   - lowercase action keywords for intent matching
   - preserve original casing for titles/category labels when useful
3. Detect the command family.
4. Extract arguments.
5. Resolve ambiguity only when needed.
6. Execute the command against the installed storage files.
7. Return a concise human-readable result.

## Command families

### 1. `insert` / `add`
Purpose:
- manually add an item into bSearch as if it passed through the normal workflow

Accepted shapes:
- `bSearch insert <url> <score>`
- `bSearch add <url> <score>`
- `bSearch insert <short reference> <score>`
- `bSearch add <short reference> <score>`

Parsing rules:
- `insert` and `add` are equivalent
- score should be parsed as the trailing integer or real number in range `1..5`
- the preceding text is the item reference
- if no score is present, ask for it
- if score is outside range, ask for correction

Resolution rules:
- if the reference is a URL, fetch/inspect the item directly when possible
- if the reference is a short repo/project title, attempt normal resolution using web/GitHub search behavior
- if multiple plausible matches remain, ask one short clarification question

Storage behavior:
- append one normalized candidate record to `runs/candidate-pool-history.jsonl`
- append one normalized delivered record to `runs/delivered-history.jsonl`
- append one normalized feedback record to `data/feedback-history.jsonl`
- mark the records with `run_type: manual_insert`
- include `manual_inserted: true`
- store the original user command as `manual_insert_input`
- refresh `data/category-stats.json`
- refresh `user-interest-profile.md`

Minimum normalized candidate fields:
- `run_timestamp_utc`
- `run_type`
- `candidate_position`
- `candidate_pool_size`
- `title`
- `source_type`
- `category`
- `predicted_interest`
- `rank_progress`
- `final_score`
- `links`
- `description`
- `manual_inserted`
- `manual_insert_input`

Minimum normalized delivered fields:
- `run_timestamp_utc`
- `run_type`
- `title`
- `category`
- `predicted_interest`
- `final_score`
- `manual_inserted`

Minimum normalized feedback fields:
- `run_timestamp_utc`
- `run_type`
- `title`
- `category`
- `predicted_interest`
- `final_score`
- `user_feedback_score`
- `user_feedback_comment`
- `recorded_at_utc`
- `manual_inserted`
- `source_reference`

Response shape:
- title
- 2-5 sentence summary
- 1-3 useful links
- stored category
- stored score
- note that profile/category stats were refreshed

### 2. `list`
Purpose:
- browse categories
- browse items in a category
- allow sort and limit controls

Supported modifiers:
- sort: `score` or `alpha`
- scope word: `categories`
- limit: integer `N` or `all`
- category by label
- category by contextual index

Default behavior:
- `bSearch list` means category view
- default sort is `score`
- default limit is `10`

#### 2A. Category list mode
Examples:
- `bSearch list`
- `bSearch list categories`
- `bSearch list score`
- `bSearch list alpha`
- `bSearch list 6`
- `bSearch list all`

Data source:
- primary: `data/category-stats.json`
- fallback if needed: derive categories from `data/feedback-history.jsonl`

Output format:
- numbered list
- each line should include category name and score
- recommended displayed score = `feedback_avg`
- if useful, include item count too

Sort behavior:
- `score` = descending by category score, then category name
- `alpha` = ascending by category name

Limit behavior:
- if `N` supplied, return first `N`
- if `all`, return all
- if omitted, return first `10`

#### 2B. Category item list mode
Examples:
- `bSearch list AI`
- `bSearch list AI 4`
- `bSearch list alpha AI`
- `bSearch list category 3`
- `bSearch list category 3 4`
- `bSearch list category 3 limit 4`

Resolution order:
1. if explicit `category <index>` form is used, resolve by the most recent numbered category list context
2. else if a category label/name is present, resolve by fuzzy category-name match
3. else if a single bare number is present immediately after a recent category list, it may refer to contextual category index
4. else if no category can be resolved, stay in category list mode

Ambiguity rule:
- `bSearch list 3 4` is ambiguous
- do not guess
- ask a short clarification question

Data source:
- `data/feedback-history.jsonl` as the authoritative scored-item history
- optionally enrich from `runs/delivered-history.jsonl` when needed

Output format:
- numbered list of items in the category
- each line should include item title and score
- when useful, include source type or a very short note

Category item sorting:
- `score` = descending by user feedback score, then title
- `alpha` = ascending by title

Category item limit behavior:
- if category label/name is present, a following number means item limit
- if omitted, default item limit is `10`
- `all` means all items in the resolved category

### 3. `rate` / `score` / `update score`
Purpose:
- add or revise a score for an already known item

Accepted shapes:
- `bSearch rate <item> <score>`
- `bSearch score <item> <score>`
- `bSearch update score for <item> to <score>`

Behavior:
- resolve the referenced item from known history first
- if multiple matches remain, ask a short clarification question
- append a new feedback record rather than mutating old history in place
- refresh category stats and user-interest profile after the update

### 4. `show` / `open` / `tell me about`
Purpose:
- show the stored detail for one item

Behavior:
- resolve an item by title or contextual index from the most recent numbered item list
- return stored summary data and key links
- if insufficient stored detail exists, enrich from linked history records

### 5. `search memory` / `find saved`
Purpose:
- search the stored bSearch knowledge base

Behavior:
- search across titles, categories, descriptions, and links derived from stored history
- return a numbered result list with title, category, and score
- support later contextual follow-up using item indices

### 6. `show profile` / `update profile` / `add interest` / `remove interest`
Purpose:
- inspect or directly adjust the learned interest profile

Behavior:
- `show profile` reads `user-interest-profile.md`
- direct edit commands should patch the profile text in a minimal way
- after direct edits, keep category stats unchanged unless underlying scored data also changed

### 7. `settings` / `set`
Purpose:
- inspect or change runtime configuration

Config targets for v1:
- schedule
- candidate pool size
- delivered item count
- exploration strength
- source preferences
- preferred model pinning

Behavior:
- read/update `config.yaml`
- when schedule changes later require cron changes, the handler should report both config change and cron follow-up requirement

### 8. `run` / `search now`
Purpose:
- trigger an unscheduled discovery run

Behavior:
- before starting a new run, check whether the most recent delivered run still has unhandled items
- if it does, do not create a new run
- instead return a concise blocked result with the blocked run timestamp, pending item count, pending titles, and a suggested review command: `bSearch review pending`
- load current config/profile/history only after the gate passes
- run one discovery cycle using the existing prompt/spec
- persist candidate/delivered history
- present the result in the normal bSearch review format

Handled means at least one of:
- user rated/scored the delivered item after that run
- user archived/removed the delivered item after that run

### 8A. `review pending`
Purpose:
- reopen the latest unhandled delivered run so the user can score or archive its items

Behavior:
- return the pending items from the latest blocked run as a numbered review list
- include title, category, score, and source type when available
- include a short reminder to use `bSearch score <item> <1-5>` or `bSearch archive <item>`

### 9. `remove` / `archive`
Purpose:
- hide or retire an item from normal browsing without destroying audit history

Preferred v1 behavior:
- do not delete old history rows
- instead append a new status-bearing record or maintain an archive flag file later
- hidden/archived items should be excluded from default browsing but remain auditable

## Context memory rules for numbered follow-up
The handler should keep a short-lived in-session context for the most recent numbered bSearch list, including:
- list type: categories or items
- sort mode
- applied limit
- resolved category if item-list mode
- ordered identifiers behind the shown numbers

This context should only be trusted for immediate follow-up, not as a durable cross-session ID system.

## Rebuild rules after scored changes
The following commands should trigger category/profile refresh:
- `insert`
- `add`
- `rate`
- `score`
- any other command that appends scored feedback

Refresh sequence:
1. append feedback
2. rebuild `data/category-stats.json`
3. rebuild `user-interest-profile.md`
4. return a concise confirmation summary

## Safety and ambiguity rules
- do not treat non-`bSearch` chat text as a bSearch command
- if score parsing fails, ask for correction
- if the item/category reference is ambiguous, ask one short clarification question
- if two bare numbers appear in a `list` command, do not guess
- prefer explicit forms when both index and limit are needed

## Recommended implementation shape
A later implementation can cleanly split into:
- parser
- resolver
- storage adapter
- profile/category rebuild step
- response formatter

## Suggested first implementation priority
1. `insert` / `add`
2. `list` category view
3. `list` category item view
4. `rate` / `score`
5. `show`
6. `search memory`
7. `settings`
8. `run`
9. `remove` / `archive`
