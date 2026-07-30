---
name: accord-telemetry-conventions-that-produced-wrong-answers
description: "🛑 Three rlog conventions this kit used that each produced a confident wrong answer: cruiseState.enabled as the engagement proxy (it is long+lat, reads 0.00% on parking-lot routes), raw |tq|<=200 as hands-off (the oscillation trips it, discarding 8.79x the amplitude), and mean Welch power for a bursty limit cycle (use p99/max envelope). Plus a fourth, unsolved: engagement and motion are collinear."
metadata:
  type: feedback
---

# 🛑 Three rlog conventions that each produced a wrong answer

All three surfaced on 2026-07-29/30 analysing the V57 drive. Each one flipped a headline conclusion.
**Every historical amplitude comparison in this kit needs rebuilding on the corrected conventions before
it can be trusted.**

## 1. `carState.cruiseState.enabled` is LONGITUDINAL + LATERAL — the wrong engagement proxy

Use **`carControl.latActive`** (cereal `car.capnp:345`), corroborated by CAN `0x18F` byte4 bit3
(`STEER_CONTROL_ACTIVE`) and `0xE4` `STEER_TORQUE_REQUEST` on the **`sendcan`** stream. The three agree
to **99.85-99.94%**.

- Reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot routes
  where lateral was demonstrably applying (route 29: 21.74%).
- Reads **84.0%** on route 28 while lateral applied **49.9%**.
- Using it flipped V57's deadband verdict from **INERT (0.03%)** to **NOT INERT (53.31%)** — the gate is
  enabled precisely when lateral is off, so a proxy that overcounts engagement manufactures the result.
- It inflates V56's creep baseline **28×** (2.67e5 → 7.49e6) by sweeping in hands-on parking manoeuvres
  at |ang| 89.6°.

⚠ `0xE4` is **not** on `can` src 0 — route 28 has zero such frames across 300 s. Use `sendcan`.

## 2. Hands-off must be SUSTAINED effort, never raw `|torque| <= 200`

Use `|zero-phase lowpass(tq, 3 Hz)| <= 200`. The oscillation is **±1400 counts on the torsion-bar channel
itself**, so it trips the raw test by itself:
- 68.3% of frames scored "hands-on" have the driver doing nothing sustained
- on genuinely quiet frames the raw test **keeps** 390 frames with oscillation rms **103.5** and **drops**
  746 with rms **909.2** — **8.79× the amplitude**. It selects *against* the phenomenon.
- switching recovers 2.5× more usable frames and turns subsets that had *no contiguous run* into
  computable numbers

## 3. Mean Welch power is the wrong statistic for a bursty limit cycle — use p99/max envelope

V57/V55 grinding, 18-26 Hz, matched creep: median **0.419** but **p99 0.891, max 0.898**. The apparent
"the 21 Hz halved on V57" lived **entirely in the median**, which is dominated by quiet time between
bursts. Bandpass → analytic envelope → order statistics. The operator predicted this ("perhaps your
windows are too large") before the data confirmed it.

## 4. ⚠ UNSOLVED — engagement and motion are COLLINEAR

LKAS is active **1.7%** below 0.5 m/s and **~100%** above it (corr = +0.627). **No speed bin on any route
has ≥3 windows in both arms.** So every recorded engaged/disengaged ratio (877×, 786×, 14,750×, 27.7×) is
a **moving-vs-stopped contrast wearing an engagement label**. Quote absolute engaged powers instead.
Breaking it needs a deliberate LKAS-on/off A/B at matched speed and angle.

## Also: a NaN can produce a silent false null

One `0x14A` frame arrives before the first `0x18F`, leaving the paired torque `NaN`. A **single** NaN
propagates through an FFT and makes every filtered sample NaN — which reads out as *"0 hands-off frames"*,
a plausible null rather than an error. Guard the input; don't trust it.

Related: [[accord-ratchet-and-grinding-are-two-symptoms]], [[feedback-operator-lived-experience]]
