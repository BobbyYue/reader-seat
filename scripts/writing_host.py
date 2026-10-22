#!/usr/bin/env python3
"""Native-tool transport for the common controller; never imports hand-written PASS."""
import argparse
import json
from pathlib import Path
import sys
import uuid

import writing_execution as execution
import writing_lifecycle as lifecycle


def prepare(run, packets, native_run=None):
    number, artifact, native_context = execution.prepare_dispatch(run, packets, native_run)
    requests, complete = [], {}
    with execution.task(run, True) as task:
        batch = task['batches'][str(number)]
        jobs = batch['jobs']
        for role, packet in packets.items():
            old = jobs.get(role)
            if old and old.get('status') == 'captured':
                execution.need(execution.ref(old['result']['path']) == old['result'], 'Captured result changed')
                complete[role] = old['result']['path']
        for role, packet in packets.items():
            if role in complete:
                continue
            required = execution.policy().get('dependencies', {}).get(role, [])
            if not set(required) <= set(complete):
                continue
            deps = {r: complete[r] for r in required}
            signature = execution.digest({'packet': execution.ref(packet),
                'dependencies': {r: execution.ref(p) for r, p in deps.items()}, 'native_context': native_context})
            old = jobs.get(role)
            execution.need(not old or old['signature'] == signature, 'Started host packet cannot change')
            if old and old.get('status') in {'prepared', 'launching', 'launch-uncertain', 'started'}:
                execution.need(old['transport'] == 'native-tools', 'Resume the original backend')
                job = old
            else:
                attempts = (old or {}).get('attempts', 0) + 1
                execution.need(attempts <= execution.policy()['max_technical_attempts'], 'Host technical attempts exhausted')
                attempt = uuid.uuid4().hex
                directory = Path(run).resolve() / 'execution' / ('round-' + str(number)) / (role + '-' + attempt)
                directory.mkdir(mode=0o700, parents=True)
                prompt = directory / 'prompt.txt'
                prompt.write_text(execution.review_prompt(packet, deps), encoding='utf-8')
                job = {'status': 'prepared', 'attempts': attempts, 'attempt_id': attempt,
                       'signature': signature, 'packet': execution.ref(packet), 'transport': 'native-tools',
                       'prompt': execution.ref(prompt), 'dependencies': {r: execution.ref(p) for r, p in deps.items()},
                       'native_context': native_context, 'adapter': execution.ref(Path(__file__).with_name('writing_host.js')),
                       'prepared_at': execution.now()}
                jobs[role] = job
            requests.append({'role': role, 'attempt_id': job['attempt_id'], 'status': job['status'],
                             'prompt': job['prompt']['path'], 'agent_id': job.get('agent_id'),
                             'spawn': execution.load(job['spawn']['path']) if job.get('spawn') else None})
    return {'round': number, 'requests': requests, 'results': complete,
            'complete': set(complete) == set(execution.policy()['roles'])}


def locate(task, request_id):
    found = [(number, role, job) for number, batch in task['batches'].items()
             for role, job in batch['jobs'].items() if job.get('attempt_id') == request_id]
    execution.need(len(found) == 1, 'Unknown or ambiguous host request')
    return found[0]


def claim(run, request_id):
    with execution.task(run, True) as task:
        _, _, job = locate(task, request_id)
        execution.need(job['status'] == 'prepared', 'Request was already launched; do not duplicate it')
        execution.need(execution.ref(job['prompt']['path']) == job['prompt'], 'Prepared prompt changed')
        job['status'] = 'launching'
    return {'status': 'launching'}


def started(run, request_id, spawn):
    with execution.task(run, True) as task:
        _, _, job = locate(task, request_id)
        execution.need(job['status'] == 'launching' and isinstance(spawn.get('agent_id'), str) and spawn['agent_id'], 'No actual native spawn return')
        path = Path(job['prompt']['path']).parent / 'spawn.json'
        lifecycle.write_json(path, spawn, exclusive=True)
        job.update(status='started', agent_id=spawn['agent_id'], spawn=execution.ref(path), started_at=execution.now())
    return {'status': 'started'}


def launch_failed(run, request_id, error):
    with execution.task(run, True) as task:
        _, _, job = locate(task, request_id)
        execution.need(job['status'] == 'launching', 'Launch state changed')
        path = Path(job['prompt']['path']).parent / 'launch-error.json'
        lifecycle.write_json(path, error, exclusive=True)
        job.update(status='launch-uncertain', launch_error=execution.ref(path))
    return {'status': 'launch-uncertain', 'next': 'Inspect actual failure; confirm no agent was created before recover-launch'}


def recover_launch(run, request_id, confirmed_no_agent, reason):
    execution.need(confirmed_no_agent and isinstance(reason, str) and reason.strip(), 'Operator confirmation and reason are required')
    with execution.task(run, True) as task:
        _, _, job = locate(task, request_id)
        execution.need(job['status'] in {'launching', 'launch-uncertain'} and not job.get('agent_id'), 'Do not relaunch a known live reviewer')
        job.update(status='blocked', recovery={'basis': 'operator-confirmed-no-agent', 'reason': reason, 'at': execution.now()})
    return {'status': 'blocked', 'next': 'Resume the same task; a technical attempt, not another semantic round'}


def finish(run, request_id, raw):
    with execution.task(run) as task:
        number, role, job = locate(task, request_id)
        job = dict(job)
    execution.need(job['status'] == 'started', 'Native request was not started')
    directory = Path(job['prompt']['path']).parent
    capture_path = directory / 'host-return.json'
    lifecycle.write_json(capture_path, raw, exclusive=True)
    try:
        execution.need(raw.get('arguments') == {'fork_context': False, 'message': Path(job['prompt']['path']).read_text()},
                       'Host did not use the prepared isolated prompt')
        execution.need(raw.get('spawn') == execution.load(job['spawn']['path']), 'Spawn return changed')
        status = raw['wait']['status'][job['agent_id']]
        execution.need(isinstance(status, dict) and isinstance(status.get('completed'), str), 'Native reviewer did not complete')
        answer = directory / 'answer.json'
        answer.write_text(status['completed'], encoding='utf-8')
        stderr = directory / 'stderr.txt'; stderr.write_text('')
        captured = {'capture': 'fresh-native-tools', 'returncode': 0, 'context_id': job['agent_id'],
                    'agent_id': job['agent_id'], 'answer': execution.ref(answer), 'events': execution.ref(capture_path),
                    'stderr': execution.ref(stderr), 'spawn': job['spawn'], 'adapter': job['adapter']}
        result = execution.commit_capture(run, int(number), role, request_id, captured, job['packet']['path'],
            {r: d['path'] for r, d in job['dependencies'].items()}, job.get('native_context'))
        return {'status': 'captured', 'result': result}
    except BaseException:
        with execution.task(run, True) as task:
            _, _, current = locate(task, request_id)
            current.update(status='blocked', failed_at=execution.now())
        raise


def verify_capture(captured, job):
    execution.need(execution.ref(captured['adapter']['path']) == captured['adapter'], 'Native host adapter changed')
    execution.need(execution.ref(captured['spawn']['path']) == captured['spawn'], 'Original spawn return changed')
    execution.need(execution.ref(job['prompt']['path']) == job['prompt'], 'Prepared host prompt changed')
    raw = execution.load(captured['events']['path'])
    execution.need(raw['spawn'] == execution.load(captured['spawn']['path']) and
                   raw['spawn']['agent_id'] == captured['context_id'], 'Captured native identity changed')
    execution.need(raw['arguments'] == {'fork_context': False, 'message': Path(job['prompt']['path']).read_text()}, 'Host context boundary changed')
    execution.need(raw['wait']['status'][captured['context_id']]['completed'] == Path(captured['answer']['path']).read_text(),
                   'Original native completion was changed')


def main():
    parser = argparse.ArgumentParser(description='Native tool bridge used by writing_host.js')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('run'); p.add_argument('--packets', required=True); p.add_argument('--native-run')
    for name in ('claim', 'started', 'finish', 'launch-failed'):
        p = sub.add_parser(name); p.add_argument('run'); p.add_argument('--request', required=True)
    p = sub.add_parser('recover-launch'); p.add_argument('run'); p.add_argument('--request', required=True)
    p.add_argument('--confirmed-no-agent', action='store_true', required=True); p.add_argument('--reason', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.run, execution.load(args.packets), args.native_run)
        elif args.command == 'claim':
            result = claim(args.run, args.request)
        elif args.command == 'started':
            result = started(args.run, args.request, json.load(sys.stdin))
        elif args.command == 'launch-failed':
            result = launch_failed(args.run, args.request, json.load(sys.stdin))
        elif args.command == 'recover-launch':
            result = recover_launch(args.run, args.request, args.confirmed_no_agent, args.reason)
        else:
            result = finish(args.run, args.request, json.load(sys.stdin))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print('Host execution blocked; preserve raw returns and resume the same task.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
