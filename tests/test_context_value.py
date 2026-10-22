"""Deterministic review obligations, not automated semantic quality scoring."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_value as value
from context_fixture import structural_context


class ContextValueTests(unittest.TestCase):
    def setUp(self):
        self.text = '候选方案\nX适合当前规模，不代表已证实收益。'
        self.record = structural_context(self.text)

    def test_required_review_is_not_optional(self):
        self.assertTrue(value.validate(None, self.text))

    def test_prepared_record_is_pending(self):
        self.assertTrue(value.validate(value.template(self.text), self.text))

    def test_current_record_checks_pass(self):
        self.assertEqual(value.validate(self.record, self.text), [])

    def test_changed_text_invalidates_record(self):
        self.assertTrue(value.validate(self.record, self.text + '新结论'))

    def test_old_version_is_rejected(self):
        self.record['version'] = 0
        self.assertTrue(value.validate(self.record, self.text))

    def test_automatic_signal_cannot_be_omitted(self):
        self.record['items'] = []
        self.assertTrue(value.validate(self.record, self.text))

    def test_same_signal_is_not_an_automatic_content_failure(self):
        self.assertTrue(value.probes(self.text))
        self.assertEqual(value.validate(self.record, self.text), [])

    def test_delete_result_is_recomputed(self):
        self.record['items'][0]['without'] = 'Fabricated edited paragraph'
        self.assertTrue(value.validate(self.record, self.text))

    def test_context_must_be_real(self):
        self.record['items'][0]['context'] = 'An invented context'
        self.assertTrue(value.validate(self.record, self.text))

    def test_retaining_no_value_is_unresolved(self):
        self.record['items'][0]['effect'] = 'none'
        self.assertIn('context_value unresolved content selection', value.validate(self.record, self.text))

    def test_remove_rewrite_move_require_existing_revision(self):
        for decision in ('remove', 'rewrite', 'move'):
            self.record['items'][0]['decision'] = decision
            self.assertIn('context_value unresolved content selection', value.validate(self.record, self.text))

    def test_different_judgment_needs_different_readings(self):
        item = self.record['items'][0]
        item['without_reading'] = item['with_reading']
        self.assertTrue(value.validate(self.record, self.text))

    def test_no_signal_still_needs_whole_text_scan(self):
        text = '当前只测试了一个地区。'
        record = structural_context(text)
        self.assertEqual(record['items'], [])
        self.assertEqual(value.validate(record, text), [])
        record['whole_text_scan'] = ''
        self.assertTrue(value.validate(record, text))

    def test_literary_voice_is_protected_not_functional_excuse(self):
        self.record['items'][0]['effect'] = 'voice'
        self.assertTrue(value.validate(self.record, self.text))
        self.record['profile'] = 'literary'
        self.record['attribution_replay']['profile'] = 'literary'
        self.assertEqual(value.validate(self.record, self.text, 'literary'), [])

    def test_teaching_recap_can_have_learning_effect(self):
        self.record['profile'] = 'teaching'
        self.record['attribution_replay']['profile'] = 'teaching'
        self.record['items'][0]['effect'] = 'learning'
        self.assertEqual(value.validate(self.record, self.text, 'teaching'), [])

    def test_required_disclosure_can_be_kept(self):
        self.record['items'][0]['effect'] = 'required-disclosure'
        self.assertEqual(value.validate(self.record, self.text), [])

    def test_multiple_paragraphs_all_need_coverage(self):
        text = self.text + '\n第二节。另一个主题。背景资料。\n分组使用原始精度。'
        record = structural_context(text)
        self.assertEqual(len(record['items']), 2)
        self.assertEqual(value.validate(record, text), [])
        record['items'].pop()
        self.assertTrue(value.validate(record, text))

    def test_signal_context_does_not_duplicate_an_entire_article(self):
        text = ('Ordinary supporting statement. ' * 40) + 'For reference only. ' + ('Another statement. ' * 40)
        self.assertEqual(len(value.probes(text)), 1)
        self.assertLess(len(value.probes(text)[0]['context']), len(text) / 5)

    def test_manual_suspect_without_keyword_can_be_compared(self):
        text = '先说明结果。然后再次重复结果。'
        record = structural_context(text)
        record['items'] = [dict(id='manual-1', context=text, quote='然后再次重复结果。', without='先说明结果。',
            with_reading='The result is repeated', without_reading='The same result remains', effect='none',
            reason='No extra content is lost', decision='remove')]
        self.assertIn('context_value unresolved content selection', value.validate(record, text))

    def test_multiple_signals_do_not_require_duplicate_reviews(self):
        text = '仅供参考，不代表已证实，分组使用原始精度。'
        self.assertEqual(len(value.probes(text)), 1)

    def test_duplicate_record_cannot_claim_coverage(self):
        self.record['items'].append(copy.deepcopy(self.record['items'][0]))
        self.assertTrue(value.validate(self.record, self.text))

    def test_important_neighbor_cannot_substitute_for_suspect_tail(self):
        item = self.record['items'][0]
        item['quote'] = '候选方案'
        item['without'] = item['context'].replace(item['quote'], '', 1)
        self.assertTrue(value.validate(self.record, self.text))

    def test_invalid_types_block_without_crashing(self):
        for field in ('profile', 'version'):
            record = copy.deepcopy(self.record); record[field] = []
            self.assertTrue(value.validate(record, self.text))
        for field in ('effect', 'decision', 'context', 'quote'):
            record = copy.deepcopy(self.record); record['items'][0][field] = []
            self.assertTrue(value.validate(record, self.text))


if __name__ == '__main__':
    unittest.main()
