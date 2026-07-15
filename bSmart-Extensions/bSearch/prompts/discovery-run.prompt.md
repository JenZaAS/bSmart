# bSearch discovery run prompt

Use this prompt for manual runs or future cron runs.

## Goal
Run one bSearch discovery cycle for Erling.

## Run configuration
- Candidate pool size: 10
- Delivered item count: 5
- Exploration strength: 0.5
- Timezone preference: Europe/Oslo
- Preferred scheduled run time: daily at 03:00 Norwegian time
- Preferred model for scheduled runs: `openai-codex / gpt-5.4`

## User-interest anchors
Prioritize, but do not rigidly lock to, these themes:
- MATLAB
- Hermes-compatible AI harnesses / agent tooling
- Computer games
- Practical AI agents and useful automation
- VPS / Docker / Dokploy / technical tools

## Discovery workflow
1. First generate a mixed set of topic leads.
   - Some should be directly aligned with known interests.
   - At least two should be a little surprising or adjacent.
   - Use prior stored history/pool only as soft guidance, not a hard constraint.
2. Search for concrete items across sources such as GitHub, YouTube, blogs/posts, software/tools, and broader web content.
3. Build a candidate pool of 10 items.
4. Assign each item:
   - source type
   - short topic/category label
   - predicted interest
   - rank progress using `a/b`
   - softened random factor using `0.5 + 0.5 * random()`
   - final score capped at 5 via:
     `final_score = predicted_interest + (5 - predicted_interest) * exploration_strength * rank_progress * (0.5 + 0.5 * random())`
5. Keep the 5 highest-ranked items.
6. Present output in this format:
   - numbered shortlist with one sentence each
   - then one-by-one expanded sections with 2-4 sentence summary and 1-3 key links
7. If available, persist run metadata and candidate details for future learning.

## Tone
Be concise, practical, and high-signal.
