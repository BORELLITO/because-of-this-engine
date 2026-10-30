from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from production.audio_reuse_brain import audit, AudioReuseError

def make(root,episode,track,status=None):
    folder=root/"episodes"/episode
    folder.mkdir(parents=True,exist_ok=True)
    v={"video_id":episode,"music":{"track_id":track}}
    if status:v["lifecycle_status"]=status
    p=folder/"manifest.json"
    p.write_text(json.dumps(v))
    return p

class MusicHistoryTests(unittest.TestCase):
    def test_archived_soundtrack_remains_consumed(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);make(r,"old","track-001","ARCHIVED_HISTORICAL")
            latest=make(r,"new","track-001")
            result=audit(latest,r)
            self.assertEqual(result["status"],"BLOCKED")
    def test_registry_blocks_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);latest=make(r,"new","track-001")
            ledger=r/"episodes"/"audio-memory-registry.json"
            ledger.write_text(json.dumps({"tracks":[{"episode_id":"old","track_id":"track-001"}]}))
            self.assertEqual(audit(latest,r,ledger)["status"],"BLOCKED")
    def test_missing_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);latest=make(r,"new","track-002")
            with self.assertRaisesRegex(AudioReuseError,"UNAVAILABLE"):
                audit(latest,r,r/"missing.json")
    def test_unique_track_passes(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);make(r,"old","track-001")
            latest=make(r,"new","track-002")
            self.assertEqual(audit(latest,r)["status"],"PASS")

if __name__=="__main__":unittest.main()
