---
name: accord-grind1-dose-limited-ratchet-dose-independent
description: V76 flew clean and split the two creep symptoms — grind #1 responds to damper dose, the micro-ratchet does not.
metadata:
  type: project
---

> 🛑🛑 **RETRACTED IN PART, 2026-08-07 (later the same day) — READ
> [[accord-grind1-is-inert-to-the-damper-dose]] FIRST.** V80 added a fourth dose point (`k` = 4.16) and
> all four builds were re-scored on **one** instrument with a **split-half null**: the 18–22 Hz null is
> ≈ [0.63, 1.60] and **every grind-#1 point lies inside it**. ⇒ **the "grind #1 is DOSE-LIMITED, slope
> −0.614 [−0.810, −0.416]" headline below is WITHDRAWN**, and the V75-vs-V76 grind-#1 difference is a
> **creep-EXPOSURE** difference (V76's creep windows carry 3.4× V75's steering effort).
> ✅ **The ratchet leg SURVIVES and is EXTENDED**: it is flat up to `k` = 1.58 as stated, and it *does*
> move at V80's `k` = 4.16 (0.418 [0.33, 0.61] vs V76) — consistent with the older "needs `k` = 4.2–13.5".
> ✅ The flight facts, build identity, friction-margin null and mode-lag measurement below all stand.

**V76 was flashed and driven 2026-08-07**: route `75604b0a432fdc89_00000065--ae43aa0f27`, segs 0–10,
**636.30 s / 63,477 frames**, 0–96.7 km/h, engaged 450.98 s (**70.87%**). **Clean** — zero DTC-active
transitions, zero STEER_SENSOR_STATUS 7→4, zero `0x7FFF` angle sentinels, no frame-rate collapse.
Build identity settled **four independent ways** (bits 6/5 structurally unreachable 0/63,477 · 8-value
legal payload set 0 violations · V75's thermometer invariant violated on 70.0% ⇒ not V75 · the
superseded V76's structurally-zero bit3 reads 99.926%).

## ★★★★ THE SPLIT — the decision-bearing result
Fit `ln(band / 24–28 Hz control) = a + b·k` over V72/V73 (k=0), V74 (0.5799), V75 (1.5798), V76 (1.3866);
creep, speed-stratified, **bootstrapped over EPISODES** ([[feedback-episodes-not-windows]]). V76 sits
*between* V74 and V75, so a monotone model made a falsifiable **point** prediction, not just a direction.

| band | V76 observed | monotone prediction | slope b [95% CI] | verdict |
|---|---|---|---|---|
| ratchet 6–9 Hz | 3.877 [3.098, 5.161] | 3.906 (−0.06 dB off) | **−0.094 [−0.291, +0.098]** | **DOSE-INDEPENDENT** |
| grind #1 18–22 Hz | 1.577 [1.380, 1.831] | 1.613 (−0.19 dB off) | **−0.614 [−0.810, −0.416]** | **DOSE-LIMITED** |

🛑 **More damper dose will NOT fix the micro-ratchet.** Flat across k = 0 → 1.58 with V76's own point on
the flat line. **The ratchet needs a non-dose lever.**
★ **Grind #1 is dose-limited and the prediction HELD to 0.19 dB** — the cleanest dose-response this kit
has produced. See [[accord-ratchet-characterised-on-route-4f]] for the ratchet's own characterisation
(median 7.79 Hz, speed-invariant, in the bar and angle-rate but NOT in openpilot's command).

Presence on V76, paired against the same build's own 24–28 Hz control: grind #1 rel. excess
**1.956 [1.214, 4.154]** (excludes 1 ⇒ real; worse than V75's 1.572, far better than V74's 9.154);
ratchet **5.026 [3.824, 6.592]**, indistinguishable from V74's and V75's. **Both match the operator's
report — "still grind #1 and micro-ratcheting at creep" — exactly.**

## 🛑 V76's grind-#2 prediction was FALSIFIED
Predicted 0.57× vs V75 at 42 °/s; **measured 1.394 [1.017, 1.768]** — 39% MORE, the opposite direction.
85 °/s underpowered (n=7 < 8); 255 °/s never occurred on any of the three routes.
⇒ **Discount the arithmetic surface model's ability to predict DELIVERED grind #2.** The `k` dose axis
itself was validated by the same drive, so this is specific to the grind-#2 surface. Same pattern as
[[accord-lane-change-transient-is-dose-independent]].

## Two probe results worth keeping
- **The friction-margin null is REAL, not an unarmed gate.** bit7 (`|gp-0x6b26| > 448`) fired
  **0 / 63,477** with the positive control (bit3, `gp-0x67fa == 5`) at 99.93% **in the same frames**,
  across every speed band and both arms. ⚠ **Weakens but does not refute**
  [[accord-friction-lane-ceiling-is-the-hard-fault]] — it bounds `gp-0x6c2c` from one side only.
- **Mode lag measured directly: median 994.9 ms [830.0, 1575.0]**, mean 1133, range 830–2070, n=6 clean
  disengage episodes. 🛑 **Prior handoffs quote ~2.5 s.** Treat this as the better number — it is a
  direct bit4 probe built for the question — but n=6 on one route does not prove the older figure was
  measuring the same quantity.

⚠ Standing caveat, carried unchanged: each non-zero-k point is still **n=1 route**, so the CIs are
optimistic lower bounds on true route-to-route uncertainty. V72/V73 (both k=0) are the only within-dose
replicate the fit has.
