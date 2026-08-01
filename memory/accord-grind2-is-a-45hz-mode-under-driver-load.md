---
name: accord-grind2-is-a-45hz-mode-under-driver-load
description: ★★ Grind #2 is a ~44.9 Hz Q≈37 resonance under heavy DRIVER steering load at creep, NOT LKAS-gated (1.33x vs grind #1's 6.63x), NOT a harmonic of the 20.9 Hz mode, and visible on the comma IMU. Its frequency is aliased and unresolved. V62's rate-lane doubling is the leading cause but band-specificity is untested.
metadata:
  type: reference
---

# ★★ GRIND #2 — a ~44.9 Hz mode under driver load, and it is a different animal from grind #1

Established 2026-08-01 from V65 routes `3a` (`4e55c1e0f4`, LKAS-on demo) and `3b` (`a4a7f4dbf1`,
LKAS-off demo + unrelated highway), plus a cross-build re-analysis of `2c`/`31`/`35`/`37`.

## What it is

| | grind #1 | **grind #2** |
|---|---|---|
| frequency | ~20.9 Hz | **~44.9 Hz**, sd 5.4, n = 43, **Q ≈ 37** |
| LKAS-gated? | **YES** — top-decile creep windows **100%** engaged, engaged/disengaged p99 **6.63×** | **BARELY** — 84.5% vs a 54.7% base rate, p99 **1.33×** |
| driver input | hands-off | **heavy**: `tq_avg` 1600–2700, \|angle\| 150–265° |
| speed | creep | creep (and reported at 10–20 mph on semi-hard turns) |
| fixed by V62? | ✅ 18–22 Hz **0.555 [0.467, 0.685]**, replicates on V65 | it is the thing V62 appears to have *caused* |

- ✅ **NOT a harmonic of grind #1.** Regressing the high-band peak on the 20.76 Hz mode's peak gives
  slope **0.173 [−0.92, 1.59]** against the 2.0 a harmonic requires. Independent mode.
- ✅ **It is a real mechanical vibration** — visible on the **comma device's IMU**, a sensor sharing no
  path with the EPS. First use of the IMU in this kit. ⚠ An IMU detection is only interpretable
  alongside its **positive control** (grind #1 visible on the same sensor).
- 🛑 **THE FREQUENCY IS ALIASED AND UNRESOLVED.** CAN is a ~100.5 Hz grid ⇒ Nyquist 50 Hz, so **44.9 Hz
  and ~55.6 Hz are the same observation.** The IMU's median rate is **~101 Hz** — only 0.5 Hz from CAN —
  so **IMU/CAN frequency agreement carries NO information about the alias** and must never be quoted as
  if it did. A dedicated alias test came back **underpowered** (slope −1.16 [−4.15, 2.26]).
  ⇒ It does not block a fix: the rate lane's problem is a *selectivity ratio* that is bad at both.

## Attribution to V62's rate-lane doubling: SUGGESTIVE, leading, not established

Corner-conditioned exposure (creep ∧ \|driver torque\| ≥ 1200 ∧ \|angle\| ≥ 100°), measured:

| build | Kd | corner s | burst blocks | max |
|---|---|---|---|---|
| V61 `r31` | 0 | 43.1 | 0 | 362 |
| V59 `r2c` | 1× | 36.8 | 1 | 448 |
| V64 `r35` | 1× | 25.4 | 0 | 314 |
| **V62 `r37`** (ordinary driving) | **2×** | **49.8** | **9** | **3837** |
| V65 `r3a`/`r3b` | 2× | 111.7 / 64.9 | 10 / 8 | 4046 / 3024 | ⚠ **PROVOKED — excluded from rate claims** |

⇒ The low-dose arm had **2× the corner exposure** and produced **1** burst against V62's **9**; maxima
rose **8.6×**. *"They never went there"* is refuted. Rough rate 0.0095/s vs 0.181/s ≈ **19×**.

### ★★★★ The band table — the root-cause identification

Corner-conditioned extreme-tail maxima, 219 blocks:

| band | Kd=1× | Kd=2× | **ratio** | p |
|---|---|---|---|---|
| 1–4 Hz (driver) | 4709 | 4763 | **1.01** | 1.00 |
| 6–9 Hz | 2773 | 3335 | 1.20 | 0.037 |
| 10–16 Hz | 2520 | 2005 | **0.80** | 1.00 |
| **18–22 Hz — grind #1** | 3656 | 1269 | **0.35** | 1.00 |
| 24–28 Hz | 485 | 1289 | **2.66** | 0.013 |
| 30–40 Hz | 373 | 1113 | **2.98** | 0.013 |
| **40–49 Hz — grind #2** | 301 | **3526** | **11.71** | **0.0003** |

⇒ **Monotone with a crossover at 22–24 Hz**, driver band flat as a control ⇒ **not generic roughness**.
**One knob cut grind #1 by 2.9× and raised grind #2 by 11.7×.**

### ✅✅ AND THE COMMA IMU REPRODUCES IT, on a sensor sharing no path with the EPS

Same corner, Kd=2× / Kd=1×, on the accelerometer/gyro:

| band | median | **p95** | **max** |
|---|---|---|---|
| 1–4 Hz | 0.95 | **0.76** | 1.21 |
| 18–22 Hz | 1.05 | 1.20 | 1.33 |
| 24–28 Hz | 1.04 | **0.65** | 0.91 |
| 30–40 Hz | 0.89 | 1.25 | 2.22 |
| **40–49 Hz** | 0.87 | **6.27** | **6.71** |

Medians ~1 everywhere (the phenomenon is in the tail); the rise is confined to **40–49 Hz**.
⚠ **The IMU does NOT show grind #1's reduction** (18–22 Hz 1.20/1.33), and its grind-#1 positive control
is weak. That is a *limitation to state*, but it is also physically coherent: grind #1 is a **torsional
column mode** (wheel inertia on the torsion bar) that need not reach the chassis, while grind #2 is the
one the operator describes as *"the entire car vibrates"*. **The IMU's selectivity matches the
operator's own description of which one shakes the car.**

🛑 **What still keeps this short of airtight:**
1. **The matched-cell mean says the opposite** — 30–49 Hz **0.913 [0.791, 1.026]**, inside the null
   floor. Reconciled by the matched q99 threshold being **317** against burst amplitudes of 3000–4000,
   i.e. the mean test is blind to the phenomenon. See [[feedback-mean-and-tail-must-be-reported-together]].
2. **Band-specificity is UNTESTED.** If 10–16 Hz and 24–28 Hz burst blocks also jump at Kd = 2×, this
   is generic roughness and the mechanism is wrong. **Do not build on this until that test lands.**

## The mechanism, if the attribution holds

`gp-0x4f62` is a **4-sample finite difference at 1 kHz** (`2*(x[n]−x[n−4])/4`, delay cal `0xC6C42` = 4).
A differentiator's gain **rises** with frequency: **1.93×** at 41.6 Hz and **2.60×** at 58.9 Hz relative
to 20.9 Hz. V62's ×2 is **flat in frequency**, so it raised the high band harder in absolute terms than
the mode it fixed. The V62 build note computed selectivity only against the *driver* (1 Hz, 14.6:1) and
never against a **higher** mode, where the ratio runs the wrong way.
Arithmetic: `analysis-2020accord/rate_lane_frequency_response.py`.

🛑 **A FILTER CANNOT FIX THIS — structural, not numeric.** A differentiator rises at +20 dB/dec and one
real pole falls at −20 dB/dec, so the cascade is **flat** above the corner: a single pole drives the
41.6/20.9 selectivity toward 1.0 and can never push it below. Two poles low enough to bite by 42 Hz
cost ≈2·atan(20.9/fc) at 20.9 Hz — at fc = 20 Hz that is −92°, turning the lane's +75° lead into −17°
and **destroying the damping V62 bought**. Raising the delay cal `0xC6C42` fails identically (D = 24
zeroes 41.7 Hz but leaves −0.3° at 20.9 Hz = a pure spring). **Do not re-propose either.**

⇒ The separation must come from a variable that differs between the symptoms. **Driver torque separates
them >8×**; steering rate only ~2× at creep with overlapping p90s (371 vs 359 counts); LKAS engagement
separates grind #1 but **not** grind #2.

See also [[accord-gp683c-dead-gate-is-a-free-lkas-arm]], [[accord-r24-gain-b-four-pointer-arrays]],
[[accord-v62-fixed-the-grinding]], [[feedback-episodes-not-windows]].
