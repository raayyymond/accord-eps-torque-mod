---
name: reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists
description: Fresh full disassembly of FUN_0003aa2c pins the exact instruction addresses for r24 and r26's derivative-to-aggregator path. r24 has ZERO state cells / EMA / lag anywhere between gp-0x4f62 (the shared 4-tap difference, clamped once into r1) and its clamp into the aggregator sum. r26 has exactly ONE averaging structure in the whole function -- a 2-tap boxcar (gp-0x3670 flag / gp-0x3672 prior value, shr 0x1, hardcoded) applied to its GAIN term gp-0x69a4 ("a"), NOT to the differentiated signal -- and it is Nyquist-scale (first null at 500Hz, |H(7.79Hz)|=0.9997) and not cal-adjustable. Unlike 0xC6450/0xC644A (existing disabled EMA poles at Q-unity Honda parked elsewhere in the chain), NO such disabled filter exists on r24/r26's own path -- inserting one is a cave edit, not a cal edit.
metadata:
  type: reference
---

# r24/r26 full pole census, address-exact (2026-08-09, `lever-hf` session, team-lead's structural-half brief)

[EVIDENCE, fresh `disassemble_function(0x3aa2c)`, code.bin stock, full body] Corroborates and extends
3 independent prior sessions' decompiles ([[reference_accord_r24_gainb_table_structure_and_priority_gate]],
[[reference_accord_lever_a_gate_structure_and_cal_double_equivalence]],
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]]) — all agree byte-for-byte; this session's
contribution is the byte-exact instruction table below plus the r26 boxcar mechanism, which prior sessions
named ("averaged gp-0x69a4") but had not disassembled to the instruction level.

## The shared input: `gp-0x4f62` clamped once into `r1`, untouched thereafter

```
0x3aa9c  ld.h -0x4f62,gp,r14        ; load the 4-tap backward difference (producer FUN_0007e74a, N=0xC6C42=4)
0x3aaa0-0x3aac0  clamp r14 to +-0x1400 (5120) -> r1     ; the ONLY processing gp-0x4f62 gets before r24/r26
```
`r1` is the exact value both lanes multiply. No smoothing of any kind touches it.

## r24 — zero state cells, confirmed exhaustively

```
0x3ab98  ld.bu -0x671d,gp,r6                 ; gate 1
0x3abac-3abf8  mode-indexed LERP over rate (instantaneous function, no history) -> r10 (curve-A default)
0x3abfa-3ac16  4-way priority mux: gp-0x671d!=0 -> cal(0xC6442) | lp!=0 -> cal(0xC6446) |
               r2==0 -> cal(0xC6440) | else -> r10 (curve-A)
0x3ac18  mul r10,r8,r0            ; r8 = r1 (the clamped derivative, from register copy at 0x3ac16)
0x3ac1c  ld.hu 0x71f6,tp,r12      ; cal 0xC61F6 = 3, DEADBAND
0x3ac20  sar 0xa,r8                ; Q10 shift
0x3ac22-3c  symmetric soft deadband: y = 0 if |x|<=D else sign(x)*(|x|-D), D=cal(0xC61F6)
0x3ac3e  mul r14,r6,r0            ; x polarity(gp-0x6752)
0x3ac42-58  clamp +-0x2000 -> r24
```
**No `ld`/`st` to any persistent state cell appears anywhere in this sequence.** The mode-LERP
(`0x3abac-3abf8`) is a pure function of the current rate sample (`gp-0x6ac0`/`gp-0x6e40` etc.), re-evaluated
from scratch every tick — not a filter, a memoryless nonlinear gain schedule.

## r26 — exactly ONE averaging structure, on the GAIN not the SIGNAL

```
0x3ab36  ld.bu -0x3670,gp,r15      ; init-once flag byte           <- STATE CELL #1
0x3ab3a  ld.hu -0x69a4,gp,r6       ; "a", this cycle's gain-schedule value
0x3ab3e-44  if r15==0: r15=1, r10=r6                 [first tick: no history]
            else: r10 = ld.hu -0x3672,gp              <- STATE CELL #2, PRIOR CYCLE'S "a"
0x3ab4e  st.h r6,-0x3672,gp        ; store current "a" for next cycle -- the z^-1
0x3ab52  add r10,r6
0x3ab54  shr 0x1,r6                ; r6 = (a[n]+a[n-1])/2  <<< THE ONLY AVERAGING ON EITHER LANE
0x3ab58  st.b r15,-0x3670,gp
0x3ab56/5e/64/68  gate mux (lp / r2) -> gain cal 0xC6444 or 0xC643E -> r8
0x3ab6c  mul r1,r6,r0             ; r1 (SAME clamped derivative as r24) x SMOOTHED gain r6
0x3ab70  sar 0xa,r6
0x3ab72  mul r8,r6,r0             ; x gain cal
0x3ab76  sar 0xa,r6                -> r26 (Lever A's r26 site, per prior memory)
```
This 2-tap boxcar averages `gp-0x69a4` ("a", r26's relative-weight gain schedule) — **it does NOT touch
`r1`, the differentiated signal itself.** It is architecturally fixed (`shr 0x1`, no cal controls the tap
count or coefficient) — not an editable lever regardless of interest.

**Frequency response, computed** (`H(z)=(1+z^-1)/2`, fs=1000Hz):
```
|H(7.79 Hz)|  = 0.999701   (-0.003 dB)
|H(21.09 Hz)| = 0.997806   (-0.019 dB)
first null at fs/2 = 500 Hz
```
Functionally irrelevant to the 7-25 Hz symptom band — a compiler/design-grade smoothing artifact on a
slowly-varying scheduling parameter, not a usable damping lever.

## Verdict: no disabled filter exists on r24/r26, unlike downstream in FUN_0003a382

`0xC6450`/`0xC644A` ([[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] and
[[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole]]) are EXISTING EMA structures
Honda parked at Q10 unity elsewhere in the PID chain — a single cal edit reactivates real first-order
structure, no code risk. **Nothing equivalent exists on r24/r26's own path.** Adding a pole here (on
`gp-0x4f62` before the multiply, or on r1) requires new instructions — cave-class, GATE-1 (new RAM state
cell; none of the catalogued free taps `gp-0x6ada`/`gp-0x6adc`/`gp-0x6c00` sit in this instruction stream)
and GATE-2 (phase-margin risk near the ratchet's own band if it participates in the closed loop) both
apply, plus `FUN_00043e44`'s twin — which does NOT read `gp-0x4f62`/`gp-0x6ada`/`gp-0x6adc` directly
(confirmed against the full decompile in [[reference_accord_c64c8_float_twin_mode_mirror_and_mode2_noop]])
but WOULD see the effect indirectly via `gp-0x6acc`/`gp-0x6b98`, inheriting the spine's ~10ms/±5-count
tolerance budget.

## Cheapest cal-only alternative — weak, quantified

Raising `0xC6C42` (N, the difference window) 4→7 is cal-only, GATE-1 vacuous:
```
phase(f) = 90 - 180*N*f/fs   [deg]
7.79 Hz: N=4 -> +84.39deg   N=7 -> +80.18deg   delta = -4.21deg
20 Hz:   N=4 -> +75.60deg   N=7 -> +64.80deg   delta = -10.80deg
```
An order of magnitude too small to matter against a loop with PM≈100*zeta≈1.7-3.6deg (per the ratchet's
measured ring-down zeta=0.017-0.036) if the pole sits nearby — safe, but not a fix.

## The deadband direction, computed

```
D = cal(0xC61F6) = 3.  V65 measured |dtorque| in [123,839] over 120,049 frames -> D is 0.4-2.4% of
typical excursion, confirmed inert today.
For a fixed underlying torque amplitude, N=4 diff gives dtorque(f) ~ f (ideal-derivative scaling):
dtorque(18.5Hz)/dtorque(1.5Hz) = 12.33x
```
**A fixed-count deadband clips LF-sourced derivative content FIRST (it's ~12x smaller for equal torque
amplitude), not HF-sourced content** — raising `0xC61F6` is backward for the ratchet, confirmed
arithmetically. Moot for the operator's <3Hz-preservation constraint specifically, since r24 itself barely
carries 0.5-3Hz content by the same |H(f)|~f scaling (|H(18Hz)|/|H(1Hz)| = 17.85x, computed exact).

🛑 **CORRECTION, 2026-08-22 (`deadband` session, team-lead-approved edit)** — the "0.4-2.4%" figure above
compares `D` against the PRE-GAIN `dtorque` ([123,839]) directly. That is the WRONG reference frame: the
deadband is applied to `scaled = (dtorque * gain_q10) >> 10` (confirmed by a fresh `decompile_function
(0x3aa2c)` this session, matching the golden model's `_inline_torque_rate_b` exactly), i.e. the POST-GAIN
quantity, not `dtorque` itself. At the CURRENT engaged gain (`0xC6446` = 5244, carried unchanged into
V104/V105): `scaled` ranges **629-4296** over the same V65-measured input range, so the correct fraction is
**D is 0.070%-0.48% of typical excursion** — about **5x smaller** than this file originally stated (the
5.12x gap being exactly `gain_q10/1024`). The qualitative verdict ("confirmed inert", "raising 0xC61F6 is
backward") is UNCHANGED and if anything strengthened; only the magnitude of the fraction moves. See
[[reference_accord_c61f6_deadband_is_coulomb_friction_not_percentage]] for the full re-derivation, the
first-hand decompile confirmation, and the follow-on finding (any dose large enough to matter is a
Coulomb-friction tax disqualified by the operator's rate-authority constraint) that closed this candidate.

## Related
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] — the N=4 window's own transfer function,
this file's phase numbers reproduce it exactly.
[[reference_accord_lever_a_gate_structure_and_cal_double_equivalence]] — the sar-site gate independence
this file's addresses match exactly (0x3ab76 r26 / 0x3ac20 r24).
[[reference_accord_c64c8_float_twin_mode_mirror_and_mode2_noop]] — the float-twin cross-check for any
cave-class edit on this path.
