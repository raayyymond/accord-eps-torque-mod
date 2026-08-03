---
name: accord-three-timing-instrument-constants
description: 1/median(dt) is the WRONG CAN rate (reads 100.76 on a 100.000 Hz grid); the microphone pipeline delay is 115 ms not 75; and accel/gyro carry separate timestamp offsets, so no lead/lag under ~50 ms is physical
metadata:
  type: reference
---

🛑 **THREE TIMING CONSTANTS NOBODY HAD PINNED DOWN.** Each will cost a future session real time.

## 1. `1/median(dt)` is the WRONG CAN rate
CAN frames are timestamped **per log packet**, not per frame. On route `47`, **12 % of `dt` exceed
15 ms and p10 is exactly 0** (two frames sharing one packet time). `median(dt)` then reads
**100.76 Hz** on a grid that is **100.000 Hz to 2e-5**.

⇒ **Use the MEAN rate `(n−1)/(t[-1]−t[0])` and an index lattice `t[0] + i/fs`.** Measured per route:
99.989 / 100.0008 / 99.9994 / 99.9997 / 100.0001 / 100.0005 (r3a/r3b/r37/r47/r2b/r2c).
Recorded timestamps wander from the lattice by up to **7.5–10.3 ms** — **that is the CAN alignment
uncertainty**, and it is the floor on anything timed against CAN.
⚠ Same family as the `fs_of()` bias already on record; this is the *cause*, stated for the CAN grid.

## 2. The microphone pipeline delay is 115 ms, not 75
**MEASURED** against road impacts — a pothole radiates sound and shakes the chassis within ~3 ms, so
cross-correlating IMU 30–49 Hz against `soundPressure` over long road stretches has **no physical lag
in it**. Sweeping the assumed lag: peak at **115 ms**, 35 road segments, peak ρ **0.512**.

`micd.py` alone predicts **75 ms** (half the trailing 100 ms boxcar + ~25 ms mean staleness of the
10 Hz publish loop against the 50 ms audio callback). **The extra ~40 ms is audio-capture buffering**,
which no document in this kit had accounted for.
⇒ **Any sound↔CAN alignment must subtract 115 ms.** The 10 Hz publish grid then quantises whatever
is left to 100 ms.

## 3. Accel and gyro are SEPARATE streams with SEPARATE hardware-timestamp offsets
`extract_imu_cache.py` maps each of `at` and `gt` to the CAN base by its **own** median
`logMonoTime − hw` offset, so any constant sensor→log latency is **absorbed and unrecoverable**, and
the two streams absorb *different* amounts. `a_off_sd` runs **1.47–2.19 ms** within a segment.

Demonstrated empirically: on the creep bursts the bar→IMU lags are `ax` **+45 ms [+30, +60]** and
`gx` **+80 ms [+60, +120]**; on **road excitation with no grind** — same instruments, different
excitation — they are **+90 ms** and **+40 ms**, i.e. **the same magnitudes with the order swapped**.

⇒ **±50 ms is the empirical lead/lag floor, and NO physical ordering between bar, chassis and sound
is resolvable in this corpus.** True transit is 0.2 ms structure-borne over ~1 m of steel at 44 Hz
and ~3 ms airborne — **30–500× below the finest step any of these instruments can take**. All three
channels rise within one 100 ms block (sound residual after subtracting the 115 ms pipeline: +35 to
+85 ms, under the grid step).
🛑 So a lead/lag test **cannot** distinguish "column drives chassis which radiates" from "a common
input excites all three". The discrimination is carried by **coherence** instead —
[[accord-grind1-is-torsional-grind2-reaches-the-chassis]].

⇒ `analysis-2020accord/grind2_trichannel.py` §0/§3/§3c · `_grind2_trichannel.json`.
