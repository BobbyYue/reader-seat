"""SYNTHETIC expression records for structural wiring, never quality proof."""
import direct_expression


def structural_expression_plan(answer_id="A1"):
    return {
        "lead_answer_ids": [answer_id],
        "opening_move": "direct",
        "opening_reason": "SYNTHETIC: lead with the fixture's required answer; no reader judgment.",
        "essential_boundaries": [],
    }


def structural_expression(text, stage="after"):
    record = direct_expression.template(text, stage)
    opening = next((line.strip() for line in text.splitlines() if line.strip()), "")
    record["opening"].update(
        quote=opening[:100], decision="keep",
        reader_gain="SYNTHETIC: exact opening anchor only, not reader-benefit evidence.")
    for item in record["comparisons"]:
        item.update(
            function="claim", alternative_kind="rewrite",
            alternative="SYNTHETIC alternative placeholder: " + item["quote"],
            protected_meaning="SYNTHETIC: source preservation is not evaluated by this fixture.",
            reader_gain="SYNTHETIC: structural comparison only, not measured reader gain.",
            prior_context="SYNTHETIC: context is not independently assessed.",
            reason="SYNTHETIC: exercise record validation, not a wording recommendation.",
            decision="keep")
    record["whole_text"].update(
        decision="keep", reading_effect="SYNTHETIC: complete record wiring, not a quality assessment.")
    for cluster in record["whole_text"]["clusters"]:
        cluster.update(
            decision="keep", reading_effect="SYNTHETIC: repeated-family coverage only.",
            reason="SYNTHETIC: counts are attention signals, not proof of a reader problem.")
    return record
