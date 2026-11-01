"""Synthetic scan receipts for plumbing tests; never use as editorial evidence."""
import scan_reading


def structural_scan(text, profile):
    record = scan_reading.template(text, profile)
    quote = text[:100]
    record.update(cues=[{"kind": "message" if profile == "message" else "lead", "quote": quote}],
                  takeaway="STRUCTURAL TEST FIXTURE, not actual comprehension.",
                  no_conditions_reason="STRUCTURAL TEST FIXTURE, not a source-condition judgment.",
                  detail_quote=quote)
    for check in record["checks"].values():
        check.update(status="pass", reason="STRUCTURAL TEST FIXTURE, not an editorial assessment.")
    return record
