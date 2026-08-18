# Diagnosis And Revision

Use this module for an existing document. Preserve the source unless the user explicitly authorizes in-place editing.

## Diagnose In Priority Order

### 1. Hard Failure

Examples: factual drift, unsupported claim, wrong number or definition, hidden uncertainty, scope change, ambiguous ownership, unsafe action, or missing critical source.

Action: stop stylistic polishing and fix or clearly surface the failure.

### 2. Scenario Failure

Examples: wrong primary route, missing required content, inappropriate body relationship, or a reader unable to complete the scenario's main task.

Action: load the correct scenario module and repair the smallest structural unit that resolves the failure.

### 3. Output-Standard Failure

Examples: main information buried, generation process exposed, jargon without reader need, repeated conclusion, unsupported certainty, silent assumption, or unnecessary action.

Action: identify the affected passage, reader impact, and minimal fix.

### 4. Style Choice

Examples: formality, sentence rhythm, heading density, rhetorical devices, visual style, or amount of context.

Action: preserve the author's choice unless it conflicts with the reader task or explicit user request.

## Revision Modes

| Mode | Use when | Behavior |
| --- | --- | --- |
| Local edit | The document route and main structure work | Change only the failing sentence, paragraph, heading, table, or visual |
| Section rebuild | One section has the wrong reader path | Rebuild that section and preserve the rest |
| Full restructure | The current document route or whole-document relationship is wrong | Reorder or rewrite the document while preserving the source boundary |
| Diagnostic only | The user asks for evaluation, not editing | Return findings and fixes; do not silently produce a replacement |

## Meaning-Preservation Check

Compare the result against the source for:

- subject, predicate, object, direction, magnitude, and comparison basis;
- conditions, exceptions, exclusions, time, sample, and uncertainty;
- stance, ownership, responsibility, commitment, and intended ask;
- source attribution and separation of fact from interpretation.

## Avoid Mechanical Rewriting

- Process every detected review signal through [signal-processing.md](signal-processing.md); do not jump from detection to editing.
- Sentence-length and readability thresholds identify review candidates; they are not violations.
- Passive voice matters only when it hides responsibility or makes the action unclear.
- A familiar acronym does not need expansion for every audience; an ambiguous metric may need a local definition even when its acronym is familiar.
- “AI-sounding” is not a word blacklist. Fix concrete problems such as vague abstraction, repeated structure, empty transition language, excessive symmetry, generic method headings, or unsupported polish.
- Do not assume that a leading summary or visual must be removed. Keep it when it serves the reader, but name and shape it from the content rather than exposing the framework used to create it.

## Diagnostic Output

Lead with the overall assessment. Order findings by consequence, not by document position. For each finding include:

1. affected passage or pattern;
2. why it impairs the reader task or factual integrity;
3. the smallest effective fix;
4. a rewritten example only when it helps the user act.

If no material issue exists, say so and identify only residual risk or untested reader assumptions.

When a likely mechanical edit is dismissed, briefly explain the context-specific reason if that decision helps the user trust or reuse the diagnosis.
