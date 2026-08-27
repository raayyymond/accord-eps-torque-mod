---
name: accord-highway-event-rate-null-with-power
description: The highway 40-49 Hz null re-tested with an EVENT-RATE statistic instead of a pooled level — same null, min detectable 1.61x, with two validated positive controls
metadata:
  type: reference
---

★★★ **The published highway null was challenged on the grounds that a pooled median is blind to rare
threshold-like bursts. The event-based machinery that FOUND creep grind #2 was pointed at the highway
population, and it reaches the SAME null.** Two independent statistics, one answer ⇒ the earlier null
is **not** a statistic-choice artefact.

## The event-rate test (events per engaged-highway second, by rate-lane dose)
Detector: contiguous excursions of the band envelope above **10× the Kd=1 median in the same speed
band** — threshold derived from this population, nothing imported from creep's 500 counts. Episodes
are 10 s blocks; every ratio is quoted against a split-half null with the identical estimator.

**v ≥ 12 m/s**, speed-stratified (599 / 803 / 1002 s exposure):

| band | Kd 2/1 | Kd 2.44/1 | split-half null | min detectable @80 % |
|---|---|---|---|---|
| **18–22** (positive control) | **0.565 [0.329, 0.984]** | **0.319 [0.130, 0.661]** | [0.50, 2.30] | 1.51× |
| 30–40 | 1.296 [0.666, 3.686] | 1.489 [0.627, 4.476] | [0.16, 7.70] | 1.75× |
| **40–49** | 0.855 [0.432, 1.702] | **1.152 [0.496, 2.690]** | [0.36, 2.50] | **1.61×** |

**v ≥ 22 m/s**, events/hour, Kd 1.00 / 2.00 / 2.44 — **monotone rising in NO band**; at 40–49 Hz the
maximum-dose build has the *lowest* rate (286.3 / 398.4 / **218.1**).

## Why this null is believable
- ✅ **Positive control #1:** grind #1's *event rate* falls monotonically with dose and clears its own
  null, matching the published level result (0.509 [0.39, 0.92]) in direction and size.
- ✅ **Positive control #2:** the same spectral instrument resolves wheel order 1 at prominence up to
  **79** (see [[accord-highway-30-49hz-has-no-line]]).
- 🛑 **Power is stated, not assumed:** a **1.61×** rate difference at 40–49 Hz would have been
  detected at 80 % power. A 2.0× effect is comfortably inside that.

## What is NOT resolved, and what it would cost
- **v ≥ 28 m/s is under-powered** — Kd=1 holds 38 s and 4 events, min detectable **4.4×**. Closing it
  needs **~235 s (3.9 min)** of engaged >28 m/s highway per dose arm.
- **v ≥ 22 m/s, 40–49 Hz** needs **308 s** per arm; Kd=1 has 214 s ⇒ **~100 more seconds** on a
  stock-Kd build closes it.
- 🛑 **The corpus holds 0.0 s of LKAS-off driving above 12 m/s**, verified by `carControl.latActive`
  **and** independently by the firmware's own `0x18F` byte4 bit3 (`sca`). The operator's *"it only
  happens with LKAS on"* is **untestable by construction**, not weakly testable. ⚠ `cruiseState.enabled`
  would have manufactured a fake 123–187 s LKAS-off arm per route — it is the wrong signal.

## The bound worth keeping
CAN is 100.000 Hz (Nyquist 50.00) and the IMU lattice 101.026 Hz (Nyquist 50.51). **A fixed-pitch
resonance above ~50 Hz is invisible to both**, and a fixed pitch is exactly how such a mode would
feel — consistent with Honda's own 1 kHz detector peaking near 61 Hz. ⚠ Channel weighting: the EPS
CAN torque channel rolls off 11–13 dB by Nyquist so the CAN-based nulls are **not** alias-contaminated;
the IMU **accelerometer** is flat-to-rising near 40–50 Hz and its statements there are alias-suspect.
The gyro axes reach the same null as the bar, which is useful independent corroboration.

⇒ Reproduce with `analysis-2020accord/studies/highway/highway_h1_test.py` and `analysis-2020accord/studies/highway/highway_event_hunt.py`.
Related: [[accord-both-instruments-blind-above-50hz]], [[accord-highway-events-are-the-loading-tail]],
[[accord-route47-owns-the-fast-highway-exposure]], [[feedback-episodes-not-windows-and-the-noise-floor]],
[[accord-v67-flew-both-grinds-fixed]].
