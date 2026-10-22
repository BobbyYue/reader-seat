"""Bound source/author attribution records; lexical cues request review, not a verdict."""
import hashlib
import json
import re

VERSION = 1
SOURCE = r'邮件|原文|官方|报告|论文|提交方|回复|文档说|材料显示|according to|the (?:email|report|paper|source)|official'
BOUNDARY = r'但|因此|所以|不代表|不能|未确认|未说明|没有说明|不同|不等同|建议|核对|尚未|however|therefore|\bbut\b|not (?:mean|prove|confirmed|equivalent)|unconfirmed|does not|not stated|recommend'
KINDS = {'source-fact', 'author-interpretation', 'author-recommendation', 'unknown', 'fictional-voice'}
NEGATIVES = {'not-applicable', 'unconfirmed', 'confirmed'}
SCOPES = {'quoted-passage', 'provided-material', 'not-source-claim', 'unresolved'}
ITEM_FORMAT = {'kind': sorted(KINDS), 'negative_status': sorted(NEGATIVES),
               'source_scope': sorted(SCOPES), 'status': ['pass', 'fail']}
GUIDANCE = ('For each flagged passage, distinguish every supplied clause as source fact, author interpretation/recommendation, '
    'unknown or fictional voice. Review the whole sentence, caption, quote box and citation scope; punctuation alone does not '
    'separate speakers. Identify who actually wrote/spoke, not who is merely mentioned. A quote supporting A does not support '
    'adjacent B or an A-therefore-B relation. Not stated in a quoted passage is not absent from the whole material; '
    'unconfirmed equality is not confirmed inequality. Cautious/negative wording needs support too. '
    'Reader mode records what this document makes you attribute, not what you think the source ought to mean. '
    'Source mode checks exact source evidence and scope. Keep unknowns unknown and quotations intact; use natural attribution '
    'only where needed, not visible labels on every sentence. Fictional voices are not external factual testimony. '
    'Resolve a mismatch in the existing revision, with no new role, score or round. '
    'Use these exact item enum values, not prose or aliases: ' + json.dumps(ITEM_FORMAT, separators=(',', ':')) + '. '
    'Put explanations in basis. negative_status: not-applicable=no negative claim; unconfirmed=not yet established; '
    'confirmed=asserted absence/inequality, not merely uncertainty. In reader mode speaker_basis and support_quote must be empty strings. '
    'In source mode both must be exact source substrings or empty, never explanations; a named speaker requires '
    'speaker_basis, a source-fact/confirmed negative requires support_quote. Use author/source/unknown/fictional speaker '
    'when that is all the evidence identifies. Unresolved claims stay fail, not guessed pass.')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize(text):
    return re.sub(r'\s+', '', text)


def substantive(value):
    return isinstance(value, str) and bool(value.strip()) and value.strip().lower() not in {'pass', 'ok', 'none', 'n/a', '通过', '无'}


def units(text):
    """Clause windows aid review; they do not decide semantic truth or speaker."""
    spans = [(m.start(), m.end()) for m in re.finditer(r'.+?(?:[。！？!?]|\.(?=\s+[A-Z])|\n|$)', text, re.S) if m.group().strip()]
    windows = []
    for index, (start, end) in enumerate(spans):
        left, right = spans[max(0, index-1)][0], spans[min(len(spans)-1, index+1)][1]
        context = text[left:right]
        if re.search(SOURCE, text[start:end], re.I) and re.search(BOUNDARY, context, re.I):
            windows.append((left, right))
    result, seen = [], set()
    for start, end in windows:
        context = text[start:end]
        for part in re.finditer(r'[^,，;；。！？!?\n]+(?:[,，;；。！？!?\n]|$)', context):
            quote = part.group().strip()
            if any(c.isalnum() for c in quote):
                identity = sha(str(start + part.start()) + '\0' + quote)[:16]
                if identity not in seen:
                    seen.add(identity)
                    result.append({'id': identity, 'quote': quote, 'context': context})
    return result


def template(text, source='', mode='reader', profile='functional'):
    return {'version': VERSION, 'text_sha256': sha(text), 'source_sha256': sha(source) if mode == 'source' else None,
        'mode': mode, 'profile': profile, 'whole_text_scan': '',
        'items': [dict(unit, kind='', speaker='', speaker_basis='', support_quote='',
                       source_scope='', negative_status='', basis='', status='pending') for unit in units(text)]}


def validate(record, text, source='', mode='reader', profile='functional'):
    if not isinstance(record, dict):
        return ['source_attribution missing review']
    errors = []
    if type(record.get('version')) is not int or record.get('version') != VERSION or record.get('text_sha256') != sha(text):
        errors.append('source_attribution stale version or text')
    if record.get('mode') != mode or record.get('profile') != profile:
        errors.append('source_attribution wrong mode or profile')
    if not isinstance(record.get('profile'), str) or record['profile'] not in {'functional', 'literary', 'teaching', 'spoken'}:
        errors.append('source_attribution invalid profile')
    if record.get('source_sha256') != (sha(source) if mode == 'source' else None):
        errors.append('source_attribution source binding differs')
    if not substantive(record.get('whole_text_scan')):
        errors.append('source_attribution missing whole-text observation')
    items = record.get('items')
    if not isinstance(items, list):
        return errors + ['source_attribution items must be an array']
    expected, seen = {unit['id']: unit for unit in units(text)}, set()
    normalized_source = normalize(source)
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in seen:
            errors.append('source_attribution invalid or repeated item'); continue
        seen.add(item['id'])
        quote, context = item.get('quote'), item.get('context')
        if not substantive(quote) or not substantive(context) or quote not in context or context not in text:
            errors.append('source_attribution quote/context not in current text'); continue
        if item['id'] in expected and any(item.get(key) != expected[item['id']][key] for key in ('quote', 'context')):
            errors.append('source_attribution required clause changed')
        kind, negative, scope = item.get('kind'), item.get('negative_status'), item.get('source_scope')
        if not isinstance(kind, str) or kind not in KINDS:
            errors.append('source_attribution invalid claim kind')
        if not isinstance(negative, str) or negative not in NEGATIVES:
            errors.append('source_attribution invalid negative status')
        if not isinstance(scope, str) or scope not in SCOPES:
            errors.append('source_attribution invalid evidence scope')
        if mode == 'source' and kind == 'source-fact' and scope not in ('quoted-passage', 'provided-material'):
            errors.append('source_attribution source fact has no source scope')
        if kind == 'fictional-voice' and (not isinstance(profile, str) or profile not in {'literary', 'spoken', 'teaching'}):
            errors.append('source_attribution fictional voice uses wrong profile')
        for key in ('speaker', 'basis'):
            if not substantive(item.get(key)):
                errors.append('source_attribution missing ' + key)
        for key in ('speaker_basis', 'support_quote'):
            if not isinstance(item.get(key), str):
                errors.append('source_attribution invalid ' + key)
            elif mode == 'reader' and item[key]:
                errors.append('source_attribution blind reader cannot supply unseen source evidence')
            elif mode == 'source' and item[key] and normalize(item[key]) not in normalized_source:
                errors.append('source_attribution evidence quote absent from bound source')
        if item.get('status') not in ('pass', 'fail'):
            errors.append('source_attribution missing item status')
        elif item['status'] == 'fail':
            errors.append('source_attribution unresolved claim attribution')
        if mode == 'source' and (kind == 'source-fact' or negative == 'confirmed') and not item.get('support_quote'):
            errors.append('source_attribution unresolved unsupported source/negative claim')
        if mode == 'source' and item.get('speaker') not in ('source', 'author', 'unknown', 'fictional speaker') and not item.get('speaker_basis'):
            errors.append('source_attribution unresolved speaker identity')
    if set(expected) - seen:
        errors.append('source_attribution a required clause is unreviewed')
    return errors


def compare(source_review, reader_replay):
    """Compare independent classifications, not reviewer opinions or stylistic votes."""
    if not isinstance(source_review, dict) or not isinstance(reader_replay, dict):
        return ['source_attribution missing source or reader replay']
    if not isinstance(source_review.get('items'), list) or not isinstance(reader_replay.get('items'), list):
        return ['source_attribution invalid comparison items']
    owners = {'source-fact': 'source', 'author-interpretation': 'author', 'author-recommendation': 'author',
              'unknown': 'unknown', 'fictional-voice': 'fictional'}
    mapping = {}
    for item in source_review.get('items', []):
        if not isinstance(item, dict) or not isinstance(item.get('quote'), str) or not isinstance(item.get('kind'), str) or not isinstance(item.get('negative_status'), str):
            return ['source_attribution invalid source comparison item']
        mapping.setdefault(normalize(item['quote']), []).append(item)
    errors = []
    for item in reader_replay.get('items', []):
        if not isinstance(item, dict) or not isinstance(item.get('quote'), str) or not isinstance(item.get('kind'), str) or not isinstance(item.get('negative_status'), str):
            return ['source_attribution invalid reader comparison item']
        candidates = mapping.get(normalize(item['quote']), [])
        values = lambda records: {(owners.get(record.get('kind')), record.get('negative_status')) for record in records}
        expected = values(candidates)
        if len(expected) > 1 and isinstance(item.get('context'), str):
            context = normalize(item['context'])
            narrowed = [record for record in candidates if isinstance(record.get('context'), str)
                        and (context in normalize(record['context']) or normalize(record['context']) in context)]
            expected = values(narrowed)
        actual = (owners.get(item.get('kind')), item.get('negative_status'))
        if expected != {actual}:
            errors.append('source_attribution unresolved reader/source disagreement')
    return errors
