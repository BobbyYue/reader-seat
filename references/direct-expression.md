# Direct Expression

Lead with the supported answer. Prefer affirmative phrasing only when equally
accurate; preserve source truth, scope, uncertainty and the author's natural voice.
Necessary prohibitions, refusals and negative findings can be direct answers.
“不是……而是……”, “不能” and “不按” are inspection signals, not forbidden words.

## Before, During And After

1. **Before:** add `expression_plan` to the existing required-answer plan using
   the [preplan fields](required-reader-answers.md#portable-plan-and-commands).
   Choose the leading answers, opening move and reason, and essential-boundary
   placements. Use correction for a relevant misconception, comparison for a
   real choice, instruction for an action, and direct assertion otherwise.
2. **During:** run
   `direct_expression.py prepare --text PATH --stage during --output JSON`
   on the actual complete unit. Complete its `expression_review` in the existing
   complete-unit record, comparing original wording with an equally accurate
   direct alternative and checking repetition across the reading path.
   See [writing-lifecycle.md](writing-lifecycle.md).
3. **After:** the existing independent readability reviewer supplies
   `reader_value.checks.expression.direct_expression` with `stage: after` for
   the stable candidate, without inheriting the author's keep rationales.
   Reuse the same four-reviewer batch and round policy; add no reviewer or round.
   See [reader-validation.md](reader-validation.md#readability).

The script-generated templates own exact review fields and bindings.
Counts and matches prompt contextual judgment, never pass/fail thresholds.

## Compare Meaning And Reading Cost

Compare the whole unit with a direct alternative, not only with deletion:
deletion can lose information that a different sentence would preserve.

- Identify the delayed answer and the assumption being corrected. A real
  misconception or misleading source claim may justify the contrast.
- Compare subject, polarity, scope, conditions, certainty, responsibility and
  action. “No evidence of benefit” differs from “evidence of no benefit.”
  Retain a necessary negative when an affirmative alternative changes meaning.
- Judge whether the alternative reduces detours without flattening the author's
  voice. Keep an already clear original; alternatives are review evidence,
  not automatic replacements or extra user-facing versions.
- Inspect headings, section leads and repeated labels together. Explain what
  each recurrence adds for the reading mode, including independent section
  entry. Individual keep rationales alone do not resolve accumulated burden.

Keep interpretation-changing conditions claim-adjacent. Put a shared boundary
at the section entrance when it remains visible to the relevant reader; reserve
method notes for background that does not change the nearby judgment or action.
These are placement choices, not once-only quotas. An all-keep result can be sound
after comparison; fewer negatives or completed records alone prove no improvement.

## Observed Bad Case

Provenance: [AI and Work, roles section](https://bobbyyue.github.io/reader-seat/reports/ai-and-work.zh.html#roles),
with a visible evidence cutoff of 22 Oct 2026; repository copy inspected on
23 Oct 2026. The label “不能省略的责任” appears in all six role blocks:

> 不能省略的责任：核对数据粒度、分母和归因；查询跑通，不说明分析回答了正确的问题。

The saved final readability review kept all three selected qualification
candidates. This motivates comparing direct alternatives and whole-report burden,
rather than treating a keep rationale for each caveat as sufficient.
This is generated prose, not validation of research.

An illustrative rewrite keeps the check and puts the work first:
“需要负责的工作：核对数据粒度、分母和归因；查询跑通后，仍需确认分析是否回答了要解决的问题。”

## Synthetic Contrasts

These independently invented examples illustrate choices, not fixed replacements.

| Original | Candidate or decision | Why |
| --- | --- | --- |
| 这次调整不是增加审批，而是把现有审批移到提交前。 | 这次调整把现有审批移到提交前，审批数量不变。 | Lead with the change; retain the original correction if added approval is the reader's actual concern. |
| 不按工单数量判断效果，而看问题是否解决。 | 用问题解决情况判断效果；工单数量单独列示。 | Reject this candidate: it invents an instruction to list counts. |
| 禁止将未脱敏日志发到外部群。 | Keep the prohibition. | “请注意日志安全” weakens the restriction. |
| 本轮未发现错误率下降，样本不足以排除小幅变化。 | Keep the finding and its limit. | “质量稳定” would add unsupported certainty. |

Use the paired synthetic cross-agent cases for behavioral checks. Existing
private fixtures retain their current scope; no publication is authorized.
