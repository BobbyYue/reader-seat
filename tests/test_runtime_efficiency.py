"""Actual cache/entrypoint guards using fictional local inputs, no model calls."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_writing_execution as base
import writing_execution as execution
import writing_lifecycle as lifecycle


class RuntimeEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base.ExecutionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.initialize()

    def test_same_version_calculated_once_across_stage_checks(self):
        with patch.object(lifecycle, 'measure_data', wraps=lifecycle.measure_data) as compute:
            self.fixture.candidate()
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)
        self.assertEqual(compute.call_count, 1)
        stats = execution.performance_summary(self.fixture.run)
        self.assertEqual(stats['performance']['measurement']['computed'], 1)
        self.assertEqual(stats['performance']['measurement']['reused'], 3)

    def test_corrupt_cache_recalculates_without_trusting_its_values(self):
        self.fixture.candidate()
        with execution.task(self.fixture.run, True) as record:
            cached = next(iter(record['measurement_cache'].values()))
            cached['report']['metrics']['terms']['data']['applicable'] = 999
        with patch.object(lifecycle, 'measure_data', wraps=lifecycle.measure_data) as compute:
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)
        self.assertEqual(compute.call_count, 1)

    def test_missing_cache_recalculates(self):
        self.fixture.candidate()
        with execution.task(self.fixture.run, True) as record:
            del record['measurement_cache']
        with patch.object(lifecycle, 'measure_data', wraps=lifecycle.measure_data) as compute:
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)
        self.assertEqual(compute.call_count, 1)

    def test_corrupt_cache_container_recalculates(self):
        self.fixture.candidate()
        with execution.task(self.fixture.run, True) as record:
            record['measurement_cache'] = []
        with patch.object(lifecycle, 'measure_data', wraps=lifecycle.measure_data) as compute:
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)
        self.assertEqual(compute.call_count, 1)

    def test_source_bytes_invalidate_key_even_without_a_timestamp_change(self):
        state = self.state()
        before = execution.measurement_signature(state, 'Same candidate')
        source = Path(state['sources'][0]['path'])
        source.write_text(source.read_text().replace('Synthetic', 'Different', 1))
        self.assertNotEqual(before, execution.measurement_signature(state, 'Same candidate'))

    def test_cache_does_not_hide_changed_delivered_bytes(self):
        self.fixture.candidate()
        self.fixture.artifact.write_text('A different result, not the checked statement.')
        with self.assertRaises(ValueError):
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)

    def test_cache_does_not_hide_changed_report(self):
        self.fixture.candidate()
        with lifecycle.session(self.fixture.run) as state:
            path = Path(state['candidates'][-1]['report']['path'])
        report = json.loads(path.read_text())
        report['metrics']['terms']['data']['applicable'] = 999
        path.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)

    def test_cache_does_not_hide_changed_plan(self):
        self.fixture.candidate()
        plan = json.loads(self.fixture.plan.read_text())
        plan['reader']['knowledge'] = 'Another audience'
        self.fixture.plan.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            execution.inspect_candidate(self.fixture.run, self.fixture.artifact)

    def state(self):
        with lifecycle.session(self.fixture.run) as state:
            return copy.deepcopy(state)

    def test_reader_profile_and_text_changes_invalidate_key(self):
        state = self.state()
        old = execution.measurement_signature(state, 'Same text')
        changed = copy.deepcopy(state)
        changed['plan']['reader']['knowledge'] = 'New reader'
        self.assertNotEqual(old, execution.measurement_signature(changed, 'Same text'))
        self.assertNotEqual(old, execution.measurement_signature(state, 'Changed text'))

    def test_wordlist_content_not_mtime_controls_reuse(self):
        state = self.state()
        path = self.fixture.root / 'words.txt'
        path.write_text('synthetic\nstatement\n')
        state['plan']['wordlists'] = {'en_word': str(path)}
        first = execution.measured_once(self.fixture.run, state, 'Synthetic statement.')
        path.write_text('different\nvocabulary\n')
        second = execution.measured_once(self.fixture.run, state, 'Synthetic statement.')
        self.assertNotEqual(first['metrics']['vocabulary'], second['metrics']['vocabulary'])

    def test_geometry_and_rule_bytes_invalidate_key(self):
        state = self.state()
        path = self.fixture.root / 'geometry.json'
        path.write_text('{"viewport":100}')
        first = execution.measurement_signature(state, 'Same text', path)
        path.write_text('{"viewport":200}')
        self.assertNotEqual(first, execution.measurement_signature(state, 'Same text', path))
        config = self.fixture.root / 'changed-rules.json'
        config.write_text(lifecycle.CONFIG.read_text() + '\n')
        before = execution.measurement_signature(state, 'Same text')
        with patch.object(lifecycle, 'CONFIG', config):
            self.assertNotEqual(before, execution.measurement_signature(state, 'Same text'))

    def test_mutating_return_does_not_mutate_stored_computation(self):
        state = self.state()
        report = execution.measured_once(self.fixture.run, state, 'Same text.')
        report['metrics']['terms']['data']['applicable'] = 999
        again = execution.measured_once(self.fixture.run, state, 'Same text.')
        self.assertNotEqual(again['metrics']['terms']['data']['applicable'], 999)

    def test_statistics_do_not_claim_measured_model_tokens(self):
        self.fixture.candidate()
        report = execution.performance_summary(self.fixture.run)
        self.assertEqual(report['task_id'], 'HOST-TEST-TASK')
        self.assertEqual(report['jobs'], [])
        self.assertIn('not token estimates', report['scope'])


if __name__ == '__main__':
    unittest.main()
