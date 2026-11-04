# YouTube Studio Audio Library — controlled audio intake (Because Of This V7.4 candidate)

**Current policy: YouTube + TikTok.** A track found in YouTube Studio's Audio Library is not automatically licensed for use on TikTok. YouTube's own guidance says it cannot give legal guidance for use outside its platform. Every off-platform license requires independent evidence. Do not infer clearance from the download button, royalty-free wording or a self-affirmed checkbox.

Official source: https://support.google.com/youtube/answer/3376882

## Safe process

1. Choose a music track in YouTube Studio Audio Library, inspect the actual license and copy the required attribution verbatim if applicable.
2. Record title, exact artist, license type, acquisition evidence, and the target platforms. Use a song **only after verifying its terms for each intended platform**.
3. Inspect the actual downloaded MP3 (SHA-256, sound-quality and real listening tests on phone/headphones at low volume); compare against previously used audio. Never mark a test PASS without testing it.
4. Register any candidate **only against the single global ledger** `episodes/audio-memory-registry.json`, not an episode-local license register.
5. The current ingestion tool deliberately records YouTube Audio Library tracks as `license_status=REVIEW_REQUIRED` and `off_platform_rights_verified=false`. It **never** upgrades them to final-ready based on the Studio download alone.
6. The global G5 gate independently checks SHA-256, real bytes, cross-episode music identity, SFX usage and approval; a generated report cannot override this live test.

Example metadata shape (statuses shown as PASS **only after actual verified testing**):

```json
{
  "track_id": "youtube-unique-track-title-and-artist",
  "title": "Exact track title from Studio",
  "artist": "Exact artist name",
  "attribution_required": false,
  "attribution_text": "",
  "volume": 0.08,
  "similarity_review": {"status": "PASS", "evidence": "real listening and comparison record"},
  "device_tests": {"phone": "PASS", "headphones": "PASS", "low_volume": "PASS"}
}
```

Tool invocation in an authorized local working branch:

```sh
python production/ingest_youtube_audio_library.py /local/track.mp3 /local/metadata.json \
  --confirm-audio-library-download \
  --episode-dir episodes/new-episode \
  --manifest episodes/new-episode/manifest.json \
  --register episodes/audio-memory-registry.json
```

This command is illustrative; do not run against the main production branch or an existing episode without specific approval. The tool checks global track ID and actual SHA collisions **before copying** and refuses to replace an existing soundtrack master or a previous episode's registry entry. It still cannot independently grant commercial rights on TikTok.

For **Mixkit Stock Music**, confirm the specific music track's Free License (not only the mood/category page); Mixkit allows web/social use within the Stock Music Free License restrictions: https://mixkit.co/license/modal/musicFree/

For **Pixabay music**, a valid Content License does not prevent a Content ID claim; preserve the original licensing page and contributor name: https://pixabay.com/service/license-summary/ and https://pixabay.com/service/faq/

**No automated publication, no TTS, no synthetic music generation and no modification of historical episodes are part of this audit.**
