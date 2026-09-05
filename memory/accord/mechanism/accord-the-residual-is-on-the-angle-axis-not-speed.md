---
name: accord-the-residual-is-on-the-angle-axis-not-speed
description: The operator's "understeer below 20 mph, oversteer above" is a STEERING-ANGLE effect, not a speed effect — the two axes are confounded in his driving, and the SR map's >=48 deg knots are ~9% too low
metadata:
  type: project
---

🛑 **The operator's speed split is confounded with angle, and ANGLE is the resolvable axis.**
Measured on r39 + r3a + r3c (V282 firmware unchanged on all three, 2026-09-05).

In his driving, **"hard corner below 20 mph" ≡ large steering angle** and **"above 20 mph" ≡ near
centre**. Above 10° of steering at 20–40 m/s the corpus has **essentially no data at all**, so the
speed axis cannot be read independently of the angle axis.

Map error (map/fit; >1.00 = map ratio too high → oversteer; <1.00 = too low → understeer), pooled:

| \|ang\| \ v | 2–6 m/s | 6–9 | 9–14 | 14–20 | 20–40 |
|---|---|---|---|---|---|
| 1.5–10° | 0.995 | 1.021 | 1.031 | 1.016 | 1.037 |
| 10–25° | 0.980 | 1.056 | 0.988 | 1.021 | (n=160) |
| 25–48° | 0.994 | 1.007 | 1.017 | (n=2) | (n=0) |
| **48–90°** | (n=242) | **0.926** | 0.998 | (n=0) | (n=0) |
| **90–400°** | **0.932** | **0.936** | (n=30) | (n=0) | (n=0) |

Across the top row (speed, near centre): **flat within ±4 %**. Down the 6–9 m/s column (angle): a
hard break at 48°.

**THREE-WAY DECOMPOSITION** of the angle→curvature mismatch (r39): **FLAT** (ratio level)
**0.006–0.012** — already spent by the map, do not touch · **ANGLE** (map knots ≥ 48°) **~0.09** —
the largest reachable term measured · **SPEED** (near-centre slip) **0.042**, not resolvable.

**ARBITRATED ON A THIRD INSTRUMENT** [EVIDENCE]: wheel-speed differential yaw from raw CAN `0x1D0`
(no gyro, no roll model, no Kalman, no calibration matrix). Near-centre (|sa| < 48°), scale-normalised,
r39, 7–30 m/s: spread **0.074 / 0.037 / 0.054** (wheel rear / wheel front / gyro) against
**0.155 / 0.089 / 0.096** unstratified. Restricting to near-centre halves the spread on every
instrument and leaves no resolvable crossing of 1.000. ⚠ The ≥48° stratum is itself UNRESOLVED on
that instrument (10 gated blocks) — large-angle events are transient and a steady-state gate removes
them — so the knot finding rests on the two angle-fit pipelines.

**THE FIX** (`selfdrive/controls/lib/latcontrol_vehicle_tunes.py:86`, breakpoints unchanged):
`[16.00, 16.00, 15.02, 14.52, 13.97, 13.75, 13.50, 12.81, 11.67, 11.06]` →
`[16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]` — ×1.09 from 60° up,
clamped at 16.00 to stay monotone. Measured at low speed where slip is negligible and the roll term
is 0.3–1 % of the signal, so it is a rack-geometry measurement. Because the table is a LERP it does
not touch the 0–48° flat segment, and **median |sa| above 11 m/s is 5–8°, so it cannot affect the
highway behaviour.** ⚠ Magnitude rests on 3–8 s per bin; if it overshoots, halve it (×1.045).

**Why it works:** the map feeds `VM.sR`, which enters the **measurement path only**
(`controlsd.py:478` → `latcontrol_torque.py:232`, and `calc_curvature` carries a leading minus).
A map ratio below the true rack ratio makes the controller over-read its own curvature, so the loop
backs off and settles **below** command. See [[accord-lkas-commands-rate-not-torque]] and
[[accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire]].

🛑 **This SUPERSEDES the attribution of the low-speed shortfall to the P-only firmware deadband**,
which its own author withdrew: at v < 9, `R_m` is flat across angle strata (1.07–1.21) while `1/rho`
swings 1.086 (<48°) → 0.935 (≥121°) — a 14 % move entirely on the measurement, replicated on all
three arms. See [[accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived-understeer-is-mostly-sr-12-5]].

**Do NOT touch** the flat SR level (0.14 σ from the map's 16.000) or `stiffnessFactor` (the
near-centre speed term is 0.042 and not resolvable). Aiming a flat SR at the highway oversteer
deepens the low-speed under-delivery from −7.3 % to −12.4 %.
