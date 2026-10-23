"""Bound expression comparisons; signals require judgment, never automatic rewriting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

VERSION = 1
MOVES = {'direct', 'correction', 'comparison', 'instruction'}
PLACEMENTS = {'claim-adjacent', 'section-once', 'method-note'}
FUNCTIONS = {'claim', 'scope', 'correction', 'refusal', 'prohibition', 'negative-finding', 'quotation', 'comparison'}
SIGNALS = {
    'contrast': r'不是[^。！？\n]{0,160}而是|并非[^。！？\n]{0,160}而是|\bnot\b[^.!?\n]{0,160}\bbut\b',
    'restriction': r'不能|不按|不应|不要|不宜|\b(?:cannot|can[\x27’]t|must not|should not|do not)\b',
    'qualification': r'不是|并非|不代表|不等于|不意味着|不说明|尚未|未发现|没有证据|\b(?:does not|do not|is not|are not|not yet|no evidence)\b',
}
GUIDANCE = (
    'Compare the current wording with a faithful direct alternative, not only deletion. '
    'Keep facts, scope, uncertainty, source attribution, refusals, prohibitions and negative findings. '
    'A useful distinction does not require a corrective sentence. State what is known and its applicable scope first; '
    'keep a correction when the reader actually needs that correction. In each comparison explain protected_meaning, '
    'reader_gain, and prior_context (where this distinction is already explained, or why it is new). '
    'If the direct alternative is better, decision=revise and repair the draft; never approve the unchanged candidate. '
    'Use alternative_kind=original-required only for an identified refusal, prohibition, negative finding, quotation, '
    'or real correction/comparison whose force or accuracy would change; explain why. Otherwise provide an actual alternative. '
    'Review clusters across the whole text: repeated cautionary headings, labels and caveats can be tiring even when each '
    'has a local use. Counts route attention, not quality thresholds. Record concrete reading effort and existing context, '
    'not a hypothetical generic risk of misunderstanding. A clear necessary negative may pass. The opening quote must '
    'come from the actual opening; explain the information it gives before any correction. Keep records private. '
    'Use prepare for the exact schema, and check for diagnostics. No new reviewer, score, or review round.'
)


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def meaningful(value):
    return (isinstance(value, str) and bool(value.strip()) and
            value.strip().casefold() not in {'pass', 'ok', 'none', 'n/a', '通过', '无', '已检查'})


def member(value, choices):
    return isinstance(value, str) and value in choices


def plan_errors(record, answers):
    if not isinstance(record, dict):
        return ['expression_plan is required before drafting']
    errors = []
    ids = {a['id'] for a in answers if isinstance(a, dict) and isinstance(a.get('id'), str)}
    lead = record.get('lead_answer_ids')
    if (not isinstance(lead, list) or not lead or any(not isinstance(i, str) for i in lead)
            or any(i not in ids for i in lead) or len(lead) != len(set(lead))):
        errors.append('expression_plan lead_answer_ids must reference existing reader answers')
    if not member(record.get('opening_move'), MOVES) or not meaningful(record.get('opening_reason')):
        errors.append('expression_plan requires an opening move and reader-specific reason')
    boundaries = record.get('essential_boundaries')
    if not isinstance(boundaries, list):
        return errors + ['expression_plan essential_boundaries must be an array, empty when none are needed']
    seen = set()
    for boundary in boundaries:
        if not isinstance(boundary, dict):
            errors.append('expression_plan boundary must be an object'); continue
        aid = boundary.get('answer_id')
        if not isinstance(aid, str) or aid not in ids or aid in seen:
            errors.append('expression_plan boundary must reference a unique existing reader answer')
        else:
            seen.add(aid)
        if not meaningful(boundary.get('reason')) or not member(boundary.get('placement'), PLACEMENTS):
            errors.append('expression_plan boundary requires a concrete reader risk and placement')
    return errors


def probes(text):
    # Group identical statements, retaining every occurrence for cumulative review.
    groups = {}
    for match in re.finditer(r'.+?(?:[。！？!?]|\.(?=\s|$)|\n|$)', text, re.S):
        raw = match.group()
        quote = raw.strip()
        kinds = [kind for kind, pattern in SIGNALS.items() if re.search(pattern, quote, re.I)]
        if not kinds:
            continue
        offset = match.start() + len(raw) - len(raw.lstrip())
        if quote not in groups:
            groups[quote] = {'id': sha(quote)[:16], 'quote': quote, 'signals': kinds, 'occurrences': []}
        groups[quote]['occurrences'].append(offset)
    return list(groups.values())


def clusters(items):
    result = []
    for family in SIGNALS:
        members = [p for p in items if family in p['signals']]
        if sum(len(p['occurrences']) for p in members) >= 2:
            result.append({'family': family, 'item_ids': [p['id'] for p in members]})
    return result


def template(text, stage='after'):
    if stage not in {'during', 'after'}:
        raise ValueError('expression stage must be during or after')
    items = probes(text)
    return {'version': VERSION, 'text_sha256': sha(text), 'stage': stage,
            'opening': {'quote': '', 'reader_gain': '', 'decision': 'pending'},
            'comparisons': [dict(p, function='', alternative='', alternative_kind='rewrite',
                                 protected_meaning='', reader_gain='', prior_context='', reason='', decision='pending') for p in items],
            'whole_text': {'decision': 'pending', 'reading_effect': '',
                           'clusters': [dict(c, reading_effect='', reason='', decision='pending') for c in clusters(items)]}}


def validate(record, text, stage='after'):
    if not isinstance(record, dict):
        return ['direct_expression missing review']
    errors = []
    if type(record.get('version')) is not int or record.get('version') != VERSION:
        errors.append('direct_expression stale version')
    if record.get('text_sha256') != sha(text) or record.get('stage') != stage:
        errors.append('direct_expression stale text or wrong stage')
    opening = record.get('opening')
    first = '\n'.join(line for line in text.splitlines() if line.strip())[:800]
    if not isinstance(opening, dict):
        errors.append('direct_expression missing opening review')
    else:
        if not isinstance(opening.get('quote'), str) or not opening['quote'].strip() or opening['quote'] not in first:
            errors.append('direct_expression opening quote must be in the actual opening')
        if not meaningful(opening.get('reader_gain')):
            errors.append('direct_expression opening needs concrete reader gain')
        errors.extend(decision_errors(opening.get('decision')))
    expected = {p['id']: p for p in probes(text)}
    items = record.get('comparisons')
    if not isinstance(items, list):
        return errors + ['direct_expression comparisons must be an array']
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append('direct_expression comparison must be an object'); continue
        identity = item.get('id')
        if not isinstance(identity, str) or identity in seen:
            errors.append('direct_expression duplicate or invalid comparison'); continue
        seen.add(identity)
        detected = expected.get(identity)
        if detected:
            occurrences = item.get('occurrences')
            if (not isinstance(occurrences, list) or any(type(n) is not int or n < 0 for n in occurrences)
                    or any(item.get(key) != detected[key] for key in ('quote', 'signals', 'occurrences'))):
                errors.append('direct_expression detected statement or occurrences changed')
        elif not isinstance(item.get('quote'), str) or not item['quote'].strip() or item['quote'] not in text:
            errors.append('direct_expression manual comparison quote is not anchored')
        for field in ('alternative', 'protected_meaning', 'reader_gain', 'prior_context', 'reason'):
            if not meaningful(item.get(field)):
                errors.append('direct_expression comparison missing ' + field)
        if not member(item.get('function'), FUNCTIONS):
            errors.append('direct_expression comparison must identify the statement function')
        kind = item.get('alternative_kind')
        if kind == 'rewrite':
            if item.get('alternative') == item.get('quote'):
                errors.append('direct_expression unchanged wording needs a protected original-required reason')
        elif kind == 'original-required':
            if not member(item.get('function'), {'refusal', 'prohibition', 'negative-finding', 'quotation', 'correction', 'comparison'}):
                errors.append('direct_expression original-required lacks a protected function')
            if item.get('alternative') != item.get('quote'):
                errors.append('direct_expression original-required must retain the exact original')
        else:
            errors.append('direct_expression invalid alternative_kind')
        errors.extend(decision_errors(item.get('decision')))
    if set(expected) - seen:
        errors.append('direct_expression detected statement lacks direct comparison')
    whole = record.get('whole_text')
    if not isinstance(whole, dict):
        return errors + ['direct_expression missing whole-text review']
    if not meaningful(whole.get('reading_effect')):
        errors.append('direct_expression whole-text review requires cumulative reader effect')
    errors.extend(decision_errors(whole.get('decision')))
    expected_clusters = {c['family']: c['item_ids'] for c in clusters(list(expected.values()))}
    actual = whole.get('clusters')
    if not isinstance(actual, list):
        return errors + ['direct_expression clusters must be an array']
    covered = set()
    for cluster in actual:
        if not isinstance(cluster, dict):
            errors.append('direct_expression cluster must be an object'); continue
        family = cluster.get('family')
        if not isinstance(family, str) or family in covered or family not in expected_clusters:
            errors.append('direct_expression invalid or duplicate cluster'); continue
        covered.add(family)
        if cluster.get('item_ids') != expected_clusters[family]:
            errors.append('direct_expression cluster omitted occurrences')
        if not meaningful(cluster.get('reading_effect')) or not meaningful(cluster.get('reason')):
            errors.append('direct_expression cluster needs cumulative effect and reason')
        errors.extend(decision_errors(cluster.get('decision')))
    if covered != set(expected_clusters):
        errors.append('direct_expression repeated family lacks whole-text review')
    return errors


def decision_errors(decision):
    if not member(decision, {'keep', 'revise'}):
        return ['direct_expression missing decision']
    return ['direct_expression unresolved reader effort'] if decision == 'revise' else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'check'])
    parser.add_argument('--text', required=True, help='Exact visible UTF-8 text, not HTML markup')
    parser.add_argument('--stage', choices=['during', 'after'], default='after')
    parser.add_argument('--output', required=True, help='Review JSON path')
    args = parser.parse_args()
    text = Path(args.text).read_text(encoding='utf-8')
    if args.mode == 'prepare':
        with Path(args.output).open('x', encoding='utf-8') as handle:
            json.dump(template(text, args.stage), handle, ensure_ascii=False, indent=2)
        print(json.dumps({'status': 'pending', 'guidance': GUIDANCE}, ensure_ascii=False))
    else:
        errors = validate(json.loads(Path(args.output).read_text(encoding='utf-8')), text, args.stage)
        print(json.dumps({'status': 'blocked' if errors else 'record-checks-satisfied', 'errors': errors}, ensure_ascii=False))
        if errors:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
