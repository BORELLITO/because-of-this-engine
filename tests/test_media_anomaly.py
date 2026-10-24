import unittest

from production.media_anomaly import parse_filter_log


class MediaAnomalyTests(unittest.TestCase):
    def test_blocking_black_and_advisory_freeze_silence_are_distinguished(self):
        log = "\n".join([
            "[blackdetect] black_start:10 black_end:13 black_duration:3",
            "[freezedetect] freeze_start:20 freeze_end:24 freeze_duration:4",
            "[silencedetect] silence_start:30",
            "[silencedetect] silence_end:34 silence_duration:4",
        ])
        findings = parse_filter_log(log)
        self.assertEqual([item["severity"] for item in findings], ["BLOCKING", "ADVISORY", "ADVISORY"])
        self.assertEqual([item["type"] for item in findings], ["black", "freeze", "silence"])


if __name__ == "__main__":
    unittest.main()
