# YouTube Audio Library workflow

Audio Library music is selected and downloaded manually in YouTube Studio.
The official help page says tracks can be filtered by attribution requirement,
and tracks requiring Creative Commons attribution must be credited in the
video description. Verify rights separately before distributing the rendered
episode outside YouTube.

Official guide: <https://support.google.com/youtube/answer/3376882>

## Attach a suspense bed to a v2 episode

1. In YouTube Studio, open **Audio Library** and choose a suspense-appropriate
   track. Prefer **Attribution not required** for the simplest publication
   workflow.
2. Download the MP3 from Studio. For attribution-required tracks, copy the
   exact attribution text shown by Studio.
3. Create a metadata JSON file:

```json
{
  "title": "Track title from Studio",
  "artist": "Artist from Studio",
  "attribution_required": false,
  "attribution_text": "",
  "volume": 0.08
}
```
4. Run the ingestion tool from the repository root, replacing the placeholders
   with the target episode paths:

```sh
python production/ingest_youtube_audio_library.py <download>/track.mp3 <metadata>/track.json \
  --confirm-audio-library-download \
  --episode-dir <episode> \
  --manifest <episode>/manifest.json \
  --register <episode>/music-license-register.json
```

The tool stages the file at
`<episode>/assets/music/youtube-audio-library.mp3`, updates the v2 manifest
and writes the license record. The renderer then applies voice-first mixing,
sidechain ducking and loudness/true-peak validation.

The tool never logs into Studio, downloads tracks automatically or infers
rights. Supply the exact title, artist, attribution status and required credit
copied from the Audio Library interface.
