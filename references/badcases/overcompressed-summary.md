# Bad Case: Accurate Headings Without Enough Explanation

## Observed Failure

A reader asked for the main views in a substantial discussion. The output
contained eight content-bearing headings, each followed by one short sentence.
It named the views but omitted the reasoning, useful examples and connections
that made them understandable. The visible artifact felt like a topic index.
The explanation request had been reduced to a label-coverage plan.

Only static HTML checks had passed; independent comprehension and rendered
verification had not completed. A preview limitation did not cause the missing
explanation and could not justify presenting an outline as a finished summary.
The actual triggering draft is retained locally when available, not distributed
with personal task context. The public fixture below is independently fictional.

## Reproducible Teaching Case

- [Source](../../evals/fixtures/overcompression/source.md): an internal support
  assistant discussion, including reasons, risks and rollout conditions.
- [Bad output](../../evals/fixtures/overcompression/bad.md): the same
  heading-plus-one-sentence shape, with the important links removed.
- [Better output](../../evals/fixtures/overcompression/good.md): explains the
  selected relationships without copying all the source.

The failure is not "eight headings", "short sentences" or a word count.
For the request "list the topics only", an outline can be correct. The bad
output fails an explanation task because the reader cannot say why the team
chose an internal pilot, when humans must take over, or why evidence and error
records matter to expansion.

## Required Repair

1. Before drafting, select orientation, explanation or execution in the answer
   plan, with a task-specific reason. Do not quietly equate "summary" with
   "headlines".
2. For explanation, retain the important why/how/evidence links from the
   source. Select supporting examples only when they prevent a real
   misunderstanding. No mandatory example count or paragraph recipe.
3. Separate a scan-friendly overview from explanation when that helps. A short
   artifact can also succeed without two visible sections if it answers the task.
4. Let a fresh reader restate the relationships without the source. The source
   reviewer must inspect both the plan's depth and the raw replay, not merely
   match keywords. Record depth_fit in the existing answer evaluation.

## Controls Against Overcorrection

- Keep an explicitly requested outline, lookup answer or already-clear short
  update short.
- Do not invent evidence or personal experience to add substance. If the
  source lacks a reason, retain that unknown.
- When access, source-use or requested-length constraints prevent adequate
  explanation, narrow the scope or state the limitation. Do not silently
  substitute a topic list or evade an access/source-use restriction.
- More paragraphs, visuals, repeated caveats or a minimum word count do not
  prove understanding. Preserve facts, source language, format and existing
  independent-review limits.
