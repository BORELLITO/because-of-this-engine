# YouTube Audio Library workflow

Audio Library music is selected and downloaded in YouTube Studio. The official
help page says tracks can be filtered by attribution requirement, and tracks
requiring Creative Commons attribution must be credited in the video
description. Monetization is supported for Audio Library tracks in the YouTube
Partner Program. Keep this workflow scoped to YouTube use; verify rights
separately before distributing the rendered episode elsewhere.

Official guide: <https://support.google.com/youtube/answer/3376882>

## Attach a track

1. In YouTube Studio, open **Audio Library** and choose a music track. Prefer
   **Attribution not required** for the simplest publication workflow.
2. Download the MP3 from Studio. For attribution-required tracks, copy the
   exact attribution text shown by Studio.
3. Create a metadata JSON file, for example:

   ```json
   {
     "title": "Track title from Studio",
     "artist": "Artist from Studio",
     "attribution_required": false,
     "attribution_text": "",
     "volume": 0.08
   }
   ```

4. Run the ingestion tool from the repository root. The paths below are for the
   Mars Climate Orbiter sample; replace them for another episode.

   ```sh
   python production/ingest_youtube_audio_library.py ~/Downloads/track.mp3 /tmp/track-metadata.json \
     --confirm-audio-library-download \
     --episode-dir examples \
     --manifest examples/mars-climate-orbiter-render-manifest-v1.json \
     --register examples/music-license-register.json
   ```

The tool stages the file at `examples/assets/music/youtube-audio-library.mp3`,
updates the render manifest, and writes the license record. Review the details
before committing. The final preflight remains responsible for checking the
track file and music contract before release.

The tool does not log into Studio, download tracks automatically, or infer
track metadata. Supply the exact title, artist, attribution status, and any
required credit copied from the Audio Library interface.
