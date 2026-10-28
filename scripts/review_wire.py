"""Compact review transport; restore only metadata and registered text anchors."""
import copy
import json
from pathlib import Path
import re

VERSION = 1
GUIDANCE = ('Wire protocol v1: return every requested judgment and item ID. You may omit computed metadata removed '
    'from templates and registered quote/context anchors; retain other identity fields. Code restores only exact supplied values, never verdicts, '
    'reasons or missing items. Context references point to _windows in the same template. For deletion comparisons '
    'choose the actual quote; code may derive without from that exact unique deletion. New observations need their '
    'own exact quote and context. The native schema applies after this deterministic expansion; full records remain accepted.')
META = {'version', 'artifact_binding', 'text_sha256', 'source_sha256', 'mode', 'profile'}
TEMPLATES = {'reader_value_template': 'reader_value', 'context_review_template': 'context_review',
             'source_attribution_template': 'source_attribution', 'attribution_template': 'attribution_replay'}


def kind(value):
    if not isinstance(value, dict):
        return None
    if value.get('scope') == 'entire-supplied-surface':
        return None  # Defensive records carry explicit spans; preserve them on the wire.
    if 'artifact_binding' in value and 'checks' in value:
        return 'editorial'
    if 'text_sha256' in value and 'items' in value:
        return 'attribution' if 'mode' in value else 'context'
    return None


def compact(value):
    if isinstance(value, list):
        return [compact(item) for item in value]
    if not isinstance(value, dict):
        return value
    record_kind = kind(value)
    result = {k: compact(v) for k, v in value.items() if not (record_kind and k in META)}
    if record_kind in {'attribution', 'context'}:
        windows = {}
        for item in result.get('items', []):
            if not isinstance(item, dict):
                continue
            context = item.pop('context', None)
            if isinstance(context, str) and context:
                name = next((k for k, v in windows.items() if v == context), 'w' + str(len(windows)+1))
                windows[name] = context
                item['context_ref'] = name
            item.pop('context_start', None)
            item.pop('signals', None)
            if record_kind == 'context':
                item.pop('without', None)
        if windows:
            result['_windows'] = windows
    return result


def expand(value, template):
    if not isinstance(value, dict) or not isinstance(template, dict):
        return value
    result = copy.deepcopy(value)
    record_kind = kind(template)
    if record_kind:
        for field in META & set(template):
            result.setdefault(field, copy.deepcopy(template[field]))
    if record_kind in {'attribution', 'context'} and isinstance(result.get('items'), list):
        expected = {item['id']: item for item in template['items']}
        windows = compact(template).get('_windows', {})
        for item in result['items']:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] not in expected:
                continue
            original = expected[item['id']]
            if 'context_ref' in item and (not isinstance(item['context_ref'], str) or windows.get(item['context_ref']) != original.get('context')):
                raise ValueError('Review context reference differs from the registered anchor')
            item.pop('context_ref', None)
            for field in ('context', 'context_start', 'signals'):
                if field in original:
                    item.setdefault(field, copy.deepcopy(original[field]))
            if record_kind == 'attribution' and original.get('quote'):
                item.setdefault('quote', original['quote'])
            if record_kind == 'context' and isinstance(item.get('quote'), str) and isinstance(item.get('context'), str):
                if item['quote'] and item['context'].count(item['quote']) == 1:
                    item.setdefault('without', item['context'].replace(item['quote'], '', 1))
        result.pop('_windows', None)
    for key, child in template.items():
        if key in result and isinstance(child, dict):
            result[key] = expand(result[key], child)
    return result


def editorial_block(raw):
    marker = '## Mandatory Editorial Evidence'
    if marker not in raw:
        return None
    match = re.search(r'```json\s*\n([\s\S]*?)\n```', raw[raw.index(marker):])
    if not match:
        raise ValueError('Mandatory editorial template is missing')
    template = json.loads(match.group(1))
    if kind(template) != 'editorial':
        raise ValueError('Mandatory editorial template has invalid shape')
    return match, raw.index(marker), template


def read_packet(path):
    raw = Path(path).read_text(encoding='utf-8')
    if raw.lstrip().startswith('{'):
        return json.loads(raw)
    block = editorial_block(raw)
    result = {'reader_value_template': block[2]} if block else {}
    if block and '## Required Output' in raw:
        section = raw.split('## Required Output', 1)[1].split('## Mandatory Editorial Evidence', 1)[0]
        match = re.search(r'```json\s*\n([\s\S]*?)\n```', section)
        if match:
            fields = json.loads(match.group(1))
            result['transport_metadata'] = {k: fields[k] for k in ('artifact_set_id', 'review_round') if k in fields}
    return result


def prompt_packet(path):
    raw = Path(path).read_text(encoding='utf-8')
    if raw.lstrip().startswith('{'):
        packet = json.loads(raw)
        for field in TEMPLATES:
            if field in packet:
                packet[field] = compact(packet[field])
        return json.dumps(packet, ensure_ascii=False, separators=(',', ':'))
    block = editorial_block(raw)
    if not block:
        return raw
    match, start, template = block
    return raw[:start+match.start(1)] + json.dumps(compact(template), ensure_ascii=False, separators=(',', ':')) + raw[start+match.end(1):]


def transport_packet(path):
    raw = Path(path).read_text(encoding='utf-8')
    small = prompt_packet(path)
    if len((small + GUIDANCE + ' ').encode('utf-8')) < len(raw.encode('utf-8')):
        return small, GUIDANCE
    return raw, ''


def expand_native(body, path):
    packet = read_packet(path)
    result = copy.deepcopy(body)
    for source, target in TEMPLATES.items():
        if source not in packet:
            continue
        if source == 'attribution_template' and packet.get('dimension') == 'no-context':
            understanding = result.get('reader_understanding')
            if isinstance(understanding, dict) and 'attribution_replay' in understanding:
                understanding['attribution_replay'] = expand(understanding['attribution_replay'], packet[source])
        elif target in result:
            result[target] = expand(result[target], packet[source])
    if packet.get('dimension'):
        for field in ('schema_version', 'contract_id', 'batch_id', 'round', 'packet_sha256'):
            if field in packet:
                result.setdefault(field, packet[field])
        if isinstance(packet.get('artifact'), dict) and 'sha256' in packet['artifact']:
            result.setdefault('artifact_sha256', packet['artifact']['sha256'])
    for field, value in packet.get('transport_metadata', {}).items():
        result.setdefault(field, value)
    return result
