"""Require an anchored whole-surface judgment, not a keyword-based quality score."""

CHECKS = ('answer', 'selection', 'ending')
GUIDANCE = (
    'Complete whole_text_scan as three compact observations: answer, selection, ending. '
    'Each is {status:pass|revise|unassessed|not_applicable,quote,reason,repair}; quote actual supplied text. '
    'Answer: state what this reader can now understand, judge, express or do; identify work still left to them. '
    'A promise to analyze, generic approval, list of dimensions or unspecified conditions is not the requested result. '
    'A concrete method is valid when requested; a bounded unknown is valid when evidence does not support more. '
    'Never invent certainty, evidence, decisions or requests to make an answer look complete. '
    'Selection: review section-level priorities and cumulative caveats, not just whether each sentence has a defensible use. '
    'Name the actual task-specific misreading prevented by a retained condition; do not invent a hypothetical reader. '
    'Keep examples, reasoning, transitions, useful teaching repetition and required safety/permission notices. '
    'Check decorative diagrams, internal review narration and repeated disclaimers for contribution. '
    'Ending: judge where this supplied surface should stop. Remove unrequested service offers, empty reassurance '
    'or reopening settled points; retain useful recaps, actual recipient requests and necessary unresolved conditions. '
    'For a unit, assess its local answer and transition, not whether the entire document is complete. '
    'For literary work, answer may be not_applicable with a reason; selection and ending follow intended voice, '
    'rhythm and deliberate openness. No forced conclusion, action, fixed length or negative-word quota. '
    'Pass needs a real quote and concrete reason, with repair empty. Revise/unassessed needs a specific repair; '
    'use an empty quote only when the needed answer is entirely absent and explain that absence. '
    'Reuse existing suspect-item IDs when describing the same problem. No new reviewer, round or visible checklist. '
    'The validator checks declarations, text and consistency; the semantic judgment still belongs to the reviewer.'
)


def template():
    return {key: {'status': 'pending', 'quote': '', 'reason': '', 'repair': ''} for key in CHECKS}


def substantive(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().casefold() not in {
        'pass', 'ok', 'none', 'n/a', '通过', '无', '已检查'}


def validate(record, text, profile='functional'):
    if not isinstance(record, dict) or set(record) != set(CHECKS):
        return ['reader_delivery requires answer, selection and ending observations']
    errors = []
    for key in CHECKS:
        item = record[key]
        if not isinstance(item, dict) or set(item) != {'status', 'quote', 'reason', 'repair'}:
            errors.append('reader_delivery malformed ' + key)
            continue
        status, quote, repair = item['status'], item['quote'], item['repair']
        if not isinstance(status, str) or status not in {'pass', 'revise', 'unassessed', 'not_applicable'}:
            errors.append('reader_delivery unreviewed ' + key)
        if not substantive(item['reason']):
            errors.append('reader_delivery missing task-specific reason: ' + key)
        if not isinstance(quote, str) or (quote and (not quote.strip() or quote not in text)):
            errors.append('reader_delivery unanchored quote: ' + key)
        if not isinstance(repair, str):
            errors.append('reader_delivery repair must be text: ' + key)
        if status == 'not_applicable':
            if key != 'answer' or profile != 'literary' or quote or repair:
                errors.append('reader_delivery cannot waive ' + key)
        elif status == 'pass':
            if not isinstance(quote, str) or not quote.strip():
                errors.append('reader_delivery passed observation needs actual text: ' + key)
            if repair:
                errors.append('reader_delivery pass contradicts outstanding repair: ' + key)
        elif status in ('revise', 'unassessed'):
            if not substantive(repair):
                errors.append('reader_delivery unresolved observation needs repair: ' + key)
            errors.append('reader_delivery unresolved ' + key + ': ' + status)
    return errors
