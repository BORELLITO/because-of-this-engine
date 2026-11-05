# BECAUSE OF THIS — V2.1 Integration Control Center

- Implementation ID: IMPL-V21-20261105-01
- Audit ID: AUDIT-V21-20261105-01
- Specification: PROMPT_MESTRE_IMPLEMENTACAO_INTEGRACAO_BECAUSE_OF_THIS_V2_1_FINAL(2).txt
- Prompt SHA-256: 8f51c909363ead5c6d2964b733fcdf8909632dc68fef966802b1f8a56e2cb173
- Repository: BORELLITO/because-of-this-engine
- Base: main at d35d78cd4a92d12375f54076e3e21b56cbe25fad
- Candidate branch: integration/because-of-this-v2.1-20261105
- Draft PR: 67 (branch head is authoritative; commit history is tracked by GitHub)
- Status: PARTIAL / BLOCKED_FOR_PRODUCTION
- Canonical entrypoint: production/canonical_entrypoint.py
- Canonical voice: Microsoft Edge TTS / ChristopherNeural active for zero-billing preview; Cloud/Gemini are not active routes
- Publication: manual only
- Historical protection: One Extra Minute is excluded from execution and reuse

## This changeset

- canonical_entrypoint.py is now the authority for the V2.1 read-only contract.
- The old v7_orchestrator.py delegates to the canonical entrypoint whenever the V2.1 policy is active.
- The old V2/V7 state machine is an explicit compatibility boundary; V2.1 records use pipeline_state_v21.py.
- The global asset registry is loaded automatically and missing/incomplete catalogs block.
- The production schema is validated by the canonical entrypoint, not only parsed as JSON.
- The final thumbnail manifest and delivery paths are mandatory for a canonical PASS.
- The singleton workflow audit is fail-closed in CI.
- Historical production workflows were moved to archive/v7/workflows/; they are no longer GitHub Actions entrypoints.
- Visual candidate intake is manual-only and fail-closed; it produces evidence artifacts but cannot promote assets, update the global catalog, write Drive or render.

## Evidence

| Area | Status | Evidence |
|---|---|---|
| Main / refs / PRs | FOUND | GitHub API; main d35d78c; PR 67 |
| V2.1 contracts | TESTED | Candidate CI must pass unit, schema, adapter, singleton and clean-checkout gates |
| Canonical adapter | IMPLEMENTED | v7_orchestrator.py delegates to canonical_entrypoint.py under active V2.1 policy |
| Global no-reuse | BLOCKED when incomplete | Registry is required and independent perceptual hashes are required |
| Thumbnail | BLOCKED when incomplete | Final manifest, delivery paths and strict file checks are required |
| Legacy workflows | ARCHIVED | Definitions retained under archive/v7/workflows/, outside .github/workflows |
| Drive | NOT RUN | No Drive write or media generation authorized |
| Work | UNKNOWN | No independent Work execution log |
| Edge TTS + captions preview | NATIVE_PROVIDER_TIMING_VALIDATED_GROUPED_BOUNDARIES | Audio run 41961294784 + frozen caption run 41966915074; 79.704 s; ChristopherNeural; 175 provider tokens; 2 grouped boundaries; caption artifact 13388300361 |
| Visual asset acquisition | INTAKE_WORKFLOW_READY | 15 Pexels fallback candidates plus 4 Mixkit Free-License candidates mapped to Episode 005 beats; clock and cloudy-sky candidates downloaded through the intake workflow and awaiting human/fingerprint approval; none approved for render |
| First new production | BLOCKED | Implementation stage does not authorize automatic production |

## Remaining blockers

- The 13 historical registry assets were fingerprinted from their verified Drive MP4s with the versioned video-phash-v1 algorithm; future assets must use the same catalog contract.
- Real thumbnail files and platform cover records are not yet available for a V2.1 episode.
- Renderer accepts provider-native grouped boundaries as synchronized units; no provider interval is subdivided synthetically. Final render remains blocked only by missing approved assets, thumbnail and the remaining release gates.
- Offline contracts for TTS, audio, captions, render and Drive are integrated; the canonical entrypoint verifies the real adapter files and symbols. Real Edge TTS audio and provider-native caption timing are generated and validated. Two provider boundary groups remain intentionally unsplit; the Whisper acoustic audit is retained as diagnostic and is not allowed to replace provider timing. The approved artifact is frozen; the synthesis workflow is manual-only because independent runs can produce different audio hashes. Visual asset acquisition is partially executed: two Mixkit candidates have technical intake artifacts and 9:16 QA frames, but human approval and global perceptual fingerprints remain pending. Thumbnail, render, Drive write and publication remain unexecuted. Pexels direct media download was blocked by the browser; Mixkit is now the preferred acquisition route, with license-page verification and per-file QA still mandatory. The GitHub intake workflow downloads browser-verified media URLs, records SHA-256/metadata and emits QA frames without promotion.
- Promotion to main still requires explicit approval and post-merge audit.

READY remains forbidden while any P0/P1 is open.