---
name: accord-ratchet-and-grinding-are-two-symptoms
description: "★★ The ~7.4 Hz mode is the RATCHETING and the 20-25 Hz mode is the GRINDING — two different symptoms, settled by the operator 2026-07-30. Everything written before that date conflates them. The 7.4 Hz ratchet is NOT the V42 state-4 governor ratchet (ST==4 fires 0/37,922 frames)."
metadata:
  type: reference
---

# ★★ The ratchet and the grinding are DIFFERENT phenomena

**Operator, 2026-07-30, authoritative** (lived experience overrides analysis — [[feedback-operator-lived-experience]]):

> "grinding is not 7.4 Hz, that is the ratcheting."

| | **RATCHET** | **GRINDING** |
|---|---|---|
| frequency | **~7.4 Hz**, Q≈36 @nfft=1024, 2nd harmonic locked at 15.0 Hz (ratio 2.00±0.125, 81% of windows) | **20-25 Hz**, `f ≈ 0.177·v + 20.48` |
| dominates at | parking-lot creep, large steering angle | road speed; present at creep too |
| variance share (route 29 burst) | **33.0%** (6-9 Hz) | **5.3%** (19-24 Hz) |
| vs command rail duty | **rises 8.42×** (partial r = +0.810 controlling for angle) | falls to **0.74×** |
| in openpilot's 0xE4 command? | **no** — command's 6-9 Hz peak is at 6.26 Hz, 6.4 bins away | no |

🛑 **A mid-session conclusion that "the kit has been optimising the 5.3% component for 50 builds" is
WITHDRAWN.** The 20-25 Hz focus was correct; the 7.4 Hz line is a separate, already-named symptom.

⚠ **Steering-angle excitation of the 7.4 Hz mode is a CORRELATION only**, related through
return-to-centre (operator). Do not treat angle as causal. The apparent "needs angle excitation to
appear" observation (route 29 creep |ang| 26.5° shows it, route 28 creep |ang| 5.8° does not) is
consistent with that and is not a mechanism.

## The ratchet is NOT the V42 ratchet

`STEER_STATUS == 4` fires in **0 of 37,922 frames** across both V57 routes (bits 7:4 of `0x18F` byte4 —
see [[accord-steer-status-is-byte4-bits-7-4]]). So the state-4 governor substitution at `0x454FE`,
root-caused and fixed by V42, is **not** producing this. Mechanism unknown.

## What it is, measured

A **plant limit cycle gated by applied LKAS torque, not commanded**:
- 336× LKAS-on/off in the 6-9 Hz band (5.223e8 vs 1.556e6 counts²)
- autocorrelation r = 0.797 at exactly **140 ms**
- over 0.21 s the 0xE4 command drifts **510 counts** while the torsion bar swings **2,791 counts through
  3 sign changes**
- window power correlates **+0.761** with LKAS applying but **−0.140** with driver torque (negative — it
  is not the driver's hands); the sharpest window has |driver tq| 363 and |ang| 3.0°
- present on V55 too (7.06 Hz, 674× floor at matched geometry) ⇒ **not new in V57**

## No calibration lever exists for it

All rate-limit candidates are closed — see [[accord-c61d6-slew-is-rejected-not-fresh]] and
`docs/BUILD-LINEAGE.md`. The ±565/cycle slew inside `FUN_0003b66a` is a **code immediate**
(`mov 0x440d4000,r6` = 565.0f), not a cal. Next step is measurement, not a build.

Related: [[accord-telemetry-conventions-that-produced-wrong-answers]],
[[accord-gp6a56-is-motor-rate-not-an-angle-sensor]]
