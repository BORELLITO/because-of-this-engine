# Preview approvals

A final render requires a JSON approval file whose path is declared by the
episode manifest.

The file must contain:

```json
{
  "approved": true,
  "video_id": "episode-id",
  "preview_manifest_sha256": "sha256-of-the-exact-manifest",
  "reviewer": "name",
  "approved_at": "2026-10-21T12:00:00-03:00"
}
```

Do not create this file before a human reviews the preview on a mobile screen.
The approval is bound to the exact manifest hash; any change invalidates it.
