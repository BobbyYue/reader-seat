# Visual Communication And Integrity

Use this module after [visual-decision.md](visual-decision.md) returns
`retain-visual` or `asset-visual`, or when the task reviews an existing visual
encoding. The decision module owns reader-job selection, the prose comparison,
and the deletion test. This module preserves the full implementation rules for
form selection, encoding integrity, color, layout, scenario adaptation, and
render verification.

Use [visual-evidence.md](visual-evidence.md) separately for origin, identity,
authenticity, licensing context, and synthetic disclosure. Record the reader
job selected by the decision module in the visual specification below.

## Form Selection

Choose by reader task, not by variety or visual appeal.

| Reader task | Preferred form | Use prose instead when |
| --- | --- | --- |
| One conclusion or instruction | Short prose or one bounded callout | The content does not need persistent emphasis |
| Several short peer conclusions with no shared comparison fields | Numbered list or unframed rows | Use cards only when each item has repeated fields the reader must scan or compare |
| Ordered actions | Numbered steps | Order is not meaningful |
| Exact values across shared criteria | Table | Only one or two values matter and no comparison is needed |
| Trend or change over time | Line chart | There are too few points or exact values matter more than pattern |
| Magnitude or ranking | Bar or dot plot | The comparison can be stated accurately in one sentence |
| Part-to-whole | Stacked bar; pie only under strict conditions | Parts do not share a meaningful whole or precise comparison matters |
| Relationship or correlation | Scatter plot | Sample size or evidence is too weak to support a visible pattern |
| Process, dependency, hierarchy, or system | Diagram | The relationship is simple enough for a sentence or short list |
| Real interface state or location | Cropped, annotated screenshot | The state is not source-verified or a textual instruction is sufficient |
| Options with common criteria | Decision table | Criteria differ so much that side-by-side comparison would mislead |

Prefer the least complex form that preserves the information. Do not turn a
list into cards, a sentence into a chart, or a small table into an infographic
merely to create visual variety. Two to four short conclusions remain a list or
unframed rows unless each item contains repeated fields whose grouping improves
comparison. A heading plus one sentence is not enough to justify a card.

## Visual Specification

Before building each material visual, record:

| Field | Required decision |
| --- | --- |
| Reader question | The exact question the reader should answer |
| Reader job | `locate`, `compare`, `explain`, `emphasize`, or `verify` |
| Source | Data, passage, interface state, or verified asset supporting it |
| Form | Prose, table, chart type, diagram, screenshot, callout, or no visual |
| Encoding | Position, length, angle, area, color, shape, line, annotation, or order |
| Context | Unit, denominator, period, baseline, sample, definition, missing data, and uncertainty as applicable |
| Color semantics | What each non-neutral color means and where else that meaning is used |
| Reader alternative | Text equivalent, direct labels, table, caption, or other redundant channel |
| Responsive behavior | Stable dimensions, collapse, wrapping, internal scrolling, and print behavior |
| Deletion result | The reader cost that would increase if the visual were removed |
| Verification | Value match, rendered state, accessibility, and source/caption result |

This is an internal design record. Do not expose it in the finished artifact.

## Chart Integrity

Charts are evidence expressions. Their geometry, scale, order, labels, and
omissions must preserve the source.

### Hard requirements

- Use source-backed values only. Preserve units, denominators, periods,
  definitions, comparison bases, sample information, missing-data treatment,
  and material uncertainty.
- Recompute and verify every derived annotation, tooltip, or caption value,
  including differences, rates, averages, shares, and cumulative changes. State
  or preserve the applicable denominator or interval count; do not infer a
  derived value from the visual shape.
- Start quantitative bar axes at zero. When a non-zero baseline is essential
  for another chart type, disclose it clearly and confirm it does not exaggerate
  the result.
- Do not use 3D, perspective, volume, shadows, pictograms, or area distortion
  to encode magnitude.
- Do not use a second axis unless the relationship is essential and cannot be
  understood in aligned small multiples. If retained, label both scales
  directly and verify that the apparent relationship is not an axis artifact.
- Keep time direction, category order, interval width, and aggregation
  consistent with the stated analytical question.
- Distinguish observed values, estimates, forecasts, targets, and missing data
  through labels or redundant encodings.
- Give every chart a content-bearing title or caption that states the object,
  measure, population or scope, and period needed for interpretation. A title
  may state the supported finding; it may not manufacture one.
- Place the source and necessary notes close enough that the chart remains
  interpretable when shared or screenshotted.

### Defaults and review signals

- Prefer direct labels over a distant legend when the chart remains readable.
- Use position and length before area, angle, or saturation for precise
  comparison.
- Use one neutral series treatment and one intentional highlight when the task
  is to locate a focal result.
- More than about four simultaneous series or categories is a review signal,
  not an automatic failure. Aggregate, filter, split into small multiples, or
  retain them only when the reader task genuinely requires the complexity.
- Use a pie or donut only for a meaningful whole, mutually exclusive parts,
  few categories, no negative values, and no need for precise comparison.
- Sort bars by value for ranking and by a meaningful domain order when sequence
  matters. Do not reorder merely to create a stronger story.

## Color Encoding

Color must carry a defined role and must never be the only information channel.

### Functional roles

- **Neutral**: body text, rules, inactive series, secondary context.
- **Accent**: the one item or path the reader needs to locate.
- **Categorical**: distinct peer categories with no implied order.
- **Sequential**: ordered magnitude from low to high.
- **Diverging**: movement around a meaningful midpoint such as zero, target,
  or neutral response. Do not use a diverging palette without a real midpoint.
- **Status**: success, warning, risk, failure, or unknown. Keep meanings
  consistent throughout the artifact and with the target platform when known.

### Requirements

- Define each non-neutral color's semantic role before use. Do not use a
  rainbow palette as a default series assignment.
- Pair status and category colors with text, position, shape, icon, pattern,
  or direct labels. Red versus green alone is insufficient.
- Maintain WCAG AA contrast for substantive text and controls. Important chart
  marks, focus states, and control boundaries must also remain distinguishable.
- Use saturation and strong contrast sparingly so emphasis remains meaningful.
- Do not use gradients, colored surfaces, or alternating hues as decoration
  when they imply no information.
- Test grayscale or a color-vision-deficiency preview when color carries a
  decision-critical distinction.

## Layout And Non-Chart Elements

- Use hierarchy, alignment, spacing, and grouping to expose relationships.
  Avoid decoration that competes with the main reading path.
- Keep the primary argument in unframed sections or full-width bands. Use cards
  only for repeated peers with meaningful internal structure or genuinely
  bounded tools; do not nest cards. Do not use one card per simple conclusion
  to make a sparse source look richer.
- Use a callout for a bounded exception, decision, warning, or action. Do not
  put ordinary paragraphs into callouts to make them look important.
- Use a table for exact lookup or shared-criteria comparison. Do not use it for
  long prose that needs narrative order. Keep row and column headers explicit.
- Annotate screenshots only to locate a real state or action. Crop irrelevant
  chrome while retaining enough context to orient the reader.
- Give fixed-format elements stable responsive dimensions. On small screens,
  stack or scroll the element inside its own container rather than expanding
  the entire page.
- Keep captions, units, definitions, uncertainty, source notes, and synthetic
  labels adjacent to the element they qualify.

## Scenario Adaptation

Use the selected scenario's reader task to decide which visual roles deserve
priority.

- **News or industry brief**: use timelines, verified source visuals, or small
  comparison tables when they clarify what changed and when. Do not import an
  unrelated photograph merely to supply a cover.
- **Technical proposal**: use system diagrams for boundaries and dependencies,
  sequence diagrams for runtime behavior, and decision tables for options with
  shared criteria. Label proposed and implemented states distinctly.
- **Product document**: use user flows, before/after task paths, capability-to-
  problem mappings, and verified product screenshots. Do not invent adoption
  metrics or present a concept screen as a released interface.
- **Business update**: use target-versus-actual tables, trends, contribution
  views, and status summaries. Separate activity from outcome and do not use
  color to convert weak evidence into apparent success or failure.
- **Analysis or research**: prioritize charts that answer the analytical
  question and retain scale, baseline, definition, missing data, and
  uncertainty. The chart title may carry the conclusion only at the level the
  evidence supports.
- **Procedure or SOP**: use numbered flow, decision branches, and annotated
  screenshots when they reduce execution error. Keep success signals and
  recovery paths visible near the relevant step.

## Rule Levels

Keep these levels distinct during review.

### Hard failures

- invented, altered, or untraceable values;
- geometry, axis, area, order, or color that materially distorts the source;
- missing unit, denominator, period, definition, uncertainty, or source when
  its absence can change interpretation;
- meaning communicated only through color;
- inaccessible or broken rendering that prevents the reader task;
- a visual with no valid reader job that materially obscures the document;
- a visual that silently expands provenance, product state, or causal claims.

### Defaults

- concise prose before complex graphics;
- one restrained accent and neutral context;
- direct labels when readable;
- tables for exact values and charts for patterns;
- no 3D and no dual axis;
- responsive single-column fallback on narrow screens.

### Review signals

- many simultaneous colors or series;
- repeated cards, badges, callouts, or section bands;
- decorative gradients, large empty areas, or oversized headings;
- a legend that requires repeated eye travel;
- a chart whose message can be stated fully in one short sentence;
- a visual whose title promises more than its marks and source support.

A review signal triggers inspection, not automatic deletion. Confirm the reader
impact before changing the artifact.

## Final Verification

Before delivery, verify:

1. every material visual answers a recorded reader question and passes the
   deletion test;
2. the selected form is simpler and clearer than the best prose alternative;
3. every value, label, unit, denominator, period, baseline, and definition
   matches its source;
4. every derived difference, rate, average, share, and tooltip value has been
   recomputed from the source using the correct denominator or interval count;
5. chart geometry, order, aggregation, missing data, and uncertainty do not
   alter the apparent conclusion;
6. color roles are consistent, accessible, and redundantly encoded;
7. titles, captions, annotations, and sources remain adjacent and legible;
8. desktop, mobile, print, and target-platform rendering preserve the reading
   path without page-level overflow, overlap, truncation, or blank charts;
9. the artifact still works when nonessential decoration is removed;
10. visual provenance and synthetic disclosure pass
   [visual-evidence.md](visual-evidence.md) when applicable.

## Industry Basis

The module adapts, rather than mechanically copies, these authoritative
practices:

- [Royal Statistical Society, Why we visualise data](https://royal-statistical-society.github.io/datavisguide/docs/why-visualise.html)
  and [Choosing a visualisation type](https://royal-statistical-society.github.io/datavisguide/docs/choosing.html):
  choose visuals for reader understanding and analytical purpose.
- [UK Government Analysis Function, Data visualisation: charts](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-charts/)
  and [accessible chart checklist](https://analysisfunction.civilservice.gov.uk/policy-store/charts-a-checklist/):
  use honest scales, clear titles, direct labeling, source context, and
  accessible alternatives.
- [UK Government Analysis Function, Colours in charts](https://analysisfunction.civilservice.gov.uk/policy-store/data-visualisation-colours-in-charts/):
  use color deliberately, consistently, and sparingly.
- [W3C WCAG 2.2, Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color)
  and [Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html):
  do not rely on color alone and preserve distinguishable visual information.
- [IBM Design Language, Data visualization basics](https://www.ibm.com/design/language/data-visualization/design/basics/)
  and [Carbon color palettes](https://v10.carbondesignsystem.com/data-visualization/color-palettes/):
  treat hierarchy, color, labeling, and consistency as parts of one system.

Reader's Seat adds the deletion test, visual specification, scenario routing,
and rule-level separation so these principles are operational in AI-generated
work documents rather than applied as a generic style guide.
