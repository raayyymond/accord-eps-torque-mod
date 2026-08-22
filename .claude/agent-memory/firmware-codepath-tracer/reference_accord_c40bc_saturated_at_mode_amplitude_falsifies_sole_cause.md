---
name: reference_accord_c40bc_saturated_at_mode_amplitude_falsifies_sole_cause
description: At the 21-28Hz mode's own measured rate amplitude (15-40+ deg/s), 0xC40BC's Coulomb ramp (current cal=300, knee=5.31deg/s) is DEEPLY SATURATED (B/delta = 2.8-7.5x) -- FALSIFIES "0xC40BC explains the mode's specific rise-then-collapse rate profile" as a sole/primary cause, since a saturated relay's magnitude is ~flat across that whole range and cannot itself produce the observed collapse above 100deg/s.
metadata:
  type: reference
---

# `0xC40BC` reconciled against the 21-28Hz mode's own rate profile — FALSIFIED as sole cause, 2026-08-22

`dynamics-designer` task (V106 candidate B). Extends
[[reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness]] and
`reference_accord_k1_friction_dose_and_clamp_relay.md` (analysis-2020accord tracer memory, biased-DF
table) — does not re-derive the arithmetic, applies it to a new question.

## Current on-car state [EVIDENCE — fresh Python LE byte read, stock through V105]
`0xC40BC` = 300 on V100 through V105 (stock 600, moved by V99), frozen 6 sampled builds. δ = cal/12/4.7121
°/s = **5.31°/s** at the current dose (was 10.61°/s stock).

## The reconciliation [EVIDENCE, arithmetic from the cited memory's own biased-DF table]
`ratio = clamp(pol·gp-0x6abc·12/cal, ±1)` — a saturating ramp, linear inside ±δ, pinned at ±1 (pure
Coulomb magnitude) outside. The cited memory's own table: B/δ ≈ 4.56 (p90=228 vs δ=50, OLD 600-cal
regime) was already called **"FULLY SATURATED, ring sees ~zero incremental gain."**

The 21-28Hz mode's own measured rate (V104 6×, 15-40°/s band, median 20.79°/s, per the team-lead's
brief) gives, at the CURRENT δ=5.31°/s: **B/δ ≈ 2.8-7.5×** — deeper into or comparable to the memory's
own "fully saturated" threshold.

## 🛑 VERDICT — FALSIFIES "0xC40BC's ramp explains the mode's rate-dependence," stated plainly per
the team-lead's own instruction to do so if the evidence falsifies it
A saturated relay's magnitude is **flat** (near-zero incremental/marginal gain w.r.t. rate) once B/δ≫1
— it does not itself produce a further rise, and critically does NOT produce the observed COLLAPSE
above ~100°/s (a saturated element's output stays roughly constant from 40°/s to 100°/s+, it has no
mechanism to independently fall off at very high rates). ⇒ `0xC40BC`'s specific knee position is NOT
the primary driver of the mode's measured non-monotonic (rise-then-collapse) rate profile. It MAY
still generically contribute to the mode being amplitude-*bounded* at all (any saturating nonlinearity
in the loop does that, non-uniquely — same caveat applies to gp-0x6b26's own clamp, see
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]]), and it may matter
more at the 6-9Hz ratchet band where operating amplitudes sit closer to δ (per the cited memory's own
"600 beat 6000 by 2.3x on 6-9Hz" flown-but-confounded comparison).

## GATE 2 caveat, inherited not re-derived
The cited memory's own verdict stands: `FRICTION → model → gp-0x6bfc → resid → gp-0x6b70` is Path 2,
whose loop gain is runtime gain-scheduled — NOT statically closable. Any margin-in-dB figure for a
`0xC40BC` move is an invention without a live measurement.

## Consequence for V106
NOT RECOMMENDED as a 21-28Hz lever. Already at/past its useful saturation point for that band; further
moves (either direction) are predicted to have little effect there specifically.

## Related
[[reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness]],
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]] (sibling saturating
element in the same loop, same session).
