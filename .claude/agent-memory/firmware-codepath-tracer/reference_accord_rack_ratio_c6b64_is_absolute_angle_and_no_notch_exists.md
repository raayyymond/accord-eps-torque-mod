---
name: reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists
description: 🛑 CORRECTS [[reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles]]'s fatal "Problem 2" — gp-0x6a10 IS absolute steering angle, proven in assembly (the subtracted offset is HARD-CLAMPED to ±13.0° by cal 0xC633A=130 at 0x3fc36-0x3fc5a), not a free-running tracking error. Also refutes its "Problem 1" reach argument with flight data (full 1.2058× swing exercised, n=14,289 engaged frames). Double-method Python proof that NO symmetric flat-notch-flat rack-ratio table exists anywhere in [0xBF000,0xF0000). The 13-point LERP 0xC6B64-0xC6B98 IS a partial variable-ratio-rack compensation (~1/3 of the mechanical variation in log terms), applied to the DRIVER-TORQUE term of the plant model only. But it is FLAT (1.010×, 4.9% of swing) across 0-34°, the centre band where the operator reports worst grinding.
metadata:
  type: reference
---

# The variable-ratio rack question, settled structurally (2026-08-13)

Operator supplied a rack-stroke-ratio-vs-pinion-angle curve (flat high, narrow symmetric notch to
~0.55-0.60 at centre) and observed *"worst case grinding is generally when the steering angle is in
the center band."* Hypothesis under test: the plant model assumes a constant rack ratio, so a
disturbance observer converts the angle-dependent model error into a commanded correction.

## 1. `gp-0x6a10` IS ABSOLUTE ANGLE — the ±13° clamp [EVIDENCE, assembly]

Sole real writer `FUN_0003fc16` @ `0x3fca4`:
```
gp-0x6a10 = | gp-0x69ca − clamp(gp-0x69e0 + gp+0x641c, ±cal(0xC633A)) |
cal(0xC633A) = 130 counts = ±13.0°   (0.1°/count);  enable cal(0xC64A8) = 1
```
The clamp is at `0x3fc44`–`0x3fc5a` (`subr r0,r14` / `subr r0,r15` are the negates), then
`jarl 0x49a5a` = `abs()`, `jarl 0x49a78` = saturate-to-0xFFFF.

🛑 **This kills "Problem 2 — wrong variable, judged fatal" in
[[reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles]].** A correction bounded to
±13° cannot make the signal a tracking error. `builds/v80_v107/build_v86_tva.py:141` reached the same conclusion
independently from DATA (99.94 % match to `|angle| ≥ 0.85°`); this is the instruction-stream proof.
**Both cal cells byte-identical across all 96 images.**

## 2. NO symmetric notch table exists — double method [EVIDENCE, Python ×2]

Over `[0xBF000,0xF0000)`, offset == absolute address, LE:
- **Record-format scan** (`[n:u16][X n×s16][Y n×s16]`): 2,089 valid records → requiring a TRUE
  interior V (descend AND ascend, both flanks ≥10 % of max) leaves **4 shapes**, none a rack curve
  (`0xC68B4`/`0xC6870` bipolar; `0xC63D0` collapses to 3 %; `0xC528C` ends 30 % ABOVE its flat).
- **Format-free sliding window** (no layout assumption): 24 hits, **every one a pure STEP DOWN**
  (`[87,87,87,70,70,70,70]`, `[122,…,100,…]`) — no rising flank.

⚠ My first V-scorer had a false-positive class: it picked index `n−2` as an "interior minimum" on
monotone-decreasing-then-flat arrays. **Require a real ascending flank, not just a non-terminal min.**

## 3. What DOES exist: `0xC6B64`–`0xC6B98`, absolute-angle indexed

```
count 13 @0xC6B64
X (0.1°/ct):  0  340  640  850 1000 1200 1400 1576 1736 1916 2084 2280 4776
     degrees: 0 34.0 64.0 85.0 100  120  140 157.6 173.6 191.6 208.4 228 477.6
Y (Q10):    899  908  981 1060 1083 1084 1084 1084 1084 1084 1084 1084 1084
```
Total swing **1.2058×**. **94.6 % of it sits in 34–100°; only 4.9 % (1.0100×, 0.029 %/°) in 0–34°.**
Above `gp-0x6a10 ≥ 0x2711` (1000.1°) the gain is forced to 1024. Virgin: byte-identical in all 96
images; `builds/v80_v107/build_v86_tva.py` names it only to reject it.

vs the supplied rack curve (~1.67–1.82× flat/notch, BELIEF — not digitised): the firmware
compensates **31–37 % of the mechanical ratio variation in log terms.**

## 4. WHERE it is applied — the structural crux [EVIDENCE, `0x3ba7e`–`0x3ba8a`]

```
MODEL_pre = EMA²(motor_cmd) + (angle_gain(|steer|)/1024) × clamp(FIR(EMA²(gp-0x4f60)), ±15)
gp-0x6bfc = clamp(0xC6468 × (MODEL_pre − friction − inertia), ±20000) → gp-0x6bfe → FUN_00038148
```
**The angle gain multiplies ONLY the driver-torque term, never the motor-command term.** The
driver-torque→rack-load conversion is exactly what a rack ratio governs ⇒ structurally this is a
rack-ratio compensation in the right place. [Structure EVIDENCE; the rack-ratio reading is BELIEF.]

## 5. Reach REFUTED, but the centre band does not fit

🛑 **`cs_eng` is all-zero on r80/r81 — it is the WRONG engagement key and produced a false kill**
(r82-only, max 16.9°, swing 1.0044×). Use **`cc_lat` (latActive) ≥ 0.5**; r81 → 6,591 frames,
matching [[accord-v98-comparator-ranked-the-observer-arms]] exactly.

| route | eng | p50 | p90 | max | swing |
|---|---|---|---|---|---|
| r80 | 1,719 | 10.3° | 37.1° | 55.1° | 1.032× |
| r81 | 6,591 | 34.2° | 217.2° | 346.2° | 1.206× |
| r82 | 5,979 | 10.9° | 77.1° | 379.7° | 1.206× |

Pooled n=14,289 ⇒ **the full swing IS exercised**, refuting "Problem 1"'s 0–45° reach argument.
**But the table is FLAT across 0–34°**, the band the operator names — a flat gain cannot produce an
angle-dependent error gradient there.

## 6. The SIGN — RESOLVED to EVIDENCE (2026-08-13, same session)

`FUN_00038148`: `iVar5 = (short)*(gp-0x6bfe) − (iVar4 >> 4)` — MODEL and ACTUAL differenced with
**coefficients exactly ±1, no scaling**. ⭐ And **both arms carry the SAME output-scale cal
`0xC6468`**: `0x3b94a ld.hu 0x7468,tp,r2` (MODEL, `FUN_0003b8f6`) and `0x381f2 ld.hu 0x7468,tp,r16`
(ACTUAL, `FUN_00038148`) — only 5 reads of `0xC6468` exist image-wide. `gp-0x374c`'s lanes are
aggregator/motor-command domain ⇒ **MODEL is motor-command-referred.**

⇒ Low mechanical effort at centre ⇒ gain SHOULD be low at centre ⇒ **899 is the correct direction.**
Also: the direction is **Honda's own calibration** and they specified the rack. **The open question
is DEPTH, not sign — the firmware UNDER-compensates.**

## 7. 🛑 BUILD-DIRECTION TRAP — `0xC6B80` must go DOWN, not up

`0xC6B80` **is `Y[0]` = 899, the centre-floor knot**; the plateau `Y[5..12]` = 1084.
```
swing = 1084/Y[0];  raise Y[0] -> FLATTER = LESS compensation
                    LOWER Y[0] 899 -> ~623 => swing 1.740 = matches a 0.575 notch
```
An orchestrator message on 2026-08-13 said "under-compensates (raise it)" — **that is inverted.**

## 8. The band question — my first verdict was INVERTED, and I withdrew it

I first killed the hypothesis on *"the model gradient is flat across 0-34°, so it cannot generate an
angle-dependent error there."* 🛑 **Wrong criterion.** In a disturbance observer the error is the
MISMATCH: a flat model against a varying plant is exactly how you GET an angle-dependent residual.
Correct criterion is `|d(plant)/dθ − d(model)/dθ|`, and the residual LEVEL `R(θ)−M(θ)`:
```
  0-20°  mismatch −0.254 .. −0.259  (model over-predicts 1.44×)   <- MAXIMAL AND FLAT
   34°   −0.234      50° −0.149     64° −0.074     ≥85° ~0
```
**Maximal across the centre band**, decaying to zero by ~100°; gradient peaks at 28-34°.
**Exposure (`cc_lat`, n=14,289): 0-34° = 0.649, 34-100° = 0.215, >100° = 0.137** ⇒ he spends 65 % of
engaged time where the mismatch level is largest. **Re-issued verdict: right band, UNDER-SCALED ~3×.**

⚠ The plant side rests entirely on a pixel reading of an image **I was never given and which is not
in the repo**. Every mismatch number scales with the assumed 0.575 notch depth.

⊕ **Lock-to-lock MEASURED, not assumed: ±390-400°** — all-frame max |angle| 389.4/398.4/387.7° on
r80/r81/r82 with **p99.9 ≈ max**, i.e. dwelling at a hard stop. A ±500° assumption is ~25 % high,
though the shape alignment survives either scale. ⊕ The table's own `X[12]` = 477.6° spans full travel.

⊕ `mul 0xc,r6,r0` @`0x3bab0` is the only hardcoded ratio-like scalar on the motor-rate path — a
constant where physics demands a function of angle, but 12 is at least as likely a Q-format factor.
[BELIEF, not established.]

## Related
[[reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles]] — CORRECTED by this (Problem 2
false, Problem 1 reach false; its magnitude point survives only for the near-centre hypothesis).
[[reference_accord_angle_position_scale_0p1_deg_per_count_settled]] — the 0.1°/count scale used here.
[[reference_accord_fun3b8f6_cal_types_iir_phase_and_v86_gate_decode]] — sibling cal census of the
same function; this trace adds the complete input list including the angle read.
