"""Frozen word-cloud inventory and behavior; matches are not quality verdicts."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import defensive_expression as d
import context_value
from defensive_fixture import structural_defensive
from context_fixture import structural_context


IMAGE_TERMS = (
    '不能', '不能直接', '不能把', '还不能', '尚不能', '不能推出',
    '不能仅凭', '不能只凭', '不能只看', '不能仅靠', '不能简单', '不能据此',
    '不能说', '不能断言', '不能视为', '不能保证', '不能认定', '不能确定',
    '不能确认', '不能当作', '不能当做', '不能断定', '不能承诺', '不能说明', '不能证明',
    '不足以说明', '不足以证明', '只能证明', '只能说明', '不证明',
    '无法说明', '无法证明', '不代表', '不等于', '不等同于', '不意味着',
    '不一定', '未必', '不必然', '不完全', '不是说', '而不是',
    '并不是', '并非', '更准确地说', '不构成', '不保证',
)


class DefensiveSignalVocabularyTests(unittest.TestCase):
    def test_all_image_terms_have_full_positioned_matches(self):
        self.assertEqual(len(IMAGE_TERMS), len(set(IMAGE_TERMS)))
        for term in IMAGE_TERMS:
            text = '开头。' + term + '相关情况。'
            with self.subTest(term=term):
                self.assertEqual(d.signals(text), [{'start': 3, 'end': 3 + len(term), 'quote': term}])
                self.assertEqual(len(d.template(text)['items']), 1)
                self.assertEqual(d.template(text)['items'][0]['classification'], 'pending')
                self.assertIsNone(d.measurement(text)['data']['D'])

    def test_paired_correction_and_ellipsis_variants(self):
        for text, quote in (
                ('不是……而是……', '不是……而是'),
                ('不是...而是...', '不是...而是'),
                ('不是重做流程，而是补充检查。', '不是重做流程，而是'),
                ('并不是重做流程，而是补充检查。', '并不是重做流程，而是')):
            with self.subTest(text=text):
                self.assertEqual(d.signals(text), [{'start': 0, 'end': len(quote), 'quote': quote}])
                self.assertEqual(len(d.template(text)['items']), 1)

    def test_pair_does_not_cross_sentence_or_line_boundaries(self):
        for separator in ('。', '！', '？', '!', '?', ';', '；', '\n', '\r\n'):
            with self.subTest(separator=separator):
                text = '不是重做流程' + separator + '下一句而是补充检查。'
                self.assertEqual(d.signals(text)[0]['quote'], '不是')
                self.assertTrue(d.template(text)['items'])

    def test_overlapping_prefixes_do_not_inflate_sentence_candidates(self):
        text = '尚不能确认时间，也不能据此保证效果，只能说明本轮已完成。'
        hits = d.signals(text)
        self.assertEqual([x['quote'] for x in hits], ['尚不能', '不能据此', '只能说明'])
        self.assertTrue(all(a['end'] <= b['start'] for a, b in zip(hits, hits[1:])))
        self.assertEqual(d.measurement(text)['data']['C'], 1)
        self.assertIsNone(d.measurement(text)['data']['D'])

    def test_repeated_new_signals_remain_separate_locations(self):
        text = '未必适用。\n未必适用。'
        self.assertEqual(len(d.signals(text)), 2)
        record = structural_defensive(text)
        self.assertEqual(d.summary(record, text)['C'], 2)
        record['items'].pop()
        self.assertIn('defensive_expression detected location lacks review', d.validate(record, text))

    def test_context_gate_cannot_skip_new_vocabulary(self):
        for text in ('只能说明本轮完成。', '更准确地说，这是重试。', '未必适用。'):
            with self.subTest(text=text):
                record = structural_context(text)
                self.assertEqual(context_value.validate(record, text), [])
                missing = copy.deepcopy(record)
                missing['defensive_expression']['items'] = []
                self.assertIn('defensive_expression detected location lacks review',
                              context_value.validate(missing, text))

    def test_new_terms_can_be_retained_without_rewriting_boundaries_or_voice(self):
        for text, profile, attribution in (
                ('尚不能确认恢复时间，也不能承诺周五交付。', 'functional', 'author'),
                ('原文写道：这只能说明相关，无法证明因果。', 'functional', 'source-quote'),
                ('“未必。”她把钥匙放回口袋。', 'literary', 'character-voice')):
            with self.subTest(text=text):
                record = structural_defensive(text, profile)
                for entry in record['items']:
                    entry['attribution'] = attribution
                self.assertTrue(record['items'])
                self.assertEqual(d.validate(record, text, profile), [])
                self.assertEqual(d.summary(record, text)['D'], 0)

    def test_original_chinese_and_english_signals_are_preserved(self):
        for term in ('不足以', '不是', '并不意味着', '没有证据', '未发现', '尚未',
                     '仅供参考', '仅作参考', '因人而异', '具体情况具体分析',
                     'cannot', "can't", 'not necessarily', 'no evidence', 'must not'):
            with self.subTest(term=term):
                self.assertTrue(d.signals(term))

    def test_ordinary_text_is_not_a_new_candidate(self):
        self.assertEqual(d.signals('本周完成联调，周五发布。她把钥匙放回口袋。'), [])


if __name__ == '__main__':
    unittest.main()
