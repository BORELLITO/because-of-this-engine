# Editorial story standard v7.4

The v7.4 editorial layer is a mandatory pre-render contract for every new
Because Of This episode. It exists because a technically valid sequence of
clips can still be a weak story.

## Release rule

A story cannot enter visual research or rendering unless:

- the protagonist makes an active, irreversible choice;
- the protagonist's wound appears as behavior in the present story and changes
  that choice;
- every escalation link records a trigger, protagonist action, new cost and
  state change;
- the anomaly or investigative mechanism has a rule, a violation and a price;
- the emotional arc contains at least three caused state changes;
- the ending resolves the central question and recontextualizes the opening;
- every scene has a visual action, observable evidence and subjective stakes;
- the story has 8–14 meaningful beats, 12–24 visual shots, no repeated visuals,
  and no more than one second of padding;
- the core mechanism and its distinctive inversion are compared against at
  least three adjacent references;
- narration has no generic or orphan lines and has line-level evidence of
  action, consequence and human stakes.

## Contract location

The required contract lives at:

`manifest.story_creation.editorial_contract`

Its executable audit is:

`production/editorial_story_gates.py`

The existing C0–C11 creation gates remain active. The new E0–E10 gates are
additive and fail closed. A story must pass both groups.

## Beat density

The engine distinguishes dramatic beats from visual shots:

- meaningful beats carry a decision, discovery, reversal, cost or consequence;
- visual shots may support one meaningful beat, but cannot create fake progress;
- micro-beats are limited to six and must remain subordinate to the causal chain.

This prevents the previous failure mode in which eighteen small anomalies looked
like eighteen story events.

## Legacy material

Old manifests without `editorial_contract` remain available for audit and
history, but they are not current production sources. They are blocked by E0
and must be rewritten against the v7.4 contract before reuse.
