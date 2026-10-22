"""Format diagnostics do not approve or rewrite reviewer judgments."""
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_review_result
import writing_execution


class ReviewDiagnosticTests(unittest.TestCase):
    def test_diagnostic_preserves_a_negative_result_and_reports_errors(self):
        with TemporaryDirectory() as directory:
            packet = Path(directory) / 'packet.json'
            result = Path(directory) / 'result.json'
            packet.write_text(json.dumps({'contract_id': 'task', 'batch_id': 'batch', 'round': 1}))
            original = {'status': 'fail', 'issues': [{'severity': 'major'}]}
            result.write_text(json.dumps(original))
            before = result.read_bytes()
            with patch.object(check_review_result.reader_review, 'validate_result', return_value=['missing evidence']) as validate:
                value = check_review_result.inspect(packet, result)
            self.assertEqual(value['errors'], ['missing evidence'])
            self.assertEqual(validate.call_args.args[0]['status'], 'fail')
            self.assertEqual(result.read_bytes(), before)
            self.assertIn('not captured review', value['scope'])

    def test_schema_in_prompt_exposes_existing_record_constraints(self):
        with TemporaryDirectory() as directory:
            packet = Path(directory) / 'packet.json'
            packet.write_text('{"dimension":"structure-visual"}')
            prompt = writing_execution.review_prompt(packet, {})
            self.assertIn('keep/revise/remove/defer', prompt)
            self.assertIn('context.replace', prompt)
            self.assertIn('Keep legitimate negative judgments', prompt)
            self.assertIn('check_review_result.py', prompt)
            schema = json.loads((ROOT/'config/reader-review-result.schema.json').read_text())
            self.assertEqual(schema['properties']['checks']['additionalProperties']['required'], ['status', 'evidence'])


if __name__ == '__main__':
    unittest.main()
