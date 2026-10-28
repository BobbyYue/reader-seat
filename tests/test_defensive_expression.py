"""Arithmetic, anchoring and enforcement tests; fixtures are not reader verdicts."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import defensive_expression as d
import context_value
from defensive_fixture import structural_defensive
from context_fixture import structural_context


class DefensiveExpressionTests(unittest.TestCase):
    def excess(self, text):
        record = structural_defensive(text)
        entry = record['items'][0]
        entry.update(classification='excess', excess_spans=[{k: entry[k] for k in ('start', 'end', 'quote')}])
        return record

    def test_prepared_record_and_missing_record_block(self):
        self.assertTrue(d.validate(None, '普通文本'))
        self.assertTrue(d.validate(d.template('普通文本'), '普通文本'))

    def test_lexical_measurement_does_not_invent_semantic_zero(self):
        report = d.measurement('不能据此证明效果，仅供参考。')
        self.assertEqual(report['data']['C'], 1)
        self.assertIsNone(report['data']['D'])
        self.assertIsNone(report['data']['R_percent'])

    def test_negative_result_and_character_voice_can_pass(self):
        for text, profile, attribution in [('未发现显著差异。', 'functional', 'author'),
                ('“我不是怕她，我只是没想好怎么开口。”', 'literary', 'character-voice'),
                ('Do not publish raw logs.', 'functional', 'author')]:
            with self.subTest(text=text):
                record = structural_defensive(text, profile)
                for entry in record['items']:
                    entry['attribution'] = attribution
                self.assertEqual(d.validate(record, text, profile), [])
                self.assertEqual(d.summary(record, text)['D'], 0)

    def test_confirmed_problem_is_counted_and_blocks_completion(self):
        text = '今天天气好。不能据此说明气候正在改善。'
        record = self.excess(text)
        result = d.summary(record, text)
        self.assertEqual((result['C'], result['D'], result['pending']), (1, 1, 0))
        self.assertGreater(result['R_percent'], 0)
        self.assertFalse(result['completion_eligible'])
        self.assertIn('defensive_expression unresolved excess', d.validate(record, text))
        self.assertEqual(d.validate(record, text, final=False), [])

    def test_repair_requires_current_text_not_old_record(self):
        text = '天气好。不能说明气候在改善。'
        old = self.excess(text)
        fixed = '天气好。'
        self.assertTrue(d.validate(old, fixed))
        self.assertEqual(d.validate(structural_defensive(fixed), fixed), [])

    def test_pending_does_not_become_success_or_measured_zero(self):
        text = '不代表所有用户。'
        record = structural_defensive(text)
        record['items'][0]['classification'] = 'pending'
        stats = d.summary(record, text)
        self.assertEqual(stats['pending'], 1)
        self.assertIsNone(stats['R_percent'])
        self.assertFalse(stats['completion_eligible'])
        self.assertTrue(d.validate(record, text))

    def test_partial_or_stale_scope_cannot_certify_work(self):
        text = '当前只采访了十二人。'
        record = structural_defensive(text)
        record['scope'] = 'partial'
        self.assertTrue(d.validate(record, text))
        self.assertIsNone(d.summary(record, text)['D'])

    def test_each_repeated_location_needs_review(self):
        text = '仅供参考。\n仅供参考。'
        record = structural_defensive(text)
        self.assertEqual(d.summary(record, text)['C'], 2)
        record['items'].pop()
        self.assertIn('defensive_expression detected location lacks review', d.validate(record, text))

    def test_duplicate_and_overlapping_units_rejected(self):
        text = '不能据此断言，不代表所有人。'
        record = structural_defensive(text)
        record['items'].append(copy.deepcopy(record['items'][0]))
        self.assertTrue(d.validate(record, text))
        record['items'][1]['issue_id'] = 'distinct-id'
        self.assertTrue(d.validate(record, text))

    def test_semantic_split_preserves_signal_coverage(self):
        text = '不能说明效果，不代表所有人。'
        record = structural_defensive(text)
        seed = record['items'][0]
        record['items'] = []
        for start, end in ((0, 7), (7, len(text))):
            entry = d.item(text, start, end)
            for key in ('classification', 'reason', 'reader_effect', 'protected_meaning', 'prior_context'):
                entry[key] = seed[key]
            entry['direct_alternative'] = entry['quote']
            record['items'].append(entry)
        self.assertEqual(d.validate(record, text), [])
        self.assertEqual(d.summary(record, text)['C'], 2)

    def test_unflagged_excess_can_be_added(self):
        text = '天气好。世界上还有许多其他情况值得考虑。'
        self.assertEqual(d.signals(text), [])
        record = structural_defensive(text)
        entry = d.item(text, 4, len(text))
        entry.update(classification='excess', reason='当前谈话是散步计划，这句没有补充天气信息。',
                     reader_effect='删后仍然能决定是否散步。', protected_meaning='保留天气好这一判断。',
                     prior_context='前文没有谈全球天气。', direct_alternative='天气好。',
                     excess_spans=[{'start': 4, 'end': len(text), 'quote': text[4:]}])
        record['items'] = [entry]
        self.assertEqual(d.summary(record, text)['D'], 1)
        self.assertTrue(d.validate(record, text))

    def test_union_count_not_keyword_or_overlapping_sum(self):
        text = '不能说明，不代表结果。'
        record = self.excess(text)
        record['items'][0]['excess_spans'] = [
            {'start': 0, 'end': 6, 'quote': text[:6]},
            {'start': 3, 'end': len(text), 'quote': text[3:]}]
        stats = d.summary(record, text)
        self.assertEqual(stats['D'], 1)
        self.assertEqual(stats['excess_characters'], d.count(text))
        self.assertEqual(stats['R_percent'], 100)

    def test_nfc_and_nonwhite_denominator(self):
        self.assertEqual(d.count('e\u0301 中\nA'), 3)

    def test_unreliable_excess_span_retains_D_but_not_R(self):
        text = '不能证明全部情况。'
        record = self.excess(text)
        record['items'][0].update(excess_spans=[], unmeasured_reason='整句绕行，无法可靠分出多余片段。')
        result = d.summary(record, text)
        self.assertEqual(result['D'], 1)
        self.assertIsNone(result['R_percent'])

    def test_empty_surface_has_no_percentage(self):
        result = d.summary(structural_defensive(''), '')
        self.assertEqual(result['R_status'], 'not-applicable')
        self.assertIsNone(result['R_percent'])

    def test_changed_deletion_or_outside_excess_span_rejected(self):
        text = '天气好。不能据此证明气候改善。'
        record = self.excess(text)
        record['items'][0]['without'] = '伪造的删除结果'
        self.assertTrue(d.validate(record, text, final=False))
        record = self.excess(text)
        record['items'][0]['excess_spans'] = [{'start': 0, 'end': 3, 'quote': text[:3]}]
        self.assertTrue(d.validate(record, text, final=False))

    def test_original_quote_not_silently_rewritten(self):
        text = '原文说：不能证明效果。'
        record = self.excess(text)
        record['items'][0]['attribution'] = 'source-quote'
        self.assertTrue(d.validate(record, text, final=False))

    def test_invalid_types_fail_closed(self):
        text = '不能说明效果。'
        for key, bad in [('items', None), ('profile', []), ('scope', []), ('version', True)]:
            record = structural_defensive(text); record[key] = bad
            self.assertTrue(d.validate(record, text))
        for key, bad in [('start', False), ('end', '4'), ('quote', []), ('context_start', []),
                         ('classification', {}), ('issue_id', {}), ('excess_spans', None)]:
            record = structural_defensive(text); record['items'][0][key] = bad
            self.assertTrue(d.validate(record, text))

    def test_context_gate_rejects_missing_stale_or_excess_metric(self):
        text = '不能据此说明收益。'
        record = structural_context(text)
        self.assertEqual(context_value.validate(record, text), [])
        for bad in (None, d.template(text + '新'), self.excess(text)):
            candidate = copy.deepcopy(record); candidate['defensive_expression'] = bad
            self.assertTrue(context_value.validate(candidate, text))

    def test_legacy_context_review_requires_migration(self):
        text = '可直接发布。'
        record = structural_context(text)
        record['version'] = 3
        record.pop('defensive_expression')
        self.assertTrue(context_value.validate(record, text))


if __name__ == '__main__':
    unittest.main()
