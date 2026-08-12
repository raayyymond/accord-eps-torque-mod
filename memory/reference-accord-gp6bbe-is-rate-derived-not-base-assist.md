---
name: reference-accord-gp6bbe-is-rate-derived-not-base-assist
description: "gp-0x6bbe responds to WHEEL RATE, not to driver torque: the bbe<-tq transfer is 0.01 counts/count and its phase is fully explained by both channels being driven by omega. Flat 87-92 ct/(rad/s) from 2-12 Hz at +18 deg = source-side at 6-9 Hz. But it is only 9-15 % of Re(Z) and its rate part is 4-9 % of a DC assist pedestal, so a weight cut is a bad trade. CONTRADICTS the 'base-assist output' identification."
metadata:
  type: reference
---

# ★★★★ `gp-0x6bbe` IS RATE-DERIVED, NOT THE BASE ASSIST — and it is too small to be a lever

Route 79 (V92) is the only build that has ever put this lane on the wire: CAN 427 = `|gp-0x6bbe|`
with `sar 4`, plus the sign on `0x14A` byte4 b7 at 100 Hz. Measured 2026-08-12.

> 🛑🛑 **REGIME SCOPE, added 2026-08-12 — READ BEFORE CITING.** Every number in this file was
> measured **ENGAGED + HANDS-OFF**. The operator produces the symptom by **OVERRIDING** (engage,
> then turn against the command), and override is `steeringPressed == True` **by definition**, so
> this file characterises a regime **the symptom does not occur in**. The measurements are correct
> for what they measure — latent loop damping, hands-off — and they are **not** symptom
> measurements. See [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]].

## 1. IT IS NOT TORQUE-DERIVED [EVIDENCE]

A base assist is a function of DRIVER TORQUE, so its phase relative to wheel rate would track `tq`'s
(−122° at 6–9 Hz). Measured, micro regime, 6–9 Hz:

```
gp-0x6bbe <- tq   =  0.01 counts/count  ∠ +144°      coh² 0.26
                     └─ and +144° is EXACTLY  phase(bbe vs ω) − phase(tq vs ω) = 18 − (−122)
                        ⇒ the tq relation is fully explained by both being driven by ω.
gp-0x6bbe <- ω    =  92.3 ct/(rad/s)    ∠ +18°       coh² 0.28
```

Gain and phase against wheel rate across the band (micro regime, route 79):

| band | 2–4 | 4–6 | **6–9** | 9–12 | 12–16 | 18–22 |
|---|---|---|---|---|---|---|
| ct/(rad/s) | 87 | 88 | **92** | 74 | 72 | 69 |
| phase | −31° | −8° | **+18°** | +24° | +25° | +66° |

**Flat gain 2–12 Hz with the phase passing through zero at 5–6 Hz.** That is a rate-derived term,
not an assist map of torque.

🛑 **This CONTRADICTS `docs/STATE.md` §A1 and [[accord-gp6bbe-is-viscous-plus-dc-pedestal]]**, which
identify the lane as "the base-assist output (assist map × polarity, speed-clamped)". The viscous
≈90 ct/(rad/s) figure in that memory is confirmed; the *identification* is not. Hand the producer
(`FUN_00034a72`) back to a tracer.

## 2. IT IS SOURCE-SIDE AT 6–9 Hz [EVIDENCE for the phase, physics for the direction]

`Z = jωJ + b − T_motor/Ω` ⇒ `Re(Z)` is reduced by the part of MOTOR torque in phase with rate. At
+18° this lane is aligned with rate ⇒ **anti-damping**. It sits **119–121° away from `gp-0x6b26`**
(+137°), whose side of the ledger is fixed independently by V94's on-car result — and that phase
SEPARATION is robust to the shared downstream, because both lanes sum into `gp-0x6b70` and travel
the same path to the motor. See [[accord-gp6b26-is-a-real-6to9hz-damper]].

## 3. 🛑 THE SIZING KILLS IT AS A LEVER — do not propose a weight cut

ω-partialled share of `Re(Z)` at 6–9 Hz: **+9 % [−2, +18] (micro regime), +15 % [+6, +25] (all
rates).** Zeroing `Re(Z)` would need **10.9×** the lane's entire rate response.

And the rate-proportional part cannot be separated from the assist:

```
|gp-0x6bbe|  p50 73.6–80 counts   (DC pedestal)     aggregator window ±2048
6–9 Hz AC amplitude   2.6–6.9 counts               = 4–9 % of the DC pedestal
```

⇒ **a flat weight cut takes both.** A 25 % cut buys ~71 counts of `Re(Z)` — about 1.2× the detection
floor — and costs **25 % of the power steering**. That is a bad trade and the operator would feel the
assist loss long before the instrument saw the damping.

## METHOD NOTES
- Skew swept ±2 samples of the 100 Hz sign grid (the magnitude rides 50 Hz CAN 427, the sign rides
  100 Hz `0x14A`); every conclusion above is sign- and magnitude-stable across the sweep.
- 🛑 427 is RECTIFIED, so 26–31 Hz folds to 2–12 Hz on the raw magnitude channel. The **signed**
  reconstruction used here is clean (coh² 0.001 against the folding source at 6–9 Hz); the raw
  `|427|` channel is not. See [[reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz]].
- The other five rungs V92 flew (`gp-0x6b62` sign and live, `gp-0x6bda` window, dwell-snap,
  `gp-0x6c00`) read **identically constant** — dead rungs, and therefore free bits on the next cave.

## REPRODUCE
`python rlog-tools/v95_lane_decomposition.py` (parts 1–3).

Links: [[accord-gp6bbe-is-viscous-plus-dc-pedestal]] · [[accord-gp6b26-is-a-real-6to9hz-damper]] ·
[[accord-angle-rate-lane-gp6bbe-top-candidate]] · [[reference-accord-rez-anchored-on-car-and-its-floor]] ·
[[accord-anti-damping-is-not-the-pid]]
