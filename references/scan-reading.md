# Scan Reading In The Existing Review

Help readers locate relevant answers before choosing what to read closely.
Keep evidence, explanations and decisive conditions. F-shaped eye movements
describe one observed scanning behavior; do not design an F-shaped page or
infer comprehension from a heatmap.

## Before, During And After Writing

- Before writing, use the existing reader-task/required-answer plan to identify
  first-pass answers and their decisive conditions. Plan the cues that expose
  them: a useful overview, descriptive heading, opening sentence, emphasized
  statement, visual label or message opening. Do not create a separate plan.
- During each complete unit, read its cues together. Front-load the actual
  subject, finding or request; preserve uncertainty and actionable conditions
  with it. Group related content, use distinguishable hierarchy and spacing,
  and avoid repeated generic headings, decorative interruption and excessive
  emphasis. Keep explanation sufficient for the requested depth.
- After stabilization, the existing expression reviewer fills
  `reader_value.checks.expression.scan_reading`: quote the cues, restate their
  takeaway, locate decisive conditions within the cues, and locate the detail
  that makes the answer understandable. Compare against the locked required
  answers and the whole text. This is an editorial simulation, not a blind
  human experiment. Keep existing no-context reviews isolated and uncoached.
- The existing visual review inspects the actual native page: cues must really
  be noticeable, qualifiers must stay readable beside their claims, and tables
  or diagrams must not hide key content through clipping, scrolling or tiny
  text. Text matching alone does not prove visibility.

## Adapt To The Output

| Output | Focus of the same scan check |
| --- | --- |
| Complete document | Overview where readers need one; headings and leads reveal the reasoning path; definitions, evidence and detail have clear destinations. |
| 3080 brief | TLDR judgment, main picture and question table retain all decisive answers and conditions. Full explanations remain in the body; the scan does not waive visual coverage or body completeness. |
| Workplace message | The recipient can see the supplied update, intent or ask and the conditions needed to act. A factual update needs no invented request, deadline, heading or expansion. One clear sentence can supply every cue. |

For example, `上线安排` gives a topic; `回滚验证通过后上线` states the actual
condition. Emphasizing only `上线` would change what a scanning reader takes
away. This is a constructed example, not a source-backed release decision.

## Checks And Reuse

The prepared record starts pending and blocks acceptance. Missing records, stale text, unanchored
cues, recorded conditions absent from their cues, incomplete reasons or a
failed orientation/conditions/detail judgment block the existing validator.
The code checks evidence structure and binding; reviewers decide relevance,
coverage, truth, meaning and actual visibility. No automatic readability score
or blanket phrase ban is added.

Record negative judgments faithfully: a condition buried in the body has
`location: body`, its real `quote`, and `cue_index: null`; an omitted condition
has `location: missing`, `expected_condition`, its source/task `basis`, and a
null cue index. Both require a failed conditions judgment and block delivery.
They are completed failures, not incomplete reviews. Do not enlarge the cue set
or invent an anchor just to make the record pass. A correct condition elsewhere
also cannot rescue an unconditional emphasized claim; review both in context.
An actual quote such as `OK` or `可以` is valid message content, while those
words alone are inadequate review reasons. Specificity remains a semantic
judgment; the validator only rejects obvious empty attestations.

Merge findings into the same paragraph revision task. Within the existing
change-impact policy, recheck changed cues, claims, conditions, detail and
affected render; reuse only evidence whose inputs remain valid. Keep the
existing formal-review isolation, rounds and draft exit. Do not add a review
batch or a separate public report. Human time-to-find, accurate restatement and
condition omissions belong to separate usability tests when required; report
AI simulation and human observations separately. Any timing target is a local
task setting, not a universal result of the F-pattern study.

## Research Basis

- [Nielsen, 2006: original F-pattern study](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content-discovered/)
- [Pernice, 2017: context and common misconceptions](https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/)
- [Pernice, 2019: layer-cake scanning and descriptive headings](https://www.nngroup.com/articles/layer-cake-pattern-scanning/)

The workflow and evidence fields above are this project's application of those
findings, not an NN/g measurement standard.
