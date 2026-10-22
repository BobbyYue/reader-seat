"""Reject incomplete native review returns before they become cached successes."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import writing_execution as execution
import test_runtime_contract as runtime_fixture


class NativeReturnTests(unittest.TestCase):
    def test_missing_reader_value_is_a_technical_return_failure(self):
        fixture = runtime_fixture.RuntimeContractTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.init_contract()
        artifact = fixture.write_html(language='en', body='The inspected period is known; later changes are not established. ' * 4)
        fixture.complete_review(artifact)
        aggregate = execution.load(fixture.complete_reader_review(artifact))
        record = next(r for r in aggregate['reviews'] if r['dimension'] == 'readability')
        manifest = execution.load(aggregate['manifest_path'])
        packet = next(p['path'] for p in manifest['packets'] if p['dimension'] == 'readability')
        original = execution.load(record['result_path'])
        execution.validate_native_return(fixture.base, original, 'readability', packet)
        missing_context = copy.deepcopy(original)
        del missing_context['reader_value']['checks']['selection']['context_review']
        with self.assertRaisesRegex(ValueError, 'Native return has malformed'):
            execution.validate_native_return(fixture.base, missing_context, 'readability', packet)
        incomplete = copy.deepcopy(original)
        del incomplete['reader_value']
        with self.assertRaisesRegex(ValueError, 'Native return has malformed'):
            execution.validate_native_return(fixture.base, incomplete, 'readability', packet)


if __name__ == '__main__':
    unittest.main()
