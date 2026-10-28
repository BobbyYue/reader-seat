"""Count context-reviewed defensive expressions; lexical hits are only candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

VERSION = 1
PROFILES = {'functional', 'literary', 'teaching', 'spoken'}
PATTERN = re.compile(
    r'不能|不足以|不代表|并不意味着|并非|不是|不等于|没有证据|未发现|尚未|'
    r'仅供参考|仅作参考|因人而异|具体情况具体分析|不构成|不保证|'
    r'\b(?:cannot|can[\x27’]t|does not|do not|is not|are not|not necessarily|'
    r'no evidence|not yet|for reference only|results may vary|no guarantee|'
    r'it depends|should not|must not)\b', re.I)
GUIDANCE = (
    'Complete defensive_expression within this same contextual review; no extra reviewer or round. '
    'Read the entire supplied surface, including opening, conclusions, captions and footnotes. '
    'Lexical signals are candidates only; add unflagged irrelevant corrections, empty disclaimers or repeated limits. '
    'Use one item per independently judged expression; split/merge spans when needed, retaining coverage of every signal. '
    'C counts reviewed candidates, D counts confirmed excess items, R counts the union of attributable excess characters '
    'over nonwhite NFC characters of this same supplied surface. Pending stays pending; never call it zero defects. '
    'For each item compare original, deletion and a faithful direct alternative; record the actual reader effect, '
    'protected meaning, prior context and reason. Use retain, excess or pending. Retain necessary negative findings, '
    'prohibitions, uncertainty, source quotes and supported character/narrator voice. When wording must stay exact, '
    'the direct alternative may equal the original with a concrete reason. Excerpts and partial scope cannot certify a whole work. '
    'Classify attribution as author, source-quote or character-voice. For excess supply exact excess_spans inside the item '
    'or an unmeasured_reason if a reliable span cannot be isolated. Moving text to notes is not a fix. '
    'Whole-text review must explain cumulative repetition, including when independent entry points need the same limit. '
    'D=0 is the completion target for confirmed problems, not a negative-word quota or industry threshold; '
    'repair excess items and remeasure the actual final text. Keep records private and reuse issue_id across other metrics.'
)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def count(text):
    return sum(not c.isspace() for c in unicodedata.normalize('NFC', text))


def meaningful(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {'pass', 'ok', 'none', 'n/a', '无', '通过', '已检查'}


def signals(text):
    """Preserve every location, including repeated words; no semantic verdict."""
    return [{'start': m.start(), 'end': m.end(), 'quote': m.group()} for m in PATTERN.finditer(text)]


def item(text, start, end):
    context_start = text.rfind('\n', 0, start) + 1
    found_end = text.find('\n', end)
    context_end = len(text) if found_end < 0 else found_end
    return {'issue_id': sha(str(start) + ':' + str(end) + ':' + text[start:end])[:16],
            'start': start, 'end': end, 'quote': text[start:end],
            'context_start': context_start, 'context_end': context_end,
            'context': text[context_start:context_end],
            'without': text[context_start:start] + text[end:context_end],
            'classification': 'pending', 'attribution': 'author', 'reason': '',
            'reader_effect': '', 'protected_meaning': '', 'prior_context': '',
            'direct_alternative': '', 'excess_spans': [], 'unmeasured_reason': ''}


def template(text, profile='functional'):
    if profile not in PROFILES:
        raise ValueError('Unknown defensive expression profile')
    hits = signals(text)
    items = []
    for match in re.finditer(r'[^。！？!?\n]+(?:[。！？!?]|$)|[^\n]+$', text, re.M):
        start, end = match.span()
        if any(start <= hit['start'] and hit['end'] <= end for hit in hits):
            items.append(item(text, start, end))
    return {'version': VERSION, 'text_sha256': sha(text), 'profile': profile,
            'scope': 'entire-supplied-surface', 'whole_text_review': '', 'items': items}


def span_ok(span, text):
    return (isinstance(span, dict) and type(span.get('start')) is int and type(span.get('end')) is int
            and 0 <= span['start'] < span['end'] <= len(text)
            and span.get('quote') == text[span['start']:span['end']] and bool(span['quote'].strip()))


def validate(record, text, profile=None, final=True):
    if not isinstance(record, dict):
        return ['defensive_expression missing review']
    errors = []
    if type(record.get('version')) is not int or record['version'] != VERSION or record.get('text_sha256') != sha(text):
        errors.append('defensive_expression stale version or text binding')
    if not isinstance(record.get('profile'), str) or record['profile'] not in PROFILES or (profile and profile != record['profile']):
        errors.append('defensive_expression wrong profile')
    if record.get('scope') != 'entire-supplied-surface' or not meaningful(record.get('whole_text_review')):
        errors.append('defensive_expression missing whole-surface contextual review')
    items = record.get('items')
    if not isinstance(items, list):
        return errors + ['defensive_expression items must be an array']
    ids, ranges = set(), set()
    for entry in items:
        if not span_ok(entry, text):
            errors.append('defensive_expression unanchored expression'); continue
        key = (entry['start'], entry['end'])
        identity = entry.get('issue_id')
        if not meaningful(identity) or identity in ids or key in ranges:
            errors.append('defensive_expression duplicate or invalid issue')
        elif any(key[0] < end and key[1] > start for start, end in ranges):
            errors.append('defensive_expression overlapping issues must be merged or split')
        ids.add(identity if isinstance(identity, str) else '')
        ranges.add(key)
        a, b = entry.get('context_start'), entry.get('context_end')
        if (type(a) is not int or type(b) is not int or not 0 <= a <= key[0] < key[1] <= b <= len(text)
                or entry.get('context') != text[a:b]
                or entry.get('without') != text[a:key[0]] + text[key[1]:b]):
            errors.append('defensive_expression deletion comparison changed')
        classification = entry.get('classification')
        if not isinstance(classification, str) or classification not in {'retain', 'excess', 'pending'}:
            errors.append('defensive_expression invalid classification')
        if entry.get('attribution') not in ('author', 'source-quote', 'character-voice'):
            errors.append('defensive_expression identify attribution')
        for name in ('reason', 'reader_effect', 'protected_meaning', 'prior_context', 'direct_alternative'):
            if not meaningful(entry.get(name)):
                errors.append('defensive_expression missing ' + name)
        spans = entry.get('excess_spans')
        if not isinstance(spans, list):
            errors.append('defensive_expression excess_spans must be an array'); continue
        for span in spans:
            if not span_ok(span, text) or not key[0] <= span['start'] < span['end'] <= key[1]:
                errors.append('defensive_expression excess span outside expression')
        if classification == 'excess':
            if not spans and not meaningful(entry.get('unmeasured_reason')):
                errors.append('defensive_expression excess span or unmeasured reason required')
            if entry.get('attribution') == 'source-quote':
                errors.append('defensive_expression preserve source quote; review author framing instead')
        elif spans:
            errors.append('defensive_expression only confirmed excess has excess spans')
        if final and classification in ('excess', 'pending'):
            errors.append('defensive_expression unresolved ' + classification)
    for hit in signals(text):
        if not any(start <= hit['start'] and hit['end'] <= end for start, end in ranges):
            errors.append('defensive_expression detected location lacks review')
    return errors


def summary(record, text, profile=None):
    """Compute counts only from structurally valid, current semantic records."""
    errors = validate(record, text, profile, final=False)
    if errors:
        return {'status': 'unmeasured', 'C': None, 'D': None, 'R_percent': None, 'errors': errors}
    entries = record['items']
    excess = [e for e in entries if e['classification'] == 'excess']
    pending = sum(e['classification'] == 'pending' for e in entries)
    ranges = sorted((s['start'], s['end']) for e in excess for s in e['excess_spans'])
    union = []
    for start, end in ranges:
        if union and start <= union[-1][1]:
            union[-1][1] = max(end, union[-1][1])
        else:
            union.append([start, end])
    denominator = count(text)
    measurable = all(e['excess_spans'] for e in excess) and not pending
    numerator = sum(count(text[start:end]) for start, end in union) if measurable else None
    return {'status': 'pending' if pending else 'reviewed', 'scope': record['scope'],
            'text_sha256': sha(text), 'C': len(entries), 'D': len(excess),
            'retained': len(entries) - len(excess) - pending, 'pending': pending,
            'excess_characters': numerator, 'visible_characters': denominator,
            'R_percent': numerator * 100 / denominator if numerator is not None and denominator else None,
            'R_status': 'not-applicable' if not denominator else 'measured' if measurable else 'unmeasured',
            'completion_eligible': not pending and not excess,
            'boundary': 'Semantic judgments supplied by reviewer; counts do not establish human benefit or whole-work coverage beyond this supplied surface.'}


def measurement(text):
    candidates = template(text)['items']
    return {'measurement_status': 'partial', 'data': {'C': len(candidates), 'D': None, 'R_percent': None,
            'visible_characters': count(text), 'count_basis': 'sentence candidates before semantic split/merge',
            'boundary': 'Lexical candidates only. Confirmed counts require the existing context review.'},
            'signals': [{'start': e['start'], 'end': e['end'], 'quote': e['quote'],
                         'issue_id': e['issue_id'], 'kind': 'defensive-expression-candidate'} for e in candidates]}


def result_schema():
    return {'type': 'object', 'required': ['version', 'text_sha256', 'profile', 'scope', 'whole_text_review', 'items'],
            'properties': {'version': {'type': 'integer'}, 'text_sha256': {'type': 'string'},
                'profile': {'type': 'string'}, 'scope': {'type': 'string'},
                'whole_text_review': {'type': 'string'}, 'items': {'type': 'array', 'items': {'type': 'object'}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'check', 'inspect'])
    parser.add_argument('--text', required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--profile', choices=sorted(PROFILES), default='functional')
    args = parser.parse_args()
    text = Path(args.text).read_text(encoding='utf-8')
    if args.mode == 'prepare':
        with Path(args.review).open('x', encoding='utf-8') as handle:
            json.dump(template(text, args.profile), handle, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'pending', 'guidance': GUIDANCE}, ensure_ascii=False))
        return
    record = json.loads(Path(args.review).read_text(encoding='utf-8'))
    errors = validate(record, text, args.profile, final=args.mode == 'check')
    print(json.dumps({'status': 'blocked' if errors else 'record-checks-satisfied',
                      'metrics': summary(record, text, args.profile), 'errors': errors}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
