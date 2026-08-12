---
name: accord-gp6b26-is-a-real-6to9hz-damper
description: "MEASURED on two independent drives: the 0xCBE74 lane gp-0x6b26 sits at +137/+139 deg vs WHEEL rate at 6-9 Hz (|cos| = 0.73) and contributes +518/+565 counts of POSITIVE Re(Z). It is a real 6-9 Hz damper. The desk figure of +75 deg / 26 % dissipative / 'structurally cannot damp 6-9 Hz' was the PRODUCER's filter phase against MOTOR rate and is superseded."
metadata:
  type: reference
---

# ★★★★★ `gp-0x6b26` IS A REAL 6–9 Hz DAMPER — measured, not calculated

Measured 2026-08-12 on the flight corpus. **This supersedes a decision-bearing phase figure that was
in this session's own record and would otherwise be reused.**

> 🛑🛑 **REGIME SCOPE, added 2026-08-12 — READ BEFORE CITING.** Every number in this file was
> measured **ENGAGED + HANDS-OFF**. The operator produces the symptom by **OVERRIDING** (engage,
> then turn against the command), and override is `steeringPressed == True` **by definition**, so
> this file characterises a regime **the symptom does not occur in**. The measurements are correct
> for what they measure — latent loop damping, hands-off — and they are **not** symptom
> measurements. See [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]].
>
> ⊕ **BUT THIS FILE'S CONCLUSION IS CORROBORATED BY A SYMPTOM, and that is why it is kept as
> load-bearing rather than scope-limited.** V94 removed 6/6ths of this lane and the operator judged
> the car **unsafe to drive**, with motor acceleration **3–7× up above 9 Hz** — the on-car,
> hands-on, symptom-level confirmation that the lane is dissipative.
> ⇒ [[accord-v94-flew-and-the-lane-is-a-damper]]

## THE MEASUREMENT [EVIDENCE]

Signed reconstruction of the lane (CAN 427 magnitude at 50 Hz × the 100 Hz sign bit `0x14A` b4 b7),
cross-spectrum against WHEEL rate (`0x18F` b2-3), engaged + hands-off + moving, **micro regime**
(window-median |rate| 1–13 °/s), shuffled-pairs control on every cell, skew swept ±2 samples of the
100 Hz sign grid with every conclusion stable.

| band | r77 (V90) 104 win / 34 ep | r78 (V91) 35 win / 14 ep |
|---|---|---|
| 4–6 | 190 ct/(rad/s) ∠+150° coh² .17 | 126 ∠+134° .03 |
| **6–9** | **189 ∠+137° coh² .21** | **218 ∠+139° coh² .17** |
| 9–12 | 172 ∠+145° .22 | 266 ∠+151° .21 |
| 12–16 | 287 ∠+157° .28 | 321 ∠+159° .31 |
| **18–22** | **452 ∠+168° coh² .76** | **463 ∠+170° coh² .66** |

The gain **rises** with frequency (105 → 190 → 189 → 172 → 287 → 452 across 2-4 … 18-22 Hz), which is
what an acceleration-derived term does. **|cos(137°)| = 0.73 ⇒ the lane is 73 % dissipative at
6–9 Hz, and 98 % dissipative at 18–22 Hz where it is largest and most coherent.**

## THE SHARE OF `Re(Z)`, ω-PARTIALLED [EVIDENCE]

`H = S_{b,tq|w} / S_{bb|w}`, then `Re(Z_lane) = Re[H × (lane per rad/s)]`, episode-bootstrapped:

| route | 6–9 Hz `Re(Z_lane)` | measured `Re(Z)` | share [95 % CI] |
|---|---|---|---|
| r77 | **+518** | −2529 | **−20 % [−37, −11]** |
| r78 | **+565** | −2168 | **−26 % [−59, −10]** |

🛑 A **NEGATIVE** share means the lane pushes `Re(Z)` the OPPOSITE way to the measured (negative)
value — i.e. **it OPPOSES the anti-damping. It damps.** Without it, `Re(Z)` at 6–9 Hz would be
~20–26 % more negative. That is exactly what V94 produced when it cut the lane 4× and the car shook
badly enough that the operator stopped driving at walking pace.

Direction fixed by physics, not by convention: `J·α = T_bar + T_motor ⇒ Z = jωJ + b − T_motor/Ω`,
so **`Re(Z)` is reduced by whatever part of MOTOR torque is in phase with rate.** A lane near 0° is
anti-damping, a lane near 180° damps. See [[reference-accord-rez-anchored-on-car-and-its-floor]] for the
parameter-free anchor that fixes the sign of `Re(Z)` itself.

## 🛑 WHAT THIS CORRECTS, EXPLICITLY

> *"`gp-0x6b26` sits at ~+75° from wheel rate, so only ~26 % of it is dissipative at 7.8 Hz, rising
> to ~68 % at 26 Hz — it structurally cannot damp 6–9 Hz."*

**That figure is wrong and must not be reused.** It is a desk calculation of the **producer's**
filter phase (`0xC643C` = 37>>7 and `0xC40DC` = 22>>6, both frozen on every build) against **MOTOR**
rate. The measurement above is of the **delivered lane** against **WHEEL** rate, **with the plant —
torsion bar and column — in between**. `analysis-2020accord/v94_damping_fraction.py` carries a
retraction banner; the arithmetic mirror and the pole coefficients in it survive, the dissipative-
fraction table does not.

⇒ **Two successive phase stories about this one lane were wrong in a decision-bearing way within
four days.** The rule that follows is in [[feedback-reducing-a-gain-is-not-a-safety-class]]: a
producer's transfer function is not the lane's contribution to impedance at the wheel, and the fix
is to **measure the delivered lane**, not to do the arithmetic more carefully.

## WHAT DOES *NOT* CHANGE
[[accord-gp6b26-is-inertia-not-damping]]'s **trace** stands: `gp-0x6c2c` really is a first difference
of the filtered motor rate, pinned in assembly at `0x41602 sub r7,r9`. What changes is the inference
drawn from it — "acceleration-derived" is not synonymous with "purely inertial", and the two poles
downstream rotate it most of the way into phase opposition with rate by 6–9 Hz.

## REPRODUCE
`python rlog-tools/v95_lane_decomposition.py` (parts 1 and 2). Instrument and the four hands-off
mask definitions: `rlog-tools/v95_rez_lib.py`.

Links: [[accord-gp6b26-is-inertia-not-damping]] ·
[[feedback-reducing-a-gain-is-not-a-safety-class]] · [[accord-v94-flew-and-the-lane-is-a-damper]] ·
[[reference-accord-gp6bbe-is-rate-derived-not-base-assist]] · [[reference-accord-rez-anchored-on-car-and-its-floor]] ·
[[feedback-decompile-first-then-assembly]]
