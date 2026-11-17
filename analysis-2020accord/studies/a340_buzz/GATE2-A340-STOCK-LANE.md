# GATE 2 — the V300-A340 angle loop with the STOCK DampAxis lane ("REV 4"), 2026-11-17

Subagent `gate2-a340-stock-lane` for the orchestrator. Offline study: nothing built, flashed or sent. **E** = EVIDENCE
(method, n), **B** = BELIEF. Scripts (all in this folder, prefix `g2_`): `g2_cache.py` 4.6 s · `g2_ident.py` 4.7 s ·
`g2_ident2.py` 5.0 s · `g2_score.py` 10 s · `g2_extra.py` 36 s (**over the seconds budget** — it re-runs `g2_score` on import
and sweeps 1100-point FRFs; flagged, not fixed). Outputs: `g2_*_out.txt`, `g2_*.json`.

## 0. What a FAIL looks like (written before applying), and the verdict

**FAIL — do not build** if any of:
- **F1** REV 4 misses a bar (PM ≥ 45° A / 30° B, GM ≥ 6 dB, closed-loop peak 5–30 Hz ≤ +3 dB) at the nominal member or at
  the central A340 estimate, at any speed.
- **F2** REV 4 misses a bar at a physically admissible point (mechanical inertia > 0 after removing the lane's own inertia)
  of the A160 family box or the A340 box, in BOTH formulations of the plant (§3).
- **F3** there is no evidence on this car that the lane's own loop is stable at stock gain.
- **F4** the data put the A340 plant outside the box in the at-risk direction (lighter AND less damped).

**Applied:** F1 no · F2 no (the one failing family point is inadmissible; the explicit formulation passes it) · F3 no (stock
firmware on the same car is quiet) · F4 not shown — but **"not shown" is not "shown inside"**: inertia and all damping above
~1.5 Hz are unidentifiable from these logs.

**Verdict: PASS-WITH-DEFECTS.** Held to the letter of the release gate (every tier-A point must pass) REV 4 scores 48/49 — the
same single corner the A160 re-score recorded (J_lo, 3 m/s: GM 5.3 dB, +5.4 dB at 11 Hz, Ms 2.67). I do not call that a FAIL
because that corner needs a negative mechanical inertia (§3.3), not because the alternative is worse. Defects D1–D5 in §5.

## 1. Reproduction of the A160 re-score (E)

`gate2_rescore_stock_terms.py` run unmodified, 6.8 s: every row of the doc's §2 table and all three tier summaries reproduce
(e.g. J_lo 3 m/s: PM 99.2 → 113.0, GM 20.0 → 5.2, T −4.2 → +5.4, Ms 1.26 → 2.68; L20/V295 1.24/1.18/1.18/1.28/1.29/1.28/1.28).

**"Stock terms" (= DampAxis stock AND r24 stock = the REV 4 lane set), PM° / GM dB / peak 5–30 Hz dB / Ms:**

| v m/s | nominal (= tau0 = tau6) | J_lo | J_hi | J_hi2 | b_lo | b_hi | ms_free |
|---|---|---|---|---|---|---|---|
| 3 | 97 / 14.3 / −3.1 / 1.43 | **113 / 5.2 / +5.4 / 2.68** | 77 / 23.9 / −9.9 / 1.22 | 68 / 28.4 / −15.0 / 1.17 | 67 / 11.8 / −0.1 / 1.66 | 93 / 17.5 / −6.5 / 1.26 | 91 / 17.3 / −4.1 / 1.34 |
| 5 | 95 / 15.6 / −3.4 / 1.38 | 111 / 9.0 / −0.1 / 1.82 | 78 / 24.1 / −10.1 / 1.23 | 71 / 28.5 / −15.0 / 1.18 | 68 / 13.4 / −0.6 / 1.57 | 96 / 19.2 / −6.7 / 1.23 | 85 / 20.9 / −6.5 / 1.28 |
| 8 | 95 / 15.9 / −3.4 / 1.37 | 112 / 9.8 / −1.2 / 1.71 | 78 / 23.9 / −9.8 / 1.25 | 74 / 28.0 / −14.8 / 1.22 | 68 / 13.7 / −0.5 / 1.57 | 100 / 19.8 / −6.8 / 1.22 | 79 / 23.6 / −9.5 / 1.26 |
| 12.5 | 94 / 24.6 / −10.4 / 1.13 | 91 / 22.6 / −11.7 / 1.12 | 101 / 26.9 / −11.5 / 1.13 | 106 / 29.9 / −15.1 / 1.12 | 113 / 18.6 / −5.9 / 1.26 | 81 / 27.6 / −13.7 / 1.08 | 109 / 37.3 / −24.0 / 1.11 |
| 19 | 95 / 29.4 / −15.7 / 1.06 | 94 / 28.9 / −16.2 / 1.05 | 96 / 31.1 / −15.5 / 1.07 | 96 / 32.8 / −17.1 / 1.07 | 109 / 24.1 / −10.8 / 1.13 | 83 / 33.7 / −19.2 / 1.03 | 98 / 35.5 / −21.0 / 1.07 |
| 26 | 83 / 30.8 / −16.4 / 1.05 | 81 / 31.7 / −17.4 / 1.04 | 81 / 32.6 / −17.1 / 1.06 | 79 / 33.9 / −18.6 / 1.06 | 101 / 24.5 / −11.3 / 1.11 | 71 / 35.1 / −20.0 / 1.03 | 80 / 32.8 / −17.4 / 1.06 |
| 30 | 81 / 30.9 / −16.5 / 1.05 | 79 / 31.9 / −17.5 / 1.03 | 79 / 32.6 / −17.2 / 1.05 | 77 / 34.0 / −18.8 / 1.06 | 99 / 24.8 / −11.4 / 1.11 | 70 / 35.5 / −20.1 / 1.03 | 79 / 32.5 / −17.3 / 1.05 |

PM passes everywhere (min 67°). One GM miss and one peak miss, the same point. Everything from 12.5 m/s up has GM ≥ 18.6 dB and
peak ≤ −5.9 dB. The doc says the peak is "at 13–17 Hz"; the scorer's own peak frequency is **11.0 Hz** (E, `g2_score.json`).

Built-image checks made here (E, LE reads): A340 REV 3 rows 26/27 = −29490/−17202/−16000, α2 `0xC40D4` 14, α1 `0xC645A` 37,
clamp 511, authority `0xC6E88` 5328 (A160 5346, −0.34 %), cave G table = A160's halved (589/733/380/280/534/1094). A160 V300:
Kp 112, Kd 48, Ki 40, r24 gate `0xC5` and `0xC6446` 512 (stock) — so A160 V300 as flown = the doc's "only r24" column.

## 2. The A340 2.0T plant from the data

**Method (E).** Engaged, not pressed, mean |tq| < 400, 10.24 s chunks, H1 = CSD/PSD of setpoint (−0xE4/10) → 0x14A angle;
plant from `1/P = C_ref/T − C_fb` with the controller cells of the image. **Positive control: the same estimator on the A160
V300 routes** (setpoint = `carControl.actuators.steeringAngleDeg`, which equals −0xE4/10 on the A340 route to r 0.9997, rms
0.21°, n 829 s). A340 n = 7/39/26/32 chunks at 6–10/10–16/16–23/23–32 m/s; A160 n = 20/60/176/126/197.

| band m/s | k ratio A340/A160 [5, 95 %] | Im(1/P) at 0.5 Hz ratio | tracking phase lag at 0.3 Hz, A340 vs A160 | viscous b ratio |
|---|---|---|---|---|
| 6–10 | 1.32 [0.85, 1.66] | 1.63 [0.83, 2.47] | −37° vs −25° (×1.49 [1.07, 2.00]) | 0.62 [−0.16, 1.31] |
| 10–16 | 0.99 [0.73, 1.43] | 1.00 [0.57, 2.33] | −42° vs −30° (×1.39 [1.03, 2.08]) | 0.17 [−0.05, 0.83] |
| 16–23 | 1.04 [0.89, 1.15] | 1.09 [0.85, 1.35] | −44° vs −32° (×1.37 [1.22, 1.53]) | 0.77 [0.32, 2.87] |
| 23–32 | 1.36 [1.25, 1.47] | 1.13 [0.97, 1.29] | −39° vs −29° (×1.35 [1.26, 1.45]) | 1.14 [0.81, 1.52] |

- **What is identified (E):** below ~1.5 Hz the A340 car is as stiff or stiffer (k ×1.0–1.4) and tracks with 35–50 % more phase
  lag, i.e. more low-frequency loss. Coherence is < 0.5 above 0.8–1.7 Hz in every band (the setpoint has no content there).
- **Closest family member:** by log-distance of T the ranking is b_hi (6–10), J_hi2/b_lo (10–16), J_hi2/J_hi (16–23),
  J_lo/nominal (23–32) — and the A160 car itself ranks the same way with this estimator (b_hi, J_hi2/b_lo, ms_free, nominal).
  **At the family's resolution the two cars are not distinguishable below 1.5 Hz** (E). No member is "the" A340 member.
- **Estimator accuracy:** on the A160 car it returns k 34/24/48/69 against the family's 20/39/74/56 — within a factor 2 (E).
  Use the ratios, not the absolute values.
- **Not identifiable (stated plainly):** J (bootstrap CI −1.0 … +6.2 T/(deg/s²)), transport delay, and all damping above 1.5 Hz.
  The viscous/Coulomb split is not resolved (b ratio CIs span zero). > 10 Hz is the buzz. A "quiet" subset (BZ < 4) exists only
  at 23–32 m/s (9 chunks) and gives the same k (103 vs 94).
- **Confounds (B):** the buzz acts as dither (should LOWER apparent friction, yet loss is higher); the user's resting hands
  (mean |tq| 185 vs 118 on A160; torsion-bar/angle FRF at 0.2–0.3 Hz is 55–73 vs 40–59 units/deg, coherence 0.4–0.5 —
  comparable, not decisive).
- **Creep exposure (E):** engaged not pressed at 1–3 m/s 18 s, 3–6 m/s 25 s on the modded route, all buzzing; **0 s below
  10 m/s on the stock route** (stock LKAS does not engage there). The at-risk speed has no usable A340 data.
- **Stock route (E):** stock LKAS command → wheel rate is coherent 0.4–3 Hz (coh 0.68–0.90, 133 s) but there is no A160
  stock-LKAS counterpart in the cache and the A340 stock lane is a different compile — descriptive only, not used. Manual
  free returns: 2.2 s (analyst) — unusable. The engaged wheel-rate spectrum on stock firmware is smooth 4–48 Hz, 1.3–2× the
  A160 V300 level, **no line** (133 s) — no sign of a lightly damped mode under stock.
- **From the buzz itself (B):** if it is the lane's local loop (§4), the motor-side inertia at 65–130 Hz is 0.01–0.045
  T/(deg/s²) on the kit's lane scale (which carries a BELIEF ×1.155). That is the light direction, but it is the inertia the
  motor sees with the rim decoupled, not the 5–15 Hz inertia.

## 3. GATE 2 scores

Controller = A160 V300's cells × 5328/5346. r24 stock in every column. Sign anchors as the release doc (lane = lagged positive
inertia; the tracer's decompile gives the same sign). Configurations: **REV 3** rows ×3, α2 14 · **REV 4** rows stock, α2 22 ·
**MID** rows stock, α2 14 · doses ×1.5 and ×2 of the stock rows.

### 3.1 A160 family box, the release doc's formulation `P' = P/(1 − P·ΔF)` (E for arithmetic; 7 members × 7 speeds)

| config | fails of 49 | min PM | min GM dB | max peak 5–30 dB | max Ms |
|---|---|---|---|---|---|
| REV 3 ×3/α14 | 0 | 64.8 | 19.4 | −2.5 | 1.41 |
| **REV 4 stock/α22** | **1: J_lo 3 m/s** | 67.6 | **5.3** | **+5.4 (11.0 Hz)** | 2.67 |
| MID stock/α14 | 1: J_lo 3 m/s | 68.2 | 5.7 | +4.6 (11.4 Hz) | 2.52 |
| ×1.5/α22 | 0 | 67.3 | 9.2 | −0.5 | 1.77 |
| ×2/α22 | 0 | 66.4 | 12.6 | −1.1 | 1.52 |
| ×2/α14 | 0 | 66.5 | 14.1 | −1.3 | 1.47 |

REV 4 against REV 3 at the nominal member: GM 21.5 → 14.3 dB (3 m/s), 28.4 → 24.6 (12.5), 33.8 → 30.8 (26); peak −5.0 → −3.2,
−10.9 → −10.5, −16.6 → −16.5; L20 ×1.23–1.30 at every speed. J_lo at 5 / 8 m/s: GM 9.0 / 9.8 dB, peak −0.2 / −1.2 dB (pass).

### 3.2 A340 box on the family (k × {1.0, 1.3, 2.4}, b × {0.7, 1.0, 1.6, 3.0}; nominal, J_lo, J_hi, ms_free; 336 points)

| config | fails | worst point |
|---|---|---|
| REV 3 | 0 | PM 50, GM 16.6, peak −1.5 |
| **REV 4** | **12, all J_lo: 3 m/s at b × 0.7 and × 1.0, 5 and 8 m/s at b × 0.7** | J_lo 3 m/s b×0.7: PM 1–2°, peak +28…+32 dB at 10.4 Hz |
| MID | 12, same points | J_lo 3 m/s b×0.7: PM 0–4°, peak +26…+37 dB |
| ×1.5/α22 | 3 (J_lo 3 m/s b×0.7) | PM 42, GM 5.1, peak +6.5 |
| ×2/α22, ×2/α14 | 0 | GM 8.8 / 9.7, peak +1.7 / +0.7 |

Central A340 estimate (nominal, k×1.3, b×1.6), REV 4: PM 92/97/103/86/88/76/74, GM 18.3/19.9/20.6/28.2/34.3/35.9/36.1 dB, peak
−7.1/−7.3/−7.4/−14.3/−19.7/−20.6/−20.7 dB, Ms ≤ 1.24 at 3/5/8/12.5/19/26/30 m/s — **passes with margin**. J_lo with b×1.6
passes too (3 m/s: GM 17.8, peak −5.1). Every failure needs J_lo together with b ≤ the A160 nominal.

### 3.3 Why the J_lo corner fails, and the explicit formulation (E arithmetic, B physics)

The lane's low-frequency inertia at 3 m/s is 0.1295 T/(deg/s²) at ×3 and 0.0432 at stock (kit scale). J_lo is a total of 0.10
**including** the ×3 lane, so its mechanical inertia is 0.10 − 0.13 = **−0.03**: inadmissible at 3 m/s (and 0.003 at 5–8 m/s).
Separately, the doc's formula subtracts the ×3 lane's lagged damping (4.6 T/(deg/s) at 15 Hz, 2.3 at 10 Hz) from a rigid member
whose b (4.9 at 3 m/s) was fitted below 8 Hz, where the lane supplies ≤ 0.6 — it removes damping the member never contained.

Explicit form: mechanical plant (J_m, b, k) + the lane as its own block with 2 ms delay (`g2_score` C2, `g2_extra` E1):
- REV 4 with b,k = nominal, J_m 0.012 … 0.15, rigid or two-mass, 6 speeds (60 cases): **0 fails**; PM 75–113°, GM ≥ 26.1 dB,
  peak ≤ −4.6 dB, peak 30–200 Hz ≤ −23.6 dB, Ms ≤ 1.27. With b,k ×(1.6, 1.3): 0 fails, GM ≥ 28.3 dB, peak ≤ −8.0 dB. MID the
  same to 0.1 dB. REV 3's local loop is unstable in 8 and 2 of those 60 (J_m ≤ 0.02 at ≤ 8 m/s).
- **REV 4 passes once the mechanical viscous damping reaches 0.3–0.5 × the A160 nominal (1.5–2.5 T/(deg/s)) at 3–8 m/s and
  0.1–0.2 × (1.1–2.2) at 12.5 m/s; below that it fails** (sweep steps 0/0.1/0.2/0.3/0.5/0.7/1.0, six J_m, two k). At b = 0:
  PM 3–24°, peak up to +24 dB at 5–11 Hz. REV 3 passes from 0.2–0.5× wherever its local loop is stable (its lane adds 2.3–4.6
  T/(deg/s) at 10–15 Hz; the stock lane adds 0.6–1.25).
- Two-mass stress (rim mode 16.5/22/25 Hz, ζ 0.03, rim share 0.3/0.6, 60 cases): worst peak REV 3 −5.4, REV 4 −4.6, MID −4.7 dB.

So the two formulations disagree only at J_lo ≤ 8 m/s, and the disagreement is whether real damping of ~1.5–2.5 T/(deg/s)
exists at 5–11 Hz at creep. A160's low-frequency fit is 4.9–5.5 (b_lo 3.5). On A340 that quantity is unmeasured.

## 4. The lane's own loop (acceleration feedback, 2 EMAs, delay, ±511 clamp)

Reproduced the tracer's `loop.py` with the plant as a ZOH inertia (E; my delay count is one tick less than the tracer's `d`):

| lane + transport delay | α2 22: g_crit, frequency (alias at 100 Hz) | α2 14 |
|---|---|---|
| 1 ms | 5.63, 129 Hz (29 Hz) | 7.28, 115 Hz (15.2 Hz) |
| 2 ms | 3.24, 90 Hz (10 Hz) | 4.10, 81 Hz (19.2 Hz) |
| 3 ms | 2.44, 72 Hz (28 Hz) | 2.99, 65 Hz (35 Hz) |

g = lane inertia / motor-side inertia. Lane inertia stock → REV 3: 0.0557 → 0.167 (0 km/h), 0.0325 → 0.0975 (20 km/h, ×3.00),
0.0210 → 0.0938 (16 m/s, ×4.46), 0.0111 → 0.0907 (≥ 90 km/h, ×8.14).

- **(a) buzz on REV 3: consistent (B).** Predicted aliases 15.2 / 19.2 Hz against the measured 16.3 Hz median (12.7–22.1);
  kick-triggered and self-sustaining fits a linearly unstable loop held quiet at small amplitude by Coulomb friction.
- **(b) quiet on stock: consistent (B)**, and required: stock firmware on this car is quiet (E, analyst: 362 s moving, 1.8 %).
- **Stock margin.** Same speed, ≤ 20 km/h: 0 < m ≤ 20·log10(3 × g_crit22/g_crit14) = **7.3–7.5 dB** — not 9.5 dB, because α2 22
  has a 2.0 dB lower critical gain than α2 14. If the motor-side inertia is speed-independent and REV 3 is at or past critical
  at 16 m/s (100 % duty there): m ≤ 4.7–5.3 dB at 3 m/s, ≤ 7.2–7.8 at 20 km/h, ≤ 11.0–11.5 at 16 m/s, ≤ 16.5–17.1 at 25 m/s.
  The pure-inertia model overstates low-speed instability (REV 3 duty is only 45–56 % below 10 m/s where its gain is highest).
- **Intermediate doses, margin relative to stock's m at 20 km/h:** MID **+1.4…+2.0 dB**; ×1.5/α22 −3.5; ×2/α14 −4.0…−4.6;
  ×2/α22 −6.0; REV 3 −7.5…−8.1. With m known only to lie in (0, 7.5] dB, **no dose above stock is defensible without a
  drive**, and on this car's key the rows also act in manual, which is where the user's complaint is.
- **REV 4 engaged vs stock engaged:** the angle loop's feedback at 81–115 Hz is 69–91 T/deg against 5 200–10 400 for the
  inertia term (J_m 0.02) and 2 000–5 000 for the stock lane — 1–2 % (E arithmetic). The local loop under REV 4 is stock's.
- Open (B): at J_m ≈ 0.02 a ±13 deg/s motion at 81 Hz gives ~150 counts of lane output, below the ±511 clamp, so the clamp
  may not be what fixes the amplitude; whether 0x14A's rate is point-sampled or averaged over 10 ms decides it.

## 5. Verdict for REV 4, the corner at risk, and the readout

**PASS-WITH-DEFECTS.**
- **D1** Fails the release gate as written at J_lo, 3 m/s (GM 5.3 dB, +5.4 dB at 11 Hz). Inadmissible corner on the kit's own
  lane scale, but that scale is BELIEF and A340 has no data below 6 m/s.
- **D2** The loop needs ≥ 1.5–2.5 T/(deg/s) of real viscous damping at 5–11 Hz below ~8 m/s (≥ 1.1–2.2 at 12.5 m/s). Unmeasured
  on A340; the A340 viscous estimate at 10–16 m/s is 1.5 [−0.4, 7.0] from ≤ 1.5 Hz data.
- **D3** L20 is 1.23–1.30× REV 3's (the doc's L20 ≤ V295 relative gate fails as on A160). Absolute L20 ≤ 0.054 nominal.
- **D4** Stock local-loop margin on this car is bounded only to (0, ~5–7.5 dB] below 20 km/h: fine at stock, no headroom.
- **D5** The A340 plant is "not distinguishable from A160 below 1.5 Hz", not "inside the box".

**If the at-risk corner is real, the driver feels:** engaged only, at parking / creep speed (≤ ~18 km/h, worst near 10 km/h),
hands off or light, after a steering correction: a 10–11 Hz wheel shudder ringing for 3–5 cycles (the J_lo reading), or in
the no-damping extreme a sustained 5–11 Hz oscillation. Firm grip stops it. Not present in manual, not above ~12 m/s.

**One readout, one short engaged drive:** rms of the **8–20 Hz band of the 0x14A wheel rate over 1 s windows**, request bit
set, not pressed, **v 1–8 m/s**, ≥ 20 s. Baselines (E): A160 V300 at 1–6 m/s p50 0.57 / p90 1.42 / p99 2.83 deg/s (686 s);
A340 stock firmware at 10–20 m/s 1.21 / 2.33 / 3.81 (135 s); A340 REV 3 at 1–6 m/s 4.75 / 8.73 (44 s).
**Clean: p50 ≤ 1.0 and p90 ≤ 2.0. Flag: p50 > 1.5 or p90 > 3.0. Revert: ≥ 2 s above 4 deg/s.** A flag at creep only = the
angle-loop corner (lever: the low-speed G(v) knots / Kd, not the lane); a flag at every speed with the analyst's
Δangle-vs-rate correlation negative = the lane loop again. Null sentence: p50 ≤ 1.0 and p90 ≤ 2.0 over ≥ 20 s at 1–8 m/s
licenses "the creep corner is not real on this car". The fix itself is scored by the analyst's SCORE < 1.0 / DUTY < 2 %.

**α2 14 with stock rows (MID) vs fully stock:** on the numbers MID is slightly better — local-loop critical gain +1.4…+2.0 dB,
lane damping at 5–20 Hz +16…+33 % (0.20 vs 0.15 at 5 Hz, 2.37 vs 2.04 T/(deg/s) at 20 Hz), J_lo corner GM 5.7 vs 5.3 dB and
peak +4.6 vs +5.4 dB — and it fails the same single corner. **I still recommend fully stock:** (i) MID is not stock in manual
on this car, and "manual = stock in every dynamic term" is the only claim here backed by a drive on this car; (ii) MID is safe
only if the rows are live on this car's key — if the car is not TWAA0/1, α2 14 alone is what REV 3 changed in manual, and MID
would keep it; (iii) the gain is 0.4 dB of GM. MID in manual has flown quietly only on A160 (manual rows stock, α2 14).

## 6. Defects found in existing work (reported, not fixed)

1. **Tracer report T3 / hypothesis 2: "α2 22 → 14 ADDS 10–30 % low-frequency anti-damping" is a sign error.** A lagged
   positive-inertia term is positive damping for lags < 180° (perturbation of J·ẍ + K·ẍ(t−τ) + k·x gives decay −Kτω²/2(J+K);
   `g2_extra` E3: every configuration is positive at 2–80 Hz, negative only above ~100 Hz with 2 ms delay). The ratios (×1.3 at
   5 Hz, ×1.13 at 20 Hz) are right; the sign is not. It does not change the tracer's headline.
2. **Release doc §0/§2:** the J_lo 3 m/s peak is at 11.0 Hz, not "13–17 Hz"; and the `P/(1 − P·ΔF)` step applied to a rigid
   low-frequency fit removes lane damping the fit never contained (§3.3). Its verdict is therefore conservative at high
   frequency; its J_lo corner is inadmissible at 3 m/s by its own lane inertia. The doc's note says so only as a BELIEF aside.
3. **Brief:** the stock-margin bound is 7.3–7.5 dB at ≤ 20 km/h, not 9.5 dB.
4. **`build_v300_a340.py` REV 2 docstring:** "the A340 plant is BELIEF-identical" was the basis for carrying the 13 bytes; the
   mode map (tracer) and this car's result contradict it for the lane's local loop.
5. `g2_extra.py` runs 36 s.

## 7. Caveats

- The lane scale (5.44 counts per deg/s, BELIEF ×1.155) sets every lane inertia and the J_m window; margins in dB do not depend on it.
- §4 assumes the rows are live on this car (key TWAA0/1 — the tracer's open fact). REV 4's lane is stock whatever the key.
- "Manual = stock" under REV 4 rests on the tracer's request-off audit; not re-verified here.
- The A340 r24 lane was taken as A160's stock schedule (A340's own tables not read); the term moves PM by ≤ 0.7°.
- Linear scores: clamps, the hand fade and Coulomb friction are off. Friction makes small oscillations at creep harder to start.
