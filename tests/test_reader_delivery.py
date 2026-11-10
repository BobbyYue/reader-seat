"""Exercise enforcement using synthetic judgments, not claim model improvement."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_value
import reader_delivery
from context_fixture import structural_context


class ReaderDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.text = '登录和支付已通过测试，退款尚未测试。先补退款测试，再决定上线。'
        self.record = structural_context(self.text)

    def test_prepared_three_observations_are_pending(self):
        record = context_value.template(self.text)
        self.assertEqual(set(record['whole_text_scan']), set(reader_delivery.CHECKS))
        self.assertTrue(context_value.validate(record, self.text))

    def test_old_freeform_scan_and_old_version_cannot_pass(self):
        for old in ('全文已审查，无问题。', {}, None):
            record = copy.deepcopy(self.record)
            record['whole_text_scan'] = old
            self.assertTrue(context_value.validate(record, self.text))
        self.record['version'] = 4
        self.assertTrue(context_value.validate(self.record, self.text))

    def test_each_observation_is_required_without_keyword_hits(self):
        text = '请按业务情况综合考虑。'
        for key in reader_delivery.CHECKS:
            record = structural_context(text)
            del record['whole_text_scan'][key]
            self.assertTrue(context_value.validate(record, text))

    def test_zero_defensive_excess_cannot_override_missing_answer(self):
        text = '整体方向很好，实施时结合业务情况继续完善。'
        record = structural_context(text)
        self.assertEqual(record['defensive_expression']['items'], [])
        record['whole_text_scan']['answer'].update(status='revise', quote=text,
            reason='SYNTHETIC: request asked which of two supplied options to choose, but this text selects neither.',
            repair='Use the supplied constraints to state a supported choice or identify the decisive unknown.')
        self.assertIn('reader_delivery unresolved answer: revise', context_value.validate(record, text))

    def test_completed_answer_does_not_override_overload_or_padding(self):
        for key in ('selection', 'ending'):
            record = copy.deepcopy(self.record)
            record['whole_text_scan'][key].update(status='revise',
                reason='SYNTHETIC: extra service framing repeats settled information.',
                repair='Remove the unrequested closing offer while preserving the actual decision condition.')
            self.assertTrue(context_value.validate(record, self.text))

    def test_unassessed_is_not_a_zero_issue_pass(self):
        self.record['whole_text_scan']['selection'].update(status='unassessed', repair='Read the omitted section.')
        self.assertTrue(context_value.validate(self.record, self.text))

    def test_pass_needs_current_text_and_cannot_hide_repairs(self):
        for change in ({'quote': 'A fabricated conclusion'}, {'quote': ''}, {'repair': 'Still rewrite this part'}, {'reason': 'pass'}):
            record = copy.deepcopy(self.record)
            record['whole_text_scan']['answer'].update(change)
            self.assertTrue(context_value.validate(record, self.text))

    def test_necessary_unknown_and_clear_message_can_pass(self):
        for text in (self.text, '恢复时间尚未确认。', '安全BP已申请文档权限。', '谢谢，我先自己试一下。', 'OK', '无'):
            self.assertEqual(context_value.validate(structural_context(text), text), [])

    def test_real_recipient_offer_or_method_is_not_banned(self):
        for text in ('如果你需要，我明天下午可以一起排查。', '先按客户分别汇总两周金额，再用本周减上周。'):
            self.assertEqual(context_value.validate(structural_context(text), text), [])

    def test_no_forced_factual_answer_for_literature(self):
        record = structural_context('他把没写完的信收回抽屉。', 'literary')
        record['whole_text_scan']['answer'].update(status='not_applicable', quote='',
            reason='A deliberately open scene, not a factual question or work request.')
        self.assertEqual(context_value.validate(record, '他把没写完的信收回抽屉。', 'literary'), [])
        record['whole_text_scan']['ending']['status'] = 'not_applicable'
        self.assertTrue(context_value.validate(record, '他把没写完的信收回抽屉。', 'literary'))

    def test_functional_answer_cannot_be_waived(self):
        self.record['whole_text_scan']['answer'].update(status='not_applicable', quote='')
        self.assertTrue(context_value.validate(self.record, self.text))

    def test_invalid_types_block_without_crashing(self):
        for key in ('status', 'quote', 'reason', 'repair'):
            record = copy.deepcopy(self.record)
            record['whole_text_scan']['answer'][key] = []
            self.assertTrue(context_value.validate(record, self.text))


if __name__ == '__main__':
    unittest.main()
