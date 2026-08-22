---
name: reference_accord_gp6b26_acceleration_authority_vs_hard_steering
description: Operator constraint check -- does raising gp-0x6b26 (an acceleration-opposing term) cost him "high angular acceleration under high steering force/velocity"? Team-lead's hypothesis (both K saturate identically during hard steering, so the raise is free) holds only for extreme sub-100ms onset ramps (simulated against the validated 1kHz recurrence). But REAL telemetry (V104/ra4) shows the better reason it's likely safe: genuine high-|rate_c| frames have LOWER reconstructed |gp-0x6c2c| than the corpus overall and essentially never approach either K's clamp -- the rare high-acceleration events that do clip are not coincident with hard sustained steering, consistent with coming from the target oscillation instead.
metadata:
  type: reference
---

# Does raising `gp-0x6b26` cost the operator's "support high angular acceleration" constraint?

2026-08-22, `dynamics-designer` task. Operator stated: *"I also want to support high angular
accelerations with LKAS commanded torque on top of high steering wheel force and velocity."* Since
`gp-0x6b26 = -K·accel` ([[accord-gp6b26-is-inertia-not-damping]]), raising K directly opposes this.
Team-lead proposed the ±511 clamp already saturates identically at both K during hard steering, making
the raise free at the high end. Checked rather than accepted.

## Team-lead's hypothesis, corrected [EVIDENCE, simulated against the validated 1kHz recurrence]
The clamp knee tracks **acceleration (ramp steepness)**, not peak rate — a sustained high rate produces
near-zero acceleration once settled (`H(0)=0` exactly). Simulating rate ramps (0→peak over a realistic
onset duration) through the exact integer recurrence:
```
x1.5 (current) clamps at ~6,000-6,700 deg/s^2 sustained ramp acceleration
x3.0 (proposed) clamps at ~3,000-3,500 deg/s^2 (roughly half, Y doubles)
```
At REALISTIC hard-fast onsets (200-400°/s reached over 150-300ms): mostly UNCLAMPED at both K, and
×3.0 delivers close to 2× more opposition than ×1.5 in this range. **The hypothesis (both already
saturated, raise is free) holds only for extreme sub-100ms onsets — a wheel-slap, not typical hard
steering.** 511 counts = **4.99% of the aggregate ±10,240 clamp** even fully saturated.

## The real answer — telemetry, not synthetic ramps [EVIDENCE, V104/`ra4`, FFT-validated reconstruction
from [[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]]]
Unconditional (all in-burst frames): raise increases opposition across ~99.9% of the range (90.03%
get exactly 2×, 9.88% get a partial 1-2× increase, only 0.09% already-equal at the shared ceiling) —
taken alone this looks like real cost everywhere.

**But conditioned on genuinely high real `|rate_c|` (the direct empirical proxy for "hard fast
steering"), the picture flips:**
```
|rate_c|>=100 deg/s (7.07% of corpus): p50=82 p90=218 p99=412 max=532  -- 99.88% NEITHER K clamps
|rate_c|>=150 deg/s (4.51% of corpus): p50=72 p90=186 p99=397 max=532  -- 100% NEITHER K clamps
|rate_c|>=200 deg/s (1.56% of corpus): p50=77 p90=202 p99=416 max=452  -- 100% NEITHER K clamps
```
Reconstructed acceleration content is SMALLER during genuine fast steering than in the corpus overall
(p99 drops 1704→397-416). Physically sensible: sustained fast rate has settled past its onset, so
acceleration is low; the rare high-`gp-0x6c2c` events that DO occasionally clip are NOT coincident
with hard steering — consistent with coming from the TARGET OSCILLATION instead (this cascade's gain
is 7-9× higher at 21-28Hz / 6-9Hz than near DC, so a modest ripple produces disproportionate
acceleration content with no large steering input underneath it).

## Verdict [mixed EVIDENCE/BELIEF, one drive's corpus]
The raise's cost lands predominantly on the oscillation, not on the operator's deliberate hard/fast
inputs — empirically, in this corpus. Cannot rule out a more extreme real-world input not sampled here
(a genuine emergency flick). Recommend the on-car `gp-0x6b26`+sign channel confirm this directly rather
than resting on this analysis alone.

## Grind #2 (44.9Hz) connection [BELIEF, no direct measurement — CAN427 is blind above ~25Hz]
This cascade's gain is HIGHER at 44.9Hz than at grind #1's 21-28Hz (|H(45Hz)|≈11.6 vs |H(21.9Hz)|≈7.5)
— if grind #2 has real acceleration-domain content, this term is well-positioned to reach it. A hard
turn's own acceleration concentrates in the brief onset (sub-second); grind #2's ripple, if present,
rides throughout the sustained portion. During onset the two could compete for the same clamped budget
(capped either way at the shared 511 ceiling — cannot be hurt beyond it). During the sustained portion,
the onset's contribution settles near zero and the term is free to respond to grind #2 alone, likely
within its linear range by the same reasoning as above — not measured, flagged as BELIEF.

## Related
[[accord-gp6b26-is-inertia-not-damping]] (project memory, the H(0)=0 acceleration-term identity this
whole analysis depends on), [[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]]
(the validated reconstruction method and dataset this reuses),
[[reference_accord_gp6b26_v106_transfer_function_correction_and_disqualification]] (the build this
gates).
