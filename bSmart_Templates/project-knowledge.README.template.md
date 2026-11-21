# Project knowledge

This folder is for curated, reusable knowledge that belongs to this project specifically. Rules: `bSmart_Protocols/knowledge.md`.

Notes live in topic folders, never directly in this folder:

- `code/` — code knowledge, including items created by `create bKnowledge {filename}`. Language-agnostic notes may sit directly in `code/`; language notes go in `code/<language>/`, such as `code/matlab/`.
- `tools/` — apps, services, and external references, one subfolder each, such as `tools/<some-app>/`.
- `general/` — last resort when no better topic fits.
- Any other topic you need, at any depth.

`index.md` lists the topics, one line each. Each topic folder has its own `index.md` that lists its notes, one line each. Add the line in the same step as the note. `CHANGELOG.md` records what was added, moved, or fixed.

Use it for:
- project-specific references and guides
- summaries that should be reused later
- templates or examples useful inside this project
- cleaned-up lessons from workdocs or research
- context that helps an AI or human understand this project later

Use `workdocs/` for active working notes, investigations, and handoffs. Use the instance Library instead when the material is useful beyond this project.

This folder is named `knowledge/` rather than `library/` to avoid confusion with software libraries in coding projects.

An entry that describes code names it in a `Code:` line, for example ``- Code: `src/app.py` — `main` ``. After a code change, update or remove the entries that no longer match (see `knowledge_upkeep` in `bSmart.md`).

`scripts/bKnowledgeCheck --project <project>` checks this layout; fix what it finds yourself.

Do not store secrets here.
