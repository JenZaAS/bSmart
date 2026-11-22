# bTeach rules

Use this when the user asks to be taught or to have something explained at
their level. Two modes; explain is the default.

## Never during a build

Do not teach while a build is running: a bSwarm run, or a coding task in
progress in this session. Say in one line that you will explain it when the
work is done, and offer it then. A few words of plain explanation inside a
normal answer are still fine (`response_style` in `bSmart.md`).

## Mode 1: explain (default)

1. **Find the level.** Use what the instance profile, memory, and earlier
   corrections say about the user's background. Assume strong knowledge of
   their own field; do not start from basics they already know. If the level
   is unknown, ask one short question about it first.
2. **Look it up first.** Before explaining a project word or design, check
   the project glossary index and the matching ADRs
   (`bSmart_Protocols/design-context.md`). Read only the lines and records the
   topic needs. For general AI-coding words, the external reference in that
   protocol (section 3) may help. Do not explain from memory what the repo or
   a source can confirm; say when something is uncertain.
3. **Explain one thing.** Short plain sentences, at that level: what it is,
   why it matters here, and one concrete example from the project when there
   is one. Explain any jargon in a few words. No long lecture.
4. **Point to the source.** Name the glossary entry, ADR, file, or source the
   explanation rests on, so the user can read more.
5. **Check once.** Ask one short question, or ask the user to say it in
   their own words. If the answer shows a gap, explain that part once more,
   differently. Then stop, unless the user asks for the next part.

A correction of a term the user gives is saved as the knowledge habits say
(`bSmart_Protocols/knowledge.md`, habit 6).

## Mode 2: course (only on request)

Only when the user asks to learn a topic over several sessions.

- **Where.** A folder outside any product or code repo:
  `<content-root>/Workdocs/learn/<topic>/` by default, or a Library topic if
  the user prefers. Never inside a code repo.
- **Start.** Ask what the user already knows and what they want to be able to
  do afterwards (a concrete result, not "understand X"). Write
  `course.md` from `templates/course.template.md`. Collect trusted sources
  before writing lessons.
- **Lessons.** One short markdown lesson at a time in `lessons/`
  (`0001-<slug>.md`, from `templates/lesson.template.md`): one sitting, one
  clear win, sources named, one check question at the end. Knowledge first,
  then a short practice or quiz.
- **Progress.** After each lesson, add one line to the progress list in
  `course.md`: what the user showed they know, or a corrected
  misunderstanding. Use it to pick the next lesson, so a new session can say
  "next lesson" and continue.
- **Change the goal** only after the user confirms.
- Keep it concise. Markdown only; no generated web pages.

## Limits

- The coder never runs bTeach; it is for the human.
- Teaching never gives permission to edit, build, commit, or publish.
- bTeach writes only its own course folder. It does not write the glossary,
  ADRs, or project knowledge; suggest a change instead.

### Only if there's an issue

- The explanation missed the level: ask what was unclear, then save the
  level as a preference in memory or the course file so it sticks.
- A course folder ended up inside a code repo: move it to the default place
  and tell the user.
