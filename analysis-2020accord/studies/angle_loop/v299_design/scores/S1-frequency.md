# S1-frequency — the common frequency scorer for the V299 design round (2026-10-02)

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent. The fork, the firmware, the golden model and the kit's STATE/lineage were not
touched, and nothing was committed. Ghidra was not used: every byte came from a Python little-endian read of the V298 image (sha
`177abf04…`, asserted) or from the designers' published cave hex.
**Author:** S1-frequency, a SUBAGENT of the orchestrator. Designers do not grade their own work here. Every candidate of every designer
went through ONE code path: the same engine, members, frame box, hold ages, operating points, friction states, extractor and bars.
**Labels:** EVIDENCE = computed by the scripts below on bytes read from the image (the method is named). BELIEF = a modelling choice or an
inference. Every frequency-domain result is a model of the linearised loop. Results on the car are the time scorer's and the drive's.

---

## 0. The answer on one page

### 0.1 Verdict per candidate (frequency lens only)

| candidate | inner loop it reduces to | R2 gate box (panel bars) | new vs V298 on the extended axes | fork-coupled loops | verdict |
|---|---|---|---|---|---|
| **V298 (control)** | V298 | 0 fails, worst 39.1° (+9.1) | — | O1 (lead 0.06): GM **6.0 dB** at Trt 60 ms, 3.2 dB at 90; clip loop 44.3°/9.6 dB | baseline |
| **D1c** (rec.) | V298 (bytes; hex table verified) | = V298 | none | O1 as V298. **I now runs under a 600–1229 hand during O1**: oscillatory margin unchanged (61.1° vs 63.4°), plus a near-neutral DC drift (\|S\| 17 at ≤ 0.01 Hz) | **PASS** (note) |
| D1a | V298 | = V298 | none | as D1c | PASS (designer: not for flight) |
| D1-a2 G0-1400 | own table | 0 fails, worst 37.8° | 2 R79 sub-bar points (29.7°, ρ 0.974); low-speed PM −9.1°; **5–30 Hz \|L\| ×1.029 / ×1.052 (R79) at the 5 Hz edge** | O1-PID drift \|S\| 28 vs 17 | **FLAG** (brief rule) |
| D1 fork bar | no loop term | = V298 | none | none | PASS |
| **D2a** | V298 (0 fw bytes) | = V298 | none | **O1 lead 0: GM 9.4–9.6 dB at 60 ms (V298 6.0), 8.3 dB at 90 (3.2)**; clip loop = V298's; path PMo 64.3° (V298 59.3°) | **PASS** (the only candidate that adds O1-loop margin) |
| D2b | V298 | = V298 | none | as D2a; path PMo 76.1°; 20 Hz reference not assessable (interpolated plan, BELIEF) | PASS (note) |
| **D3-a** (rec.) | own table (G0 1414) | 0 fails, worst 37.3° (= D3's own +7.3) | 2 R79 sub-bar (29.3°); low-speed −9.6°; **5–30 Hz ×1.031 / ×1.056 (5 Hz edge)** | **post-clip K3 lead enters the clip-bound loop: 42.1°/6.4 dB at 60 ms, 24.5°/4.5 dB at 90 (V298 44.3°/9.6, 33.1°/8.3)**; reference 13–22 Hz ×2 | **FLAG** — fixable (§3.4) |
| D3-b | = D3-a (the rail is a clamp) | = D3-a | = D3-a | = D3-a | FLAG |
| **D4b** (rec.) | V298 (bytes; hex table verified) | = V298 | none | O1 = V298's (lead 0.06; debounce is time-domain) | **PASS** |
| D4a | GB-S13 | **23 fails, worst 25.1°** (b_lo/b_q × ms_free, 10–17.5 m/s) | +20 R79 sub-30; op-point ζ 0.010 (V298 0.040); **5–30 Hz ×1.040 / ×1.074** | as V298 | **FAIL as the panel defines the gate** (0 fails if the ms_free family is report-only) |
| D4b+GBS13 | GB-S13 | = D4a | = D4a | as V298 | **FAIL** (as D4a) |
| **D5 V299-b** (rec.) | V298 (two immediates) | = V298 | none | O1 as D1c (I runs under 600–1229); the lead is placed before the clip, so no clip-loop term. 20 Hz reference unchanged (boxcar null); path PMo 61.3° | **PASS** |
| D5 V299-a | own (Kp 140 + washout D) | 0 fails, worst **30.4°** (+0.4 = D5's own) | 17 R79 sub-bar (22.5°); 67 new op-point sub-30; **5–30 Hz ×1.073 / ×1.135** | **O1: 17.4°/1.5 dB at 90 ms, 5.2°/3.0 dB at 30 ms**; clip 26.3°/5.5 dB | **FAIL** (designer: not recommended) |

**The brief's two flags, literally:**
- **Worst PM < 30° anywhere on the extended grid:** every candidate, V298 included. V298's own minimum is 6.1°, at a ms_free product
  at a curve-hold point. So the flag is scored as **NEW vs V298 at identical points** (§2.3).
- **5–30 Hz loop gain above V298's:** D1-a2, D3-a/b, D4a, D4b+GBS13 and D5 V299-a are flagged. Every excess sits at the 5 Hz edge,
  where \|L\| ≤ 0.41. In the 13–17 and 18–22 Hz bands every candidate is at or below V298 (×0.98–1.00) and ≤ 0.97 of V295 (§2.4).

### 0.2 Decision-bearing findings

1. **The V298-loop candidates (D1c, D1a, D1 bar, D2a, D2b, D4b, D5 V299-b) share V298's GATE 2 by construction.**
   - **EVIDENCE.** No Kp/Ki/Kd/G/operand byte changes; D1c's and D4b's published cave hex carry the image's GB-P table byte for byte
     (`s1_bands.py`: decode_cave rows == image).
   - Their freezes, bounds and clamps only switch between PID and PD. Both pass the R2 box (worst +9.1° PID, +17.1° PD).
   - Among the firmware candidates the frequency lens therefore cannot rank D1c / D4b / D5b. The fork-coupled loops (finding 4) can.
2. **GB-S13 (D4a, D4b+GBS13) fails the panel-2 R2 box. EVIDENCE, two engines.**
   - 23 points: b_lo/b_q × ms_free, 10–17.5 m/s, aged hold. Worst 25.1° at b_lo×ms_free+h10, 11 m/s, FA.83.
   - The panel-2 engine (`panel2/score_freq.py`, independent pipeline) reproduces it: 25.1° / 26.2° / 26.1° / 26.6° at the four
     binding points vs V298's 39.1° / 41.3° / 41.5° / 40.2° (`s1_crosscheck.py` (a)).
   - It is stable everywhere (exact periodic ρ 0.994–0.996, ζ 0.06–0.09). At the curve-hold point (11.75 m/s, a 2.5 m/s²) ζ falls
     from 0.040 to **0.010** (ρ 0.9985 → 0.9996).
   - D4's own "0 fails" excluded the ms_free products. The panel-2 R2 box gates them as tier B. Excluding them, GB-S13 also has
     0 fails here.
   - **The orchestrator must rule on which definition binds.** Under the panel's definition D4a fails.
3. **The route-79 measured D fraction (0.55×) costs V298 itself 1.5° at one member.** EVIDENCE (model).
   - Point: b_lo×ms_free+h10 at 10–11 m/s, PM 28.5–30.0° against the bar of 30; ρ 0.991–0.994, ζ 0.11–0.14.
   - Every V298-loop candidate inherits it.
   - The G0-raising tables add b_lo×J_hi+h10 at 2–3.1 m/s (29.3–29.7°, ρ 0.974, ζ 0.26).
4. **The O1 override relay is a closed loop whose least margin lies at 4.5–7.7 Hz, and V298's 0.06 s O1 lead is what thins it.**
   - Numbers, worst over 19 members × 3 frames × e 0/10:
     - lead 0.06: GM **6.0 dB at Trt 60 ms**, **3.2 dB at Trt 90 ms** (PM 27.5°), crossing 5.2–5.6 Hz, peak \|S\| 2.2–3.7 at
       6.3–7.7 Hz;
     - lead 0 (D2): GM 9.4–9.6 dB at 60 ms and 8.3 dB at 90 ms, peak \|S\| 2.1–2.4.
     EVIDENCE (model, `s1_fork_trt.py`, `s1_o1_slow.py`).
   - The factorised form (1+L)(1−T_in·W), which is D2's outer-loop form, equals my combined loop to 1e−13 (`s1_crosscheck.py` (b)).
   - **BELIEF:** this band is where route 79 measured the 4–8 Hz wheel-rate excess near O1 (6.99 vs 3.06 deg/s). Hands-off twist
     trips close this loop with no hand impedance to damp it.
   - D2 (lead 0) raises the margin. D2, D3, D4 and D5 all cut the twist trips (345 → 30 / 0 / 63 / 18). D1 changes neither.
5. **D3's K3 lead is added after the error clip, so it feeds the wheel's own rate back whenever the clip binds.**
   - EVIDENCE that it is placed after the clip:
     - D3 page, K3 row: `raw = floor(−10·(apply + lead))`, with ṡ taken from the post-clip `apply`;
     - fork `carcontroller._update_angle`: `apply_angle_last` is stored after the clip.
   - Clip-bound loop, D3a + K3: 42.1° / 6.4 dB at 60 ms and **24.5° / 4.5 dB at 90 ms**. V298 plain: 44.3° / 9.6 dB and
     33.1° / 8.3 dB. EVIDENCE (model).
   - D3 raises the clip 1.6–2× and so increases clip-bound time (D5's open-loop recompute: 0.1 % → 8.8–12.4 %). That raises the
     share of time this loop is closed.
   - **Fix:** zero K3 while the clip binds, or take ṡ before the clip, which is D5's placement. With either fix the clip loop
     returns to 32.4–44.0°.
6. **Route-79 consistency of the plant family is partial.** EVIDENCE (model vs the drive read).
   - The free (no-friction) model predicts V298's closed-loop bandwidth as:
     - 1.78 Hz at 8 m/s (measured 0.4–0.6);
     - 0.40–0.68 Hz at 10–13 m/s (matches);
     - 0.28–0.31 Hz at 15–17.5 m/s (measured 0.4–0.6);
     - 0.76 Hz at 26.9 m/s (measured 1.1).
   - Friction (describing function at A = 1–5°) reproduces 8–9 m/s, but predicts peaking (\|T\| 1.2–2.7) that route 79 did not
     see (\|H\| ≤ 0.96).
   - **BELIEF:** above 15 m/s the real loop gain is higher than modelled, roughly ×1.5–2 in bandwidth. Modelled PMs there may be
     optimistic. That bears most on table edits that raise G at 15–27 m/s: GB-S13 at 17.5 m/s, and D1's rejected highway ×1.25.

---

## 1. The pipeline (one code path)

| item | choice | source / check |
|---|---|---|
| engine | `refute_stability/c3r1/c3r1_model.py`, imported **unchanged** | The independent model that cleared V298. Exact sampled-data plant channels, the 100 Hz hold at offset e, the gp-0x6abe EMA 37/128, the output lag OA 992 / OB 507, FWD 5346, fade 254/256. |
| plant family | r71b identification (p5c J-profile, p5b ms_free), the same identification as harness_freq's v294_plant family | Members: SINGLE (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6, mode13, mode20, ms_free) + COMBINED (b_lo×J_hi, b_lo×tau6, J1.0, b_q, b_q×J_hi, b_q×J1.0, b_q×tau6, b_lo×ms_free, b_q×ms_free) = the panel-2 R2 set. |
| image constants | re-read from the **V298** image (LE) and asserted equal to the engine's | OA, OB, FWD, EMA α, 1159, the GB-P table at 0xC4CDA, Ki 0xC63E6 = 40, Kp knots 0xE5384 = 112 ×5, Kd knots 0xE5126 = 48 ×4. `s1_freq.py` module asserts. |
| candidate tables | the V298 table with each designer's bytes applied | G0-1400 (714, 1400, 236). D3a (714, 1414, 185). GB-S13 = ×1.3 on knots 2–4, reslope: asserts D4's listed halfwords −4238 / 988 / −2643 / 728 / 1388. The slope rule reproduces the image table (assert). |
| D5 V299-a | small-signal Kp 112 + Kf 28, with D × washout HPF 1 − 2⁻⁹/(1 − (1−2⁻⁹)z⁻¹); saturated Kp 112 + washout | D5's own linearisation (`s4_closed_loop.py` A_FEAT). Not re-derived from cave bytes; D5 published none. BELIEF. |
| frames | nom, FA.83, FA1.155, FB.83, FB1.155 (the panel box) **+ R79.55 (D ×0.55, P/I ×0.93) + R79.88 (D ×0.88, P/I ×0.96)** | The route-79 measured fractions (drive read §5) |
| hold ages | e = −1 / 0 / 10 (core); 0 / 10 elsewhere | e10 = the panel's "+h10" |
| operating points | k → k·sech²(θop/sat(v)), sat = 19.3 + 546 e^(−v/3.01); θop = θ(v, a_lat 1.5 / 2.5 m/s²), SR 16, L 2.83 m, cap 360° | The refuter-F1 form D1/D3/D4 used |
| friction states | describing function of the route-79 Coulomb friction: b_eq(f) = 4Fc/(π A 2πf), closed round the plant's rate channel (Pt' = Pt/(1 + b_eq·Pw)); Fc 156 T ≤ 5 m/s → 85 T ≥ 8 m/s; A = 5° and 1° | Fc from the drive read (single method). The DF is a sliding approximation (BELIEF). |
| loop states | PID (hands-off), PD (I frozen or A3-bounded), PD at the hands-on fade 76/254 | — |
| fork loops | O1: sp = θ(t−Trt)(1 + τ_O1·s); clip-bound: sp = θ(t−Trt) ± c, with D3's post-clip lead (1 + 0.5 τ_D(v)·s·LP30); Trt 30 / 60 / 90 ms (60 = the panel's convention); fade 1 and 0.297 | Fork code read: `_update_angle` (clip, then `apply_angle_last`; O1 `steering_angle + rate·ANGLE_OVERRIDE_LEAD_S`) |
| path loop | the panel's outer model (integral τ_o 1 s, 60 ms) round T_ref × the candidate's reference lead | Report only. D2's SteerDelay and plan lead are modelled as a first-order advance (BELIEF; this overstates 20 Hz). |
| extractor | ONE vectorised PM/fc/GM_up (PM = 180 − \|wrap(phase)\| at \|L\| = 1, the c3r1 / panel convention) | Equals `c3r1_model.pm_gm` row for row (selftest, 36 rows, < 1e−9) |
| exact check | `c3r1_model.Periodic` ρ (10-tick monodromy, q = 4) at every loop's worst PM < 32 points | §2.5 |
| bars | tier-A singles 45° (e ≤ 0) / 30° (e > 0); combined 30°; GM_up ≥ 6 dB; \|T_c\| 5–30 Hz ≤ +3 dB | rb_gate2 / panel R2 |

**Validation (EVIDENCE).**
- V298 control reproduces the published anchors:
  - R2 box 0 fails, worst 39.1° at b_lo×ms_free+h10 @11 m/s FA.83. The panel-2 engine gives 39.1° at the same point
    (`s1_crosscheck`), and SCORE-FREQ's C3B-P row is 38.5° @11.9.
  - D1's per-operating-point anchor at 3.1 m/s, nominal: PM 83.7°, GM 23.2 dB, Ms 1.24, fc 1.81 Hz. The path table here gives the
    same T_ref (1.233 / 1.62 Hz / 69 / 141 ms) as D5's `s5_gate2` V298 row on the panel-2 engine.
- D3a reproduces D3's own +7.3° (b_lo×J_hi+h10 @2 m/s FB.83).
- D5 V299-a reproduces D5's own +0.4° (b_q×J1.0+h10 @30 m/s FB.83).
- The D5 lead's T_ref reproduces D5's V299b row (lag 32/105 ms at 3.1 m/s, path PM 85.2°).

---

## 2. Results

### 2.1 Inner loop, per unique linear loop (PID + PD, fade 1; `out/s1_tables.md` §A)

| loop | block | n | fails | worst PM−bar (at) | min PM | min GM dB | max Ms | max T_c dB |
|---|---|---|---|---|---|---|---|---|
| V298 | core (7 frames) | 12768 | 2 | −1.5 (b_lo×ms_free @11 R79.55 e10) | 28.5 | 12.4 | 2.36 | +0.2 |
| V298 | op 1.5 | 6080 | 24 | −9.2 (b_lo×ms_free @11.75 FA.83 e10) | 20.8 | 13.6 | 2.83 | −0.2 |
| V298 | op 2.5 | 6080 | 101 | −23.9 (same) | 6.1 | 13.7 | 9.32 | −0.3 |
| V298 | friction A5 | 4864 | 0 | +4.1 | 45.7 | 14.1 | 1.77 | −3.3 |
| V298 | friction A1 | 4864 | 1441 | −31.0 (b_hi @2 R79.55 e0) | 13.6 | 17.4 | 4.23 | −6.9 |
| G0-1400 | core / op2.5 / A1 | — | 4 / 101 / 1441 | −1.5 / −23.9 / −28.7 | 28.5 / 6.1 / 15.8 | 12.4 | 2.36 / 9.32 / 3.66 | +0.2 |
| D3a-tab | core / op2.5 / A1 | — | 4 / 101 / 1441 | −1.5 / −23.9 / −28.6 | 28.5 / 6.1 / 15.9 | 12.4 | 2.36 / 9.32 / 3.63 | +0.2 |
| GB-S13 | core / op2.5 / A1 | — | **47** / 150 / 1282 | **−14.3** / −28.5 / −31.0 | **15.7** / 1.5 / 13.6 | 12.4 | 3.94 / 30.1 / 4.23 | +0.2 |
| D5a-small | core / op2.5 / A1 | — | 19 / 146 / 1238 | −7.5 / −29.6 / −27.7 | 22.5 / 0.4 / 16.9 | **8.6** / 0.4 | 2.89 / 106 / 3.42 | +0.5 |
| D5a-sat | core / op2.5 / A1 | — | 2 / 163 / 1495 | −2.3 / −35.7 / −31.2 | 27.7 / 0.1 / 13.4 | 12.9 / 0.1 | 2.48 / 101 / 4.28 | −0.5 |

**R2 gate box only** (core, the panel's five frames, PID + PD; `s1_bands.py`):

| loop | fails | worst PM (at) | ms_free family excluded |
|---|---|---|---|
| V298 | 0 | 39.1 (b_lo×ms_free @11 FA.83 e10) | 0 / 39.8 (b_q×J1.0 @30 FB.83 e10) |
| G0-1400 | 0 | 37.8 (b_lo×J_hi @2 FB.83 e10) | 0 / 37.8 |
| D3a-tab | 0 | 37.3 (b_lo×J_hi @2 FB.83 e10) | 0 / 37.3 |
| **GB-S13** | **23** | **25.1** (b_lo×ms_free @11 FA.83 e10) | 0 / 39.8 |
| D5a-small | 0 | 30.4 (b_q×J1.0 @30 FB.83 e10) | 0 / 30.4 |
| D5a-sat | 0 | 40.7 | 0 / 42.4 |

**Worst PID PM per speed** (core, gate frames). The table edits act where their designers said they would:

| v m/s | 2 | 3.1 | 5 | 6.5 | 8 | 9 | 10 | 11 | 11.75 | 13 | 15 | 17.5 | 20 | 26.9 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 45.7 | 45.7 | 45.5 | 44.9 | 44.0 | 40.8 | 40.2 | 39.1 | 41.3 | 42.9 | 41.5 | 47.0 | 43.0 | 39.8 |
| G0-1400 | 37.8 | 37.8 | 40.4 | 42.2 | 44.0 | = V298 → | | | | | | | | |
| D3a-tab | 37.3 | 37.3 | 40.1 | 42.1 | 44.0 | = V298 → | | | | | | | | |
| GB-S13 | = V298 | | | | 44.0 | 35.7 | **26.6** | **25.1** | **26.2** | **27.2** | **26.0** | **29.8** | 32.5 | 39.8 |
| D5a-small | 39.9 | 39.9 | 38.9 | 37.8 | 36.4 | 34.6 | 34.4 | 33.0 | 34.8 | 36.8 | 35.5 | 39.3 | 34.4 | **30.4** |

### 2.2 The route-79 frames (D ×0.55 / ×0.88 measured): the sub-bar points, PID

| loop | points below the bar (PM) |
|---|---|
| V298 (and every V298-loop candidate) | b_lo×ms_free+h10 @10 (30.0) and @11 (28.5) — ρ 0.991 / 0.994, ζ 0.14 / 0.11 |
| G0-1400 | the V298 pair + b_lo×J_hi+h10 @2 / 3.1 (29.7), ρ 0.974, ζ 0.27 |
| D3a-tab | the V298 pair + b_lo×J_hi+h10 @2 / 3.1 (29.3), ρ 0.974, ζ 0.26 |
| GB-S13 | 24 points, worst **15.7** (b_lo×ms_free+h10 @11 R79.55) |
| D5a-small | 19 points, worst **22.5** |

PD (the I-frozen / bounded state) passes on every loop: worst +6.8° (GB-S13), +11.4° (D3a), +19.6° (V298).

### 2.3 Every loop vs V298 at IDENTICAL points (`s1_delta.py`)

| loop | block | new PM < 30 | new PM < bar | rescued PM < 30 | new GM < 6 | min ΔPM (at) |
|---|---|---|---|---|---|---|
| G0-1400 | core gate / R79 / op / friction | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 | −9.1 (b_lo×tau6 @2 FB.83 e10) |
| D3a-tab | same | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 | −9.6 (same point) |
| GB-S13 | same | **23 / 20 / 95** / 0 | 23 / 22 / 101 / 0 | **205 (friction)** | 0 | (sub-30 counts are the measure here) |
| D5a-small | same | 0 / 17 / 67 / 0 | 0 / 17 / 72 / 0 | 248 (friction) | 1 | — |
| D5a-sat | same | 0 / 1 / 72 / 56 | 0 / 1 / 90 / 54 | 1 | 12 | — |

Large negative ΔPM values at points where both PMs exceed 90° carry no information. The counts are the measure.

### 2.4 The bands: 13–17 Hz, 18–22 Hz and 5–30 Hz (`s1_bands.py`, core, gate frames, PID)

| loop | max 13–17 Hz \|L\| / V295 | max 18–22 Hz \|L\| / V295 | max 5–30 Hz \|L\|/\|L_V298\| (gate / R79) | where the 5–30 excess sits |
|---|---|---|---|---|
| V298 | 0.942 | 0.973 | 1.000 / 1.000 | — |
| G0-1400 | 0.942 | 0.973 | **1.029 / 1.052** (≤ 5 m/s) | 5.0 Hz edge. At 15 / 20 Hz the ratio is 0.994 / 0.993 (3.1 m/s, nominal). \|L\|(5 Hz) 0.41 |
| D3a-tab | 0.942 | 0.973 | **1.031 / 1.056** (≤ 5 m/s) | 5.0 Hz edge. At 15 / 20 Hz 0.994 / 0.990 |
| GB-S13 | 0.940 | 0.970 | **1.040 / 1.074** (9–20 m/s) | 5.0 Hz edge. At 15 / 20 Hz 0.992 / 0.990 (17.5 m/s). \|L\|(5 Hz) 0.15 |
| D5a-small | 0.938 | 0.969 | **1.073 / 1.135** (20–30 m/s) | 5.0 Hz edge. At 20 Hz 0.983 |

**EVIDENCE (model):**
- No candidate raises the 13–17 or 18–22 Hz loop gain. Each stays ≤ 0.97 of V295 on the same member and frame (the panel's L20
  criterion), and ≤ 1.00 of V298.
- Every brief-rule flag is an excess at the 5 Hz end, where the P term still passes the hold and the D term dominates above it.
- The reference path is a separate matter (§2.7): D3's K3 lead doubles \|T_ref\| at 13–22 Hz.

### 2.5 Exact periodic check at each loop's worst LTI points (`s1_extra.py` §F; 70 points)

| loop | worst ρ (ring Hz, ζ) | where |
|---|---|---|
| V298 / G0-1400 / D3a-tab | 0.9985 (0.58 Hz, ζ 0.040) | b_lo×ms_free+h10 @11.75 FA.83, curve-hold a 2.5 |
| G0-1400 / D3a-tab, core R79 | 0.974 (1.52 Hz, ζ 0.26) | b_lo×J_hi+h10 @2–3.1 R79.55 |
| **GB-S13** | **0.9996 (0.65 Hz, ζ 0.010)** | b_lo×ms_free+h10 @11.75 FA.83, a 2.5. Core R79 point: 0.996 (0.94 Hz, ζ 0.072) |
| D5a-* | not computed: the washout state is not in `Periodic` (LTI only) | — |

**Every computed ρ is < 1.** No low LTI PM on this grid is a hidden instability (EVIDENCE). The low-PM points are lightly damped
0.6–1.5 Hz modes of the heavy ms_free family. GB-S13 cuts that ζ fourfold.

### 2.6 Fork-coupled loops (`s1_fork_trt.py`, `s1_extra.py` §G, `s1_o1_slow.py`; 19 members × nom/FA.83/FB1.155 × e 0/10, fade 1)

| loop (inner) | O1 lead | state | Trt 30 ms PM / GM | Trt 60 ms PM / GM | Trt 90 ms PM / GM | crossing at the 60-ms worst | max \|S_tot\| (60 / 90 ms) |
|---|---|---|---|---|---|---|---|
| O1, V298 | 0.06 | PD | 102.8 / 11.8 | 63.4 / **5.9** | **28.5 / 3.4** | 5.19 Hz (b_lo×tau6 @8 FB1.155) | 2.15 / 3.61 at 6.4–7.7 Hz |
| O1, V298 | 0.06 | PID | 66.1 / 11.8 | 61.1 / 6.0 | 27.5 / 3.2 | 5.21 Hz | 2.18 / 3.72; **plus \|S\| 17 at ≤ 0.01 Hz at Trt 30** |
| **O1, V298 (D2)** | **0** | PD / PID | 64.9 / 11.3 | 45.0 / **9.4** | 33.8 / **8.3** | 4.75 Hz | 2.08 / 2.39 |
| O1, G0-1400 / D3a | 0.06 | PID | **20.1 / 11.6** · 23.6 / 11.5 | 61.0 / 6.0 | 27.4 / 3.2 | 5.2 Hz | DC drift \|S\| 28 / 23 at ≤ 0.01 Hz |
| O1, D5a-small | 0.06 | PID | **5.2 / 3.0** | 53.9 / 4.6 | **17.4 / 1.5** | 5.66 Hz | Trt_crit 130–140 ms |
| clip-bound, V298 | — | PID | 64.1 / 11.4 | 44.3 / 9.6 | 33.1 / 8.3 | 4.69 Hz | — |
| clip-bound, D3a-tab | — | PID | 63.5 / 11.2 | 44.0 / 9.3 | 32.4 / 8.1 | 4.50 Hz | — |
| **clip-bound + D3 K3 post-clip lead** | — | PID / PD | 76.2 / 10.3 | **42.1 / 6.4** | **24.5 / 4.5** | 5.17 Hz | — |
| clip-bound, D5a-small | — | PID | 62.4 / 10.7 | 39.3 / 8.1 | 26.3 / 5.5 | 4.88 Hz | — |

**Readings:**
- **The O1 loop with V298's 0.06 s lead sits at the 6 dB GM bar at Trt 60 ms and below it at 90 ms** (EVIDENCE, model).
  - Its least-margin crossing is at 5.2–5.6 Hz, with \|S\| peaking at 6.3–7.7 Hz.
  - With the lead at 0 the margin rises to 9.4 / 8.3 dB.
  - The low-margin mode is at the wheel's own frequency, not the setpoint's, so it is a property of the relay, not of the plan.
  - **BELIEF:** it coincides with route 79's 4–8 Hz wheel-rate excess near O1 (REFUTE-data #18, causal direction undecided). If the
    operator wants that coincidence tested, the O1 lead is the single cheapest lever. D2a ships it.
- **Trt.** Physically this is the fork's round trip: carState[i−1], a 100 Hz frame, CAN, and the 0xE4 hold. 30–90 ms brackets it;
  **60 ms is the panel convention, not a measurement** (BELIEF). Route 79's "torque word leads 0x18F by 10 ticks" and "liveDelay
  never estimated" leave Trt unidentified.
- **I running under O1** happens with D1c, D1a, D1-a2 and D5 V299-b, whose hard freeze sits at 1229, above an O1 trigger of 600.
  - The oscillatory margin is unchanged (61.1° vs 63.4°).
  - It adds a near-neutral DC drift: \|S\| 17 (V298 table) / 28 (G0-1400) / 23 (D3a) at ≤ 0.01 Hz, Trt 30 ms. Under O1 the I has
    no anchor. That is not an oscillation, but whatever the I accumulates is released at O1 release. This is the co-steer
    droop / release lurch cost that D1 already declared and that the time scorer owns.
- **D4b** freezes on its LP hand word above 512, so under O1 it is PD (V298's state).
- **D2 and D3** keep V298's freeze or put O1 at 1200 held: PD under O1.
- **Convention.** D2 reported "clip-bound PM 20.8° at 0.15 Hz". That is the near-neutral \|T_in·W\| ≈ 1 region of its outer-loop
  metric: peak \|T_in·W\| 1.008 at 0.32 Hz here (PID). It is not an oscillatory margin. Both forms describe the same characteristic
  equation (`s1_crosscheck` (b), 1e−13).

### 2.7 Reference path and the fork's path loop (nominal member, nom frame, e 0; `out/s1_tables.md` §D)

| loop + reference lead | path PMo min (°) | \|T_ref\| 13–17 Hz max | \|T_ref\| @20 Hz max | lag @0.5 Hz, 3.1 / 8 / 17.5 m/s (ms) |
|---|---|---|---|---|
| V298 | 59.3 | 0.0180 | 0.0050 | 141 / 138 / 356 |
| D3a + K3 lead | 61.7 | **0.0369** (×2.0) | **0.0101** (×2.0) | 78 / 103 / 309 |
| V298 + D5 lead (boxcar) | 61.3 | 0.0189 | 0.0050 (null) | 105 / 108 / 316 |
| V298 + D2a SteerDelay +0.1 s | 64.3 | 0.148 † | 0.063 † | 44 / 41 / 259 |
| V298 + D2b plan lead | 76.1 | 0.232 † | 0.120 † | 91 / 41 / 91 |
| G0-1400 / GB-S13 / D5a-small | 59.3 / 64.1 / 62.3 | ≤ 0.0225 | ≤ 0.0062 | — |

† D2's leads are modelled as a first-order advance (1 + τs) on the reference. That turns the 20 Hz model staircase into a ×12–24
artefact. In reality D2a advances the planner's sample time, and D2b samples and interpolates the trajectory. **The 20 Hz figures for
D2 are not assessable by this scorer** (BELIEF); the time scorer must check them on the recorded staircase.

D3's K3 lead runs through a 30 ms pole and no boxcar, so it doubles the reference content at 13–22 Hz: 0.010 at 20 Hz, still small
in absolute terms. D3 declared this un-simulated (M-D3-9). D5's boxcar has a zero at 20 Hz, and its 20 Hz figure is unchanged.

### 2.8 Friction states (describing function; `s1_extra.py` §H, `out/s1_tables.md` §A4)

| v m/s | 2 | 3.1 | 5 | 8 | 10 | 11.75 | 15 | 17.5 | 26.9 |
|---|---|---|---|---|---|---|---|---|---|
| V298 worst PID PM at A = 1° | 13.6 | 13.6 | 16.2 | 34.5 | 23.9 | 21.3 | 37.2 | 44.5 | 43.5 |
| G0-1400 / D3a-tab | 15.8 / 15.9 | 15.8 / 15.9 | 17.5 / 17.6 | = | = | = | = | = | = |
| GB-S13 | = | = | = | = | 27.3 | 23.8 | 39.7 | 46.8 | = |
| D5a-small / D5a-sat | 16.9 / 13.4 | 16.9 / 13.4 | 19.8 / 16.0 | 40.9 / 33.5 | 27.3 / 23.5 | 23.9 / 21.1 | 40.5 / 36.9 | 48.2 / 44.1 | 49.6 / 42.7 |
| amplitude below which PM < 30°, V298 PID (deg) | 2.0 | 2.0 | 1.5 | 0.7 | 1.0 | 1.5 | 0.7 | 0.5 | 0.5 |

**EVIDENCE (model):**
- No describing-function limit cycle is predicted above 0.05° (PID, ≤ 5 m/s) or at any amplitude (PD, or above 5 m/s).
- PM falls below 30° under 0.5–2° sliding amplitude: the small-correction regime route 79 measured (breakaway \|err\| median
  0.8°).
- Higher stiffness raises PM in this regime: G0-1400 / D3a +2° at ≤ 5 m/s, GB-S13 +2.5–3.4° at 10–17.5 m/s, D5a's Kf +3–6°.

**BELIEF:**
- This is frequency-domain support for "more gain eases the stick". It is not evidence of a stick fix: the stuck (zero-velocity)
  state is outside a sliding describing function.
- D5a-sat (washout, no Kf) loses PM here: 56 new sub-30 points. Removing low-frequency D hurts the friction regime.

### 2.9 Route-79 consistency (V298 PID, closed-loop T_ref = θ/θ_sp; `out/s1_tables.md` §B)

| v m/s | modelled bandwidth, free / A5 / A1 (Hz) | modelled \|T\|pk, free / A5 / A1 | route 79 measured |
|---|---|---|---|
| 8 | 1.78 / 1.36 / 0.57 | 1.03 / 1.18 / 1.94 | 0.4–0.6 Hz, \|H\| ≤ 0.96 |
| 10 | 0.68 / 0.55 / 0.28 | 1.02 / 1.25 / 2.50 | 0.4–0.6 |
| 11.75 | 0.47 / 0.39 / 0.20 | 1.01 / 1.28 / 2.74 | 0.4–0.6 |
| 15 | 0.31 / 0.32 / 0.24 | 0.99 / 1.06 / 1.68 | 0.4–0.6 |
| 17.5 | 0.28 / 0.29 / 0.25 | 0.98 / 1.03 / 1.45 | 0.4–0.6 |
| 26.9 | 0.76 / 0.70 / 0.51 | 1.03 / 1.11 / 1.49 | 1.1 Hz |

**Reading (BELIEF):**
- The family plus friction brackets 8–13 m/s.
- Above 15 m/s every member is slower than the car, by roughly ×1.5–2 in bandwidth. Either the real plant stiffness k there is lower
  than identified, or the delivered P is higher than modelled; the measured P is 0.93–0.96×, which argues for the former.
- The free model's absence of peaking matches the car. The DF peaking at A1 does not, so A1 is a stress state, not the cruise
  state.
- Consequence: margins that bind at 15–27 m/s (GB-S13's 17.5 m/s knot; D5a's 26.9–30 m/s) are the least trustworthy numbers in this
  scorer.

---

## 3. Per-candidate notes (what the frequency lens can and cannot say)

### 3.1 D1c / D1a / D1 fork bar
- The linear loop is V298's.
  - EVIDENCE: hex table == image; D1's own H1 interpreter run shows the gains and operands unchanged.
  - The asymmetric A3 bound and the 1229 freeze switch PID ↔ PD only. Both states pass everything V298 passes.
- **Frequency-domain cost:**
  - The O1-with-I-running state is new for D1c's 600–1229-word hands. Its oscillatory margin equals V298's. Its DC drift is the
    declared droop.
  - D1 leaves V298's O1 lead (0.06) and the 345 twist trips, so it keeps the 6 dB-at-60-ms O1 loop closed hands-off as often as
    V298 does.
- **The bar:** no loop term.

### 3.2 D1-a2 G0-1400 (separate later dose)
- R2 box 0 fails (37.8°, −1.3° vs V298's worst).
- Costs:
  - low-speed PM −9.1°;
  - +2 R79 sub-bar points (29.7°, ρ 0.974, well damped);
  - 5–30 Hz \|L\| ×1.03–1.05 at 5 Hz → **flag (brief rule)**;
  - with D1c's I running under O1 at Trt 30 ms, a deeper DC drift (\|S\| 28).
- It is mixed in the time scorer too (D1's own reading).

### 3.3 D2a / D2b
- Zero firmware bytes: GATE 1 is vacuous and the inner loop is V298's.
- **D2 is the only candidate that adds margin to a fork-coupled loop.** O1 lead 0 takes GM from 6.0 to 9.4 dB at 60 ms, and from
  3.2 to 8.3 dB at 90 ms.
- The clip ×1.6 changes no linear loop (the clip-bound loop is V298's, 44.3° / 9.6 dB at 60 ms), only how often it is closed.
- The cap, takeover ramp and second-order limiter are nonlinear and not scored here.
- Path-loop PM rises (64.3° / 76.1°).
- **Not assessable here:** D2's 20 Hz reference content (the model artefact †).

### 3.4 D3-a / D3-b
- Table: R2 box 0 fails (37.3°, reproduces D3's +7.3° exactly). Costs as D1-a2: low-speed −9.6°, +2 R79 sub-bar points, 5–30 Hz
  ×1.03–1.06 → **flag (brief rule)**.
- **Defect (fixable):** K3 is added after the clip.
  - In the clip-bound state it is positive wheel-rate feedback. GM falls to **6.4 dB at 60 ms** and **4.5 dB at 90 ms**, PM to
    24.5° at 90 ms (V298: 9.6 / 8.3 dB, 33.1°).
  - D3's own clip ×1.6–2 makes that state more frequent.
  - Fixes, either of which restores V298's clip loop:
    1. gate K3 to zero while |apply − θ| is at the clip (the same rule as "zero under O1");
    2. compute ṡ from the pre-clip limiter output (D5's placement).
- **Reference:** K3's 30 ms pole passes the 20 Hz staircase ×2 at 13–22 Hz (small absolute value). Adding D5's 5-frame boxcar would
  null it.
- **D3-b** is linearly identical to D3-a. Its rail is a clamp that this scorer cannot see, and D3 itself shows it is never reached.

### 3.5 D4b / D4a / D4b+GBS13
- **D4b:** linear loop V298's (hex table verified; the hand rule is a policy). Its O1 debounce is time-domain. **PASS.**
- **GB-S13 (D4a, the graft): FAILS the panel R2 box** on the ms_free products at 10–17.5 m/s.
  - 23 points, worst 25.1°; two engines agree to 0.1°.
  - It cuts the ms_free curve-hold ζ fourfold (0.040 → 0.010). Its 17.5 m/s knot sits exactly where §2.9 says the model
    under-states the real loop gain.
  - In its favour: it is the only stiffness edit that lifts the friction-regime PM at 10–17.5 m/s (+2.5–3.4°; rescues 205 sub-30
    friction points).
  - **Ruling needed:** if the panel keeps the ms_free products gated (SCORE-FREQ R2), GB-S13 is a GATE-2 fail. If they are
    report-only (D1/D4's reading), it passes with the lowest margin of any table here.

### 3.6 D5 V299-b / V299-a
- **V299-b:** linear loop V298's (two immediates).
  - The fork lead sits before the clip, so it adds no clip-loop term.
  - It leaves the 20 Hz reference content unchanged (boxcar null), adds ≤ 5 % at 13–17 Hz, and raises path PM to 61.3°.
  - O1 keeps the 0.06 lead, with I running under 600–1229 hands as in D1c. **PASS.**
- **V299-a:** GATE-2-marginal on the gate box (+0.4°).
  - With the route-79 D fraction it fails 17 points (22.5°).
  - The washout strips low-frequency D, so the O1 loop collapses: 17.4° / 1.5 dB at 90 ms, 5.2° / 3.0 dB at 30 ms.
  - 5–30 Hz ×1.07–1.14. **FAIL** (its designer already does not recommend it).

---

## 4. What this scorer cannot see (declared)

- **Nonlinear limits:**
  - the rate cap, the error clip *value*, the second-order limiter, the takeover ramp, the debounce timings;
  - the A3 bound *switching*. Only the two linear states each side are scored.
  - BELIEF: switching between two stable loops at a bound does not destabilise. The time scorer owns hunting.
- **Hand impedance** in the O1 loop. It is not modelled: worst case for the hands-off twist trips, probably conservative with a
  real hand (BELIEF).
- **The stuck state** of Coulomb friction. The DF covers sliding only.
- **The ms_free / J ≈ 2 identification.** The panel has gated it; D1/D4 call it disfavoured by held-out data. This scorer reports
  both readings.
- **Trt.** It is not identified on the car: 60 ms is convention, 30–90 the bracket.
- **D5 V299-a's cave.** Its linearisation is D5's; no cave bytes exist to re-derive it from.

---

## 5. Scripts, outputs and wall times (all < 30 s; 16 processes)

| script (under `scores/S1-frequency/`) | does | wall |
|---|---|---|
| `s1_freq.py` | the common scorer: 6 unique loops × 19 members × 16 speeds × frames × e × PID/PD × op-points × friction (209,760 inner rows) + the fork-coupled loops (240,768 rows) + the r79 consistency rows. Writes `_scratch/v299_S1/s1_rows.npz` and `s1_paths.json` | **20.5 s** (pool 18.1 s; ≈ 3.4 s per unique loop) |
| `s1_freq.py selftest` | extractor == c3r1 `pm_gm`; engine `loop()` == assembly; image tables / Ki / Kp / Kd asserted | 0.9 s |
| `s1_report.py` | the tables `out/s1_tables.md`, `out/s1_summary.json` | 2.3 s |
| `s1_extra.py` | exact ρ (70 points), the Trt delay scan, the friction amplitude scan → `out/s1_extra.md` | 6.3 s |
| `s1_bands.py` | band gains per speed, the R2 box with and without ms_free, the R79 fails, the cave-hex table checks → `out/s1_bands.md` | 0.9 s |
| `s1_delta.py` | per-point ΔPM vs V298 → `out/s1_delta.md` | 0.8 s |
| `s1_fork_trt.py` | fork-loop margins per Trt → `out/s1_fork_trt.md` | 1.0 s |
| `s1_crosscheck.py` | the second method: GB-S13 on the panel-2 engine; the O1 factorisation identity → `out/s1_crosscheck.txt` | 0.9 s |
| `s1_o1_slow.py` | \|S_tot\| with the I running under O1 → `out/s1_o1_slow.md` | 2.8 s |

⚠ **Rule breach, fixed.**
- The first `s1_freq.py` grid (18 speeds × every axis on every frame) took 114.5 s. It was cut to block-wise frames and a 640-point
  frequency grid.
- The first `s1_o1_slow.py` looped serially and took 62 s. It was rewritten onto a 16-process pool (2.8 s).
- Neither long run's numbers are used.

Shared files: none touched. (The modified Ghidra project index files predate this scorer and come from other designers' sessions.)
