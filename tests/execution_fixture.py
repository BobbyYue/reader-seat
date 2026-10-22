"""Synthetic registry fixtures only, NOT actual Codex calls or quality evidence.

Tests populate the capture store just as they populate native reviewer records.
There is deliberately no production fixture-import command or skip switch.
"""
import json
from pathlib import Path
import uuid

import writing_execution as execution
import writing_lifecycle as lifecycle


def init_fixture(run, mode='independent'):
    return execution.initialize(run, 'SYNTHETIC-' + uuid.uuid4().hex,
                                Path(run).parent / 'synthetic-execution.sqlite3', mode)


def seed_fixture(run, result_path):
    aggregate = execution.load(result_path)
    with lifecycle.session(run) as state:
        batch = state['rounds'][-1]
        number = batch['round']
        current = state['candidates'][-1]
    rules = execution.policy()
    originals = {}
    packets = {}
    if isinstance(aggregate.get('reviews'), list) and aggregate.get('manifest_path'):
        originals = {r['dimension']: Path(r['result_path']) for r in aggregate['reviews']}
        manifest = execution.load(aggregate['manifest_path'])
        packets = {p['dimension']: Path(p['path']) for p in manifest['packets']}
    elif 'reader_value_receipt' in aggregate:
        for entry in aggregate['reader_value_receipt']['reviews']:
            path = Path(entry['path'])
            originals[execution.load(path)['reviewer_role']] = path
        native_dir = Path(aggregate['reader_value_receipt']['inputs']['path']).parent
        packets = {r: native_dir / ('review_packet_' + r + '.md') for r in originals
                   if (native_dir / ('review_packet_' + r + '.md')).is_file()}
    elif 'reviewer_records' in aggregate:
        for record in aggregate['reviewer_records']:
            role = record['role']
            path = Path(run) / ('synthetic-return-' + str(number) + '-' + role + '.json')
            lifecycle.write_json(path, record)
            originals[role] = path
        packets = {r: Path(v['path']) for r, v in batch.get('packets', {}).items()}
    if set(originals) != set(rules['roles']):
        return
    jobs = {}
    for role, original in originals.items():
        body = execution.load(original)
        reviewer = body.get('reviewer', {})
        context = reviewer.get('session_id', body.get('context_id', 'SYNTHETIC-' + role + '-' + str(number)))
        agent_id = reviewer.get('agent_id', context)
        folder = Path(run) / 'synthetic-capture' / (str(number) + '-' + role)
        folder.mkdir(parents=True, exist_ok=True)
        packet = packets.get(role)
        if packet is None:
            packet = folder / 'packet.json'
            lifecycle.write_json(packet, {'synthetic': True, 'role': role})
        events = folder / 'events.jsonl'
        events.write_text(json.dumps({'type': 'thread.started', 'thread_id': context, 'SYNTHETIC': True}) + '\n')
        stderr = folder / 'stderr.txt'
        stderr.write_text('Synthetic process-record fixture, not a real invocation.')
        dependencies = {}
        if role == 'source-reliability':
            dependencies = {'no-context': execution.ref(originals['no-context'])}
        jobs[role] = {'status': 'captured', 'attempts': 1, 'signature': 'SYNTHETIC',
            'packet': execution.ref(packet), 'result': execution.ref(original),
            'dependencies': dependencies, 'body_digest': execution.digest(body),
            'captured': {'capture': 'fresh-codex-process', 'context_id': context, 'agent_id': agent_id,
                         'returncode': 0, 'answer': execution.ref(original), 'events': execution.ref(events),
                         'stderr': execution.ref(stderr), 'command': ['SYNTHETIC-NOT-AN-INVOCATION']}}
    with execution.task(run, True) as task:
        task['batches'][str(number)].update(jobs=jobs, status='captured')
    if rules['skill'] != 'writer-pen':
        execution.register_packets(run, {r: j['packet']['path'] for r, j in jobs.items()}, result_path)
