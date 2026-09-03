# The r35 "largely pronounced grinding incident" — 23:48:21, segment 16 (V281 rev 3, Kp flat 248)

Subagent `grindr35`, 2026-09-03. Script `grind_incident_r35.py` (this folder; full output `_scratch/grind_incident_r35.txt`; extra streams read by
`grind_r35_extra_read.py` → `_scratch/r35_extra.npz`, segments 13–18). Route r35 = `75604b0a432fdc89_00000035--580292087d`, V281 rev 3
(LKAS rate-PID Kp LERP flat 248; map ×6 line, Kd 128, fb clamp 46080, 427 tap byte-identical to V280 rev 2 — verified from both images at run
time). Comparator r34 = V280 rev 2, new tune. Analysis only. Every CAN stream was put back on its nominal frame counter before any spectrum or
phase (creep20's `dejitter`; residual p50/p90 4.6/8.6 ms on both 0x18F and 0x1AB).

## 0. Headline

1. **Anchor [EVIDENCE]:** unix = logMonoTime + **1788417054.155 s** (GPS fix-valid n = 2976, sd 0.007 s; post-sync `clocks` agrees to 0.027 s).
   Local = **PDT (UTC−7)**, as for r32/r34. Route t = 0 (first 0x18F) = 23:31:24 PDT 2026-09-02; 23:48:21 → **route t = 1016.7 s = segment 16**,
   exactly the operator's segment. The line detector's core is **t 1016.0–1018.0 s (23:48:20–23:48:22)** — 0.0 s from his timestamp.
2. **What it was [EVIDENCE]:** the **start of a left turn from a standstill**. Stopped t 1001.6–1014.4 (brake on, left blinker on from 999.9),
   lateral re-engaged at t 1014.5 as the car moved off (gas from 1014.4), command ramped −86 → −1963 in 1.5 s (idx 10 → 137), the wheel ran
   +6° → +170° at 37–60 deg/s (p90 63), v 2.6–3.8 m/s (6–8 mph), T −300 → −840, hands light-on (|tq| p50 388, p90 991 raw) — then at
   t 1018.2 the driver grabbed the wheel (2500–2770 raw; the post-PID fade drops to 0.30) and finished the turn; disengaged at 1035.3.
3. **The grind is a 0.9 s BURST of the same 20 Hz mode, plus a 7.5 Hz companion [EVIDENCE]:** bar 20.12 Hz ×22.8, rate 20.05 Hz ×43.4, tap
   20.09 Hz ×27.1, bar↔rate coherence 0.98, bar↔tap 1.00. Bar 18–22 = **240 raw over the core, 306 in the peak second, Hilbert envelope
   peak 500 raw at t 1017.2**; rate 18–22 = **13.8 deg/s** (envelope peak 28.6); tap T 18–22 = **160 counts** on a |T| of 428 (ripple/level
   0.37). Simultaneously a **7.46 Hz line ×88** on the bar: 6–8.5 Hz bar 596 raw, rate 8.7 deg/s, tap 178 (ripple/level 0.42) — the
   strong-turn stutter class, at idx 100–140.
4. **Shape [EVIDENCE for the fit, BELIEF for the reading]:** the 20 Hz envelope grows **exponentially at +1.42 /s for 0.9 s** (e-fold 0.70 s =
   14 cycles: 41 → 121 → 166 → 436 → 493 raw at 0.25 s steps) while idx climbs 21 → 137 and the wheel rate 8 → 60 deg/s, then **collapses at
   −3.9 /s in 0.44 s** as the hands tighten (|tq| 270 → 800–1200 raw from t 1017.0) — a full second before the 2500-raw grab. Only 32 % of the
   core sits within 50 % of the peak; envelope sd/mean 0.78. **It is not a plateau; it is a transient that tracked the excitation ramp and
   was killed by the hands.** The envelope correlates with |rate| (+0.52), not with the 7 Hz envelope (+0.20).
5. **No rail was active [EVIDENCE, 1 kHz mirror with the live arms]:** P rail 0.000 (|P| p90 7494 of 15360; at Kp 248 P rails at |E| 15855, |E|
   p50 3084), D rail 0.040, sum rail 0.021, T cap 0.000, fb clamp 0.000 (|fb| p90 15024 of 46080), tap saturation 0.000, setpoint taper 0.000,
   the dead 2240 cliff 0.000, post-PID fade 1.00 (min 0.65 at the end). **The chain was linear through the burst.**
6. **The mirror reproduces it and D carries two thirds [EVIDENCE]:** T_sim vs tap in the 18–22 band: 188 vs 159 (P 82, D 167), corr 0.86,
   coherence 0.99, phase +31° (the usual ~4 ms stream offset). D/P = 2.0 at Kp 248 as the arithmetic says. Kd 0 → 82 (0.44×), Kd 64 → 124
   (0.66×), 2.5 Hz output-lag pole → 95 (0.50×), rate low-passed < 15 Hz → 35 (0.19×), **command frozen → 186 (no change)**, V280's Kp
   (592 at this idx) → 180 with P railing 17 % of ticks. **Not the command; 81 % through the rate feedback.**
7. **Bit 4 (sign r24) reads −165° re the wire rate at 20.3 Hz (coherence 0.70, −152…−179° across 17–22 Hz) [EVIDENCE for the number,
   NOT for its meaning]:** by the r24 record's convention that is PUMP, where the creep record read DAMP (+2…−16°). But the closed form
   from the measured bar/wire phase (+143°) predicts **+38°**, and the same sign transform applied to T — a signal we have — reads −92° where
   T itself reads +84°: **the sign transform fails in the core** (T never changes sign, bit 7 duty 0.97, coherence 0.02; the bar carries a
   7.5 Hz tone as large as the 20 Hz one, so sign(r24) is not the sign of its 20 Hz component). **The bit-4 phase in the incident is
   unreadable; it does not license "r24 pumped".** Duties: bit 7 0.97, bit 6 0.00, bit 5 0.89, bit 4 0.48, bit 3 0.52.
8. **Nothing on the chassis [EVIDENCE]:** gyro 18–22 Hz 0.0003–0.0005 rad/s, identical to the engaged minute before (0.0002–0.0006); lateral
   accel 18–22 0.076 vs baseline 0.067 m/s². Bar/rate/tap only — the 48-event record holds.
9. **What differs from the r34 "very very attenuated" seconds [EVIDENCE]:** not the mode (same 20.1 Hz, same D-dominated mirror), not the
   peak amplitude (r34's loudest attenuated window t 337–339 reached envelope 609 raw, per-second 281; this one 500 / 306) — **the operating
   point and the company**: idx 100–137 vs 11–34, wheel rate 37–60 vs 6–42 deg/s, |T| 437 vs 134–408, angle sweeping through 60–110° at
   the start of a turn vs holding 13–32°, hands light-on and tightening (|tq| 390 → 1200) vs hands-off (150–375), and a **7.5 Hz stutter
   ripple of 596 raw riding underneath** (r34's creep windows: 6–10 Hz bar ≈ 250 p50). BELIEF: "pronounced" is the 20 Hz burst and the 7 Hz
   ripple arriving together on a fast-moving loaded wheel, felt through hands that were on the rim.
10. **V281 vs V280 creep-line census [EVIDENCE]:** engaged v < 6 windows: **line present 17 % (r35) vs 59 % (r34)**, bar 18–22 p50 27 vs 78
    raw; creep (1–3 m/s) 13 % vs 63 %, amp p50 21 vs 75; by idx bin (p50 raw) 0–20: 24 vs 43, 20–60: 38 vs 103, 60–120: 65 vs 149, > 120: 22 vs
    88. Frequency 20.25 ± 1.02 vs 20.54 ± 2.08 Hz, lower in every idx bin by 0.2–0.8 Hz. The 5–12 Hz line is also rarer (59 % vs 75 %, bar 6–10
    p50 91 vs 245). **On this one route Kp flat 248 cut the creep line's presence ~3.5× and its amplitude ~2.5× at matched idx** — larger
    than creep20's open-loop −6 % for a 341 cap. BELIEF on the mechanism: the closed loop's sensitivity peak (Ms 2.6 → 1.8, direct-G table)
    shrinks with Kp; the open-loop mirror does not see that. The incident is the **98th percentile** of r35's own windows and the 84th of r34's.

## 1. Anchor and context (section 1 of the output)

| item | value |
|---|---|
| GPS offset | unix = logMonoTime + 1788417054.155 s (n 2976, sd 0.007); `clocks` post-sync 1788417054.181 (+0.027) |
| route start / end | 23:31:24 / 23:49:29 PDT, 1085.1 s, engaged 919.5 s |
| 23:48:21 PDT | t 1016.7 s, segment 16 |
| liveTorqueParameters nearest | latAccelFactor 2.110 (raw 5.159), friction 0.030 (raw 0.136), liveValid 0 |
| controlsState in the core | torque controller active 1.00, \|error\| p50 0.587, \|output\| p50 0.404, saturated 0.00 |
| curvature in the core | −0.0142 1/m (a left turn), angle −3 → +80° inside the 2 s core, on to +170° by t 1019 |

Preceding minute: disengaged 987.3, engaged 989.4, disengaged 1001.6 (stopped 1001.6–1014.4, brake 995–1014, left blinker 999.9–1022.7), engaged
1014.5, gas 1014.4–1029.3, disengaged 1035.3 (brake 1034.4). Per-second trace (bar 18–22 / 6–10 raw, rate 18–22 deg/s, tap 18–22, idx, |tq|):

| t | local | v | ang | cmd | idx | \|tq\| | T | bar 18–22 / 6–10 | rate 18–22 | tap 18–22 | bar line | rails P/D/fb | fade |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1014 | 23:48:18 | 0.3 | −8 | 0 | 0 | 94 | 0 | 2 / 7 | 0.23 | 4 | — | 0/0/0 | 1.00 |
| 1015 | 23:48:19 | 1.4 | −7 | −86 | 10 | 131 | +58 | 19 / 47 | 0.81 | 13 | 23.0 ×4 | 0/0/0 | 1.00 |
| 1016 | 23:48:20 | 2.6 | +6 | −1283 | 80 | 299 | −300 | **106 / 245** | 5.2 | 81 | 20.2 ×106 | 0/0.02/0 | 1.00 |
| **1017** | **23:48:21** | 3.2 | +59 | −1963 | 121 | 653 | −672 | **306 / 873** | **18.8** | **191** | 21.1 ×54 | 0/0.06/0 | 0.98 |
| 1018 | 23:48:22 | 3.8 | +112 | −1875 | 116 | 2529 | +212 | 33 / 198 | 1.8 | 21 | 20.5 ×5 | 0/0.04/0 | 0.30 |
| 1019 | 23:48:23 | 4.3 | +170 | −870 | 106 | 475 | −742 | 40 / 379 | 1.7 | 29 | 25.7 ×2 | 0/0.08/0 | 1.00 |
| 1021 | 23:48:25 | 5.3 | +135 | +2406 | 150 | 485 | −569 | 75 / 766 | 3.7 | 73 | 20.0 ×19 | 0/0.06/0 | 1.00 |
| 1022 | 23:48:26 | 6.0 | +47 | +1670 | 104 | 457 | −152 | 122 / 751 | 5.0 | 101 | 20.0 ×58 | 0/0.07/0 | 1.00 |
| 1023 | 23:48:27 | 6.7 | +11 | +447 | 28 | 225 | −38 | 118 / 331 | 4.4 | 68 | 20.0 ×113 | 0/0.01/0 | 1.00 |

A second, smaller 20 Hz stretch (t 1020.5–1022.5, 79 raw, idx 123) sits on the unwind of the same turn.

## 2. The incident core (t 1016.0–1018.0)

**Lines (Hann periodogram, nfft 4096, de-jittered):** bar 20.12 Hz ×22.8, rate 20.05 ×43.4, tap 20.09 ×27.1; 5–12 Hz: bar **7.46 Hz ×88**, rate
7.30 ×27.5; 30–45 Hz: 37.3 ×5 (nothing); no 2·f0. Bar band amps (raw): 6–10 **642**, 10–15 126, 15–18 130, **18–22 240**, 22–26 45, 24–28 22
(control), 30–45 13. Rate (deg/s): 6–10 9.1, 18–22 13.8, 24–28 2.0. Tap (native 50 Hz): 18–22 160, 24–28 2, |T| p50 428, mean −472.
bar/wire at 20 Hz: coherence 0.98, phase **+143°** (creep record +114°); at 7.4 Hz |H| 8.7 raw per deg/s, −93°, coherence 1.00 (the wheel's
inertial reaction, as in the F7 record). Operating point: v 2.9 m/s, |angle| p50 28 (−3 … +80°), cmd p50 −1629 (|cmd| p90 2217), idx p50/p90
100/137, |tq| 388/991, T −437 (|T| p90 839), |rate| 37/63 deg/s, engaged 1.00, carState.steeringTorque 381.

**Envelope at 20.1 ± 2 Hz (Hilbert), bar raw | rate deg/s | tap, 0.25 s steps from t 1015.5:** 20|0.8|14 · 34|1.5|19 · 41|1.9|22 · 121|5.5|80 ·
148|5.4|108 · 166|10.2|115 · **436|23.5|277 · 371|24.7|269** · 170|10.7|112 · 39|2.9|33 · 64|4.0|53 · 34|1.4|19 (t 1018.25, |tq| 2502) · 18 · 15 · 10.
Fit: rise **+1.42 /s over 0.91 s** (e-fold 0.70 s, 14 cycles), decay **−3.91 /s over 0.44 s**; rate envelope rise +1.79 /s, decay −5.42 /s; peak 500
raw at 1017.21. At 50 ms resolution the envelope is a single hump (peak 493 at 1017.15–1017.20) with a dip at 1016.7 (61 raw) between two
lobes — while the wheel rate runs +37 → +83 deg/s and |tq| climbs 270 → 813 → 1010 → 1187 through 1017.0–1017.8. r34's loudest attenuated window
(t 334–344) has the same bursty shape (peak 609 at 338.98, rise +10 /s over 0.22 s, decay −2.1 /s, env ≥ 0.5 peak 10 %, sd/mean 0.99).

**Rails (V281r3 cells, live fade, 1 kHz, open loop on the measured rate):** P 0.000 · D 0.040 · sum 0.021 · T cap 0.000 · fb clamp 0.000 · fade
p50/min 1.00/0.65 · taper 0.000 · old cliff 0.000 · tap sat 0.000. |P| p50/p90 2986/7494, |D| 1808/7904, |fb| 9294/15024, |E| p50 3084.

**Cave byte and the bit-4 phase:** see headline 7. Full table at 15.6–25 Hz (core ±4 s, nperseg 128, 14 windows): bit 4 re wire −145 … −180°,
coherence 0.26–0.61; bit 3 −104° (0.48). The control that the r24 record used (sign bar vs bar, ±20°) is not applicable to a two-tone bar; the
control available here (sign T vs T: −92° vs +84°) fails by 176°. Closed form from the measured bar/wire phase: ang(bar/wire) + ang(D4) + 180 =
**+38°** vs the bit's **−165°**. Unresolved; not evidence either way.

**Command:** p50 −1629, range −2667 … −224, |Δcmd| p50/p90 42/120, changes every frame; a line at 19.87 Hz ×68 with 18–22 amp 48 counts (the
outer loop echoing the column, 3 % of level) — **inert on T** (mirror with the command frozen: 186 vs 188). **IMU:** no signature (headline 8).

## 3. Against the attenuated seconds and the census (section 3 of the output)

| window | v | idx | \|ang\| | \|T\| | \|tq\| | \|rate\| | bar 18–22 | rate 18–22 | f | tap 18–22 |
|---|---|---|---|---|---|---|---|---|---|---|
| **r35 incident core 1016–1018** | 2.9 | 100 | 28 | 437 | 388 | 38 | **240** | **13.8** | 20.12 | **160** |
| r34 t 336–342 (attenuated, loudest) | 2.5 | 32 | 40 | 408 | 375 | 42 | 173 | 7.6 | 20.18 | 132 |
| r34 t 419–422 | 2.1 | 13 | 7 | 199 | 148 | 5.6 | 123 | 4.8 | 20.42 | 75 |
| r34 t 437–440 | 10.6 | 18 | 6 | 134 | 280 | 10.5 | 128 | 4.9 | 20.26 | 71 |
| r35 creep, line present (n 15) | 2.1 | 18 | 7 | 202 | 141 | 5.3 | 49 | 2.0 | 20.12 | |
| r35 creep, line absent (n 99) | 1.8 | 10 | 3 | 126 | 170 | 2.6 | 20 | 1.0 | | |
| r34 creep, line present (n 82) | 2.3 | 23 | 11 | 239 | 217 | 13.3 | 109 | 4.9 | 20.40 | |
| r34 creep, line absent (n 49) | 2.2 | 16 | 9 | 189 | 215 | 8.7 | 38 | 1.8 | | |
| r34 v<6, amp ≥ 150 (n 55) | 4.7 | 96 | 57 | 605 | 1120 | 48 | 174 | 8.0 | 20.18 | |

The incident's class on r35 (idx > 60, v < 6, n 54): the four incident windows are 215–241 raw; the next is 122 (t 441, idx 84, 6–10 amp 597);
r34's same class tops at 274 (t 378, idx 150), 236, 229 … with 6–10 amps 390–1980 raw. Spearman(bar 18–22, bar 6–10) over v < 6 windows: r34
+0.65, r35 +0.81 — the two bands co-occur; the 7 Hz ripple is the company the 20 Hz line keeps when it is loud.

Census (2 s windows, step 0.5 s, engaged v < 6; line = 15–26 Hz prominence ≥ 8 and bar 18–22 ≥ 40 raw):

| route | build | n | present | f mean ± sd (p10/p90) | amp p50/p90/max | present % (amp p50) at idx 1–20 / 20–60 / > 60 |
|---|---|---|---|---|---|---|
| r34 | V280r2 | 341 | 202 (59 %) | 20.54 ± 2.08 (18.7/23.3) | 78/169/274 | 44 (43) / 64 (103) / 72 (106) |
| r35 | V281r3 flat 248 | 229 | 40 (17 %) | 20.25 ± 1.02 (19.4/20.9) | 27/65/241 | 11 (24) / 26 (38) / 31 (55) |

Creep (1–3 m/s): r34 131 windows, 63 % present, amp p50 75, amp↔idx ρ +0.49; r35 114 windows, **13 %**, amp p50 **21**, amp↔idx ρ +0.10 (the
idx dependence is gone with Kp flat), amp↔|rate| +0.30. f by idx bin, r34 vs r35: 0–20 20.30/20.14, 20–60 20.18/19.79, 60–120 20.96/20.62,
> 120 20.82/20.03 (n 2). r35 line-present stretches ≥ 1.5 s route-wide: 16, of which the incident (226/241 raw) and t 440.9 (112/122) are the
only ones above 100 raw; the rest 42–86.

## 4. Chain mirror on the core (FUN_00028ea6, V281r3 cells, live fade, ZOH command, open loop on the measured rate), 18.1–22.1 Hz

| variant | \|T\| meas/sim | band amp meas / sim (P, D) | corr_band / phase / coh | rails P D S cap fb |
|---|---|---|---|---|
| **as built (Kp 248, Kd 128, fade live)** | 428 / 472 | **159 / 188 (82, 167)** | 0.86 / +31° / 0.99 | 0.00 0.03 0.02 0.00 0.00 |
| no fade | 428 / 481 | 159 / 192 (83, 172) | 0.86 / +31 / 0.99 | same |
| Kp = V280r2 table (592 here) | 428 / 1052 | 159 / 180 (145, 167) | 0.94 / +16 / 0.99 | **0.17** 0.03 0.11 0 0 |
| Kd 0 | 428 / 498 | 159 / 82 (82, 0) | 0.85 / −31 / 1.00 | 0 0 0 0 0 |
| Kd 64 | 428 / 466 | 159 / 124 (82, 89) | 0.96 / +14 / 0.99 | 0 0 0 0 0 |
| lag 1008/253 (2.5 Hz pole) | 428 / 513 | 159 / 95 (41, 85) | 0.91 / +24 / 0.99 | |
| lag 960/1014 (10 Hz pole) | 428 / 478 | 159 / 350 (153, 309) | 0.73 / +43 / 0.99 | |
| fb single-sample ×2 | 428 / 479 | 159 / 186 (81, 165) | 0.83 / +34 / 0.99 | |
| rate low-passed < 15 Hz | 428 / 507 | 159 / 35 (16, 37) | 0.80 / +15 / 0.89 | |
| cmd frozen | 428 / 570 | 159 / 186 (80, 160) | 0.81 / +36 / 0.98 | |
| cmd frozen AND rate < 15 Hz | 428 / 534 | 159 / 18 (9, 15) | 0.71 / +43 / 0.98 | |

7 Hz band (6–8.5 Hz): meas 178, sim 190 (P 141, D 109), corr 0.98, coh 1.00; with V280's Kp 248 (P 248, D 109) and P railing 17 %; Kd 0 → 141.
Controller-only |L_fw| at 20.1 Hz: Kp 248 14.0, Kp 610 19.7, Kd 0 at 248 5.9 counts per deg/s. Identity test in the core: measured |T/rate_x|
11.7 ∠−103° (coh 0.97) vs L_fw(248) 13.9 ∠−73° → ratio 0.84 (the same ~4 ms offset). r34's attenuated seconds re-run with the live fade: as
built 132/139, 75/87, 71/76; with Kp flat 248 counterfactually 109, 74, 68 (−18 %, −2 %, −4 % open loop).

## 5. Settled / not
- **Settled [EVIDENCE]:** where and what (a turn start from a stop, hands on, idx 100–140); the same 20.1 Hz mode as the attenuated creep line,
  bar/rate/tap coherent, D-dominated, reproduced by the mirror to 18 %; a 0.9 s exponential burst that tracked the demand/rate ramp and died as
  the hands tightened; no rail; nothing on the chassis; the command inert on it; a 7.5 Hz stutter ripple underneath; the census: V281 has
  the creep line ~3.5× less often and ~2.5× smaller at matched idx, 0.2–0.8 Hz lower.
- **Not settled [BELIEF]:** why this burst grew — the excitation (a fast, loaded wheel with 7 Hz ripple) vs a damping loss with hands on the
  rim (bar/wire +143° here vs +114° hands-off); whether "pronounced" was the 20 Hz alone or the 20 + 7.5 Hz pair; the r24 phase (the sign bit
  is unreadable in a two-tone core).
- **Not resolvable here:** anything above 25 Hz on T; the r24 phase without a linear tap; a second incident to compare.

## 6. Files
`grind_incident_r35.py` · `grind_r35_extra_read.py` · `_scratch/grind_incident_r35.txt` (full output) · `_scratch/r35_extra.npz` · caches
`analysis-2020accord/_scratch/cache/v280/r35.npz`, `r34.npz`, `r35_b4.npz`, `r34_b4.npz` · images V281r3 / V280r2 via
`lowcmd_loopgain_v112_v278_v280.read_build` (+ the live fade/taper records read here) · chain pieces from `creep20_loop_id.py`.
