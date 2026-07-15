# Project: bSearch extension

```yaml
project_name: bSearch extension
status: packaged_in_bsmart_system
owner: Erling H Jensen / SschwAdmin
objective: Package bSearch as an optional bundled bSmart extension that can be installed into an instance and later implemented as a scheduled AI knowledge-search workflow.
agent_focus: bSmart extension packaging, initialization design, scoring design, and safe Hermes cron-based automation planning.
created_utc: 2026-07-14
```

## Packaging model
- Canonical packaged source lives under `/workspace/bSmart-System/bSmart-Extensions/bSearch`.
- Installed instance copy lives under `/workspace/bSmart-Extensions/bSearch`.
- bSmart setup should offer this extension during initialization with a short explanation.
- bSearch remains optional even though it ships with bSmart.

## Initialization model
The installed extension should be initialized by guiding the user through:
1. Search schedule
2. Candidate pool size
3. Delivered item count
4. Exploration strength
5. Source preferences
6. Initial user-interest profile review/edit
7. Preferred scheduled-run model pinning

## Data/behavior highlights
- keep a concise editable user-interest profile
- let the user rate delivered items from 1 to 5
- keep item history and category learning data
- support later manual insertion into the knowledge repository
- support later search/retrieval over stored items

## Current status
This extension is packaged and documented, but the runtime implementation is still future work.
