---
name: accord-f0-crossover-is-the-endpoint
description: "The anti-damping is a REGION from <=16 Hz up to a crossing f0, present on stock too. f0 = 21.90/23.61/24.90 Hz at 1x/4x/6x. It is the endpoint, it needs no symptomatic drive — but it may track COMMAND AMPLITUDE rather than the gain cell."
metadata:
  type: reference
---

⭐⭐ **The 22–26 Hz anti-damping is NOT a notch on the mode. It is a REGION running from ≤16 Hz up to a
zero crossing `f0` — present on EVERY arm INCLUDING STOCK — and our gain pushes that crossing UPWARD.**

```
Hz        16  17  18  19  20  21  22  23  24  25  26  27  28
STOCK 1x   N   N   N   N   N   .   .   P   P   P   P   P   P
V100  4x   N   N   N   N   N   N   .   .   P   P   P   P   P
V102  6x   N   N   N   N   N   N   N   N   .   P   P   P   P
```
*(N = 95 % CI below zero · P = above · . = straddles)*

| arm | gain cal | **f0** | 95 % CI |
|---|---|---|---|
| **STOCK 1×** | 891 | **21.90 Hz** | [21.08, 23.03] |
| V100 4× | 3564 | **23.61 Hz** | [23.22, 23.95] |
| V102 6× | 5346 | **24.90 Hz** | [24.63, 25.26] |
**All three CIs mutually disjoint. `f0 ≈ 21.3 + 0.60 × (gain multiple)` — LINEAR.** Predicts 8× ⇒ ~26.1 Hz,
which would put the entire legacy 21.5–25.5 band inside the anti-damped region.

## ⭐ WHY IT IS THE RIGHT ENDPOINT
- 🛑 **It needs NO symptomatic driving.** A burst-tercile test shows **V102 is anti-damped in EVERY tercile
  with no trend**, while **stock is damped in every tercile and gets MORE damped as bursts grow** (control
  band rises monotonically on all arms ⇒ not a selection artefact). ⇒ **the negative margin is STANDING;
  only the EXCITATION is intermittent.** He drives normally for ~2 minutes.
- **It is immune to mode migration by construction** — a moving crossing cannot escape an endpoint that
  *is* the crossing's location. (The mode migrates **+0.157 Hz/(m/s)** and ~+1 Hz per gain doubling.)
- **`Re(Z)` does NOT need band widening**: the SIGN is robust across 21.5–25.5 / 22–26 / 20–28, but at
  18–30 both CIs touch zero. **Use 22–26 Hz as the `Re(Z)` primary; 20–28 Hz for band-RMS.**

## MEASURING IT
**~100 s engaged HANDS-OFF at 30–85 km/h** (floor 80 s; 41 s licenses nothing — P(resolve) 0.21).
🛑 **Above ~85 km/h contributes NOTHING** — stock (+104) and V102 (+80) both straddle zero there. **A
60–80 km/h arterial is ideal; a motorway cruise is the worst case despite feeling like the most data.**
🛑 **The binding constraint is HANDS-OFF, not duration.**
**Controls**: negative control is **31–35 Hz, NOT 26–31** (26–31 tracks the dose, +1061→+790→+376).
🛑 **Run `rlog-tools/studies/impedance/rez_control.py` first** — it pins the estimator to 0.00 % on all ten bands against
`_scratch/logs/v92_rez.log`'s published table.
**Dose floor**: ~1.0 Hz of `f0` is resolvable in one drive against a 3.00 Hz gap ⇒ **a lever must be dosed
for ≥1 Hz, preferably ≥1.5 Hz.** Conversion: **~153 ct·s/rad per Hz** ⇒ ~230 ct·s/rad buys 1.5 Hz; **1 Hz
of `f0` ≈ 1.7× of LKAS gain.** ⚠ That conversion is a **LOCAL linearisation** — do not extrapolate it.

## 🛑🛑 THE CONFOUND THAT MAY UNDO THE GAIN ATTRIBUTION
**`f0` moves −0.99 Hz with COMMAND AMPLITUDE at FIXED gain** (within V102, speed-matched, CIs disjoint),
and **openpilot commands 4.7× HARDER on stock** because the weak car under-responds: median `|0x0E4|` is
**465 (stock) / 253 (4×) / 98 (6×)**. ⇒ within-route and between-build effects **share sign**, and pooled,
**the gain term goes non-significant (+30 [−99,+159], ΔR² = 0.0009).**
⇒ **[BELIEF] most of the 21.9 → 24.9 Hz march this kit attributed to `0xC6CD0` may be openpilot winding
up on a weaker car.** ~0.5 Hz of residual survives an amplitude-only fit.
🛑 **MANDATORY: report median `|0x0E4|` alongside `f0`, and `f0` adjusted for command. A shift sitting on
the amplitude law's own slope (−1.93 Hz per e-fold) is NOT evidence a lever touched the loop.**
⚠ **[NOT ESTABLISHED] causal direction** — command is itself caused by the plant's response.
⭐ **Closes with ONE DRIVE, no build**: within a single route at fixed firmware, contrast ~100 s sustained
high command against ~100 s low command, hands-off, 30–85 km/h.

## RELATED
The anti-damping at 6–9 Hz is **Honda's** (stock −1297/−1709/−1507; we multiply it 2.4–3.0× below
86 km/h) — but at **22–26 Hz we REVERSE THE SIGN** (stock +247/+496 → V102 −134/−99, disjoint CIs), the
only band where our firmware flips sign rather than size.
See [[accord-the-antidamping-is-hondas]], [[accord-gp6752-is-negative-one]],
[[accord-rez-antidamping-replicated-three-drives]].
