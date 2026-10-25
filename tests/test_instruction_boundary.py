"""Review obligations and protected uses, not a semantic quality score."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_value as value
from context_fixture import structural_context


class InstructionBoundaryTests(unittest.TestCase):
    def test_direct_and_paraphrased_echoes_request_review(self):
        for text in (
            '按照你的要求，本文采用专业但易读的表达方式。',
            '为了让读者三十秒看懂，下面先给出结论。',
            '这一段不夸张、不刻意吸引眼球。',
            'As requested, this article uses professional yet readable language.',
            'This section will avoid hype while remaining reader-first.',
        ):
            with self.subTest(text=text):
                probes = value.probes(text)
                self.assertTrue(any('writing-instruction' in p['signals'] for p in probes))
                self.assertTrue(value.validate(value.template(text), text))

    def test_detected_echo_cannot_skip_existing_review(self):
        text = '按照你的要求，本文从读者视角讲清楚。'
        record = structural_context(text)
        record['items'] = []
        self.assertIn('context_value a detected passage lacks comparison', value.validate(record, text))

    def test_unresolved_echo_blocks_until_candidate_is_revised(self):
        text = '这一段不夸张。试验只覆盖一个地区。'
        record = structural_context(text)
        record['items'][0].update(effect='none', decision='remove')
        self.assertIn('context_value unresolved content selection', value.validate(record, text))
        clean = '试验只覆盖一个地区。'
        self.assertTrue(value.validate(record, clean))
        self.assertEqual(value.validate(structural_context(clean), clean), [])

    def test_same_phrase_is_not_a_ban_on_recipient_agreements(self):
        text = '按照你的要求，我已把排期发给项目组。'
        record = structural_context(text)
        record['items'][0].update(effect='action', reason='Synthetic schema case: confirms a supplied recipient agreement.')
        self.assertEqual(value.validate(record, text), [])

    def test_method_quote_can_be_retained_for_teaching(self):
        text = '提示词示例：按照你的要求，本文从读者视角展开。'
        record = structural_context(text, 'teaching')
        record['items'][0].update(effect='learning', reason='Synthetic schema case: quoted wording is the lesson subject.')
        self.assertEqual(value.validate(record, text, 'teaching'), [])

    def test_intentional_fictional_speech_can_be_retained(self):
        text = '按照你的要求，我没写结尾。他把空白稿纸递过去。'
        record = structural_context(text, 'literary')
        record['items'][0].update(effect='voice', reason='Synthetic schema case: fictional dialogue enacts the conflict.')
        self.assertEqual(value.validate(record, text, 'literary'), [])

    def test_evidence_boundary_is_not_a_writing_instruction(self):
        text = '本报告采用分层抽样，只覆盖东区；尚不能外推到其他地区。'
        self.assertFalse(any('writing-instruction' in p['signals'] for p in value.probes(text)))
        self.assertEqual(value.validate(structural_context(text), text), [])

    def test_unflagged_paraphrase_can_be_manually_reviewed(self):
        text = '这份文字会以轻松的口吻陪你把问题看明白。'
        record = structural_context(text)
        record['items'] = [dict(id='manual-echo', context=text, quote=text, without='',
            with_reading='A promise about prose tone', without_reading='No subject information is lost',
            effect='none', reason='Synthetic schema case: authoring preference became the paragraph content.', decision='rewrite')]
        self.assertIn('context_value unresolved content selection', value.validate(record, text))

    def test_old_record_does_not_prove_new_instruction_review(self):
        text = '结论仍待验证。'
        record = structural_context(text)
        old = copy.deepcopy(record)
        old['version'] = 2
        self.assertIn('context_value stale version or text binding', value.validate(old, text))
        self.assertEqual(value.validate(record, text), [])


if __name__ == '__main__':
    unittest.main()
