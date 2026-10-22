"""Actual state/guard tests; review subprocesses are synthetic, not quality proof."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import writing_execution as execution
import writing_lifecycle as lifecycle


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rules = {'version': 1, 'skill': '3080-brief', 'roles': ['reader', 'source', 'visual'],
                      'dependencies': {'source': ['reader']}, 'max_rounds': 3, 'max_technical_attempts': 2,
                      'rules': [{'id': 'candidate', 'stage': 'candidate', 'owner': 'actual code'},
                                {'id': 'delivery', 'stage': 'delivery', 'owner': 'native verifier'}]}
        self.original_policy = execution.policy
        self.policy_patch = patch.object(execution, 'policy', lambda: self.rules)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)
        self.artifact = self.root / 'article.txt'
        self.artifact.write_text('Synthetic statement. No release date is confirmed.', encoding='utf-8')
        plan = {'task': 'Synthetic task', 'genre': 'report', 'domain': 'testing', 'purpose': 'Inspect process constraints',
                'language': 'en', 'format': 'text', 'reader': {'knowledge': 'No author context', 'need': 'Understand the statement'},
                'authority': {'status': 'confirmed', 'basis': 'Synthetic test only', 'reference': 'Not real acceptance'},
                'material': {'mode': 'source-grounded', 'gaps': []},
                'required_answers': [{'id': 'A1', 'question': 'What is known?', 'expected': 'No release date is confirmed.', 'source_location': 'synthetic'}],
                'reading_path': [{'id': 'U1', 'purpose': 'One complete statement'}]}
        self.plan = self.save('plan.json', plan)
        self.run = self.root / 'run'
        lifecycle.init_run(self.run, self.plan, 'functional', [self.artifact])
        self.registry = self.root / 'registry.sqlite3'
        self.calls, self.lock = [], threading.Lock()

    def save(self, name, value):
        path = self.root / name
        lifecycle.write_json(path, value)
        return path

    def initialize(self, mode='independent'):
        return execution.initialize(self.run, 'HOST-TEST-TASK', self.registry, mode)

    def candidate(self):
        value = self.artifact.read_text()
        unit = self.save('unit.json', {'unit_id': 'U1', 'summary': 'Synthetic observation',
            'observations': [{'quote': value, 'reason': 'Identity fixture only'}]})
        lifecycle.record_unit(self.run, self.artifact, unit)
        report_path = self.root / 'measurement.json'
        report = lifecycle.measure(self.run, self.artifact, report_path)
        assessment = self.save('assessment.json', {'text_sha256': report['text_sha256'],
            'report_sha256': execution.ref(report_path)['sha256'],
            'observations': [{'metrics': list(report['metrics']), 'quote': value, 'reason': 'Synthetic coverage only'}],
            'dispositions': [{'signal_id': s['id'], 'decision': 'retain', 'reason': 'Synthetic retention'}
                             for m in report['metrics'].values() for s in m['signals']], 'issues': []})
        lifecycle.register_candidate(self.run, self.artifact, self.artifact, report_path, assessment)

    def fake_invoke(self, prompt, directory, timeout):
        role = json.loads(prompt.split('\n\n', 1)[1].split('\n\nFrozen', 1)[0])['role']
        with self.lock:
            self.calls.append(role)
        directory = Path(directory)
        directory.mkdir(parents=True)
        answer = directory / 'answer.json'
        lifecycle.write_json(answer, {'verdict': 'PASS', 'reviewer_role': role, 'answer_responses': [],
            'checks': [{'result': 'PASS', 'reason': 'Synthetic fixture only'}],
            'blocking_issues': [], 'unsupported_claims': [], 'missing_coverage': [], 'required_fixes': []})
        context = 'SYNTHETIC-' + role + '-' + directory.name
        events = directory / 'events.jsonl'
        events.write_text(json.dumps({'type': 'thread.started', 'thread_id': context, 'SYNTHETIC': True}) + '\n')
        stderr = directory / 'stderr.txt'; stderr.write_text('Synthetic generator, not actual Codex.')
        return {'answer': execution.ref(answer), 'events': execution.ref(events), 'stderr': execution.ref(stderr),
                'context_id': context, 'agent_id': context, 'returncode': 0, 'capture': 'fresh-codex-process'}

    def review(self):
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        with patch.object(execution, '_invoke', self.fake_invoke):
            return execution.dispatch(self.run, packets)

    def complete(self):
        self.initialize(); self.candidate()
        lifecycle.start_review(self.run, self.artifact)
        dispatched = self.review()
        aggregate = self.save('aggregate.json', {'status': 'pass', 'reader_value_receipt': {'reviews':
            [execution.ref(p) for p in dispatched['results'].values()]}})
        lifecycle.finish_review(self.run, aggregate, 'pass')
        return aggregate

    def test_stable_task_cannot_reset_by_changing_directory(self):
        self.initialize()
        other = self.root / 'another-run'
        lifecycle.init_run(other, self.plan, 'functional', [self.artifact])
        with self.assertRaisesRegex(ValueError, 'another run'):
            execution.initialize(other, 'HOST-TEST-TASK', self.registry)

    def test_resume_does_not_reset_state(self):
        self.initialize()
        with execution.task(self.run, True) as state:
            state['native'].append({'fixture': 'retained'})
        self.assertEqual(self.initialize()['status'], 'resumed')
        with execution.task(self.run) as state:
            self.assertEqual(len(state['native']), 1)

    def test_task_identity_is_required(self):
        with self.assertRaises(ValueError):
            execution.initialize(self.run, '', self.registry)

    def test_new_rule_without_a_registered_validator_is_rejected(self):
        actual = execution.load(execution.POLICY)
        actual['rules'][0]['id'] = 'unimplemented-requirement'
        path = self.save('unknown-rule-policy.json', actual)
        with patch.object(execution, 'POLICY', path), self.assertRaisesRegex(ValueError, 'no registered validator'):
            self.original_policy()

    def test_retroactive_initialization_is_rejected(self):
        self.candidate()
        with self.assertRaisesRegex(ValueError, 'before writing'):
            self.initialize()

    def test_missing_execution_does_not_accept_filled_records(self):
        with self.assertRaisesRegex(ValueError, 'Managed execution missing'):
            execution.inspect_candidate(self.run, self.artifact)

    def test_directory_round_four_and_retargeting_rejected(self):
        self.initialize()
        for n in range(1, 4):
            execution.reserve_batch(self.run, n, 'original')
        with self.assertRaises(ValueError):
            execution.reserve_batch(self.run, 4, 'original')
        with self.assertRaises(ValueError):
            execution.reserve_batch(self.run, 3, 'changed')

    def test_dispatch_honors_dependency_and_reuses_completed_jobs(self):
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        first = self.review()
        self.assertLess(self.calls.index('reader'), self.calls.index('source'))
        count = len(self.calls)
        self.assertEqual(self.review(), first)
        self.assertEqual(len(self.calls), count)

    def test_captured_originals_and_native_verifier_accept(self):
        aggregate = self.complete()
        result = execution.accept_native(self.run, self.artifact, [aggregate],
            {'status': 'pass', 'artifact_sha256': execution.ref(self.artifact)['sha256']})
        self.assertEqual(result['status'], 'managed')

    def test_changed_original_event_is_rejected(self):
        aggregate = self.complete()
        with execution.task(self.run) as task:
            event = task['batches']['1']['jobs']['reader']['captured']['events']['path']
        Path(event).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            execution.verify_reviews(self.run, [aggregate])

    def test_missing_original_role_is_rejected(self):
        aggregate = self.complete()
        value = execution.load(aggregate); value['reader_value_receipt']['reviews'].pop()
        changed = self.save('missing-role.json', value)
        with self.assertRaisesRegex(ValueError, 'omits'):
            execution.verify_reviews(self.run, [changed])

    def test_unrelated_hash_cannot_substitute_an_original_return(self):
        aggregate = self.complete()
        value = execution.load(aggregate)
        original = value['reader_value_receipt']['reviews'][0]
        copied = execution.load(original['path'])
        copied['checks'][0]['reason'] = 'A different author-written acceptance record'
        path = self.save('substitute.json', copied)
        value['reader_value_receipt']['reviews'][0] = execution.ref(path)
        value['unrelated_transport_sha256'] = original['sha256']
        changed = self.save('substitute-aggregate.json', value)
        with self.assertRaisesRegex(ValueError, 'omits'):
            execution.verify_reviews(self.run, [changed])

    def test_dispatch_rejects_a_copy_with_extra_author_material(self):
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        packets['reader'] = self.save('contaminated.json', {'role': 'reader', 'author_context': 'Answer supplied by the author'})
        with patch.object(execution, '_invoke', self.fake_invoke), self.assertRaisesRegex(ValueError, 'exact registered'):
            execution.dispatch(self.run, packets)
        self.assertEqual(self.calls, [])

    def test_malformed_json_return_is_a_retryable_technical_failure(self):
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        failed = set()
        def malformed_once(prompt, directory, timeout):
            result = self.fake_invoke(prompt, directory, timeout)
            role = execution.load(result['answer']['path'])['reviewer_role']
            if role == 'reader' and role not in failed:
                failed.add(role)
                Path(result['answer']['path']).write_text('{}')
                result['answer'] = execution.ref(result['answer']['path'])
            return result
        with patch.object(execution, '_invoke', malformed_once):
            with self.assertRaises(ValueError):
                execution.dispatch(self.run, packets)
            self.assertEqual(execution.dispatch(self.run, packets)['round'], 1)
        with execution.task(self.run) as task:
            self.assertEqual(task['batches']['1']['jobs']['reader']['attempts'], 2)

    def test_native_host_transport_records_actual_spawn_and_completion_shape(self):
        import writing_host
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        first = writing_host.prepare(self.run, packets)
        self.assertEqual({r['role'] for r in first['requests']}, {'reader', 'visual'})
        for request in first['requests']:
            writing_host.claim(self.run, request['attempt_id'])
            spawn = {'agent_id': 'SYNTHETIC-host-' + request['role'], 'nickname': 'Fixture'}
            writing_host.started(self.run, request['attempt_id'], spawn)
            result = {'verdict': 'PASS', 'reviewer_role': request['role'], 'checks': [{'result': 'PASS', 'reason': 'Synthetic'}],
                      'blocking_issues': [], 'unsupported_claims': [], 'missing_coverage': [], 'required_fixes': []}
            raw = {'arguments': {'fork_context': False, 'message': Path(request['prompt']).read_text()},
                   'spawn': spawn, 'wait': {'status': {spawn['agent_id']: {'completed': json.dumps(result)}}}}
            writing_host.finish(self.run, request['attempt_id'], raw)
        second = writing_host.prepare(self.run, packets)
        self.assertEqual([r['role'] for r in second['requests']], ['source'])

    def test_native_host_never_relaunches_an_uncertain_request(self):
        import writing_host
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        request = writing_host.prepare(self.run, packets)['requests'][0]
        writing_host.claim(self.run, request['attempt_id'])
        with self.assertRaisesRegex(ValueError, 'already launched'):
            writing_host.claim(self.run, request['attempt_id'])

    def test_failed_launch_has_controlled_recovery_without_resetting_rounds(self):
        import writing_host
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        request = writing_host.prepare(self.run, packets)['requests'][0]
        writing_host.claim(self.run, request['attempt_id'])
        writing_host.launch_failed(self.run, request['attempt_id'], {'message': 'SYNTHETIC spawn rejection'})
        same = writing_host.prepare(self.run, packets)
        self.assertIn('launch-uncertain', [r['status'] for r in same['requests']])
        with self.assertRaises(ValueError):
            writing_host.recover_launch(self.run, request['attempt_id'], False, 'No confirmation')
        writing_host.recover_launch(self.run, request['attempt_id'], True, 'SYNTHETIC operator confirmed no child exists')
        resumed = writing_host.prepare(self.run, packets)
        self.assertEqual(resumed['round'], 1)
        self.assertNotEqual(next(r for r in resumed['requests'] if r['role'] == request['role'])['attempt_id'], request['attempt_id'])

    def test_failed_native_result_cannot_be_promoted(self):
        aggregate = self.complete()
        with self.assertRaisesRegex(ValueError, 'not final'):
            execution.accept_native(self.run, self.artifact, [aggregate], {'status': 'fail'})

    def test_wrong_artifact_native_result_is_rejected(self):
        aggregate = self.complete()
        with self.assertRaisesRegex(ValueError, 'different bytes'):
            execution.accept_native(self.run, self.artifact, [aggregate], {'status': 'pass', 'artifact_sha256': 'wrong'})

    def test_self_check_cannot_turn_into_independent(self):
        self.initialize('self-check'); self.candidate()
        lifecycle.start_review(self.run, self.artifact)
        result = self.save('self.json', {'status': 'pass'})
        lifecycle.finish_review(self.run, result, 'pass')
        with self.assertRaisesRegex(ValueError, 'promote'):
            execution.verify_reviews(self.run, [result])
        self.assertEqual(execution.verify_reviews(self.run, [result], 'self-check')['method'], 'self-check')

    def test_next_step_and_owned_delivery_binding(self):
        self.initialize()
        self.assertEqual(execution.next_step(self.run)['next'], 'write-and-register-unit')
        with self.assertRaisesRegex(ValueError, 'owns'):
            execution.deliver(self.run, ['--lifecycle-run=other'])

    def test_technical_failure_resumes_same_round(self):
        self.initialize(); self.candidate(); lifecycle.start_review(self.run, self.artifact)
        original = self.fake_invoke
        failed = set()
        def once(prompt, directory, timeout):
            role = json.loads(prompt.split('\n\n', 1)[1].split('\n\nFrozen', 1)[0])['role']
            if role == 'reader' and role not in failed:
                failed.add(role)
                raise OSError('Synthetic transport interruption')
            return original(prompt, directory, timeout)
        packets = {r: self.save(r + '-packet.json', {'role': r}) for r in self.rules['roles']}
        execution.register_packets(self.run, packets, self.plan)
        with patch.object(execution, '_invoke', once):
            with self.assertRaises(OSError):
                execution.dispatch(self.run, packets)
            result = execution.dispatch(self.run, packets)
        self.assertEqual(result['round'], 1)
        with execution.task(self.run) as task:
            self.assertEqual(task['batches']['1']['jobs']['reader']['attempts'], 2)


if __name__ == '__main__':
    unittest.main()
