---
name: reference-accord-rez-anchored-on-car-and-its-floor
description: "Re(Z) is anchored twice for the first time: the sign convention by mean(T*w) over manual hands-on hard steering (n=20,159, P(>0)=0.9238), and the metric itself against the operator's lived report (it ranks V80 worst at 12-16/18-22 Hz, and V80 is the build he called the worst grinding ever). Detection floor ~60 counts at >=12 episodes; use 150 conservative. 🛑 Do NOT quote Re(Z) below 6 Hz from a steeringPressed mask."
metadata:
  type: reference
---

# ★★★★★ `Re(Z)` — ANCHORED TWICE, AND ITS DETECTION FLOOR

Established 2026-08-12. Until this session `Re(Z)` was an instrument nobody had validated in either
direction: the sign convention was assumed, and the metric had never been tied to anything the
operator said.

> 🛑🛑 **REGIME SCOPE, added 2026-08-12 — READ BEFORE CITING.** Every number in this file was
> measured **ENGAGED + HANDS-OFF**. The operator produces the symptom by **OVERRIDING** (engage,
> then turn against the command), and override is `steeringPressed == True` **by definition**, so
> this file characterises a regime **the symptom does not occur in**. The measurements are correct
> for what they measure — latent loop damping, hands-off — and they are **not** symptom
> measurements. See [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]].
>
> ⊕ **The V80 ranking in §2 IS a genuine instrument↔symptom link and survives the scope banner** —
> `Re(Z)` independently picked out the build the operator called *"worst grinding ever"* without
> being told. **KEEP this file. It validates the instrument; it just does not measure the symptom.**

## 1. THE SIGN CONVENTION, ANCHORED PARAMETER-FREE [EVIDENCE]

`mean(T · ω)` over **MANUAL + HANDS-ON + |wheel rate| > 30 °/s** — a case where the driver *must* be
doing net positive work against tyre scrub and column friction. Raw time-domain product, **no
spectral estimator, no window selection, no free parameter.**

```
r66/V80 +2302 · r5e/V75 +5834 · r70/V86B +3412 · r6f/V86 +5141
r73/V88 +4117 · r77/V90 +4082 · r78/V91 +2959 · r79/V92 +4708
POOLED  n = 20,159 frames   mean +3859   median +3198   P(T·ω > 0) = 0.9238
```

Positive on all 8 routes across 8 builds. ⇒ **`Re(Z) > 0` = DISSIPATIVE; `Re(Z) < 0` = the column
doing work on the driver's hands.** The kit's reading of −3375 as a genuine energy source is
correct and the standing caveat on it is retired.

Physics that carries the convention into the lanes: `J·α = T_bar + T_motor ⇒ Z = jωJ + b −
T_motor/Ω`, so **`Re(Z)` is REDUCED by whatever part of MOTOR torque is in phase with rate.**

**Largest replication to date:** engaged hands-off 6–9 Hz = **−3306 [−3455, −3157]** over 1906
windows / 229 episodes / 17 routes.

## 2. THE METRIC, ANCHORED AGAINST THE OPERATOR'S OWN REPORT [EVIDENCE]

Cross-build ledger, engaged hands-off, matched 5–22 m/s and |rate| < 13 °/s:

| | 12–16 Hz | 18–22 Hz |
|---|---|---|
| **V80 (route 66)** | **−8883** | **−3581** |
| V76 | −7210 | −1610 |
| V81 | −6250 | −1328 |
| **V83a (route 68)** | **−2753** | **−427** |
| V84 … V92 | −3924 … −4393 | −662 … −800 |

3.2× and 8.4× against a same-build floor of 195 / 156. **The metric ranks V80 worst — and V80 is the
build the operator independently called the worst grinding he has ever felt**
([[accord-v80-damper-relay-and-grind1-inert]]). First time `Re(Z)` and his lived report have been
tied together, from opposite directions.

## 3. THE DETECTION FLOOR — use this, not the band-power placebo floors [EVIDENCE]

Tightly matched **10–20 m/s, |rate| 0.3–3.0 °/s**, 6–9 Hz: **r76 −3288 · r77 −3286 · r78 −3280 ·
r79 −3227** — four drives, three builds, **spread 61 counts.** The one same-build replicate with
thin exposure (V89 on r75, 8 episodes) sits 645 away.

⇒ **floor ≈ 60 counts at ≥ 12 episodes / ≥ 85 windows in the matched cell; use 150 conservative.**
Same-build (V89 r75 vs r76) differences per band: 4-6 **89** · 6-9 **645** · 9-12 **481** ·
12-16 **195** · 18-22 **156** · 26-31 **61** · 32-38 **177**.

🛑 **Signal-to-floor differs enormously by band: 18–22 Hz ≈ 75×, 6–9 Hz ≈ 2.5×.** 18–22 is by far the
better-conditioned endpoint; **any 6–9 Hz pass/fail must enforce the exposure requirement** or the
drive-to-drive term swamps the effect. The kit's 1.37× / 1.31× / 1.99× floors are **band-power**
ratios and do not transfer to `Re(Z)`.

## 4. 🛑 THE MASK CONTAMINATES `Re(Z)` BELOW 6 Hz

`steeringPressed` is `|STEER_TORQUE_SENSOR| > 1200` (`opendbc/car/honda/carstate.py:163`;
`HONDA_ACCORD` is **not** in the `STEER_THRESHOLD` override dict) — **a threshold on the NUMERATOR
of `Z`**, matching the flag on 99.28–99.96 % of frames with a free-fit threshold of exactly 1200.
Because `runs_of` requires every frame to pass, it drops **39 % of engaged and 93 % of manual**
candidate windows, and the dropped windows carry **3.91×** the 6–9 Hz torque in the engaged arm
against **1.20×** in the manual arm — **arm-asymmetric by 3.3×**, so it does not cancel in a contrast.

| band | D0 strict (old kit mask) | D3 band-orthogonal | verdict |
|---|---|---|---|
| 2–4 | −1312 [−1399,−1215] | **+612** | 🛑 SIGN REVERSES |
| 4–6 | −1608 | −561 | 🛑 −65 % of magnitude |
| **6–9** | **−3383** | **−3394** | ✅ invariant, 16 counts |
| 9–12 … 18–22 | −4698 / −4457 / −697 | −5102 / −3731 / −603 | ✅ within 16 % |

⇒ **`Re(Z)` at 6 Hz and above is safe. Do not quote `Re(Z)` below 6 Hz from a `steeringPressed`
mask.** Fix: `D3 = window-median |cs_tq| < 1200` — a median over 512 samples has no leverage from
2–38 Hz content. ⚠ **No torque-independent hands-on sensor exists on this car**, so no mask is fully
clean; D3 is band-orthogonal, not torque-free. The same defect makes the grip contrast
*irreducibly* confounded: hands-on is defined by high `|tq|`, the numerator of `Z`.

## REPRODUCE
`python rlog-tools/v95_rez_polarity_and_mask.py` (both anchors and the mask pricing) ·
`python rlog-tools/v95_crossbuild_rez_ledger.py` (the ledger and the floor panel).

Links: [[accord-rez-antidamping-replicated-three-drives]] · [[accord-v80-damper-relay-and-grind1-inert]]
· [[accord-gp6b26-is-a-real-6to9hz-damper]] · [[feedback-episodes-not-windows]] ·
[[accord-averaged-spectrum-needs-matched-speed-distributions]] ·
[[feedback-run-the-control-before-the-measurement]]
