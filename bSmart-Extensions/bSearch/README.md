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
- learn from explicit user ratings over time
- preserve prior items as a searchable knowledge repository

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
- optional future implementation files such as storage schemas, prompts, scripts, and cron templates
