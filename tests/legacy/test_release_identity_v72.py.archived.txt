from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from production.release_integrity_v72 import audit_release_identities

def episode(root,name,sha,track):
    path=root/"episodes"/name/"manifest.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({
      "video_id":name,"scenes":[{"scene_id":"S01",
        "asset":{"asset_id":name+"-s01","sha256":sha,
         "drive_file_id":name,"source_page_url":"https://site.example/"+sha}}],
      "music":{"track_id":track}
    }))
    return path

class IdentityGateTests(unittest.TestCase):
    def test_valid_unique_source_identity_verifies_both_ledgers(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/"episodes").mkdir(exist_ok=True)
            (r/"episodes/asset-memory-registry.json").write_text('{"schema_version":1,"assets":[]}')
            (r/"episodes/audio-memory-registry.json").write_text('{"schema_version":1,"tracks":[]}')
            p=episode(r,"one","a"*64,"track-1")
            result=audit_release_identities(p)
            self.assertEqual(result["asset_reuse_gate"],"ASSET_REUSE_PASS")
            self.assertEqual(result["audio_reuse_gate"],"PASS")
            self.assertFalse(result["license_provenance_independently_verified"])
    def test_archived_asset_source_still_blocks_release(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/"episodes").mkdir(exist_ok=True)
            (r/"episodes/asset-memory-registry.json").write_text('{"schema_version":1,"assets":[]}')
            (r/"episodes/audio-memory-registry.json").write_text('{"schema_version":1,"tracks":[]}')
            old=episode(r,"old","a"*64,"track-1")
            m=json.loads(old.read_text());m["lifecycle_status"]="ARCHIVED_HISTORICAL"
            old.write_text(json.dumps(m))
            target=episode(r,"new","a"*64,"track-2")
            with self.assertRaisesRegex(ValueError,"source history"):
                audit_release_identities(target)
    def test_reused_music_blocks_release(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);(r/"episodes").mkdir(exist_ok=True)
            (r/"episodes/asset-memory-registry.json").write_text('{"schema_version":1,"assets":[]}')
            (r/"episodes/audio-memory-registry.json").write_text('{"schema_version":1,"tracks":[]}')
            episode(r,"old","a"*64,"track-1")
            target=episode(r,"new","b"*64,"track-1")
            with self.assertRaisesRegex(ValueError,"music history"):
                audit_release_identities(target)
if __name__=="__main__":unittest.main()
