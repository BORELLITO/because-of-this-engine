"""Positive/negative factual-source evidence contract tests (synthetic)."""
import copy
import unittest

from production.ledgers_v21 import validate_source_ledger
from tests.test_v21_integration import valid_manifest


class SourceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.manifest = copy.deepcopy(valid_manifest())

    def test_independent_secure_sources_pass_structurally(self):
        result = validate_source_ledger(self.manifest)
        self.assertEqual(result["status"], "PASS", result)
        # Structural PASS is not independent historical fact-checking.

    def test_same_url_with_two_publisher_names_fails(self):
        entries = self.manifest["source_ledger"]
        entries[1]["source_url"] = entries[0]["source_url"]
        entries[1]["publisher_or_author"] = "Different publisher label"
        result = validate_source_ledger(self.manifest)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("repeated source URL" in issue for issue in result["failures"]))

    def test_non_https_source_is_blocked(self):
        self.manifest["source_ledger"][0]["source_url"] = "http://example.test/insecure"
        result = validate_source_ledger(self.manifest)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("must use HTTPS" in issue for issue in result["failures"]))


if __name__ == "__main__":
    unittest.main()
