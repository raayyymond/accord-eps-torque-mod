# ★★★ V61 FLASHED → WORSE. The torsion-bar RATE lane is the mode's DAMPER, not its amplifier.

**The first SIGNED on-car result this kit has ever obtained on a vibration lever.** Every prior build was
a null or a fault; V61 made the symptom **worse**, which is strictly more informative than any null.

## What V61 did and what the car did
V61 zeroed the torsion-bar torque-RATE lane at **both** taps of its shared value
`r1 = clamp(gp-0x4f62, ±5120)` — `0x3AB6C mul r1,r6,r0 → mul r0,r6,r0` (r26) and
`0x3AC16 mov r1,r8 → mov r0,r8` (r24). Two single-bit reg1 changes, no cave, 5 bytes off V59.

Operator, 2026-07-31 (authoritative):
- **LKAS ON, forward** — grinding still present and **significantly worse**, higher amplitude and louder.
- **LKAS OFF, forward** — grinding **newly present** in manual driving when turning.
- **LKAS OFF, reverse** — grinding **definitely newly present** in manual driving.

## The sign — verified from image bytes, not relayed
- `gp-0x6752` (polarity) is **one load @`0x3AB78` reused unmodified by both lanes**, and the *same byte*
  is read by `FUN_0003a382`'s resonance lane @`0x3A71A` — the aggregator's one genuinely
  torque-**proportional** P-term. ⇒ **polarity CANCELS in the comparison**; its concrete value is not
  needed. (It is also the literal `1`, written at boot in `FUN_000490ac` @`0x490b6`-`0x490c0`.)
- The combine chain `0x3ACC8`–`0x3ACDA` is **ten instructions, every lane entering with `add`**, each
  add's `reg1` threading the previous add's `reg2` — a textbook accumulator chain. **Not one `sub`.**
- ⇒ `r24, r26 = +Kd · d(T_bar)/dt`, **added in phase with assist**. `Kp·x + Kd·dx/dt` — a lead compensator.

## Why "in phase with assist" is DAMPING, not positive feedback
Hands-off, the mode is the **steering-wheel inertia on the torsion bar**. With motor torque applied to
the column only, `T_m = K·T_b + Kd·dT_b/dt`, `phi = theta_w − theta_c`, `T_b = k·phi`:

```
J_w·theta_w'' = -T_b ;  J_c·theta_c'' = +T_b + T_m - T_road
------------------------------------------------------------
phi'' + (Kd·k/J_c)·phi' + k·(1/J_w + (1+K)/J_c)·phi = T_road/J_c
------------------------------------------------------------
```
The `phi'` coefficient is **`Kd·k/J_c > 0` — positive damping, LINEAR in Kd**. At `Kd = 0` the mode has
**no damping term at all**. That is V61, and that is what the car did — including in **manual** driving,
where base assist is the only loop running, and worst in **reverse**.

With the motor/current-loop lag `tau`, the `K·T_b` term contributes `≈ -K·k·tau/J_c`, so
`zeta_net ~ (Kd - K·tau)·k/(2·J_c·omega)`. Stock pins the operating point: the mode **sustains with no
ring-down at all** (66 candidate decays, longest 0.63 cycles) ⇒ `zeta_net ≈ 0` ⇒ `Kd ≈ K·tau`. So
V61 (`Kd=0`) ⇒ `zeta_net < 0` ⇒ diverges. **Observed.**

🛑 **The DC-neutrality argument rules out the obvious alternative.** A derivative term is zero at constant
torque, so V61 could not have "removed assist" — it changed **only** dynamics. That is what makes this a
clean signed measurement rather than a confound.

## 🛑 What this FALSIFIES in the record
`eps_lkas_chain_model.py:1792` framed r26 as **"excitation-to-amplifier: faster slew → bigger
column-torque derivative → bigger r26 → more motor torque → more column motion → repeat"**, and
recommended "the r26 cal kill attacks the amplifier". **That predicts killing it helps. It doesn't.**
Both passages are struck and corrected in place (2026-07-31).

⇒ **V39 (killed r24, conditionally), V42 (killed r26), V61 (killed both) all tested the lane DOWNWARD.**
Their nulls/regression stand — they simply bracket the **wrong side** of the optimum. **V61 measured the
gradient, and it points UP.** This is the exact inverse of the FactorC/V44 trap: there a withdrawn
*rationale* was mistaken for a withdrawn *result*; here the results all stand and only the direction was
wrong. See [[accord-check-build-lineage-before-proposing-lever]].

## Why this lane and not the dampers that were already tried
`FUN_0003aa2c` is **task 1, 1000 Hz** ⇒ ~3.8° of ZOH lag at 20.9 Hz. The boost/damping lanes are
**task 5, 100 Hz** ⇒ **37.6–75.2°** of lag — the structural reason every damper lever (V44 FactorC,
V47 Factor E) was null. **The rate lane is the only damping mechanism in the chain fast enough to act on
a 20.9 Hz mode.** See [[accord-task5-is-100hz-damper-cannot-damp-21hz]].

## ⇒ V62
Doubles the lane via **two `sar 0xa` → `sar 0x9` immediates** (`0x3AC20` r24, `0x3AB76` r26) — the same
edit class as V61, mode- and arm-agnostic. See [[accord-v62-doubles-the-rate-lane]].

Related: [[reference_accord_loop_through_torque_sensor_uncompensated]],
[[accord-torque-rate-lane-v52c-structurally-blind]], [[accord-vibration-requires-lkas-engaged]].
