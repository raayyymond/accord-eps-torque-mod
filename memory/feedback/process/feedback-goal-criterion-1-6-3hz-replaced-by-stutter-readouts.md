---
name: feedback-goal-criterion-1-6-3hz-replaced-by-stutter-readouts
description: "RULING 2026-10-02: the goal's 'hard-turn 1.6–3 Hz wheel-rate energy ≤ V282' criterion is REPLACED by the stutter readouts (stall-surges/min, ratchet trains/min of turning, 4–8 Hz wheel-rate modulation, dwells/min, each ≤ V282; no surge enrichment near a hand-torque threshold crossing) — a fast slew is itself 1.6–3 Hz content, so the old criterion penalised authority by construction"
metadata:
  type: feedback
---

**Ruling (operator, 2026-10-02, "Your recommendation for the criterion replacements makes sense to me"):** drop the
1.6–3 Hz hard-turn energy criterion from THE GOAL; score stutter with the panel's direct readouts instead.

**Why:** route 79 read 8.5 deg/s vs V282's 3.5–4.0 on that band, yet every authority design (the operator's note 2)
worsens it by construction (config A ×1.35, the deferred authority dose ×3): a 60° turn-in in 0.5 s *is* 1.6–3 Hz
content. The readouts that actually measured the ratchet on route 79 are stall-surges per minute, ratchet trains per
minute of turning, the 4–8 Hz wheel-rate modulation, dwells per minute, and the enrichment of surges within ±0.25 s
of a 300/512 (now 1229) crossing.

**How to apply:** THE GOAL box in `docs/STATE.md` carries the replacement; drive cards and the drive read score the
readouts, with V282 (r6c/r39) as the reference and the crossing-enrichment test as the mechanism check.
Related: [[accord-v298-flew-route79-loop-live-freeze-and-o1-fire-on-reaction-twist]].
