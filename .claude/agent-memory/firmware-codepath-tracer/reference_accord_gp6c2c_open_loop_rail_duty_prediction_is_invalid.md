---
name: reference_accord_gp6c2c_open_loop_rail_duty_prediction_is_invalid
description: The V107 build session's open-loop rail-duty prediction method (push an existing |gp-0x6c2c| distribution through a gain ratio) is DEMONSTRATED WRONG by 32x -- predicted <=1.05% vs route 1e's measured 33.49% at 10-25km/h. Root cause identified by cross-team analysis (inherit-audit, from telemetry; hfmech, from code structure independently): gp-0x6b26 feeds the aggregator -> motor -> motor rate -> gp-0x6c2c, a closed loop, so |gp-0x6c2c|'s distribution is NOT invariant to K as the method assumed. The size of the miss (32x, not a modest correction) is consistent with genuine closed-loop self-excitation, plausibly via the gp-0x6b26 90-180deg sector-crossing above 74.5Hz (see the sibling memory) letting the term actively drive rather than just damp a resonance once dose crosses some threshold. Any future rail-duty prediction via this method on this signal should be treated as UNVERIFIED, direction-only, magnitude untrustworthy, until either a real closed-loop model or an on-car measurement exists.
metadata:
  type: reference
---

# `gp-0x6c2c`/`gp-0x6b26` rail-duty prediction — the open-loop push-through method is invalid, by measurement

2026-08-26, `hfmech` task, cross-referenced with `inherit-audit` (loop-gain-budget teammate, same
session). This is a methodological correction that applies to EVERY prior and future rail-duty estimate
built by "take a measured `|gp-0x6c2c|` distribution and scale it by a gain ratio" on this signal.

## The discrepancy [EVIDENCE, both halves independently sourced]
The V107 build session predicted rail duty `<=1.05%` everywhere by extrapolating route `77`'s (×1.0
dose) `|gp-0x6c2c|` distribution through a Y-ratio. `inherit-audit` decoded V107's own new 427 tap on
route `1e` (988.6s engaged, fault-free) and measured the REAL duty directly:
```
 km/h    predicted (open-loop push-through)   measured (route 1e, direct)
10-25         <=1.05%                              33.49%           <- 32x miss
25-40         <=1.05%                              20.77%
overall       <=1.05%                               9.69%
```
**A 32x miss is not method noise or a rounding error — it is a real signal that the method's core
assumption is false.**

## The root cause — closed loop, not open loop [EVIDENCE for the structure, BELIEF for the mechanism]
`inherit-audit`'s diagnosis, independently reachable from the code: `gp-0x6b26` is not an isolated
filter reading an EXTERNAL signal — it feeds the aggregator (`FUN_0003aa2c`) -> governor -> ... -> FOC
-> motor -> motor rate (`gp-0x4f50`) -> the EMA cascade -> `gp-0x6c2c`. **This is a closed loop.**
Pushing a `|gp-0x6c2c|` distribution MEASURED AT ONE DOSE through a gain ratio to predict its
distribution AT A DIFFERENT DOSE silently assumes the excitation reaching the cascade doesn't itself
depend on the dose — false for a term that is part of the loop generating its own input.

**Independently, from the code side** (this session, see
[[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]]): `gp-0x6b26`'s own torque phasor
crosses from the proven-safe 180-270° sector into 90-180° (the ONE sector capable of raising/sustaining
a resonance) at 74.5Hz on today's design, and a mere ~0.04° column wobble at 100Hz is enough to
saturate the ±511 clamp. **These two facts together are consistent with genuine closed-loop
self-excitation**: above ~74Hz the term can structurally DRIVE an oscillation rather than merely
respond to one, and once railed its own harmonic-rich relay output would feed straight back into the
same loop. A 32x undercount is the right ORDER of miss for a self-sustaining mechanism the open-loop
method cannot see at all (a linear scaling error would typically be within a small factor, not 32x).
**Labeled BELIEF — not provable from static analysis alone, but the code structurally supports it and
the size of the discrepancy is the kind of signature this mechanism would leave.**

## Consequence — every future duty NUMBER on this signal needs this caveat
Any `|gp-0x6c2c|`-percentile-based duty prediction for a NEW candidate (a Y-table reshape, an α2 move,
anything touching `gp-0x6b26`'s gain) inherits the SAME invalid assumption unless it is built from a
real closed-loop model or validated on-car. **Direction (a gain cut very likely reduces duty) is well
supported; magnitude is not — treat "duty falls to X%" claims built this way as UNVERIFIED until flown
or modeled closed-loop.** A candidate operating below whatever gain threshold sustains a self-excited
cycle could see duty collapse far more than a linear ratio predicts (an upside case); one still above
threshold could see little improvement despite a large open-loop gain cut (a downside case the ratio
method cannot distinguish from the upside one).

## Related
[[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]] (the sector-crossing this connects
to), [[reference_accord_gp6b26_alpha0_shared_alpha2_isolated_bandlimit_sweep]] (the α2 lever whose own
duty prediction carries this exact caveat), [[reference_accord_gp6c2c_real_distribution_overflow_wall_not_binding]]
(the earlier V106-era duty-prediction work this corrects — that work's own FFT-reconstruction method was
methodologically careful but shares the same open-loop assumption at its foundation).
