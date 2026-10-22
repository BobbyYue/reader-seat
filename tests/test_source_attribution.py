"""Synthetic record/flow tests, not proof that model judgments are true."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import source_attribution as attribution
import context_value
from context_fixture import structural_attribution, structural_context

TEXT = '邮件写道：field_x 已加入回传。但是否等同 official_time 仍待确认。'
SOURCE = '提问者：field_x 已加入回传。'


class SourceAttributionTests(unittest.TestCase):
    def setUp(self):
        self.record = structural_attribution(TEXT, SOURCE, 'source')

    def test_guidance_declares_actual_machine_values_not_invented_aliases(self):
        self.assertEqual(set(attribution.ITEM_FORMAT['kind']), attribution.KINDS)
        self.assertEqual(set(attribution.ITEM_FORMAT['negative_status']), attribution.NEGATIVES)
        self.assertEqual(set(attribution.ITEM_FORMAT['source_scope']), attribution.SCOPES)
        self.assertIn(json.dumps(attribution.ITEM_FORMAT, separators=(',', ':')), attribution.GUIDANCE)
        self.assertEqual(set(context_value.ITEM_FORMAT['effect']), context_value.EFFECTS)
        self.assertEqual(set(context_value.ITEM_FORMAT['decision']), context_value.DECISIONS)
        self.record['items'][0]['kind'] = 'source_fact'
        self.assertIn('source_attribution invalid claim kind', attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_template_pending_and_clause_coverage(self):
        record = attribution.template(TEXT, SOURCE, 'source')
        self.assertGreater(len(record['items']), 1)
        self.assertTrue(attribution.validate(record, TEXT, SOURCE, 'source'))

    def test_overlapping_windows_stay_local_and_do_not_duplicate_clauses(self):
        sizes = []
        for repeats in (40, 80):
            record = attribution.template('报告称流程已更新，但效果尚未确认。' * repeats)
            identities = [item['id'] for item in record['items']]
            self.assertEqual(len(identities), len(set(identities)))
            self.assertTrue(all(len(item['context']) < 80 for item in record['items']))
            sizes.append(len(json.dumps(record, ensure_ascii=False)))
        self.assertLess(sizes[1], sizes[0] * 2.2)

    def test_structural_record_has_all_required_clauses(self):
        self.assertEqual(attribution.validate(self.record, TEXT, SOURCE, 'source'), [])

    def test_missing_record_blocks(self):
        self.assertTrue(attribution.validate(None, TEXT))

    def test_missing_clause_blocks(self):
        self.record['items'].pop()
        self.assertIn('source_attribution a required clause is unreviewed', attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_stale_text_blocks(self):
        self.assertTrue(attribution.validate(self.record, TEXT + '补充', SOURCE, 'source'))

    def test_stale_source_blocks(self):
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE + '补充', 'source'))

    def test_boolean_version_blocks(self):
        self.record['version'] = True
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_changed_context_blocks(self):
        self.record['items'][0]['context'] = '另一封邮件'
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_duplicate_blocks(self):
        self.record['items'].append(copy.deepcopy(self.record['items'][0]))
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_invalid_item_does_not_crash(self):
        self.record['items'] = [None]
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_invented_support_blocks(self):
        self.record['items'][0]['support_quote'] = '已经证实不同'
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_source_claim_needs_support(self):
        self.record['items'][0]['kind'] = 'source-fact'
        self.assertTrue(any('unresolved unsupported' in e for e in attribution.validate(self.record, TEXT, SOURCE, 'source')))

    def test_confirmed_negative_needs_support(self):
        self.record['items'][-1]['negative_status'] = 'confirmed'
        self.assertTrue(any('unresolved unsupported' in e for e in attribution.validate(self.record, TEXT, SOURCE, 'source')))

    def test_named_speaker_needs_basis(self):
        self.record['items'][0]['speaker'] = '平台回复者'
        self.assertTrue(any('unresolved speaker' in e for e in attribution.validate(self.record, TEXT, SOURCE, 'source')))

    def test_source_fact_cannot_claim_non_source_scope(self):
        self.record['items'][0].update(kind='source-fact', support_quote=SOURCE, source_scope='not-source-claim')
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_actual_quote_and_speaker_anchor_accepted_structurally(self):
        self.record['items'][0].update(kind='source-fact', speaker='提问者', speaker_basis='提问者：', support_quote='field_x 已加入回传。', source_scope='quoted-passage')
        self.assertEqual(attribution.validate(self.record, TEXT, SOURCE, 'source'), [])

    def test_blind_reader_cannot_use_unseen_source(self):
        record = structural_attribution(TEXT)
        record['items'][0]['support_quote'] = SOURCE
        self.assertTrue(any('unseen' in e for e in attribution.validate(record, TEXT)))

    def test_whole_scan_required_without_lexical_hits(self):
        record = structural_attribution('请周五发我结果。')
        self.assertEqual(record['items'], [])
        record['whole_text_scan'] = ''
        self.assertTrue(attribution.validate(record, '请周五发我结果。'))

    def test_reader_source_owner_mismatch_blocks(self):
        reader = structural_attribution(TEXT)
        reader['items'][0]['kind'] = 'source-fact'
        self.assertTrue(attribution.compare(self.record, reader))

    def test_repeated_quote_can_have_different_owners_in_distinct_contexts(self):
        source = {'items': [dict(quote='尚未确认。', context='报告写道：尚未确认。', kind='source-fact', negative_status='unconfirmed'),
                            dict(quote='尚未确认。', context='作者的核对结果：尚未确认。', kind='author-interpretation', negative_status='unconfirmed')]}
        reader = {'items': [copy.deepcopy(source['items'][1])]}
        self.assertEqual(attribution.compare(source, reader), [])

    def test_unconfirmed_is_not_confirmed(self):
        reader = structural_attribution(TEXT)
        reader['items'][0]['negative_status'] = 'confirmed'
        self.assertTrue(attribution.compare(self.record, reader))

    def test_matching_replay_passes_structure(self):
        self.assertEqual(attribution.compare(self.record, structural_attribution(TEXT)), [])

    def test_reader_can_replay_subset_not_unrelated_clause(self):
        reader = structural_attribution(TEXT)
        reader['items'] = reader['items'][:1]
        self.assertEqual(attribution.compare(self.record, reader), [])
        reader['items'][0]['quote'] = '其他句子'
        self.assertTrue(attribution.compare(self.record, reader))

    def test_ambiguous_duplicate_quote_does_not_silently_win(self):
        duplicate = copy.deepcopy(self.record['items'][0])
        duplicate['kind'] = 'source-fact'
        self.record['items'].append(duplicate)
        self.assertTrue(attribution.compare(self.record, structural_attribution(TEXT)))

    def test_malformed_comparison_does_not_crash(self):
        for value in (None, {}, {'items': [None]}, {'items': [{'quote': 'x', 'kind': 'unknown', 'negative_status': []}]}):
            self.assertTrue(attribution.compare(value, self.record))
            self.assertTrue(attribution.compare(self.record, value))

    def test_same_cue_can_pass_with_explicit_negative_source(self):
        source = '官方回复：field_x 与 official_time 不同。'
        text = '官方回复：field_x 与 official_time 不同。'
        record = structural_attribution(text, source, 'source')
        for item in record['items']:
            item.update(kind='source-fact', negative_status='confirmed', speaker='官方回复者', speaker_basis='官方回复：', support_quote=source, source_scope='provided-material')
        self.assertEqual(attribution.validate(record, text, source, 'source'), [])

    def test_fictional_voice_preserved_not_external_testimony(self):
        record = structural_attribution(TEXT, profile='literary')
        for item in record['items']:
            item['kind'] = 'fictional-voice'
        self.assertEqual(attribution.validate(record, TEXT, profile='literary'), [])
        record['profile'] = 'functional'
        self.assertTrue(attribution.validate(record, TEXT))

    def test_invalid_profile_does_not_crash(self):
        self.record['profile'] = []
        self.assertTrue(attribution.validate(self.record, TEXT, SOURCE, 'source'))

    def test_context_review_cannot_omit_replay(self):
        record = structural_context('请周五发我结果。')
        del record['attribution_replay']
        self.assertTrue(context_value.validate(record, '请周五发我结果。'))

    def test_standalone_source_claim_requires_source_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, review = root / 'text.txt', root / 'review.json'
            path.write_text(TEXT)
            record = structural_context(TEXT)
            record['attribution_replay']['items'][0]['kind'] = 'source-fact'
            review.write_text(json.dumps(record))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/context_value.py'), 'check', '--text', str(path), '--review', str(review)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('source snapshot required', result.stdout)

    def test_source_binding_is_checked_inside_context_review(self):
        record = structural_context(TEXT)
        record['source_attribution'] = self.record
        self.assertEqual(context_value.validate(record, TEXT, source=SOURCE), [])
        self.assertTrue(context_value.validate(record, TEXT, source=SOURCE + '变化'))


if __name__ == '__main__':
    unittest.main()
