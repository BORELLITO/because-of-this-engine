# BECAUSE OF THIS — V2.1 Integration Control Center

- Implementation ID: IMPL-V21-20261105-01
- Audit ID: AUDIT-V21-20261105-01
- Specification: PROMPT_MESTRE_IMPLEMENTACAO_INTEGRACAO_BECAUSE_OF_THIS_V2_1_FINAL(2).txt
- Prompt SHA-256: 8f51c909363ead5c6d2964b733fcdf8909632dc68fef966802b1f8a56e2cb173
- Repository: BORELLITO/because-of-this-engine
- Base: main at d35d78cd4a92d12375f54076e3e21b56cbe25fad
- Candidate branch: integration/because-of-this-v2.1-20261105
- Draft PR: 67
- Candidate commit: authoritative PR head
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
| Edge TTS real preview | GENERATED_AND_VALIDATED | GitHub Actions run 41954211512; 79.704 s; ChristopherNeural; artifact 13382850131 |
| First new production | BLOCKED | Implementation stage does not authorize automatic production |

## Remaining blockers

- The 13 historical registry assets were fingerprinted from their verified Drive MP4s with the versioned video-phash-v1 algorithm; future assets must use the same catalog contract.
- Real thumbnail files and platform cover records are not yet available for a V2.1 episode.
- Offline contracts for TTS, audio, captions, render and Drive are integrated; the canonical entrypoint verifies the real adapter files and symbols. Real Edge TTS preview generated and validated; downstream transcription/captions, media generation, Drive write and publication remain unexecuted.
- Promotion to main still requires explicit approval and post-merge audit.

READY remains forbidden while any P0/P1 is open.