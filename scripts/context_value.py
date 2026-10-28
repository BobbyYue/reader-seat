"""Context-bound deletion comparisons. Signals select review, never prescribe edits."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import source_attribution
import defensive_expression

VERSION = 4
INSTRUCTION_BOUNDARY_GUIDANCE = (
    'Separate agent-facing writing instructions from reader-facing content. Turn tone, audience, structure, length, '
    'method and revision requests into writing choices, not literal or paraphrased compliance statements in titles, '
    'body, captions, labels or copyable messages. During whole_text_scan ask whether each passage explains the subject '
    'or merely announces which writing instructions were followed; a clean signal scan does not answer this. '
    'Use the existing items for suspect passages, including unflagged paraphrases. Keep independently useful methodology, '
    'evidence limits, metric definitions, risks, recipient-facing directions/agreements and intentional quoted or fictional '
    'speech. Retain requested process explanations only on the surface requested, not by inserting them into the work. '
    'Review source-prescribed text without silently altering it. Do not give private author instructions to a source-free reader. '
)
EFFECTS = {'information', 'interpretation', 'confidence', 'action', 'connection', 'learning', 'voice', 'required-disclosure', 'none'}
DECISIONS = {'keep', 'remove', 'rewrite', 'move'}
ITEM_FORMAT = {'effect': sorted(EFFECTS), 'decision': sorted(DECISIONS)}
GUIDANCE = (INSTRUCTION_BOUNDARY_GUIDANCE + 'Read the whole supplied surface for its actual audience. For each suspect passage compare the paragraph with and without it. '
    'A true sentence is not automatically useful: omit repetition of established context and internal correctness reports. '
    'Prefer an accurate claim to an overstated claim plus a disclaimer. Keep new evidence, actual clarification, decision/action changes, '
    'necessary connections, required disclosures and intentional literary/teaching effects. Identify the concrete difference, not hypothetical '
    'generic misunderstanding. Terms are signals, not bans. Mark unresolved remove/rewrite/move requests for normal revision; do not add '
    'reviewers, a style score or another review round. Keep this record private. Complete attribution_replay as what the text '
    'actually makes the reader attribute; inspect source claims next to author limits/recommendations. '
    'New context_review.items require id, context, quote, without, with_reading, without_reading, effect, reason, decision; '
    'without is context minus one exact unique quote. Use exact enums: ' + json.dumps(ITEM_FORMAT, separators=(',', ':')) + '. '
    'Do not substitute status/action or descriptive enum values. ' + source_attribution.GUIDANCE)
GUIDANCE += " " + defensive_expression.GUIDANCE
SIGNALS = (('qualification', r'不代表|并不意味着|不能据此|仅供参考|仅作阅读|not (?:proof|evidence)|does not (?:mean|prove)|for (?:reference|reading) only'),
           ('calculation-note', r'原始精度|展示值|未按.{0,12}重新分组|rounded (?:values|display)|unrounded|display precision'),
           ('writing-instruction', r'(?:按|按照|遵照)(?:你|您|用户)的?(?:要求|指令)|(?:本文|本段|本节|这一段|这篇(?:文章|报告)).{0,32}(?:专业但易读|读者视角|不夸张|不刻意吸引眼球)|为了让(?:读者|你).{0,20}(?:看懂|读懂).{0,20}(?:先|下面)|(?:as (?:you )?requested|according to your (?:instructions|request))|this (?:article|section|paragraph).{0,50}(?:professional (?:but|yet) readable|reader[- ]first|avoid hype)'))


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {'pass', 'ok', 'none', 'n/a', '通过', '无'}


def probes(text):
    """Nearby sentence context, not a duplicated full article or a length verdict."""
    result = []
    spans = [(m.start(), m.end()) for m in re.finditer(r'.+?(?:[。！？!?]|\.(?=\s+[A-Z])|\n|$)', text, re.S) if m.group().strip()]
    windows = []
    for index, (start, end) in enumerate(spans):
        sentence = text[start:end]
        if any(re.search(pattern, sentence, re.I) for _, pattern in SIGNALS):
            window = (spans[max(0, index-1)][0], spans[min(len(spans)-1, index+1)][1])
            if windows and window[0] <= windows[-1][1]:
                windows[-1] = (windows[-1][0], max(window[1], windows[-1][1]))
            else:
                windows.append(window)
    for start, end in windows:
        context = text[start:end]
        kinds = [name for name, pattern in SIGNALS if re.search(pattern, context, re.I)]
        if kinds:
            result.append({'id': sha(str(start) + '\0' + context)[:16], 'context': context,
                           'context_start': start, 'signals': kinds})
    return result


def template(text, profile='functional'):
    if profile not in {'functional', 'literary', 'teaching', 'spoken'}:
        raise ValueError('Unknown content profile')
    return {'version': VERSION, 'text_sha256': sha(text), 'profile': profile,
            'attribution_replay': source_attribution.template(text, profile=profile),
            'defensive_expression': defensive_expression.template(text, profile),
            'audience': '', 'purpose': '', 'whole_text_scan': '',
            'items': [dict(p, quote='', without='', with_reading='', without_reading='', effect='', reason='', decision='pending') for p in probes(text)]}


def validate(record, text, profile=None, source=None):
    if not isinstance(record, dict):
        return ['context_value missing contextual comparison']
    errors = defensive_expression.validate(record.get('defensive_expression'), text, record.get('profile'))
    errors.extend(source_attribution.validate(record.get('attribution_replay'), text, profile=record.get('profile')))
    if source is not None:
        errors.extend(source_attribution.validate(record.get('source_attribution'), text, source, 'source', record.get('profile')))
        if isinstance(record.get('source_attribution'), dict) and isinstance(record.get('attribution_replay'), dict):
            errors.extend(source_attribution.compare(record['source_attribution'], record['attribution_replay']))
    if type(record.get('version')) is not int or record.get('version') != VERSION or record.get('text_sha256') != sha(text):
        errors.append('context_value stale version or text binding')
    if not isinstance(record.get('profile'), str) or record.get('profile') not in {'functional', 'literary', 'teaching', 'spoken'} or (profile and record.get('profile') != profile):
        errors.append('context_value wrong writing profile')
    for key in ('audience', 'purpose', 'whole_text_scan'):
        if not nonempty(record.get(key)):
            errors.append('context_value missing ' + key)
    items = record.get('items')
    if not isinstance(items, list):
        return errors + ['context_value items must be an array']
    expected = {p['id']: p for p in probes(text)}
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append('context_value item must be an object'); continue
        identity = item.get('id')
        if not isinstance(identity, str) or identity in seen:
            errors.append('context_value duplicate or invalid comparison ID'); continue
        seen.add(identity)
        context, quote = item.get('context'), item.get('quote')
        if not nonempty(context) or context not in text or not nonempty(quote) or quote not in context:
            errors.append('context_value context/quote is not anchored'); continue
        if identity in expected and (context != expected[identity]['context'] or item.get('context_start') != expected[identity]['context_start']):
            errors.append('context_value detected context was changed')
        if identity in expected and any(not re.search(pattern, quote, re.I) for name, pattern in SIGNALS if name in expected[identity]['signals']):
            errors.append('context_value deletion span does not cover the detected concern')
        if context.count(quote) != 1:
            errors.append('context_value select an unambiguous deletion span')
        without = context.replace(quote, '', 1)
        if item.get('without') != without:
            errors.append('context_value deletion comparison does not match the exact edit')
        for key in ('with_reading', 'without_reading', 'reason'):
            if not nonempty(item.get(key)):
                errors.append('context_value missing concrete ' + key)
        if not isinstance(item.get('effect'), str) or item.get('effect') not in EFFECTS:
            errors.append('context_value unknown reader effect')
        if isinstance(item.get('effect'), str) and item.get('effect') not in {'none', ''} and item.get('with_reading') == item.get('without_reading'):
            errors.append('context_value claimed difference has identical readings')
        if item.get('effect') == 'voice' and (not isinstance(record.get('profile'), str) or record.get('profile') not in {'literary', 'spoken'}):
            errors.append('context_value voice-only justification uses the wrong profile')
        if not isinstance(item.get('decision'), str) or item.get('decision') not in DECISIONS:
            errors.append('context_value missing content decision')
        elif item['decision'] != 'keep' or item.get('effect') == 'none':
            errors.append('context_value unresolved content selection')
    if set(expected) - seen:
        errors.append('context_value a detected passage lacks comparison')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'check'])
    parser.add_argument('--text', required=True, help='Exact UTF-8 visible text/script, not HTML source or private review records')
    parser.add_argument('--review', required=True)
    parser.add_argument('--source', help='Authorized exact source snapshot; never substitute surrounding conversation or an unrelated excerpt')
    parser.add_argument('--profile', choices=['functional', 'literary', 'teaching', 'spoken'], default='functional')
    args = parser.parse_args()
    text = Path(args.text).read_text(encoding='utf-8')
    source = Path(args.source).read_text(encoding='utf-8') if args.source else None
    path = Path(args.review)
    if args.mode == 'prepare':
        with path.open('x', encoding='utf-8') as handle:
            record = template(text, args.profile)
            if source is not None:
                record['source_attribution'] = source_attribution.template(text, source, 'source', args.profile)
            json.dump(record, handle, ensure_ascii=False, indent=2)
        result = {'status': 'pending', 'review': str(path), 'guidance': GUIDANCE, 'attribution_guidance': source_attribution.GUIDANCE}
    else:
        errors = validate(json.loads(path.read_text(encoding='utf-8')), text, args.profile, source)
        record = json.loads(path.read_text(encoding='utf-8'))
        replay = record.get('attribution_replay', {}) if isinstance(record, dict) else {}
        if source is None and isinstance(replay, dict) and isinstance(replay.get('items'), list) and any(
                isinstance(item, dict) and item.get('kind') == 'source-fact' for item in replay['items']):
            errors.append('source_attribution source snapshot required for quoted source claims')
        result = {'status': 'blocked' if errors else 'record_checks_satisfied', 'errors': errors,
                  'defensive_expression_metrics': defensive_expression.summary(record.get('defensive_expression'), text, args.profile)}
    print(json.dumps(result, ensure_ascii=False))
    if args.mode == 'check' and errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
