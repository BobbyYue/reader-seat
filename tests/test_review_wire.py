"""Synthetic codec tests: metadata reconstruction cannot invent semantic approval."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_wire as wire
import reader_value
import context_value
from editorial_fixture import structural_review

TEXT = '报告称 field_x 已接入，但不代表已证实收益。'


def small_reply(value, template):
    """Simulate omission of only the documented computed fields."""
    result = copy.deepcopy(value)
    record_kind = wire.kind(template)
    if record_kind:
        for field in wire.META:
            result.pop(field, None)
    if record_kind in {'context', 'attribution'}:
        for item in result['items']:
            item.pop('context', None)
            item.pop('context_start', None)
            item.pop('signals', None)
            item.pop('without', None)
            if record_kind == 'attribution':
                item.pop('quote', None)
    for key, child in template.items():
        if key in result and isinstance(child, dict):
            result[key] = small_reply(result[key], child)
    return result


class ReviewWireTests(unittest.TestCase):
    def setUp(self):
        self.template = reader_value.template(('expression', 'selection', 'meaning'), 'a'*64, TEXT, TEXT)
        self.full = structural_review(('expression', 'selection', 'meaning'), 'a'*64, TEXT, TEXT)

    def errors(self, value):
        return reader_value.validate(value, ('expression', 'selection', 'meaning'), 'a'*64, TEXT, source=TEXT)

    def test_compact_response_reconstructs_the_original_record(self):
        result = wire.expand(small_reply(self.full, self.template), self.template)
        self.assertEqual(result, self.full)
        self.assertEqual(self.errors(result), [])

    def test_explicit_wrong_binding_is_not_repaired(self):
        reply = small_reply(self.full, self.template)
        reply['artifact_binding'] = 'wrong'
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_missing_record_is_not_created(self):
        self.assertIsNone(wire.expand(None, self.template))
        reply = small_reply(self.full, self.template)
        del reply['checks']['meaning']['source_attribution']
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_missing_judgment_stays_missing(self):
        reply = small_reply(self.full, self.template)
        del reply['checks']['meaning']['source_attribution']['items'][0]['kind']
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_missing_item_is_not_filled(self):
        reply = small_reply(self.full, self.template)
        reply['checks']['meaning']['source_attribution']['items'].pop()
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_unknown_id_cannot_borrow_a_registered_anchor(self):
        reply = small_reply(self.full, self.template)
        reply['checks']['meaning']['source_attribution']['items'][0]['id'] = 'unknown'
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_explicit_bad_quote_is_not_repaired(self):
        reply = small_reply(self.full, self.template)
        reply['checks']['meaning']['source_attribution']['items'][0]['quote'] = 'Invented result'
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_explicit_bad_deletion_is_not_repaired(self):
        reply = small_reply(self.full, self.template)
        reply['checks']['selection']['context_review']['items'][0]['without'] = 'Wrong deletion'
        self.assertTrue(self.errors(wire.expand(reply, self.template)))

    def test_pending_template_does_not_become_a_pass(self):
        prepared = wire.expand(wire.compact(self.template), self.template)
        self.assertTrue(self.errors(prepared))

    def test_contexts_are_indexed_once_per_record(self):
        record = self.template['checks']['meaning']['source_attribution']
        compact = wire.compact(record)
        self.assertEqual(len(compact['_windows']), 1)
        self.assertTrue(all('context' not in item for item in compact['items']))
        self.assertLess(len(json.dumps(compact)), len(json.dumps(record)))

    def test_wrong_window_reference_blocks_expansion(self):
        reply = small_reply(self.full, self.template)
        reply['checks']['meaning']['source_attribution']['items'][0]['context_ref'] = 'unseen'
        with self.assertRaises(ValueError):
            wire.expand(reply, self.template)

    def test_legacy_full_record_keeps_all_judgments(self):
        self.assertEqual(wire.expand(self.full, self.template), self.full)

    def test_complete_reader_record_does_not_gain_extra_protocol_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reader.json'
            packet = {'dimension': 'readability', 'schema_version': 1, 'contract_id': 'fixture', 'batch_id': 'batch',
                'round': 1, 'packet_sha256': 'b'*64, 'artifact': {'sha256': 'a'*64}, 'invocation_mode': 'parallel-batch',
                'reader_value_template': self.template}
            path.write_text(json.dumps(packet))
            body = {key: packet[key] for key in ('dimension', 'schema_version', 'contract_id', 'batch_id', 'round', 'packet_sha256')}
            body.update(reader_value=self.full, artifact_sha256='a'*64)
            self.assertEqual(wire.expand_native(body, path), body)

    def test_markdown_template_uses_json_parser_and_preserves_other_material(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.md'
            path.write_text('Source inventory remains here.\n## Mandatory Editorial Evidence\n```json\n' + json.dumps(self.template) + '\n```\n')
            self.assertIn('Source inventory remains here.', wire.prompt_packet(path))
            result = wire.expand_native({'reader_value': small_reply(self.full, self.template)}, path)
            self.assertEqual(result['reader_value'], self.full)

    def test_no_context_packet_does_not_gain_sources_or_expected_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            template = self.template['checks']['selection']['context_review']['attribution_replay']
            packet = {'dimension': 'no-context', 'attribution_template': template, 'source_bundle': None}
            path.write_text(json.dumps(packet))
            compact = json.loads(wire.prompt_packet(path))
            self.assertIsNone(compact['source_bundle'])
            self.assertNotIn('expected_answers', compact)
            full = self.full['checks']['selection']['context_review']['attribution_replay']
            result = wire.expand_native({'reader_understanding': {'attribution_replay': small_reply(full, template)}}, path)
            self.assertEqual(result['reader_understanding']['attribution_replay'], full)

    def test_markdown_transport_metadata_is_filled_but_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.md'
            identity = {'artifact_set_id': 'a'*64, 'review_round': 1}
            path.write_text('## Required Output\n```json\n' + json.dumps(identity) + '\n```\n## Mandatory Editorial Evidence\n```json\n' + json.dumps(self.template) + '\n```\n')
            self.assertEqual(wire.expand_native({}, path), identity)
            self.assertEqual(wire.expand_native({'artifact_set_id': 'wrong'}, path)['artifact_set_id'], 'wrong')

    def test_tiny_packets_keep_legacy_protocol_without_extra_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tiny.json'
            path.write_text('{"role":"reader"}')
            text, guidance = wire.transport_packet(path)
            self.assertEqual(text, path.read_text())
            self.assertEqual(guidance, '')

    def test_transport_including_guidance_is_never_larger(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            path.write_text(json.dumps({'reader_value_template': self.template}, ensure_ascii=False, indent=2))
            text, guidance = wire.transport_packet(path)
            self.assertLessEqual(len((text + guidance + (' ' if guidance else '')).encode()), len(path.read_bytes()))


if __name__ == '__main__':
    unittest.main()
