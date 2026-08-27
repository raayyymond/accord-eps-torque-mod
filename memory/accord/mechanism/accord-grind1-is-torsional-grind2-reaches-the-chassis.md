---
name: accord-grind1-is-torsional-grind2-reaches-the-chassis
description: Two independent estimators — level ratio and scale-free coherence — show grind #2 couples to the chassis on every IMU axis while grind #1 reaches none of them; grind #1 is a torsional column mode, which is why the IMU never showed its reduction
metadata:
  type: reference
---

★★ **GRIND #1 DOES NOT REACH THE BODY. GRIND #2 DOES.** Measured two independent ways on the same
events, 2026-08-03.

Events are the kit's own burst lists at creep (v ≤ 4 m/s): grind #2 = 30–49 Hz bursts, **n = 10**
(8 LKAS ON r3a/V65, 2 LKAS OFF r3b seg 2/V65); grind #1 = 18–26 Hz bursts, **n = 48**. Every event
matched to controls in its **exact** (speed, effort, |rate|) cell, 18–304 control blocks, no
relaxation. Both lists are CAN-defined, so the `tq` row is a selection tautology and the informative
quantity is **transfer = channel ratio / CAN ratio**.

## Method 1 — burst p90 / matched-control median, event-bootstrapped, each vs its own null

| channel | axis is | **grind #2** (40–49 Hz) | clears null | transfer | **grind #1** (18–22 Hz) | clears null |
|---|---|---|---|---|---|---|
| `tq` 0x18F | torsion bar | **77.1** [53.5, 130.9] | ✅ | 1.000 | **12.87** [9.0, 14.9] | ✅ |
| IMU `ay` | **lateral** | **58.8** [29.8, 87.6] | ✅ | **0.763** | 1.451 [1.19, 1.59] | ✗ |
| IMU `gz` | **roll** | **36.2** [21.4, 49.3] | ✅ | 0.470 | 1.463 | ✗ |
| IMU `gy` | pitch | 21.3 [13.7, 24.8] | ✅ | 0.276 | 1.513 | ✗ |
| IMU `ax` | vertical | 20.1 [12.7, 28.2] | ✅ | 0.261 | 1.681 | ✗ |
| IMU `az` | longitudinal | 19.2 [11.2, 23.1] | ✅ | 0.249 | 2.100 | ✗ |
| IMU `gx` | yaw | 11.4 [7.2, 14.3] | ✅ | 0.148 | 1.465 | ✗ |
| mic un-weighted | 0–8 kHz | **4.59** [2.95, 8.31] | ✅ | 0.060 | **1.061** | ✗ |

Nulls (contiguous non-burst pseudo-events, identical estimator) run 1.0–4.4. **Every IMU axis clears
for grind #2; NOT ONE clears for grind #1, on 48 events.**

Axes identified **from the data**, not a mount drawing: `ax` carries 9.67 m/s² ⇒ vertical; `az`
ρ = **−0.839** vs d(vEgo)/dt ⇒ longitudinal; `gx` ρ = **+0.975** vs v·steer ⇒ yaw; `gy`/`gz` split by
|ρ| vs d(surge)/dt **0.690** vs d(sway)/dt **0.723** ⇒ pitch / roll. Self-consistent.

## Method 2 — bar→chassis COHERENCE (scale-free, uses no level at all)

| | `ax` | `ay` | `az` | `gx` | `gy` | `gz` |
|---|---|---|---|---|---|---|
| **grind #2**, event (n=10) | 0.846 | **0.861** | 0.842 | 0.823 | 0.880 | 0.846 |
| grind #2, control (n=8) | 0.320 | 0.605 | 0.309 | 0.296 | 0.331 | 0.410 |
| **grind #1**, event (n=48) | 0.345 | 0.403 | 0.365 | 0.331 | 0.341 | 0.270 |
| grind #1, control (n=32) | 0.288 | 0.307 | 0.258 | 0.338 | 0.330 | 0.465 |

⇒ **grind #1 is a TORSIONAL COLUMN MODE.** That is *why* the IMU never showed grind #1's reduction
across the dose series — the instrument was never coupled to it. Any future IMU null on a column-mode
hypothesis is **silence, not absence**, at any frequency, independently of the 50 Hz ceiling
([[accord-both-instruments-blind-above-50hz]]).

**BELIEF, NOT MEASUREMENT:** grind #2's axis ordering — lateral ≫ roll > pitch ≈ vertical ≈
longitudinal ≫ yaw — reads as a **lateral rack/subframe force with a roll couple** (the comma sits
high on the windscreen, so lateral translation and roll dominate there). It is
**translational-dominant with a rotational partner**; it is *not* a vertical wheel-hop mode and
*not* a yaw mode. Yaw being weakest is expected for a force roughly on the yaw axis.

⇒ `analysis-2020accord/studies/grind2/grind2_trichannel.py` §4/§4b. See
[[accord-mic-two-weightings-are-a-filter-bank]] and [[accord-grind2-is-a-45hz-mode-under-driver-load]].
