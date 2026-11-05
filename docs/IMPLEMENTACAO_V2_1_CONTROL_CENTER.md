# BECAUSE OF THIS — V2.1 Integration Control Center

- Implementation ID: IMPL-V21-20261105-01
- Audit ID: AUDIT-V21-20261105-01
- Specification: PROMPT_MESTRE_IMPLEMENTACAO_INTEGRACAO_BECAUSE_OF_THIS_V2_1_FINAL(2).txt
- Repository: BORELLITO/because-of-this-engine
- Base: main at d35d78cd4a92d12375f54076e3e21b56cbe25fad
- Candidate branch: integration/because-of-this-v2.1-20261105
- Status: BLOCKED_FOR_PRODUCTION / IMPLEMENTATION_CANDIDATE
- Canonical voice: Gemini TTS / Charon preserved; Cloud Charon remains OFFLINE_CONTRACT_ONLY
- Publication: manual only
- Historical protection: One Extra Minute is excluded from execution and reuse

## Implemented in this isolated candidate

- One V2.1 canonical entrypoint: production/canonical_entrypoint.py.
- Deterministic PACKAGE_GATE_PRE with a 10-point story score and factual-pilot pillars.
- Source ledger, rights ledger and global no-reuse checks.
- visual_truth_class vocabulary and evidence-versus-representation separation.
- Fail-closed V2.1 state machine with no critical state skips.
- Thumbnail concept gate plus final manifest/mobile/platform status contract.
- legacy_registry.json with legacy_rollback_only semantics.
- Schema production-record/3.1.0.
- No media, TTS, render, Drive write, publication or account mutation is performed by the entrypoint.

## Evidence classification

| Area | State | Evidence |
|---|---|---|
| GitHub repository/main | FOUND | API read of repository, refs, PRs and workflow runs |
| Candidate code | IMPLEMENTED | files on this branch after commit |
| Unit/schema contracts | TESTED | isolated V2.1 test workflow |
| Drive catalog | PARTIAL | accessible folders found; global byte/fingerprint reconciliation not proven |
| Work session | UNKNOWN | no independent execution log exposed |
| Rights | BLOCKED until episode-specific evidence | generic manifest approvals are insufficient |
| Safe zones | BLOCKED for real UI | geometry contract only; no real TikTok/Shorts captures |
| Gemini TTS real call | NOT_RUN | no credits consumed; existing voice lock preserved |
| First new production | BLOCKED | prompt does not authorize automatic production

## P0/P1

- P0: candidate not promoted to main; no approval to merge.
- P0: global historical asset and incident catalog is not fully reconciled.
- P0: independent rights evidence is not complete for a new episode.
- P1: visual QA needs human review of the final preview.
- P1: safe-zone validation on real platform UI is not evidenced.
- P1: Work orchestration state is unknown.

## Required promotion sequence

1. Run the candidate read-only workflow and inspect its artifacts.
2. Review the branch diff and regression output.
3. Obtain explicit human approval to merge.
4. Merge to main and run post-merge audit directly on main.
5. Only after that may a separately approved factual story enter production.

READY is forbidden while any P0/P1 remains open.
