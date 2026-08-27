---
name: accord-rate-f-is-0p7996-of-true-degs
description: "rate_c and rate_f are ONE channel, not two - rate_c = 1.2506 x rate_f at every frequency with identical phase. rate_c is true deg/s; rate_f is 0.7996x. Any past |Z|, impedance or inertia number built on rate_f is 1.25x too large. Resolved from data at 0.2-0.7 Hz, no Ghidra needed."
metadata:
  type: reference
---

# 🛑★★★★ THE deg/s SCALE, RESOLVED FROM THE DATA

2026-08-21, `rlog-tools/studies/identification/plant_scale_resolve.py`. This was the blocker that forced the column
impedance work to quote only a scale-free ratio.

## Method
`ang` is openpilot's own decoded `carState.steeringAngleDeg` (`ang == wang == cs_ang` **bit-for-bit**),
so its degree scale is the DBC's. `ang` is quantisation-limited *in band* — but that is a
high-frequency problem, and **a scale constant does not care which band it is measured in.**
At **0.2–0.7 Hz** the wheel swings tens of degrees and `d(ang)/dt` has SNR ~300.

| channel | gain vs `d(ang)/dt` | over |
|---|---|---|
| **`rate_c`** | **0.9994 [0.9671, 1.0236]** | 12 windows, 6 routes, coherence 0.95–0.999 |
| `rate_f` | **0.7996** | same |

⇒ **`rate_c` is true deg/s. `rate_f` is 0.7996×.** `rate_c = 1.2506 × rate_f` at every frequency with
identical phase — **they are ONE channel, not two.**

## 🛑 CONSEQUENCES
1. **Any past `|Z|`, impedance or inertia number built on `rate_f` is 1.2506× TOO LARGE.**
2. **Any past claim of "agreement between `rate_c` and `rate_f`" is VACUOUS** — they are the same
   channel scaled.
3. Ratios of the form `J/b` are **untouched** (the scale cancels), so
   [[accord-column-cannot-host-q10-at-8hz]]'s scale-free result stands exactly as reported.

## ⊕ Two neighbouring channel defects found at the same time
- **The `0x18F` stale-frame trap is 12.5 ms, not the recorded ~10 ms** — `arg(rate_f / d(ang)/dt)` is
  linear at **−4.51 deg/Hz** across 2–24 Hz. [EVIDENCE]
- **`ang` (`0x14A`, LSB 0.1 deg) is quantisation-limited in band**: 6–9 Hz band-RMS 0.0155–0.032 deg
  against a 0.0071 deg quantiser floor (SNR 2.2–4.8, below one LSB), and `|rate_f / d(ang)/dt|` falls
  to 0.15 by 20 Hz ⇒ the differentiated angle is **~7× pure noise there**.
  🛑 **Do not use a differentiated `ang` as a denominator above ~6 Hz.**
- ⚠ **UNRECONCILED:** `docs/research/ANALYSIS-2026-08-20-torsion-bar-and-lane-weight.md` quotes `|ang|` at
  6–9 Hz as **0.089 deg**; measured **0.0155–0.032** on every route under an engaged mask. Factor 3–6,
  not chased. Flagged, not claimed as an error.

Related: [[accord-column-cannot-host-q10-at-8hz]] · [[accord-raw14-offbyone-in-every-cache]]
