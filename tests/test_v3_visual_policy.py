import unittest

from production.v3_visual_policy import audit_visual_manifest


class VisualPolicyV3Tests(unittest.TestCase):
    def test_diagram_manifest_is_blocked(self):
        report = audit_visual_manifest(
            {
                "assets": [{"candidate_id": "bad", "truth_class": "MAP_OR_DIAGRAM", "source_role": "S01"}],
                "shot_assignments": [],
            }
        )
        self.assertEqual(report["status"], "V3_VISUAL_POLICY_BLOCKED")

    def test_direct_photorealistic_manifest_passes(self):
        report = audit_visual_manifest(
            {
                "assets": [{"candidate_id": "good", "truth_class": "REPRESENTATIONAL", "source_role": "S01"}],
                "shot_assignments": [
                    {
                        "shot_id": "S01",
                        "requested_truth_class": "REPRESENTATIONAL",
                        "requested_visual": "Photorealistic officer in a period-accurate bunker making the decision.",
                    }
                ],
            }
        )
        self.assertEqual(report["status"], "V3_VISUAL_POLICY_PASS")


if __name__ == "__main__":
    unittest.main()
