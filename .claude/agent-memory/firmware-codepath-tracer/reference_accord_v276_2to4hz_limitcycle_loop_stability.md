---
name: reference_accord_v276_2to4hz_limitcycle_loop_stability
description: V276's two edited cells (0xC9A88 assist map x6, 0xC62E6 feedback clamp x6) are BOTH inside the LKAS rate-PID error junction at FUN_00028ea6, but neither is a classical loop-gain cell -- Kp/Kd/plant gain/torque cap are all frozen byte-identical. The mechanism for the operator's reported 2-4Hz self-excited limit cycle (engaged-only, killed by driver grip) is loss of negative feedback via near-permanent P/D saturation, not a small-signal gain-margin shift. The loop's own two firmware IIR poles (fc~5.0Hz, fc~16.5Hz) supply only ~28-52 deg of phase at 2-4Hz -- nowhere near -180 -- so the oscillation frequency is set by unmodeled MECHANICAL PLANT dynamics, not firmware filters.
metadata:
  type: reference
---

Traced 2026-09-01, GhidraMCP fresh disassembly (positive-controlled) + the V276 build script's own
ground-truth arithmetic (`analysis-2020accord/builds/v108_plus/build_v276_tva.py`), for `main`'s
"why does V276 oscillate at 2-4Hz" question. Extends [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]].

## Loop sample rate: 1 kHz, EVIDENCE (not re-derived fresh here, cited from a prior trace and cross-checked)

`docs/traces/TRACE-2026-08-20-loop-lag-map.md`: **`FUN_0002214a` (the caller of `FUN_00028ea6`) = 1 kHz**,
confirmed on-car via STEER_STATUS=4 dwell; an earlier OSTM0-based belief is explicitly REFUTED there.
The state-mask bits gating sub-blocks inside `FUN_0002214a` (`uVar2 = 1<<(gp-0x67fa & 0xf)`, masks like
`0x930`) do **NOT** divide the call rate -- `reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz.md`
(prior session) established every gated block fires every 1kHz tick. I independently cross-checked the
"5 Hz output LPF" comment in the V276 build script against this rate (see below) and it lands within
0.1Hz -- corroborating, not just trusting, the 1kHz figure.

## Both V276 cells sit AT the error junction, on opposite operands -- but neither is a "loop gain" cell

`E = 32*setpoint - feedback_lag_output` (0x29d78, `sub r26,r16`). Ground truth from the build script
(which reads/asserts these bytes on the actual image, not from a docstring):

- **`0xC9A88`** (28-record assist-map bank) sets the **minuend** -- `setpoint = LERP_variant(|driver
  demand|)`, scaled Y-only x6, X (index) axis untouched, ALL 28 records scaled uniformly (sidesteps the
  variant-selector dead-slot question -- doesn't matter which of the 28 is live). This is a REFERENCE /
  FEEDFORWARD scale, not a loop-gain multiplier -- it does not multiply the error itself.
- **`0xC62E6`** (`tp+0x72E6`) is the **saturation clamp on the feedback lag's output** (state `gp-0x3d30`,
  the first-order lag of measured column rate `gp-0x6a56`), 7680 -> 46080. A clamp bounds the subtrahend;
  it is not a gain either.
- **Kp, Kd, the plant/forward gain `0xC6CD0`=5346, and the torque cap `0xC61B4`=3072 are ALL FROZEN**
  byte-identical V268->V276 (asserted in the build script and independently confirmed by
  `bytes(code[0x28EA6:0x2A30D]) == bytes(base[...])` -- the whole function body is byte-identical, only
  cal DATA changed). ⇒ **there is no single "open-loop gain x N" number for this build** in the classical
  small-signal sense -- I want to say this plainly rather than force a number the mechanism doesn't have.

## The real mechanism: V276 expands the region where the loop has NO negative feedback

The V276 build script's own flown-data arithmetic (182,248 engaged frames, routes r66/r67/r68/r6d,
`|cmd|>=80% rail`) is the load-bearing evidence:
```
  median achieved column rate                 27 deg/s
  56.3% of high-command frames EXCEED the CURRENT (V268) reference ceiling (~22.3 deg/s)
  43.4% of high-command frames EXCEED the CURRENT (V268) feedback clamp     (~31.1 deg/s)
```
So **on V268 already**, in high-command driving, actual wheel rate frequently exceeds both the setpoint
target AND the feedback clamp -- meaning V268 is ALREADY partly blind to overshoot 43% of the time in
that regime, yet (per the record) is not reported to limit-cycle. V276 scales setpoint AND feedback
clamp by the SAME factor (6x), preserving Honda's setpoint:feedback ratio EXACTLY (1.395, asserted) --
but it does **NOT** scale the torque cap or forward gain, which are frozen. Consequence: **the crossover
rate at which error can go negative (loop starts damping/correcting instead of pushing) moves from
~23 deg/s (V268) to ~137 deg/s (V276)** -- a rate the plant, with UNCHANGED max torque, essentially never
reaches. ⇒ **the loop's own negative-feedback (damping) branch becomes practically unreachable across the
whole realistic driving envelope**, not merely reduced. The build script's own assertion corroborates
this from the arithmetic side: **P reaches its clamp (`0xC61BC`=15360) in ALL 28 slots at full demand**,
vs 97.4% for V268 -- i.e. the P term is pushed to near-permanent saturation, converting a proportional
controller into something close to a sign(error) relay. D likely saturates similarly or more (per
[[reference_accord_d_term_is_on_error_and_already_saturates]]-class finding, Kd unchanged but error swings
are now 6x bigger). **A saturated (relay-like) controller with the sign staying pinned in one direction
across most of its operating envelope, driving an underdamped mechanical plant, is the textbook route to
a self-sustaining limit cycle** that only stops when external damping (the driver's grip) is added --
which matches the operator's report point for point (engaged-only, self-exciting, killed by firm grip,
returns on release).

## The 2-4Hz frequency itself is NOT explained by this loop's own firmware filters

Fresh `disassemble_bytes(0x2a170,80)` on `code.bin`, GhidraMCP, matches the memory's prior structural
read exactly (positive control): two first-order IIRs sit in this loop's forward/feedback paths, BOTH
FROZEN V268->V276 (asserted in the build script):
```
  feedback lag   gp-0x3d30   a=0xC63E8=923  pole=923/1024=0.9014   corner fc = 16.5 Hz  (at fs=1kHz)
  output  lag    gp-0x3d3c   a=0xC63EC=992  pole=992/1024=0.9688   corner fc =  5.05 Hz (at fs=1kHz)
```
(The 5.05Hz figure independently cross-checks the prior trace's own "0xC63EC/EE ... fc~4.97Hz" line to
within 0.1Hz -- two different sessions, two different derivations, same answer.) Phase contributed by
these two poles ALONE (Python, exact, `pole_H` model) plus the 1-sample/1kHz transport delay:
```
   f=2Hz  fb=-6.5   out=-21.2   delay=-0.7   sum=-28.5 deg
   f=3Hz  fb=-9.8   out=-30.2   delay=-1.1   sum=-41.0 deg
   f=4Hz  fb=-12.9  out=-37.6   delay=-1.4   sum=-52.0 deg
```
**That is 128-152 degrees short of the -180 deg needed for a linear-loop oscillation condition.**
⇒ **BELIEF, clearly flagged as such:** the 2-4Hz frequency itself must be set predominantly by
**unmodeled mechanical plant dynamics** (steering column inertia, torsion-bar compliance, rack/tire
friction and compliance) -- NOT by anything in this firmware loop's own filters. This kit has no
characterized 2-4Hz plant model on record (the existing loop-lag-map trace only characterizes 6-9Hz and
20-26Hz bands). A relay-driven lightly-damped mechanical resonance at 2-4Hz is physically plausible for
an EPS column/rack system but is NOT verified from firmware bytes -- it would need physical
system-identification data (a step/chirp response) to confirm, which is outside this kit's firmware
tracing method.

## CORRECTION to the brief: `0xC693E` and `0xC6384` are NOT in this loop

Both were named in the brief as "known cells to include." `search_instructions(function=FUN_00028ea6,
operand_pattern="0x793e")` and `"0x7384"` both return **0 matches** (positive-controlled: the same
scope/method against `"0x73ec"` correctly finds the one known hit at 0x2a184, so the null is
trustworthy). These two cals belong to a **different lane** (`FUN_0003aa2c`/`FUN_0003ad74`, the rate-lane
arm and base-assist damper, per [[reference_accord_rate_lane_gain_surface_found]]-class prior work) --
they do not sit on this rate-PID's forward or feedback path and should not be counted in this loop's
2-4Hz phase budget.

## The loop-delay-hypothesis-refuted memory does NOT transfer to this question

`docs/handoffs/2026-08/HANDOFF-2026-08-30-the-gain-ladder.md`: *"The loop-delay hypothesis is refuted by
its own control"* sits in the **6-9Hz ratchet / assist-map-path** investigation (a different symptom, a
different lane, a different frequency band) -- confirmed by reading the surrounding closure list in the
same handoff. It says nothing about `FUN_00028ea6`'s 2-4Hz behavior. This loop's OWN delay is the
1-sample/1kHz transport figure above (~0.7-1.4 deg at 2-4Hz), independently negligible and structural
(not editable) either way.

## Dose-response reasoning for a partial back-off (BELIEF, not measured)

Since the mechanism is a **threshold/coverage effect** (how much of the realistic operating envelope
falls inside vs. outside the loop's negative-feedback region), not a smooth small-signal margin, a
partial dose does not have a clean linear gain-margin number to quote. Rough crossover-rate estimates
(1.035 x scale x reference ceiling, using the kit's inherited-but-unclosed 8-counts/deg-s factor,
BELIEF): 1x(V268)=~23 deg/s, 2x=~46, 3x=~68, 6x(V276)=~137. Median achieved high-command rate today is
27 deg/s (EVIDENCE, V268 flown data) -- already close to/above the 1x and 2x crossovers, so **2x-3x would
likely still leave a meaningful fraction of ordinary driving with negative feedback available**, unlike
6x where the crossover (137 deg/s) is essentially unreachable. This is a plausibility argument for "back
off helps," not a computed gain-margin guarantee -- I would not fly a specific dose on this reasoning
alone without a telemetry readout of achieved-rate-vs-crossover duty cycle, which V276 already carries
for free (`gp-0x6a56` on CAN 0x18F @ 100Hz).

## Related
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] -- the full PID structure this extends.
[[reference-accord-op-0e4-steer-command-full-path]] -- the CAN 0x0E4 intake and downstream torque path.
