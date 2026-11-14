# BECAUSE OF THIS — Immutable Core Protocol

Status: active.

## Default rule

Approved decisions are preserved. The engine must not silently replace, reorder or regenerate approved clips; move or resize the logo; move, restyle or re-time captions; switch voice provider/model; activate a historical runtime; publish; upload; spend money; or treat metadata as human approval.

Any drift is a blocking condition.

## Global engine lock

The global contract is production/immutable_core_policy_v1.json. The guard verifies authority-file identities, active runtime, Gemini/Charon, no fallback, 1080x1920 at 60 FPS, logo geometry y=190/width=360, caption margin_v=650, active word color #F04444 and the V2.1 preview baseline.

## Episode surface lock

When an episode reaches approved_for_render, it must have episodes/<episode-id>/approved-surface-lock.json. That file records exact shot assignments, clip hashes, logo geometry and caption geometry. Any mismatch blocks rendering.

## Authorized change process

An ordinary request such as “melhore”, “faça upgrade” or “deixe mais profissional” does not authorize changes to this core.

A core change requires a separate branch, a Pull Request to main, the marker AUTHORIZED-IMMUTABLE-CORE-UPDATE in the PR title, an exact scope description, passing checks and Borelli's explicit approval before merge.

Recommended authorization wording:

AUTORIZO ATUALIZAR A TRAVA IMUTÁVEL: <escopo exato>. PRESERVAR TODO O RESTANTE.

This updates only the named scope.

## Operational rule

Before preview or production: read the active policy, read the immutable-core policy, run the guard and read the episode surface lock when present. If blocked, stop and report the exact drift. Never repair drift by changing the lock automatically.

## GitHub requirement

Protect main manually with required Pull Requests, required immutable-core checks, disabled direct pushes, disabled force pushes and disabled branch deletion. The connected integration can inspect files, create branches and prepare Pull Requests, but lacks repository-administration permission to guarantee these settings automatically.

Rollback means closing the Pull Request or reverting its commit. Never delete history.
