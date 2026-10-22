#!/usr/bin/env python3
"""Managed task identity, captured checks and fresh review processes.

The cooperating caller owns the registry. This is not a security boundary against
the same OS user, a fabricated executable, or an unrestricted host bypass.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'config/execution-policy.json'
RULE_STAGES = {'current-stages': 'candidate', 'reproducible-measurement': 'candidate',
               'actual-artifact': 'candidate', 'captured-review': 'delivery', 'native-acceptance': 'delivery'}


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def ref(path):
    p = Path(path).resolve()
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def load(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    need(isinstance(value, dict), 'Expected an object')
    return value


def now():
    return datetime.now(timezone.utc).isoformat()


def policy():
    data = load(POLICY)
    need(data.get('version') == 1 and data.get('roles'), 'Invalid execution policy')
    need(len(data['roles']) == len(set(data['roles'])), 'Duplicate review roles')
    rules = data.get('rules', [])
    need(len(rules) == len(RULE_STAGES) and {r.get('id'): r.get('stage') for r in rules} == RULE_STAGES,
         'Execution rule has no registered validator, or a mandatory rule was removed')
    need(data['max_rounds'] == load(ROOT / 'config/writing-quality.json')['max_review_rounds'],
         'Execution and lifecycle round limits differ')
    expected = {'reader-seat': {'no-context', 'readability', 'source-reliability', 'structure-visual'},
                '3080-brief': {'reader', 'source', 'visual'}, 'writer-pen': {'professional', 'reader'}}
    need(set(data['roles']) == expected.get(data.get('skill')), 'Execution roles differ from the native skill')
    return data


def default_registry():
    return Path.home() / '.local/state/writing-skills/tasks.sqlite3'


def components():
    return {name: ref(ROOT / 'scripts' / name) for name in ('writing_host.py', 'writing_host.js', 'review_wire.py')}


def measurement_signature(state, value, geometry=None):
    import writing_lifecycle as lifecycle
    paths = [state['plan_ref']['path']] + [source['path'] for source in state['sources']]
    paths += list(state['plan'].get('wordlists', {}).values())
    paths += [item['source_path'] for item in state['plan'].get('evidence_items', []) if item.get('source_path')]
    if geometry:
        paths.append(geometry)
    return digest({'profile': state['profile'], 'plan': state['plan'], 'sources': state['sources'],
        'text': hashlib.sha256(value.encode('utf-8')).hexdigest(), 'implementation': state['implementation'],
        'config': ref(lifecycle.CONFIG), 'dependencies': [ref(p) for p in dict.fromkeys(paths)]})


def measured_once(run, state, value, geometry=None):
    """Reuse only program-computed facts in this managed task, never review verdicts."""
    import writing_lifecycle as lifecycle
    if not state.get('execution'):
        return lifecycle.measure_data(state, value, geometry)
    started = time.perf_counter()
    signature = measurement_signature(state, value, geometry)
    with task(run) as record:
        entries = record.get('measurement_cache')
        cached = entries.get(signature) if isinstance(entries, dict) else None
    hit = (isinstance(cached, dict) and type(cached.get('version')) is int and cached['version'] == 1
           and isinstance(cached.get('report'), dict) and cached.get('signature') == signature
           and cached.get('report_digest') == digest(cached['report'])
           and cached['report'].get('text_sha256') == hashlib.sha256(value.encode('utf-8')).hexdigest()
           and cached['report'].get('plan_sha256') == digest(state['plan'])
           and cached['report'].get('profile') == state['profile'])
    report = cached['report'] if hit else lifecycle.measure_data(state, value, geometry)
    need(measurement_signature(state, value, geometry) == signature, 'Measurement inputs changed during verification')
    elapsed = (time.perf_counter() - started) * 1000
    with task(run, True) as record:
        if not isinstance(record.get('measurement_cache'), dict):
            record['measurement_cache'] = {}
        entries = record['measurement_cache']
        entries[signature] = {'version': 1, 'signature': signature, 'report_digest': digest(report), 'report': report}
        while len(entries) > 4:
            del entries[next(iter(entries))]
        if not isinstance(record.get('performance'), dict):
            record['performance'] = {}
        metric = record['performance'].setdefault('measurement', {'computed': 0, 'reused': 0, 'elapsed_ms': 0})
        metric['reused' if hit else 'computed'] += 1
        metric['elapsed_ms'] += elapsed
    return report


def performance_summary(run):
    def elapsed(left, right):
        if not left or not right:
            return None
        try:
            value = (datetime.fromisoformat(right) - datetime.fromisoformat(left)).total_seconds() * 1000
            return value if value >= 0 else None
        except (ValueError, TypeError):
            return None

    with task(run) as record:
        jobs = []
        for batch in record['batches'].values():
            for role, job in batch['jobs'].items():
                prompt = job.get('prompt', {}).get('path')
                answer = job.get('captured', {}).get('answer', {}).get('path')
                jobs.append({'round': batch['number'], 'role': role, 'status': job['status'],
                    'transport_attempts': job.get('attempts', 0), 'prepared_at': job.get('prepared_at'),
                    'started_at': job.get('started_at'), 'completed_at': job.get('completed_at'),
                    'prepared_to_started_ms': elapsed(job.get('prepared_at'), job.get('started_at')),
                    'started_to_captured_ms': elapsed(job.get('started_at'), job.get('completed_at')),
                    'prompt_bytes': Path(prompt).stat().st_size if prompt and Path(prompt).is_file() else None,
                    'answer_bytes': Path(answer).stat().st_size if answer and Path(answer).is_file() else None})
        return {'task_id': record['id'], 'performance': record.get('performance', {}), 'jobs': jobs,
                'scope': 'Measured controller timings and bytes, not token estimates or writing-quality scores.'}


def connection(path):
    p = Path(path).absolute()
    need(not p.is_symlink(), 'Registry must not be a symlink')
    p.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    db = sqlite3.connect(p, timeout=30)
    db.execute('PRAGMA busy_timeout=30000')
    db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    p.chmod(0o600)
    return db


def descriptor(run):
    state = load(Path(run) / 'lifecycle.json')
    link = state.get('execution')
    need(isinstance(link, dict), 'Managed execution missing; initialize before writing')
    return link


@contextmanager
def task(run, write=False):
    link = descriptor(run)
    db = connection(link['registry'])
    try:
        db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        row = db.execute('SELECT body FROM tasks WHERE id=?', (link['task_id'],)).fetchone()
        need(row, 'Task is missing from the host registry')
        state = json.loads(row[0])
        need(state['run'] == str(Path(run).resolve()), 'Task cannot move to another run directory')
        need(state['policy'] == ref(POLICY) and state['engine'] == ref(__file__),
             'Execution implementation changed; explicitly migrate the task')
        need(state.get('components') == components(), 'Execution collector changed; do not reuse its old acceptance')
        yield state
        if write:
            db.execute('UPDATE tasks SET body=? WHERE id=?',
                       (json.dumps(state, ensure_ascii=False), link['task_id']))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def initialize(run, task_id, registry=None, mode='independent'):
    import writing_lifecycle as lifecycle
    need(isinstance(task_id, str) and 1 <= len(task_id.strip()) <= 240, 'A stable host task ID is required')
    rules = policy()
    need(mode == 'independent' or (mode == 'self-check' and rules['skill'] == '3080-brief'), 'Unsupported execution mode')
    registry = Path(registry or default_registry()).absolute()
    run = Path(run).resolve()
    # Registry identity is independent of a caller-selected working directory.
    with lifecycle.session(run, True) as state:
        if state.get('execution'):
            need(state['execution'] == {'task_id': task_id, 'registry': str(registry)}, 'Task identity is already locked')
            with task(run) as recorded:
                need(recorded['mode'] == mode, 'Execution mode changed')
            return {'status': 'resumed', 'task_id': task_id, 'run': str(run)}
        need(not state['units'] and not state['candidates'] and not state['rounds'], 'Initialize managed execution before writing checkpoints')
        record = {'id': task_id, 'run': str(run), 'skill': rules['skill'], 'mode': mode,
                  'plan': state['plan_ref'], 'policy': ref(POLICY), 'engine': ref(__file__),
                  'components': components(),
                  'created_at': now(), 'batches': {}, 'checks': {}, 'native': []}
        db = connection(registry)
        try:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT body FROM tasks WHERE id=?', (task_id,)).fetchone()
            if existing:
                old = json.loads(existing[0])
                need(old['run'] == str(run) and old['plan'] == state['plan_ref'],
                     'This task ID already owns another run; resume it instead of resetting rounds')
            else:
                db.execute('INSERT INTO tasks VALUES (?,?)', (task_id, json.dumps(record, ensure_ascii=False)))
            db.commit()
        finally:
            db.close()
        state['execution'] = {'task_id': task_id, 'registry': str(registry)}
    return {'status': 'initialized', 'task_id': task_id, 'run': str(run), 'mode': mode}


def inspect_candidate(run, artifact):
    import writing_lifecycle as lifecycle
    descriptor(run)
    with lifecycle.session(run) as state:
        need(state['candidates'] and state['units'], 'Candidate stages are incomplete')
        current = state['candidates'][-1]
        need(ref(artifact) == current['artifact'], 'Artifact differs from the registered candidate')
        last_unit = max(e['sequence'] for e in state['events'] if e['operation'] == 'during')
        last_candidate = max(e['sequence'] for e in state['events'] if e['operation'] == 'candidate')
        need(last_unit < last_candidate, 'Checkpoints changed after candidate registration')
        report = load(current['report']['path'])
        geometry = report.get('geometry')
        need(report == measured_once(run, state, current['text'], geometry['path'] if geometry else None),
             'Measurements do not reproduce for this version')
        need(lifecycle.compact(lifecycle.artifact_text(artifact)) == lifecycle.compact(current['text']),
             'Registered text differs from the delivered artifact')
        signature = digest({'artifact': current['artifact'], 'report': current['report'],
                            'record': current['record'], 'plan': state['plan_ref'], 'sources': state['sources']})
    checks = {r['id']: {'status': 'pass', 'owner': r['owner'], 'signature': signature}
              for r in policy()['rules'] if r['stage'] == 'candidate'}
    with task(run, True) as record:
        record['checks'] = checks
    return signature


def reserve_batch(run, number, artifact_sha256):
    with task(run, True) as state:
        batches = state['batches']
        key = str(number)
        if key in batches:
            need(batches[key]['artifact_sha256'] == artifact_sha256, 'Cannot retarget a started batch')
            return
        need(number == len(batches) + 1 and number <= policy()['max_rounds'], 'Task review round limit or sequence violated')
        batches[key] = {'number': number, 'artifact_sha256': artifact_sha256, 'jobs': {}, 'status': 'prepared'}


def register_packets(run, packets, owner):
    """Called by the native packet builder, before any reviewer receives input."""
    import writing_lifecycle as lifecycle
    with lifecycle.session(run) as state:
        need(state['candidates'], 'Register a stable candidate before native packets')
        artifact = state['candidates'][-1]['artifact']
    need(set(packets) == set(policy()['roles']), 'Native packet set has missing or unexpected roles')
    record = {'artifact': artifact, 'owner': ref(owner), 'packets': {r: ref(p) for r, p in packets.items()}}
    with task(run, True) as state:
        entries = state.setdefault('packet_sets', [])
        if record not in entries:
            entries.append(record)


def validate_return(body, role):
    """Reject malformed transport output, not a valid negative judgment."""
    skill = policy()['skill']
    if skill == 'reader-seat':
        need(body.get('status') in {'pass', 'fail', 'blocked'} and body.get('dimension') == role,
             'Reader result is malformed; retry the technical return')
        need(isinstance(body.get('checks'), dict) and body['checks'] and isinstance(body.get('issues'), list), 'Reader checks are missing')
    elif skill == '3080-brief':
        need(body.get('verdict') in {'PASS', 'FAIL'} and body.get('reviewer_role') == role, '3080 result is malformed')
        need(isinstance(body.get('checks'), list) and body['checks'], '3080 checks are missing')
        need(all(isinstance(c, dict) and c.get('result') in {'PASS', 'FAIL'} and isinstance(c.get('reason'), str)
                 and c['reason'].strip() for c in body['checks']), '3080 check shape is incomplete')
        need(all(isinstance(body.get(k), list) for k in ('blocking_issues', 'unsupported_claims', 'missing_coverage', 'required_fixes')),
             '3080 issue records are missing')
    else:
        need(body.get('verdict') in {'pass', 'fail'} and isinstance(body.get('summary'), str)
             and body['summary'].strip() and isinstance(body.get('evidence'), list) and body['evidence']
             and isinstance(body.get('issues'), list), 'Literary result is malformed')
        need((body['verdict'] == 'fail') == bool(body['issues']), 'Literary verdict and unresolved issues conflict')


def validate_native_return(run, body, role, packet_path):
    """Reuse native structural/anchor validators before caching a return."""
    skill = policy()['skill']
    errors = []
    if skill == 'reader-seat':
        import reader_review
        packet = load(packet_path)
        manifest = {key: packet[key] for key in ('contract_id', 'batch_id', 'round')}
        errors = reader_review.validate_result(body, manifest, packet)
        if role == 'no-context':
            responses = body.get('answer_responses')
            need(isinstance(responses, list) and len(responses) == 1 and isinstance(responses[0], dict), 'Blind answer response shape is incomplete')
            need({'surface_id', 'surface_sha256', 'reader_id', 'findings', 'remaining_questions'} <= set(responses[0]), 'Blind answer fields are missing')
        if role == 'source-reliability':
            evaluation = body.get('answer_evaluation')
            need(isinstance(evaluation, dict) and {'manifest_sha256', 'response_sha256', 'reviewer_id', 'plan_source_coverage',
                'source_coverage_evidence', 'source_fidelity', 'answers', 'questions'} <= set(evaluation), 'Source answer evaluation is incomplete')
            if packet.get('depth_requirement'):
                depth = evaluation.get('depth_fit')
                need(isinstance(depth, dict) and {'mode', 'status', 'reason', 'source_quote', 'reader_quote'} <= set(depth),
                     'Source depth evaluation is incomplete')
    elif skill == 'writer-pen':
        import writing_lifecycle
        import source_attribution
        with writing_lifecycle.session(run) as state:
            text = state['candidates'][-1]['text']
            source = '\n'.join(writing_lifecycle.text(s['path']) for s in state['sources'])
        need(all(isinstance(e, dict) and isinstance(e.get('quote'), str) and e['quote'] in text
                 and e['quote'].strip() and isinstance(e.get('reason'), str) and e['reason'].strip()
                 for e in body['evidence']), 'Literary evidence does not identify the current text')
        if role == 'professional':
            import context_value
            errors = context_value.validate(body.get('context_review'), text, 'literary')
            errors.extend(source_attribution.validate(body.get('source_attribution'), text, source, 'source', 'literary'))
        else:
            errors = source_attribution.validate(body.get('attribution_replay'), text, profile='literary')
        need(not errors or body.get('verdict') == 'fail', 'Literary verdict conflicts with unresolved review findings')
    elif skill == '3080-brief':
        # Genuine native packets carry the mandatory editorial contract. Small
        # synthetic transport probes cannot use this exception as native acceptance.
        if 'Mandatory Editorial Evidence' in Path(packet_path).read_text(encoding='utf-8'):
            import editorial_gate
            native_packet = ref(packet_path)
            with task(run) as state:
                owners = [s['owner']['path'] for s in state.get('packet_sets', []) if s['packets'].get(role) == native_packet]
            need(owners, 'Native editorial packet owner is missing')
            errors = editorial_gate.validate(body, load(owners[-1]))
    # A valid negative judgment is not a transport error. Missing fields,
    # wrong bindings or absent quoted evidence remain retryable technical errors.
    semantic = ('source_attribution unresolved', 'context_value unresolved content selection', 'retains an unresolved reader problem', 'missing or unresolved; no extra style-only review round',
                ' review did not pass', ' required checks are absent, failed or unexplained', ' has unresolved or missing ')
    structural = [error for error in errors if not any(value in error for value in semantic)]
    need(not structural, 'Native return has malformed fields or invalid evidence; retry the technical return')


def _invoke(prompt, directory, timeout):
    """Capture one genuinely fresh Codex process; no resume or parent context."""
    executable = shutil.which('codex')
    need(executable, 'Codex CLI is unavailable; independent review cannot be attested')
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    answer = directory / 'answer.json'
    command = [executable, 'exec', '--skip-git-repo-check', '--ephemeral',
               '--sandbox', 'read-only', '--color', 'never', '--json',
               '--output-last-message', str(answer), '-']
    # Retain the user's model/provider configuration; never silently choose a
    # different model. A new process receives no parent conversation or resume ID.
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, cwd=directory, start_new_session=True)
    timed_out = False
    try:
        output, errors = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, errors = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, errors = process.communicate()
    stdout, stderr = directory / 'events.jsonl', directory / 'stderr.txt'
    stdout.write_text(output, encoding='utf-8')
    stderr.write_text(errors, encoding='utf-8')
    need(not timed_out and process.returncode == 0 and answer.is_file(), 'Review process failed; raw diagnostic files were retained')
    events = []
    for line in output.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    identities = {e.get('thread_id') for e in events if e.get('type') == 'thread.started' and e.get('thread_id')}
    need(len(identities) == 1, 'CLI did not expose one actual fresh thread identity')
    return {'answer': ref(answer), 'events': ref(stdout), 'stderr': ref(stderr),
            'context_id': identities.pop(), 'agent_id': directory.name, 'returncode': process.returncode,
            'command': command, 'executable': ref(executable), 'capture': 'fresh-codex-process'}


def _stamp_identity(body, context, role, packet, dependencies=None, native_context=None, agent_id=None):
    import review_wire
    body = review_wire.expand_native(body, packet)
    rules = policy()
    agent_id = agent_id or context
    if rules['skill'] == 'reader-seat':
        body['reviewer'] = {'agent_id': agent_id, 'session_id': context,
                            'context_isolation': 'fresh-subagent', 'parent_context_received': False,
                            'invocation_mode': 'parallel-batch'}
        for response in body.get('answer_responses', []):
            response['reader_id'] = agent_id
        if role == 'source-reliability' and isinstance(body.get('answer_evaluation'), dict):
            import reader_answers
            native_packet = load(packet)
            evaluation = body['answer_evaluation']
            evaluation['reviewer_id'] = agent_id
            evaluation['manifest_sha256'] = reader_answers.object_digest(load(native_packet['answer_manifest']))
            responses = load(next(iter((dependencies or {}).values()))).get('answer_responses', [])
            evaluation['response_sha256'] = reader_answers.object_digest(responses)
    elif rules['skill'] == 'writer-pen':
        body.update(role=role, context_id=context, packet_sha256=ref(packet)['sha256'])
        if native_context:
            body['draft_id'] = native_context['draft_id']
    return body


def review_prompt(packet, dependencies):
    import review_wire
    packet_text, wire_guidance = review_wire.transport_packet(packet)
    prompt = ('Perform this isolated review. Use only the supplied packet and its authorized materials. '
              'Do not inspect the parent directory, other reviews, or author history. '
              'Return only the native machine-readable JSON result, never a PASS placeholder.'
              + (' ' + wire_guidance if wire_guidance else '') + '\n\n' + packet_text)
    if policy()['skill'] == 'reader-seat':
        prompt += '\n\nNative result schema:\n' + (ROOT / 'config/reader-review-result.schema.json').read_text()
    if policy()['skill'] == 'writer-pen':
        prompt += ('\n\nReturn verdict (pass/fail), summary, evidence [{quote,reason}], and issues '
                   '[{impact,reason}]. No unresolved issues for pass; at least one for fail. '
                   'Transport identity and draft bindings will be supplied by the caller.')
    if dependencies:
        # Only the raw blind answers, not another reviewer's judgments, reach source review.
        blind = load(next(iter(dependencies.values())))
        prompt += '\n\nFrozen no-context answer_responses:\n' + json.dumps(blind.get('answer_responses', []), ensure_ascii=False)
        if blind.get('reader_understanding', {}).get('attribution_replay'):
            prompt += '\n\nFrozen no-context attribution replay (raw reading, not reviewer opinion):\n' + json.dumps(blind['reader_understanding']['attribution_replay'], ensure_ascii=False)
    return prompt


def _job(run, number, role, packet, dependencies, timeout, native_context=None):
    packet_ref = ref(packet)
    with task(run, True) as state:
        batch = state['batches'][str(number)]
        prior = batch['jobs'].get(role)
        dependency_refs = {r: ref(p) for r, p in dependencies.items()}
        signature = digest({'packet': packet_ref, 'dependencies': dependency_refs, 'native_context': native_context})
        need(not prior or prior['signature'] == signature, 'A started role cannot change its input packet or dependencies')
        if prior and prior.get('status') == 'captured':
            need(prior['signature'] == signature and ref(prior['result']['path']) == prior['result'], 'Captured input or result changed')
            return prior['result']['path']
        need(not prior or prior.get('transport', 'cli') == 'cli', 'Resume the original host transport, not another backend')
        if prior and prior.get('status') == 'running':
            try:
                os.kill(prior['owner_pid'], 0)
            except ProcessLookupError:
                pass
            else:
                raise ValueError('Review job still belongs to a live executor')
        attempts = (prior or {}).get('attempts', 0) + 1
        need(attempts <= policy()['max_technical_attempts'], 'Technical retry budget exhausted; report blocked, not a semantic failure')
        attempt_id = uuid.uuid4().hex
        batch['jobs'][role] = {'status': 'running', 'attempts': attempts, 'owner_pid': os.getpid(),
                               'signature': signature, 'attempt_id': attempt_id, 'packet': packet_ref, 'transport': 'cli',
                               'prepared_at': now(), 'started_at': now()}
        batch['status'] = 'running'
    directory = Path(run) / 'execution' / ('round-' + str(number)) / (role + '-' + attempt_id)
    prompt = review_prompt(packet, dependencies)
    try:
        captured = _invoke(prompt, directory, timeout)
        return commit_capture(run, number, role, attempt_id, captured, packet, dependencies, native_context)
    except BaseException:
        with task(run, True) as state:
            state['batches'][str(number)]['jobs'][role].update(status='blocked', failed_at=now())
        raise


def commit_capture(run, number, role, attempt_id, captured, packet, dependencies, native_context=None):
    original = load(captured['answer']['path'])
    validate_return(original, role)
    body = _stamp_identity(original, captured['context_id'], role, packet, dependencies, native_context, captured.get('agent_id'))
    validate_native_return(run, body, role, packet)
    result = Path(captured['answer']['path']).parent / 'native-result.json'
    import writing_lifecycle
    writing_lifecycle.write_json(result, body, exclusive=True)
    with task(run, True) as state:
        current = state['batches'][str(number)]['jobs'][role]
        need(current['attempt_id'] == attempt_id and current['status'] in {'running', 'started'}, 'Job ownership changed')
        prior_contexts = {j['captured']['context_id'] for b in state['batches'].values()
                          for j in b['jobs'].values() if j.get('captured')}
        need(captured['context_id'] not in prior_contexts, 'A fresh review process reused an earlier context')
        current.update(status='captured', captured=captured, result=ref(result), body_digest=digest(body),
                       dependencies={r: ref(p) for r, p in dependencies.items()}, native_context=native_context, completed_at=now())
    return str(result.resolve())


def prepare_dispatch(run, packets, native_run=None):
    import writing_lifecycle as lifecycle
    rules = policy()
    need(set(packets) == set(rules['roles']), 'Review packets must contain exactly the configured roles')
    for path in packets.values():
        need(Path(path).is_file(), 'Review packet is missing')
    with lifecycle.session(run) as state:
        need(state.get('execution') and state['rounds'] and state['rounds'][-1]['verdict'] is None,
             'Start the current lifecycle review batch before dispatch')
        current = state['rounds'][-1]
        number, artifact = current['round'], state['candidates'][-1]['artifact']['path']
    for role, filename in packets.items():
        raw = Path(filename).read_text(encoding='utf-8')
        if rules['skill'] in {'reader-seat', 'writer-pen'}:
            packet = load(filename)
            need(packet.get('dimension', packet.get('role')) == role, 'Packet belongs to another reviewer role')
            if rules['skill'] == 'writer-pen':
                need(packet.get('artifact_sha256') == ref(artifact)['sha256'], 'Literary packet is stale')
                if role == 'reader':
                    need(set(packet) == {'artifact_sha256', 'text', 'role', 'known_context', 'task',
                                         'attribution_template', 'attribution_guidance'},
                         'Literary reader packet contains author context or extra material')
            elif role == 'no-context':
                need(packet.get('source_bundle') is None and not packet.get('render_evidence')
                     and 'reader_value_template' not in packet and 'answer_manifest' not in packet,
                     'No-context packet contains source, answer plan or another review surface')
        else:
            valid = (load(filename).get('role') == role) if raw.lstrip().startswith('{') else ('Role key: `' + role + '`' in raw)
            need(valid, '3080 packet belongs to another reviewer role')
    actual_packets = {r: ref(p) for r, p in packets.items()}
    if rules['skill'] == 'writer-pen':
        with lifecycle.session(run) as state:
            need(actual_packets == state['rounds'][-1]['packets'], 'Literary dispatch must use the exact native packets')
    else:
        with task(run) as recorded:
            need(any(s['artifact']['sha256'] == ref(artifact)['sha256'] and s['packets'] == actual_packets
                     and ref(s['owner']['path']) == s['owner'] for s in recorded.get('packet_sets', [])),
                 'Dispatch packets are not the exact registered native packet set')
    inspect_candidate(run, artifact)
    reserve_batch(run, number, ref(artifact)['sha256'])
    dependencies = rules.get('dependencies', {})
    native_context = None
    if rules['skill'] == 'writer-pen':
        need(native_run, 'Writer-pen review requires its native run directory')
        import writing_run
        with writing_run.session(native_run) as state:
            current_draft = writing_run.current(state)
            need(current_draft['sha256'] == ref(artifact)['sha256'] and
                 Path(state['lifecycle_run']).resolve() == Path(run).resolve(), 'Native literary task differs')
            native_context = {'draft_id': current_draft['id']}
    for role, required in dependencies.items():
        need(role in packets and set(required) < set(packets) and role not in required, 'Invalid dependency graph')
    return number, artifact, native_context


def dispatch(run, packets, timeout=420, native_run=None):
    """Run only missing jobs; semantic revision batches and technical retries differ."""
    number, artifact, native_context = prepare_dispatch(run, packets, native_run)
    rules = policy()
    dependencies = rules.get('dependencies', {})
    finished, running, pending = {}, {}, set(packets)
    with ThreadPoolExecutor(max_workers=len(packets)) as pool:
        while pending or running:
            ready = [r for r in pending if set(dependencies.get(r, [])) <= set(finished)]
            for role in ready:
                pending.remove(role)
                inputs = {r: finished[r] for r in dependencies.get(role, [])}
                running[pool.submit(_job, run, number, role, packets[role], inputs, timeout, native_context)] = role
            need(running, 'Review dependency graph is cyclic')
            done, _ = wait(running, return_when=FIRST_COMPLETED)
            errors = []
            for future in done:
                role = running.pop(future)
                try:
                    finished[role] = future.result()
                except BaseException as error:
                    errors.append(error)
            if errors:
                # The context manager waits for already-running independent jobs.
                raise errors[0]
    with task(run, True) as state:
        state['batches'][str(number)]['status'] = 'captured'
    return {'status': 'captured', 'round': number, 'results': finished,
            'scope': 'Actual fresh CLI processes captured; semantic acceptance belongs to native validators.'}


def evidence_paths(run):
    paths = set()
    with task(run) as state:
        for batch in state['batches'].values():
            for job in batch['jobs'].values():
                if job.get('status') == 'captured':
                    paths.update(p['path'] for p in (job['packet'], job['result'], job['captured']['answer'],
                                                   job['captured']['events'], job['captured']['stderr']))
                    paths.update(p['path'] for p in (job.get('prompt'), job['captured'].get('spawn'),
                                                   job['captured'].get('adapter')) if p)
    return sorted(paths)


def verify_reviews(run, result_paths, method='independent', scoped_bindings=None):
    import writing_lifecycle as lifecycle
    with lifecycle.session(run) as state:
        need(state['rounds'] and state['rounds'][-1].get('verdict') is not None, 'Native review must finish first')
        number = state['rounds'][-1]['round']
        current_sha = state['candidates'][-1]['artifact']['sha256']
    with task(run) as state:
        if method == 'self-check':
            need(state['mode'] == 'self-check' and policy()['skill'] == '3080-brief', 'Self-check was not selected before writing')
            return {'method': 'self-check', 'scope': 'No independent-review claim'}
        need(state['mode'] == 'independent', 'Cannot promote a self-check task to independent')
        batch = state['batches'].get(str(number))
        need(batch and batch['artifact_sha256'] == current_sha, 'Managed batch differs from the current review')
        aggregates = [load(p) for p in result_paths]
        bindings = {}
        if method == 'scoped-revalidation':
            need(isinstance(scoped_bindings, dict), 'Scoped verifier must identify its actual consumed review files')
            bindings = scoped_bindings
        elif policy()['skill'] == 'reader-seat':
            entries = [r for a in aggregates for r in a.get('reviews', [])]
            for entry in entries:
                role = entry['dimension']
                need(role not in bindings, 'Duplicate native role return')
                bindings[role] = {'path': str(Path(entry['result_path']).resolve()), 'sha256': entry['result_sha256']}
        elif policy()['skill'] == '3080-brief':
            entries = [r for a in aggregates for r in a.get('reader_value_receipt', {}).get('reviews', [])]
            for entry in entries:
                role = load(entry['path'])['reviewer_role']
                need(role not in bindings, 'Duplicate native role return')
                bindings[role] = {'path': str(Path(entry['path']).resolve()), 'sha256': entry['sha256']}
        # Scoped receipts may reuse prior native reviewers only when the native scope verifier passes.
        available = list(state['batches'].values()) if method == 'scoped-revalidation' else [batch]
        by_role = {}
        contexts = set()
        evidence = set()
        for b in available:
            for role, job in b['jobs'].items():
                if job.get('status') != 'captured':
                    continue
                captured = job['captured']
                need(captured['capture'] in {'fresh-codex-process', 'fresh-native-tools'} and captured['returncode'] == 0, 'Review has no successful captured process')
                for item in (job['packet'], job['result'], captured['answer'], captured['events'], captured['stderr']):
                    need(ref(item['path']) == item, 'Original dispatch evidence changed')
                    evidence.add(item['path'])
                for item in (job.get('prompt'), captured.get('spawn'), captured.get('adapter')):
                    if item:
                        need(ref(item['path']) == item, 'Original host collection evidence changed')
                        evidence.add(item['path'])
                if captured['capture'] == 'fresh-native-tools':
                    import writing_host
                    writing_host.verify_capture(captured, job)
                else:
                    events = [json.loads(line) for line in Path(captured['events']['path']).read_text().splitlines() if line.strip().startswith('{')]
                    need(any(e.get('type') == 'thread.started' and e.get('thread_id') == captured['context_id'] for e in events), 'Captured identity is not in the original process events')
                native_body = load(job['result']['path'])
                stamped = _stamp_identity(load(captured['answer']['path']), captured['context_id'], role,
                    job['packet']['path'], {r: d['path'] for r, d in job.get('dependencies', {}).items()},
                    job.get('native_context'), captured.get('agent_id'))
                need(native_body == stamped, 'Native review was changed instead of importing the original return')
                included = bindings.get(role) == job['result']
                if policy()['skill'] == 'writer-pen':
                    included = any(digest(r) == digest(native_body) for a in aggregates for r in a.get('reviewer_records', []))
                if included:
                    need(captured['context_id'] not in contexts, 'Independent roles reused a process context')
                    contexts.add(captured['context_id'])
                    by_role[role] = job['result']['sha256']
        need(set(by_role) == set(policy()['roles']), 'Native result omits an original managed reviewer return')
    return {'method': method, 'original_results': by_role, 'evidence_paths': sorted(evidence)}


def accept_native(run, artifact, result_paths, native, method='independent'):
    """Called by package-owned checked exits after their real native verifier."""
    signature = inspect_candidate(run, artifact)
    review = verify_reviews(run, result_paths, method, native.get('managed_review_bindings'))
    need(native.get('status') in {'pass', 'review-incomplete-draft'}, 'Native verifier is not final')
    need(native.get('artifact_sha256', native.get('sha256')) == ref(artifact)['sha256'], 'Native verifier checked different bytes')
    with task(run, True) as state:
        receipt = {'at': now(), 'artifact': ref(artifact), 'signature': signature,
                   'native_result_digest': digest(native), 'review': review,
                   'rules': {r['id']: {'status': 'pass', 'owner': r['owner']}
                             for r in policy()['rules'] if r['stage'] == 'delivery'}}
        state['native'].append(receipt)
    return {'status': 'managed', 'task_id': descriptor(run)['task_id'], 'review': review,
            'scope': 'Checked entrypoint with captured execution; no host-wide enforcement or semantic-quality proof.'}


def next_step(run):
    import writing_lifecycle as lifecycle
    with lifecycle.session(run) as state:
        descriptor(run)
        if not state['units']:
            action = 'write-and-register-unit'
        elif not state['candidates']:
            action = 'measure-and-register-candidate'
        elif not state['rounds'] or state['rounds'][-1]['artifact_sha256'] != state['candidates'][-1]['artifact']['sha256']:
            action = 'start-review'
        elif state['rounds'][-1]['verdict'] is None:
            action = 'dispatch-or-resume-reviews'
        elif state['rounds'][-1]['verdict'] == 'pass':
            action = 'checked-native-delivery'
        else:
            action = 'present-incomplete-draft' if len(state['rounds']) == policy()['max_rounds'] else 'revise-affected-units'
    return {'next': action, 'task_id': descriptor(run)['task_id']}


def packet_map(run, source=None):
    """Derive role paths from the native owner instead of hand-maintaining them."""
    import writing_lifecycle as lifecycle
    skill = policy()['skill']
    if skill == 'writer-pen':
        with lifecycle.session(run) as state:
            need(state['rounds'] and state['rounds'][-1]['verdict'] is None, 'Start a literary review batch first')
            result = {role: item['path'] for role, item in state['rounds'][-1]['packets'].items()}
    elif skill == 'reader-seat':
        manifest = load(source)
        for item in manifest['packets']:
            need(ref(item['path'])['sha256'] == item['sha256'], 'Native packet changed')
        result = {item['dimension']: item['path'] for item in manifest['packets']}
    else:
        need(source, '3080 packet directory is required')
        result = {role: str((Path(source) / ('review_packet_' + role + '.md')).resolve()) for role in policy()['roles']}
    need(set(result) == set(policy()['roles']) and all(Path(p).is_file() for p in result.values()), 'Native packet set is incomplete')
    return result


def deliver(run, arguments):
    """One checked public route; package-specific verifiers remain authoritative."""
    need(isinstance(arguments, list) and all(isinstance(a, str) for a in arguments), 'Delivery arguments must be a string array')
    need(not any(a == '--lifecycle-run' or a.startswith('--lifecycle-run=') for a in arguments),
         'The execution controller owns the lifecycle binding')
    with task(run):
        pass
    script = 'writing_run.py' if policy()['skill'] == 'writer-pen' else 'deliver.py'
    if script == 'writing_run.py':
        need(arguments and arguments[0] in {'check', 'deliver'}, 'Only checked literary exits are allowed')
    command = [sys.executable, '-B', str(ROOT / 'scripts' / script), *arguments, '--lifecycle-run', str(Path(run).resolve())]
    process = subprocess.run(command, text=True, capture_output=True)
    with task(run, True) as state:
        state['last_delivery'] = {'at': now(), 'command': command, 'returncode': process.returncode,
                                 'stdout_sha256': hashlib.sha256(process.stdout.encode()).hexdigest(),
                                 'stderr_sha256': hashlib.sha256(process.stderr.encode()).hexdigest()}
    if process.returncode:
        raise ValueError('Checked native delivery failed; no verified completion was issued')
    return process.stdout


def main():
    parser = argparse.ArgumentParser(description='Managed writing execution; ordinary writing rules remain in the selected task packet')
    subs = parser.add_subparsers(dest='command', required=True)
    init = subs.add_parser('init')
    init.add_argument('run'); init.add_argument('--task-id', required=True)
    init.add_argument('--registry'); init.add_argument('--mode', choices=('independent', 'self-check'), default='independent')
    nxt = subs.add_parser('next'); nxt.add_argument('run')
    stats = subs.add_parser('stats'); stats.add_argument('run')
    review = subs.add_parser('review'); review.add_argument('run')
    review.add_argument('--packets', required=True, help='JSON object mapping exact role names to native packet paths')
    review.add_argument('--timeout', type=int, default=420)
    review.add_argument('--native-run', help='Writer-pen native run; other profiles omit it')
    output = subs.add_parser('deliver'); output.add_argument('run')
    output.add_argument('--arguments', required=True, help='JSON array of the original native checked-exit arguments')
    packets = subs.add_parser('packets'); packets.add_argument('run')
    packets.add_argument('--source', help='Reader native round manifest or 3080 packet directory; literary omits this')
    packets.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result = initialize(args.run, args.task_id, args.registry, args.mode)
        elif args.command == 'next':
            result = next_step(args.run)
        elif args.command == 'stats':
            result = performance_summary(args.run)
        elif args.command == 'review':
            result = dispatch(args.run, load(args.packets), args.timeout, args.native_run)
        elif args.command == 'packets':
            import writing_lifecycle
            values = packet_map(args.run, args.source)
            writing_lifecycle.write_json(args.output, values, exclusive=True)
            result = {'status': 'prepared', 'packets': str(Path(args.output).resolve())}
        else:
            sys.stdout.write(deliver(args.run, json.loads(Path(args.arguments).read_text())))
            return 0
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.TimeoutExpired):
        print('Execution blocked; retain the current task and inspect private diagnostics. No acceptance was issued.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
