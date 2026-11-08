"""Read-only acoustic risk triage is heuristic: NEVER a no-siren certificate."""
from __future__ import annotations
import importlib.util
import math
import unittest

from production.music_content_screen_v21 import analyze_samples, SourceScreenError, SR

HAS_NUMPY = importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy")


@unittest.skipUnless(HAS_NUMPY, "NumPy/SciPy required for optional spectral test")
class SpectralMusicScreenTests(unittest.TestCase):
    def test_steady_dark_drone_does_not_create_false_sweep_certificate(self):
        import numpy as np
        t = np.arange(SR * 15) / SR
        steady = (.14 * np.sin(2 * np.pi * 120 * t)).astype("float32")
        result = analyze_samples(steady)
        self.assertEqual(result["siren_like_tonal_sweep_candidates"], [])
        self.assertFalse(result["absence_of_sirens_certified"])
        self.assertFalse(result["subjective_story_fit_certified"])
        self.assertFalse(result["no_content_id_claim_certified"])
        self.assertEqual(result["status"],
                         "NO_HEURISTIC_CANDIDATES_HUMAN_AUDITION_STILL_REQUIRED")

    def test_repeated_gliding_siren_like_tone_is_flagged_not_certified(self):
        import numpy as np
        t = np.arange(SR * 15) / SR
        hz = 550 + 400 * (1 - np.abs(2 * ((t / 2.6) % 1) - 1))
        x = (.25 * np.sin(2 * np.pi * np.cumsum(hz) / SR)).astype("float32")
        result = analyze_samples(x)
        self.assertTrue(result["siren_like_tonal_sweep_candidates"], result)
        self.assertEqual(result["status"], "CANDIDATES_FOR_AUDITION")
        self.assertFalse(result["absence_of_sirens_certified"])

    def test_silence_and_nonfinite_inputs_rejected_or_not_certified(self):
        import numpy as np
        with self.assertRaises(SourceScreenError):
            analyze_samples(np.array([float("nan")] * SR * 4))
        silence = analyze_samples(np.zeros(SR * 6, dtype="float32"))
        self.assertFalse(silence["absence_of_vocals_certified"])


if __name__=="__main__":
    unittest.main()
