"""A 10/10 package gate means complete metadata, not a great story."""
import unittest
from production.package_gate_pre import evaluate_package_gate
from tests.test_v21_integration import valid_manifest

class EditorialScoreDisclosureTests(unittest.TestCase):
    def test_high_score_never_auto_certifies_creative_quality(self):
        result = evaluate_package_gate(valid_manifest())
        self.assertEqual(result["score"], 10)
        self.assertEqual(result["score_scope"], "STRUCTURAL_COMPLETENESS_ONLY")
        self.assertIs(result["editorial_quality_proven"], False)

if __name__ == "__main__":
    unittest.main()
