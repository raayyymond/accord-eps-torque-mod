# S2 — COMMON TIME / NONLINEAR SCORER, V299 judge panel (2026-10-02)

Scorer S2, a subagent. **ANALYSIS ONLY**: no image built, nothing flashed or sent, no fork / firmware / golden-model / STATE / lineage / git edit.
Code: `scores/S2-time-nonlinear/s2_time.py` (sim + controls), `s2_report.py` (tables), `s2_tables.md` (all tables), `s2_control.txt`.
Raw rows (0.8 MB, regenerable): `_scratch/v299_S2/s2_results.json`.

**Wall times (EVIDENCE, measured):** every candidate is a column of the SAME run, so one run scores all 16 rows at once.

| run | wall |
|---|---|
| `python s2_time.py run`, all 5 manoeuvre groups in 5 processes | **12.9 s** total |
| per group: TI / C2 / LH / OV / RD | 8.9 / 10.2 / 12.1 / 10.4 / 6.3 s |
| `python s2_time.py control` | 11.9 s |
| `python s2_report.py` | 0.12 s |

Every candidate costs < 13 s, inside the 30 s rule.

## 1. What the one sim is (method; EVIDENCE = controlled, BELIEF = modelled)

| layer | what | status |
|---|---|---|
| plant, sensors, frame | `panel2/score_time.py`, loaded by path, unchanged. Karnopp stick-slip on the r71b family at 10 kHz sub-steps, 2 ms transport, the 100 Hz slot-4 gp-0x6a00 hold, the 1 kHz gp-0x6abe EMA with sensor noise, the correction-LERP frame, the fade records, output lag, ramp, OCL. | BELIEF (identified family) |
| members | **r79F**: nominal, with route 79's Coulomb friction (156 T ≤ 5 m/s, 85 T ≥ 6 m/s, Fs = 1.25 Fc; D5's member). **b_lo·J_hi**: the heavy refuter member. | BELIEF (single-method Fc) |
| THE LANE | `S2Lane` = `CandLane.tick` arithmetic for V298's configuration (GB-P read from the V298 image, sha 177abf04; Kp 112, Kd 48 fresh, Ki 40, ICL 8192, A3 + cap 4096 at ≤ 1382, ramp 328/66). Every V299 firmware edit is a per-column switch: hard threshold, opposing threshold, D1c asymmetric bound, D4b state word + motion gate, D5a washout + friction, G table, SCL/PCL. | **EVIDENCE**, see the controls below |
| THE FORK | `_update_angle` @ Dom 2712e1336, re-implemented at 100 Hz, with every candidate's change as a per-column switch (§1.2) | BELIEF (re-implementation; V298 semantics read from the fork source) |
| torque word gp-0x4f60 | the r79 hands-off reaction fit: **−0.69 α − 0.69 ω − 163 tanh(ω/2) − 61**. α is an 8 Hz LP of dω/dt. Plus an AR(1) residual at 100 Hz (sd 206, lag-1 0.89, from the same fit, `d1_r79.json`), plus the hand's prescribed word. Seeds 1–3 are three residual realisations; seed 0 is the deterministic twist. Each realisation is shared by every candidate column, and so is the sensor-noise draw. | sign EVIDENCE, model BELIEF |

**Twist realism check (EVIDENCE as computed):** in the V298 hands-off turn-ins the sim's |word| p90 is **534 / 560** and p99 **816 / 870** at 3 / 8 m/s.
- Flight r79, hands-off, < 8 m/s: p90 607–681, p99 1103–1206.
- So the sim's twist sits slightly **below** the flight's.
- The faster designs drive it higher in the sim:

  | design | p99 at 3 m/s |
  |---|---|
  | D3a | 1559 |
  | D5b | 1378 |
  | D2a | 1222 |

  Those values extrapolate the fit beyond the α range it was fitted on (BELIEF).

### 1.1 Controls (EVIDENCE, `s2_control.txt`)

**Method:** bit-for-bit comparison on the common scorer's own scenarios `ov_lt1000` (hand word 1000) and `hard`, at 3.1 / 11.9 / 17.0 / 26.9 m/s, member nominal, sensor noise 0.

| S2Lane column | reference lane | max\|ΔT\| | max\|Δθ\| |
|---|---|---|---|
| V298 | `score_time.CandLane(d2_common.v298_cand)` | 0 | 0 |
| D1c | `d1_time.D1Lane` (D1's own mirror, which D1 H1-tested against its bytes) | 0 | 0 |
| D4b | `d4_sim.D4Lane('b8:lp5H512')` (D4's mirror, H1-tested 0/20000) | 0 | 0 |
| D4a | `d4_sim.D4Lane('a:GBS13')` | 0 | 0 |
| **negative control:** S2Lane(D1c) vs CandLane(V298) | — | **263 / 40 / 33 / 114** | must be > 0 |

- `rb_table.GB_P` matches the rows read from the image.
- **Not separately controlled:**
  - D3a/D3b, D1a and D1c+G0 are combinations of the controlled threshold and table paths.
  - D5a's washout + friction is mirrored from DESIGN-V299-D5 §2(a)'s listing and was not H1-checked by me.
  - D3b's per-column SCL/PCL is a two-constant change.

### 1.2 Fork switches per candidate (from each design page)

All forks share these parts:
- the 20 Hz model staircase (D2b interpolates instead);
- carState i−1 (the angle and torque from the 0x14A/0x18F sample one frame older);
- VM jerk limit = min(jerk, cap), plus the VM accel limit;
- the release restart from the wheel;
- the post-clip value stored as `apply_angle_last`, as the fork does.

| fork | cap deg/s | error clip ≤ 11.75 m/s (deg) | O1 on / off (raw) | O1 lead | extra |
|---|---|---|---|---|---|
| V298 (D1 uses it) | 120 | 17 / 15.5 / 19.5 / 17 | > 600 / ≤ 500 | 0.06 | — |
| D2a | 300 | ×1.6: 27.2 / 24.8 / 31.2 / 27.2 | > 1200, or > 600 for 8 frames / ≤ 500 | 0 | takeover 0.4 s (rate and clip); SteerDelay +0.10 s = plan sampled 0.10 s ahead (BELIEF) |
| D2b | 300 | as D2a | as D2a | 0 | takeover; 2nd-order limiter 1500 deg/s²; plan lead τ(v) (bounded 4° / 0.6 m/s²), interpolated |
| D3a | 300 / 300 / 200 / 120 at 0 / 5 / 8 / 10 m/s | 30 / 25 / 19.5 / 17 | 1200 held > 10 frames, or > 2500 / ≤ 1000 | 0.06 | K3 lead 0.5·τ_D·ṡ (after the clip; 0 under O1 and for 0.3 s after release); K4 120 deg/s for 0.5 s after release |
| D3b | 400 / 400 / 200 / 120 | 40 / 30 / 19.5 / 17 | as D3a | 0.06 | as D3a |
| D4 | 120 | V298 | > 600 for 5 frames / ≤ 500 | 0.06 | — |
| D5b | 250 | 35 / 32 / 19.5 / 17 | > 1200, or > 600 for 6 frames / ≤ 500 | 0.06 | lead 0.5·(89.5/G)·ω_f (5-frame boxcar + 30 ms; before the clip; seeded on release) |
| D5a | 250 | as D5b | as D5b | 0.06 | — |

The firmware switch for each candidate, as listed in the brief:

| candidate | firmware |
|---|---|
| D1c | hard threshold 1229, opposing threshold off, asymmetric bound |
| D1a | hard and opposing thresholds both 1229 |
| D1c+G0 | D1c plus row 0 1400/236 |
| D3a | hard 1229, opposing 800, row 0 1414/185 |
| D3b | D3a plus SCL = PCL = 19072 |
| D4b | LP word, hard 512 and opposing 300 on h, motion gate 10 |
| D4a | GB-S13 |
| D5b | = D1a |
| D5a | D1a plus washout and Kf 28 |

**Grafts G:\*** are the scorer's own rows, not designer implementations: D1c's firmware under another designer's fork.

### 1.3 The common manoeuvre set and the metrics, identical for every row

| id | manoeuvre | speeds |
|---|---|---|
| TI | 60° hands-off turn-in at the planner's demand rate, min(320 = r79 planner p99, the clip_curvature jerk-5 rate) = **320 / 216 deg/s**. Hold 2.5 s, then unwind at the same rate. | 3, 8 m/s |
| C2 | 2° correction. *fast*: a 0.25 s ramp. *slow*: a 1.33 deg/s drift, r79's dwell-drift rate. | 15, 25 m/s |
| LH | hold at A/2 under a **400-count light hand**. A stiff hand (Kh 2000, Bh 30, panel convention) holds the wheel 30 % of A/2 toward centre (*c*) or outward (*o*) for 2 s, then releases. | 5, 15 m/s |
| OV | **hand override**: the word ramps to 1500 in 0.3 s while the hand drags the wheel to centre. Hold 1.5 s, then release. | 5, 15 m/s |
| RD | **request drop** mid-turn, from a hold at A/2 | 3, 8 m/s |

Metrics, the same code for every column:

| metric | definition |
|---|---|
| slew coverage | `cov@0.5s` = θ at 0.5 s / 60; `cov(sent)` = θ when the SENT setpoint reaches 60 (the flight's 0.37 measure) |
| t90 | time from plan start to 54° |
| ω pk | peak wheel rate |
| ovs | overshoot |
| settle | time to stay within ±2° of 60 |
| unwind t90 | as t90, on the unwind |
| under | overshoot past 0 on the unwind |
| tap pk | max \|T\|/8 / 307.6 |
| I kept | integration kept = Σ\|E′>>5\| on non-frozen run ticks / Σ on all run ticks |
| hand-lost | the share removed by the hand rules alone |
| frz tog/s | hand-freeze toggles per second |
| O1 eps | O1 episodes; hands-off they are twist trips |
| stall-surge | m4_episodes.stall_surge, verbatim, on the 100 Hz wheel rate |
| DJ | m4_dwell form at 100 Hz: rs < 0.25 deg/s for ≥ 0.2 s while the setpoint moves, then a ≥ 0.3° jump |
| r48 / r1.6-3 | wheel-rate rms in 4–8 Hz (the ratchet band) and 1.6–3 Hz (the goal criterion) |
| LH lurch | swing past the setpoint after release, away from the side the hand held |
| ΔI | in T, during the hold |
| OV yield | `t_O1` (ms from hand onset to fork O1); `T_res/T_pre` (lane torque in the last 0.5 s of override / before the hand); `tap pk under hand` (the peak lane torque the driver fights); `hand T` (hand force needed) |

**Cells:** r79F member, **median over seeds 1–3**. [brackets] = worst over both members × seeds 1–3.

## 2. Findings (EVIDENCE = as computed by this sim; the plant, twist and hand are BELIEF models)

### F1. Freeze relay and ratchet

The twist-keyed hand freeze is the ratchet the sim reproduces. V298 shows:

| measure | V298 at 3 / 8 m/s |
|---|---|
| hand-freeze toggles | **14.7 / 16.1 /s** |
| I kept | 0.57 / 0.52 |
| stall-surges, 2 speeds | **14** |
| O1 twist trips | 25 |

The candidates sort as follows.

| class | candidates | toggles/s | stall-surges | I kept at 8 m/s |
|---|---|---|---|---|
| **removes it** | D1c / D1a / D1c+G0 | 0 | 0 | 0.96–1.00 |
| | D5b | 3.5 / 0.8 | 0 | 0.96 |
| | D5a | 0.8 / 0 | 2 | 1.00 |
| **mostly removes it** | D3a | 1.6 / 2.0 | 0 | 0.83; but hand-lost 0.41 at 3 m/s, see F3 |
| **halves it** | D4b | 6.1 / 5.9 | 4 | 0.82 |
| **leaves it** | D2a / D2b | 9.8–13.5 | 4–5 | 0.47–0.53 |
| | D4a | 11.8 / 11.6 | 6 | 0.62 |

- **D2 and D4a leave the ratchet in place.** Their stall-surges fall only because the fork's faster or debounced setpoint changes the slew. The kept integration shows the freeze relay itself is untouched.
- **The 4–8 Hz wheel rate (r48) is NOT monotone with the ratchet fix.** At 3 / 8 m/s, against V298's 8.5 / 9.1 deg/s:

  | candidate | r48, deg/s |
  |---|---|
  | **D5b** | **14.4 / 12.0** (the highest of all rows) |
  | D5a | 11.2 / 8.8 |
  | D3a | 4.3 / 2.9 |
  | D4b | 5.8 / 6.2 |

  D5's boxcar-slope lead puts 4–8 Hz content back on the setpoint (BELIEF on cause).

### F2. Hands-off turn-in authority (t90 at 3 / 8 m/s, ω pk)

| rank | candidate | t90, s | ω pk, deg/s |
|---|---|---|---|
| — | V298 | 1.77 / 1.80 | 97 / 90 |
| 1 | **D3a** | **0.41 / 0.51** | 219 / 174 |
| 2 | D5a | 0.72 / 0.74 | — |
| 3 | D5b | 0.71 / 0.89 | — |
| 4 | D2b | 0.88 / 1.01 | — |
| 5 | D4b | 0.97 / 0.95 | — |
| 6 | D2a | 1.06 / 0.92 | — |
| 7 | D4a | 1.07 / 1.08 | — |
| 8 | D1c | 1.23 / 1.43 | — |

- **Firmware-only D1c:** −31 % / −21 % t90, purely from no longer discarding I. ω is unchanged, because the slew stays fork-limited at 120 deg/s.
- **Tap peak:**

  | candidate | tap peak, % of rail [worst] |
  |---|---|
  | D3a | 71 [79] |
  | D5b | 65 [77] |
  | V298 | 54 [62] |

- **No row reaches the rail in any manoeuvre** (max 79 %). This agrees with D3's finding that the rail never binds.

### F3. Faster slews raise the twist, which feeds back into the thresholds the designs relaxed (BELIEF on α extrapolation)

1. **D3a.** Its 1229 hard freeze still fires on its own slew:
   - hand-lost **0.41** at 3 m/s, against D3's r79 replay estimate of about 0;
   - word p99 1559.
2. **D3b** is DOMINATED by D3a. Its 400 deg/s cap trips the > 2500 instant O1 on the twist (2 episodes), so t90 is **0.65 vs D3a's 0.41** at 3 m/s and identical at 8 m/s.
3. **Instant-1200 O1** trips on the twist:

   | candidate | O1 twist trips, 3 m/s |
   |---|---|
   | D5b | 8 |
   | D2a | 2 |
   | D2b | 3 |
   | D1c (V298 fork, > 600) | 8 |
   | **D3's held-1200 rule** | **0** |

   This is D2's pre-registered X3 risk, confirmed in this sim at 3 m/s only. Outcomes vary strongly by residual realisation, hence the seed medians. t90 across seeds at 3 m/s:

   | candidate | t90 range, s |
   |---|---|
   | V298 | 1.10–2.31 |
   | D2a | 0.78–1.08 |
   | D3a | 0.39–0.43 |

### F4. Costs of the faster loop

**Turn-in overshoot**, ° median [worst]:

| candidate | overshoot |
|---|---|
| V298 | 1.6 [2.5] |
| D2a | 1.0 [1.7] (lowest) |
| D2b | 1.7 [2.8] |
| D1c | 3.0 [5.0] |
| D3a | 3.0 [6.5] |
| D4b | 3.2 [4.2] |
| D5b | 3.9 [7.2] |
| **D5a** | **5.7 [9.9]** |

**Unwind overshoot past 0 at 3 m/s:**

| candidate | overshoot past 0, ° |
|---|---|
| V298 | 4.2 |
| **D1c** | **0.6** (the asymmetric bound works) |
| D1a | 6.1 |
| D4b | 6.9 |
| D5b | 7.7 |
| D5a | 8.9 |

**The goal's 1.6–3 Hz hard-turn criterion gets worse with authority**, at 3 m/s:

| candidate | 1.6–3 Hz wheel rate, deg/s |
|---|---|
| V298 | 5.1 |
| D1c | 6.9 |
| D4b | 7.3 |
| D5b | 8.3 |
| D2a | 9.5 |
| D2b | 14.0 |
| **D3a** | **21.9** |

Every designer declared this.

### F5. Light hand (N1) — the hand-safety split

**Worst release lurch over everything:** the 5 m/s outward case on the heavy member.

| candidate | worst lurch, ° |
|---|---|
| V298 | 13.9 |
| D1c | **11.2** (best of the designer rows) |
| D4a | 14.7 |
| D2 | 14.8–14.9 |
| D3a | 15.4 |
| D4b | 16.5 |
| D5b | 18.6 |
| D1a | **23.7** |
| D5a | **26.3** |

- **This reproduces D1's own finding** that (a) fails N1 and (c) holds it.
- **D5's firmware is D1a**, so it inherits the cost: D5b 18.6, D5a 26.3.
- **Medians on r79F, outward at 5 m/s:**

  | candidate | lurch, ° |
  |---|---|
  | D1c | **4.1** |
  | V298 | 7.0 |
  | D4b | 7.5 |
  | D3a | 9.3 |
  | D1a / D5b | 10.2 |
  | D5a | 10.9 |

- **The grafts** with D1c's firmware land at 9.1–9.8 worst. The asymmetric bound removes D5b's and D3a's N1 cost.
- **O1 chatter under a 400-word light hand** (sum of 4 conditions):

  | fork | O1 episodes |
  |---|---|
  | V298 fork (V298, D1) | 25–28 |
  | debounced (D2, D4, D5) | 6–9 |
  | D3 | 0 |

### F6. Override (OV, word 1500)

**Fork O1 latency** after hand onset, 5 / 15 m/s:

| fork | latency, ms |
|---|---|
| V298 / D1 | 30 / 160 |
| D2 | 40 / 240 |
| D5 | 40 / 220 |
| D4 | 70 / 210 |
| **D3** | **370 / 400** (≈ 130–160 ms after the word passes 1229) |

**No row yields below ½ of its hold torque within 1.5 s.** T_res/T_pre is 0.73–0.94 everywhere. This is V298's own design: the I is frozen, not bled, and the fade is mild at 1500. Every candidate inherits it.

**D3a is the worst under a hand** (5 m/s):

| measure | D3a | V298 |
|---|---|---|
| peak lane torque under the overriding hand | **75 %** of the rail | 47 % |
| hand force to hold | 450 T (+21 %) | 372 T |
| residual | 0.94 | — |

1229/800 let the I wind into the hand's ramp before freezing, and O1 arrives 340 ms later. That is BELIEF on the hand model and EVIDENCE as computed. The driver can still override in every row.

### F7. Small corrections and request drop

**Small corrections (C2):** every row is within ±15 % of V298, except:

| candidate | change |
|---|---|
| D2b | slow e_rms **0.76 / 0.44** vs 0.99 / 0.60 |
| D4a / D4b+S13 | fast g@0.5 s at 15 m/s 0.44 vs 0.29 |
| G:D1c+D2bfork | 0.69 / 0.37 and 0.58 / 0.86, the best |

**This sim does NOT reproduce r79's small-correction stick.** DJ is 0 and the dwell count is identical for every row. So no candidate's stick claim is tested here.

**Request drop (RD):** identical for every row. The lane torque is 0 by +150 ms (guard B2) and the wheel springs back 10.5–14.6° in 1 s on the plant. No candidate changes the request-drop path.

## 3. Per-candidate score (one line each; the full tables follow)

| candidate | verdict (S2 time/nonlinear only) |
|---|---|
| V298 | baseline: ratchet present (14.7–16.1 tog/s, 14 stall-surges), slow turn-in (t90 1.8 s), I kept 0.52–0.57 |
| **D1c** | ratchet removed (0 tog, 0 stall-surges, I kept 0.96 at 8 m/s), unwind fixed (0.6°), best N1 (worst 11.2°). Authority gain modest (t90 −21–31 %, ω unchanged, fork-limited). Cost: overshoot 3.0 [5.0], settle 2.0 s. |
| D1a | turn-in = D1c but **N1 worst 23.7°**, unwind 6.1° — not for flight (confirms D1) |
| D1c+G0 | = D1c ± 5 % at 3 m/s; no separate signal at this resolution |
| D2a | t90 −40/−49 % (1.06/0.92), lowest overshoot; **freeze ratchet untouched** (9.8–13.5 tog/s, kept 0.46–0.47); twist O1 trips 25 → 4 |
| D2b | t90 0.88/1.01; best small-correction tracking; ratchet untouched; 1.6–3 Hz ×2.7 at 3 m/s |
| **D3a** | most authority (t90 0.41/0.51, ω 219/174, tap 71 [79] %), 0 O1 twist trips, 0 stall-surges. But the 1229 freeze fires on its own twist (hand-lost 0.41 at 3 m/s); overshoot 3.0 [6.5]; N1 worst 15.4°; **override latency 370–400 ms, 75 % rail under the hand, +21 % hand force**; 1.6–3 Hz ×4.3 |
| D3b | **dominated by D3a** (slower at 3 m/s from > 2500 twist O1 trips; identical at 8 m/s; rail never reached) |
| D4b | ratchet halved (6 tog/s, kept 0.69/0.82, 4 stall-surges), t90 0.97/0.95; overshoot 3.2 [4.2]; unwind 6.9°; N1 worst 16.5° |
| D4a | ≈ V298 on turn-in apart from the O1 debounce; helps 2° corrections at 15 m/s (+52 % g@0.5 s); ratchet untouched |
| D4b+S13 | = D4b at ≤ 8 m/s plus D4a's 15 m/s correction gain |
| D5b | t90 0.71/0.89, ratchet largely removed (kept 0.71/0.96). But **15 O1 twist trips**, **4–8 Hz wheel rate the highest of all rows (14.4)**, overshoot 3.9 [7.2], unwind 7.7°, **N1 worst 18.6° (inherits D1a)** |
| D5a | **worst N1 (26.3°) and overshoot (5.7 [9.9])**; confirms "not recommended" |
| G:D1c+D3fork | D3a's authority (t90 0.42/0.48), N1 worst 9.1°; keeps D3's override latency and 70 % rail under the hand; hand-lost 0.22 at 3 m/s |
| G:D1c+D5fork | = D5b on turn-in, with N1 worst 9.8° (vs 18.6°) |
| G:D1c+D2bfork | ratchet removed + D2b's tracking: best C2, N1 worst 9.1°, t90 1.19/0.80 (3 m/s slower, 4 O1 trips) |

**Limits of this scorer** (each is BELIEF; what would need checking):
1. The twist is a linear fit extrapolated to the faster designs' α.
2. The hand is the panel's stiff positional hand with a prescribed word, not an identified hand.
3. The residual is AR(1) with 3 seeds, and O1/freeze outcomes are bimodal per realisation.
4. SteerDelay is modelled as a pure plan time-shift.
5. The r79 stick, the 20 Hz staircase effect on stick, and the hand-steered turns of r79 are not reproduced.
6. D5a is mirrored from the design page's listing.

## 4. Tables (generated by `s2_report.py`; identical columns for every row)

### S0 summary (r79F, median of seeds 1-3; [worst over members x seeds])

| cand | TI t90 s 3/8 | TI cov(sent sp) 3/8 | TI ω pk 3/8 | TI ovs ° [worst] | TI settle s [worst] | tap pk %rail [worst] | hand-frz tog/s 3/8 | I kept 3/8 | stall-surge (TI 2 spd) | O1 twist trips (TI) | C2 fast g@0.5s 15/25 | C2 slow e_rms 15/25 | LH lurch ° worst | OV O1 ms 5/15 | OV T_res/T_pre 5/15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 1.77/1.80 | 0.75/0.76 | 97/90 | 1.6 [2.5] | 1.66 [2.40] | 54 [62] | 14.7/16.1 | 0.57/0.52 | 14 | 25 | 0.29/0.69 | 0.99/0.60 | 13.9 | 30/160 | 0.76/0.74 |
| D1c | 1.23/1.43 | 0.75/0.83 | 103/84 | 3.0 [5.0] | 2.00 [2.04] | 57 [67] | 0.0/0.0 | 0.58/0.96 | 0 | 21 | 0.33/0.75 | 0.95/0.54 | 11.2 | 30/160 | 0.73/0.74 |
| D1a | 1.23/1.43 | 0.75/0.83 | 103/84 | 3.0 [5.0] | 2.00 [2.04] | 57 [67] | 0.0/0.0 | 0.81/1.00 | 0 | 21 | 0.33/0.75 | 0.95/0.54 | 23.7 | 30/160 | 0.73/0.74 |
| D1c+G0 | 1.17/1.43 | 0.80/0.83 | 105/84 | 3.0 [5.0] | 2.00 [2.04] | 57 [67] | 0.0/0.0 | 0.58/0.96 | 0 | 22 | 0.33/0.75 | 0.95/0.54 | 11.2 | 30/160 | 0.73/0.74 |
| D2a | 1.06/0.92 | 0.57/0.61 | 121/121 | 1.0 [1.7] | 1.00 [1.67] | 57 [64] | 9.8/13.5 | 0.46/0.47 | 4 | 4 | 0.35/0.73 | 0.92/0.51 | 14.9 | 40/240 | 0.77/0.74 |
| D2b | 0.88/1.01 | 0.61/0.63 | 130/118 | 1.7 [2.8] | 0.91 [2.12] | 54 [62] | 11.6/10.6 | 0.50/0.53 | 5 | 5 | 0.47/0.73 | 0.76/0.44 | 14.8 | 40/240 | 0.77/0.74 |
| D3a | 0.41/0.51 | 0.45/0.58 | 219/174 | 3.0 [6.5] | 1.01 [1.02] | 71 [79] | 1.6/2.0 | 0.56/0.83 | 0 | 0 | 0.38/0.77 | 0.91/0.51 | 15.4 | 370/400 | 0.94/0.77 |
| D3b | 0.65/0.51 | 0.18/0.58 | 229/174 | 3.0 [5.5] | 1.01 [1.02] | 71 [79] | 3.1/2.0 | 0.50/0.83 | 2 | 2 | 0.38/0.77 | 0.91/0.51 | 15.4 | 370/400 | 0.94/0.77 |
| D4b | 0.97/0.95 | 0.75/0.77 | 117/114 | 3.2 [4.2] | 1.49 [1.77] | 61 [68] | 6.1/5.9 | 0.69/0.82 | 4 | 7 | 0.32/0.71 | 0.98/0.58 | 16.5 | 70/210 | 0.85/0.75 |
| D4a | 1.07/1.08 | 0.74/0.76 | 100/91 | 1.6 [2.5] | 0.96 [1.64] | 55 [68] | 11.8/11.6 | 0.58/0.62 | 6 | 6 | 0.44/0.70 | 0.84/0.58 | 14.7 | 70/210 | 0.78/0.75 |
| D4b+S13 | 0.97/0.95 | 0.75/0.77 | 117/114 | 3.2 [4.2] | 1.49 [1.77] | 61 [68] | 6.1/5.9 | 0.69/0.82 | 4 | 7 | 0.44/0.74 | 0.83/0.57 | 16.5 | 70/210 | 0.85/0.76 |
| D5b | 0.71/0.89 | 0.62/0.82 | 167/127 | 3.9 [7.2] | 1.35 [1.37] | 65 [77] | 3.5/0.8 | 0.71/0.96 | 0 | 15 | 0.38/0.77 | 0.91/0.51 | 18.6 | 40/220 | 0.83/0.78 |
| D5a | 0.72/0.74 | 0.73/0.72 | 158/167 | 5.7 [9.9] | 1.35 [1.39] | 71 [74] | 0.8/0.0 | 0.85/1.00 | 2 | 11 | 0.40/0.79 | 0.89/0.49 | 26.3 | 40/220 | 0.80/0.76 |
| G:D1c+D3fork | 0.42/0.48 | 0.43/0.64 | 222/178 | 3.6 [7.2] | 0.98 [0.99] | 73 [75] | 1.6/0.4 | 0.46/0.91 | 0 | 0 | 0.38/0.77 | 0.91/0.51 | 9.1 | 370/400 | 0.96/0.82 |
| G:D1c+D5fork | 0.71/0.89 | 0.62/0.82 | 167/127 | 3.9 [7.2] | 1.35 [1.37] | 65 [77] | 3.5/0.8 | 0.51/0.93 | 0 | 15 | 0.38/0.77 | 0.91/0.51 | 9.8 | 40/220 | 0.83/0.78 |
| G:D1c+D2bfork | 1.19/0.80 | 0.74/0.74 | 131/157 | 3.7 [5.9] | 1.31 [1.60] | 67 [68] | 0.4/0.0 | 0.61/0.96 | 7 | 7 | 0.58/0.86 | 0.69/0.37 | 9.1 | 40/240 | 0.89/0.81 |

### TI 60° turn-in at 3 m/s (plan 320 deg/s)

| cand | cov@0.5s | cov(sent) | t_sent s | t90 s | ω pk | ovs ° | settle s | max lag ° | unwind t90 s | under ° | tap %rail | I kept | hand-lost | frz tog/s | O1 eps | O1 frac | stall-surge | DJ | r48 °/s | r1.6-3 °/s | seed0 t90 | seed0 tog/s | heavy t90 [worst] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 0.12 | 0.75 | 1.66 | 1.77 | 97 | 1.6 | 1.66 | 58.8 | 1.04 | 4.2 | 38 | 0.57 | 0.40 | 14.7 | 11 | 0.07 | 5 | 1 | 8.5 | 5.1 | 2.00 | 9.0 | 1.37 [2.31] |
| D1c | 0.17 | 0.75 | 1.14 | 1.23 | 103 | 1.7 | 1.12 | 58.7 | 0.97 | 0.6 | 39 | 0.58 | 0.00 | 0.0 | 8 | 0.06 | 0 | 1 | 6.6 | 6.9 | 1.22 | 0.0 | 1.14 [1.42] |
| D1a | 0.17 | 0.75 | 1.14 | 1.23 | 103 | 1.7 | 1.12 | 58.7 | 0.92 | 6.1 | 39 | 0.81 | 0.00 | 0.0 | 8 | 0.06 | 0 | 1 | 6.6 | 8.2 | 1.22 | 0.0 | 1.14 [1.42] |
| D1c+G0 | 0.21 | 0.80 | 1.11 | 1.17 | 105 | 1.5 | 1.04 | 58.2 | 0.91 | 0.6 | 40 | 0.58 | 0.00 | 0.0 | 9 | 0.06 | 0 | 1 | 6.7 | 7.6 | 1.16 | 0.0 | 1.09 [1.31] |
| D2a | 0.19 | 0.57 | 0.84 | 1.06 | 121 | 1.0 | 1.00 | 54.5 | 0.72 | 1.8 | 40 | 0.46 | 0.54 | 9.8 | 2 | 0.02 | 2 | 1 | 5.7 | 9.5 | 0.89 | 2.2 | 1.35 [1.36] |
| D2b | 0.23 | 0.61 | 0.70 | 0.88 | 130 | 1.7 | 0.78 | 53.0 | 0.88 | 2.8 | 44 | 0.50 | 0.47 | 11.6 | 3 | 0.02 | 3 | 1 | 5.8 | 14.0 | 0.90 | 2.4 | 0.89 [1.35] |
| D3a | 0.99 | 0.45 | 0.27 | 0.41 | 219 | 1.5 | 0.28 | 48.9 | 0.36 | 3.7 | 61 | 0.56 | 0.41 | 1.6 | 0 | 0.00 | 0 | 1 | 4.3 | 21.9 | 0.39 | 1.2 | 0.41 [0.43] |
| D3b | 0.58 | 0.18 | 0.18 | 0.65 | 229 | 1.5 | 0.51 | 47.5 | 0.59 | 2.7 | 64 | 0.50 | 0.45 | 3.1 | 2 | 0.01 | 2 | 1 | 9.5 | 27.7 | 0.64 | 2.0 | 0.68 [0.69] |
| D4b | 0.17 | 0.75 | 0.88 | 0.97 | 117 | 1.7 | 0.85 | 57.9 | 0.73 | 6.9 | 40 | 0.69 | 0.16 | 6.1 | 4 | 0.03 | 2 | 1 | 5.8 | 7.3 | 1.28 | 3.1 | 0.87 [1.10] |
| D4a | 0.14 | 0.74 | 0.96 | 1.07 | 100 | 1.6 | 0.96 | 58.0 | 0.80 | 5.3 | 39 | 0.58 | 0.38 | 11.8 | 3 | 0.02 | 3 | 1 | 5.8 | 5.6 | 1.79 | 5.5 | 0.93 [1.21] |
| D4b+S13 | 0.17 | 0.75 | 0.88 | 0.97 | 117 | 1.7 | 0.85 | 57.9 | 0.73 | 6.9 | 40 | 0.69 | 0.16 | 6.1 | 4 | 0.03 | 2 | 1 | 5.8 | 7.3 | 1.28 | 3.1 | 0.87 [1.10] |
| D5b | 0.52 | 0.62 | 0.58 | 0.71 | 167 | 1.8 | 0.59 | 53.9 | 0.56 | 7.7 | 56 | 0.71 | 0.11 | 3.5 | 8 | 0.06 | 0 | 1 | 14.4 | 8.3 | 0.69 | 1.6 | 0.61 [0.77] |
| D5a | 0.48 | 0.73 | 0.65 | 0.72 | 158 | 4.7 | 1.35 | 54.1 | 0.58 | 8.9 | 52 | 0.85 | 0.03 | 0.8 | 6 | 0.05 | 1 | 1 | 11.2 | 7.6 | 0.63 | 0.0 | 0.64 [0.73] |
| G:D1c+D3fork | 0.97 | 0.43 | 0.27 | 0.42 | 222 | 1.7 | 0.30 | 49.6 | 0.40 | 0.6 | 62 | 0.46 | 0.22 | 1.6 | 0 | 0.00 | 0 | 1 | 4.5 | 20.9 | 0.41 | 0.8 | 0.41 [0.43] |
| G:D1c+D5fork | 0.52 | 0.62 | 0.58 | 0.71 | 167 | 1.8 | 0.59 | 53.9 | 0.64 | 0.7 | 56 | 0.51 | 0.12 | 3.5 | 8 | 0.06 | 0 | 1 | 14.7 | 6.5 | 0.69 | 1.6 | 0.61 [0.77] |
| G:D1c+D2bfork | 0.30 | 0.74 | 1.11 | 1.19 | 131 | 1.7 | 1.07 | 52.6 | 0.75 | 0.6 | 45 | 0.61 | 0.02 | 0.4 | 4 | 0.03 | 4 | 1 | 6.4 | 17.1 | 1.18 | 0.0 | 1.23 [1.24] |

### TI 60° turn-in at 8 m/s (plan 216 deg/s)

| cand | cov@0.5s | cov(sent) | t_sent s | t90 s | ω pk | ovs ° | settle s | max lag ° | unwind t90 s | under ° | tap %rail | I kept | hand-lost | frz tog/s | O1 eps | O1 frac | stall-surge | DJ | r48 °/s | r1.6-3 °/s | seed0 t90 | seed0 tog/s | heavy t90 [worst] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 0.12 | 0.76 | 1.70 | 1.80 | 90 | 0.8 | 1.61 | 57.0 | 1.25 | -0.3 | 54 | 0.52 | 0.48 | 16.1 | 14 | 0.08 | 9 | 1 | 9.1 | 6.5 | 2.66 | 11.8 | 1.54 [2.56] |
| D1c | 0.20 | 0.83 | 1.37 | 1.43 | 84 | 3.0 | 2.00 | 56.3 | 0.88 | 1.2 | 57 | 0.96 | 0.00 | 0.0 | 13 | 0.09 | 0 | 1 | 8.7 | 6.9 | 1.46 | 0.0 | 1.24 [1.48] |
| D1a | 0.20 | 0.83 | 1.37 | 1.43 | 84 | 3.0 | 2.00 | 56.3 | 0.88 | 2.3 | 57 | 1.00 | 0.00 | 0.0 | 13 | 0.09 | 0 | 1 | 8.6 | 6.7 | 1.46 | 0.0 | 1.24 [1.48] |
| D1c+G0 | 0.20 | 0.83 | 1.37 | 1.43 | 84 | 3.0 | 2.00 | 56.3 | 0.88 | 1.2 | 57 | 0.96 | 0.00 | 0.0 | 13 | 0.09 | 0 | 1 | 8.7 | 6.9 | 1.45 | 0.0 | 1.24 [1.48] |
| D2a | 0.25 | 0.61 | 0.71 | 0.92 | 121 | 0.1 | 0.85 | 53.8 | 0.80 | -0.1 | 57 | 0.47 | 0.53 | 13.5 | 2 | 0.02 | 2 | 0 | 5.8 | 11.6 | 0.98 | 2.9 | 0.90 [1.51] |
| D2b | 0.19 | 0.63 | 0.77 | 1.01 | 118 | -0.0 | 0.91 | 51.4 | 0.93 | -0.1 | 54 | 0.53 | 0.47 | 10.6 | 2 | 0.01 | 2 | 1 | 4.7 | 10.3 | 1.14 | 2.2 | 1.00 [1.22] |
| D3a | 0.89 | 0.58 | 0.39 | 0.51 | 174 | 3.0 | 1.01 | 42.2 | 0.46 | 2.8 | 71 | 0.83 | 0.16 | 2.0 | 0 | 0.00 | 0 | 1 | 2.9 | 10.9 | 0.49 | 1.2 | 0.51 [0.53] |
| D3b | 0.89 | 0.58 | 0.39 | 0.51 | 174 | 3.0 | 1.01 | 42.2 | 0.46 | 2.8 | 71 | 0.83 | 0.16 | 2.0 | 0 | 0.00 | 0 | 1 | 2.9 | 10.9 | 0.49 | 1.2 | 0.51 [0.53] |
| D4b | 0.19 | 0.77 | 0.88 | 0.95 | 114 | 3.2 | 1.49 | 55.0 | 0.70 | 2.4 | 61 | 0.82 | 0.18 | 5.9 | 3 | 0.02 | 2 | 1 | 6.2 | 5.5 | 1.49 | 3.5 | 1.03 [1.28] |
| D4a | 0.17 | 0.76 | 0.97 | 1.08 | 91 | 0.6 | 0.96 | 55.4 | 0.78 | 1.2 | 55 | 0.62 | 0.38 | 11.6 | 3 | 0.02 | 3 | 1 | 6.5 | 5.0 | 2.07 | 14.5 | 0.99 [1.41] |
| D4b+S13 | 0.19 | 0.77 | 0.88 | 0.95 | 114 | 3.2 | 1.49 | 55.0 | 0.70 | 2.4 | 61 | 0.82 | 0.18 | 5.9 | 3 | 0.02 | 2 | 1 | 6.2 | 5.5 | 1.49 | 3.5 | 1.03 [1.28] |
| D5b | 0.37 | 0.82 | 0.83 | 0.89 | 127 | 3.9 | 1.35 | 50.7 | 0.65 | 4.4 | 65 | 0.96 | 0.02 | 0.8 | 7 | 0.06 | 0 | 1 | 12.0 | 8.9 | 0.80 | 0.0 | 0.74 [0.90] |
| D5a | 0.37 | 0.72 | 0.67 | 0.74 | 167 | 5.7 | 1.06 | 51.6 | 0.68 | 4.2 | 71 | 1.00 | 0.00 | 0.0 | 5 | 0.04 | 1 | 0 | 8.8 | 11.6 | 0.85 | 0.0 | 0.78 [0.86] |
| G:D1c+D3fork | 0.95 | 0.64 | 0.39 | 0.48 | 178 | 3.6 | 0.98 | 40.3 | 0.45 | 1.5 | 73 | 0.91 | 0.01 | 0.4 | 0 | 0.00 | 0 | 1 | 3.4 | 12.7 | 0.48 | 0.0 | 0.47 [0.49] |
| G:D1c+D5fork | 0.37 | 0.82 | 0.83 | 0.89 | 127 | 3.9 | 1.35 | 50.7 | 0.65 | 2.0 | 65 | 0.93 | 0.02 | 0.8 | 7 | 0.06 | 0 | 1 | 11.9 | 9.5 | 0.80 | 0.0 | 0.74 [0.90] |
| G:D1c+D2bfork | 0.25 | 0.74 | 0.73 | 0.80 | 157 | 3.7 | 1.31 | 53.0 | 0.80 | 1.2 | 67 | 0.96 | 0.00 | 0.0 | 3 | 0.02 | 3 | 1 | 4.8 | 15.4 | 0.82 | 0.0 | 0.81 [1.16] |

### C2 2° correction (fast 0.25 s ramp; slow 1.33 deg/s drift)

| cand | fast 15: t90 | fast 15: g@0.5 | fast 15: ovs | slow 15: e_rms | slow 15: max|e| | slow 15: DJ | slow 15: dwell | fast 25: t90 | fast 25: g@0.5 | fast 25: ovs | slow 25: e_rms | slow 25: max|e| | slow 25: DJ | slow 25: dwell |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 2.26 | 0.29 | -0.10 | 0.99 | 1.82 | 0 | 2 | 1.28 | 0.69 | -0.04 | 0.60 | 1.20 | 0 | 2 |
| D1c | 2.06 | 0.33 | -0.06 | 0.95 | 1.84 | 0 | 2 | 1.00 | 0.75 | 0.00 | 0.54 | 1.10 | 0 | 2 |
| D1a | 2.06 | 0.33 | -0.06 | 0.95 | 1.84 | 0 | 2 | 1.00 | 0.75 | 0.00 | 0.54 | 1.10 | 0 | 2 |
| D1c+G0 | 2.06 | 0.33 | -0.06 | 0.95 | 1.84 | 0 | 2 | 1.00 | 0.75 | 0.00 | 0.54 | 1.10 | 0 | 2 |
| D2a | 2.15 | 0.35 | -0.10 | 0.92 | 1.76 | 0 | 2 | 1.18 | 0.73 | -0.04 | 0.51 | 1.06 | 0 | 2 |
| D2b | 2.08 | 0.47 | -0.06 | 0.76 | 1.48 | 0 | 2 | 1.20 | 0.73 | 0.01 | 0.44 | 0.92 | 0 | 2 |
| D3a | 2.00 | 0.38 | -0.05 | 0.91 | 1.77 | 0 | 2 | 0.97 | 0.77 | -0.00 | 0.51 | 1.06 | 0 | 2 |
| D3b | 2.00 | 0.38 | -0.05 | 0.91 | 1.77 | 0 | 2 | 0.97 | 0.77 | -0.00 | 0.51 | 1.06 | 0 | 2 |
| D4b | 2.17 | 0.32 | -0.09 | 0.98 | 1.84 | 0 | 2 | 1.08 | 0.71 | -0.02 | 0.58 | 1.10 | 0 | 2 |
| D4a | 1.84 | 0.44 | -0.04 | 0.84 | 1.62 | 1 | 2 | 1.21 | 0.70 | -0.04 | 0.58 | 1.16 | 0 | 2 |
| D4b+S13 | 1.76 | 0.44 | -0.04 | 0.83 | 1.59 | 1 | 2 | 1.05 | 0.74 | -0.03 | 0.57 | 1.17 | 0 | 2 |
| D5b | 2.01 | 0.38 | -0.06 | 0.91 | 1.77 | 0 | 2 | 0.97 | 0.77 | -0.00 | 0.51 | 1.05 | 0 | 2 |
| D5a | 2.31 | 0.40 | -0.12 | 0.89 | 1.70 | 0 | 2 | 1.01 | 0.79 | -0.05 | 0.49 | 1.01 | 0 | 2 |
| G:D1c+D3fork | 2.00 | 0.38 | -0.05 | 0.91 | 1.77 | 0 | 2 | 0.97 | 0.77 | -0.00 | 0.51 | 1.06 | 0 | 2 |
| G:D1c+D5fork | 2.01 | 0.38 | -0.06 | 0.91 | 1.77 | 0 | 2 | 0.97 | 0.77 | -0.00 | 0.51 | 1.05 | 0 | 2 |
| G:D1c+D2bfork | 1.71 | 0.58 | -0.03 | 0.69 | 1.34 | 0 | 2 | 0.83 | 0.86 | 0.05 | 0.37 | 0.83 | 0 | 2 |

### LH hold under a 400-count light hand (c = held 30 % toward centre, o = 30 % outward), release

| cand | c5: lurch | c5: ΔI T | c5: frz | c5: tap | o5: lurch | o5: ΔI T | o5: frz | o5: tap | c15: lurch | c15: ΔI T | c15: frz | c15: tap | o15: lurch | o15: ΔI T | o15: frz | o15: tap | worst lurch (all) | O1 eps (med, all) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 2.6 | -216 | 0.92 | 43 | 7.0 | 864 | 0.62 | 32 | 0.3 | -67 | 0.77 | 16 | 0.0 | 104 | 0.61 | 11 | 13.9 | 25 |
| D1c | 2.6 | -215 | 0.93 | 43 | 4.1 | 658 | 0.59 | 25 | 1.4 | -182 | 0.00 | 22 | 0.7 | 235 | 0.00 | 12 | 11.2 | 28 |
| D1a | 2.6 | -215 | 0.93 | 43 | 10.2 | 1122 | 0.38 | 43 | 1.4 | -182 | 0.00 | 22 | 0.7 | 235 | 0.00 | 12 | 23.7 | 26 |
| D1c+G0 | 2.4 | -216 | 0.94 | 45 | 4.0 | 657 | 0.61 | 26 | 1.4 | -182 | 0.00 | 22 | 0.7 | 235 | 0.00 | 12 | 11.2 | 28 |
| D2a | 2.4 | -216 | 0.93 | 43 | 6.8 | 905 | 0.65 | 33 | 0.3 | -65 | 0.78 | 16 | 0.0 | 103 | 0.64 | 10 | 14.9 | 6 |
| D2b | 2.5 | -216 | 0.93 | 43 | 6.8 | 905 | 0.65 | 33 | 0.3 | -67 | 0.78 | 16 | 0.0 | 103 | 0.64 | 10 | 14.8 | 6 |
| D3a | 2.5 | -216 | 0.97 | 45 | 9.3 | 1122 | 0.62 | 44 | 1.6 | -205 | 0.21 | 23 | 1.0 | 268 | 0.01 | 10 | 15.4 | 0 |
| D3b | 2.5 | -216 | 0.97 | 45 | 9.3 | 1122 | 0.62 | 44 | 1.6 | -205 | 0.21 | 23 | 1.0 | 268 | 0.01 | 10 | 15.4 | 0 |
| D4b | 2.6 | -216 | 0.96 | 43 | 7.5 | 898 | 0.67 | 33 | 0.4 | -56 | 0.81 | 16 | 0.0 | 106 | 0.64 | 10 | 16.5 | 9 |
| D4a | 2.6 | -216 | 0.94 | 43 | 7.6 | 905 | 0.65 | 33 | 0.6 | -87 | 0.78 | 18 | 0.0 | 135 | 0.64 | 10 | 14.7 | 9 |
| D4b+S13 | 2.6 | -216 | 0.96 | 43 | 7.5 | 898 | 0.67 | 33 | 0.6 | -74 | 0.81 | 18 | 0.0 | 138 | 0.64 | 10 | 16.5 | 9 |
| D5b | 2.9 | -215 | 0.96 | 47 | 10.2 | 1123 | 0.55 | 46 | 1.6 | -205 | 0.14 | 23 | 1.0 | 271 | 0.00 | 10 | 18.6 | 7 |
| D5a | 3.0 | -218 | 0.96 | 46 | 10.9 | 1119 | 0.55 | 45 | 1.6 | -216 | 0.04 | 23 | 1.0 | 262 | 0.00 | 10 | 26.3 | 7 |
| G:D1c+D3fork | 2.6 | -216 | 0.97 | 43 | 4.2 | 658 | 0.78 | 25 | 1.6 | -205 | 0.21 | 23 | 1.0 | 270 | 0.00 | 10 | 9.1 | 0 |
| G:D1c+D5fork | 2.9 | -215 | 0.96 | 47 | 4.6 | 658 | 0.75 | 28 | 1.6 | -205 | 0.14 | 23 | 1.0 | 271 | 0.00 | 10 | 9.8 | 6 |
| G:D1c+D2bfork | 2.4 | -216 | 0.97 | 43 | 3.7 | 658 | 0.71 | 25 | 1.6 | -205 | 0.04 | 23 | 0.9 | 256 | 0.00 | 10 | 9.1 | 6 |

### OV hand override (word 1500, hand drags the wheel to centre, 1.5 s), release

| cand | 5: t_O1 ms | 5: t |T|<½ ms | 5: T_res T | 5: T_pre T | 5: tap pk under hand % | 5: hand T | 5: rel t90 s | 5: rel ovs ° | 15: t_O1 ms | 15: t |T|<½ ms | 15: T_res T | 15: T_pre T | 15: tap pk under hand % | 15: hand T | 15: rel t90 s | 15: rel ovs ° |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 30 | never | 340 | 446 | 47 | 372 | 0.39 | 1.4 | 160 | never | 230 | 312 | 16 | 235 | 0.52 | 0.2 |
| D1c | 30 | never | 325 | 445 | 48 | 366 | 0.38 | 2.5 | 160 | never | 240 | 322 | 17 | 238 | 0.45 | 0.3 |
| D1a | 30 | never | 325 | 445 | 48 | 366 | 0.38 | 2.5 | 160 | never | 240 | 322 | 17 | 238 | 0.45 | 0.3 |
| D1c+G0 | 30 | never | 323 | 444 | 50 | 355 | 0.51 | 2.3 | 160 | never | 240 | 322 | 17 | 238 | 0.45 | 0.3 |
| D2a | 40 | never | 345 | 446 | 55 | 399 | 0.46 | 1.4 | 240 | never | 230 | 312 | 16 | 235 | 0.66 | 0.1 |
| D2b | 40 | never | 345 | 446 | 55 | 399 | 0.46 | 1.6 | 240 | never | 230 | 312 | 16 | 235 | 0.66 | 0.1 |
| D3a | 370 | never | 418 | 444 | 75 | 450 | 0.33 | 2.4 | 400 | never | 248 | 322 | 19 | 243 | 0.42 | 0.4 |
| D3b | 370 | never | 418 | 444 | 75 | 450 | 0.33 | 2.4 | 400 | never | 248 | 322 | 19 | 243 | 0.42 | 0.4 |
| D4b | 70 | never | 380 | 447 | 56 | 403 | 0.37 | 2.5 | 210 | never | 233 | 312 | 16 | 235 | 0.50 | 0.3 |
| D4a | 70 | never | 347 | 446 | 55 | 387 | 0.39 | 1.6 | 210 | never | 243 | 323 | 17 | 240 | 0.44 | 0.3 |
| D4b+S13 | 70 | never | 380 | 447 | 56 | 403 | 0.37 | 2.5 | 210 | never | 246 | 323 | 18 | 243 | 0.42 | 0.4 |
| D5b | 40 | never | 370 | 445 | 60 | 421 | 0.31 | 2.9 | 220 | never | 250 | 322 | 17 | 244 | 0.36 | 0.5 |
| D5a | 40 | 826 | 359 | 446 | 59 | 345 | 0.33 | 3.8 | 220 | never | 241 | 318 | 17 | 246 | 0.38 | 0.5 |
| G:D1c+D3fork | 370 | never | 429 | 445 | 70 | 439 | 0.34 | 2.6 | 400 | never | 264 | 322 | 19 | 253 | 0.41 | 0.5 |
| G:D1c+D5fork | 40 | never | 370 | 445 | 60 | 421 | 0.31 | 2.9 | 220 | never | 250 | 322 | 17 | 244 | 0.36 | 0.5 |
| G:D1c+D2bfork | 40 | never | 395 | 445 | 56 | 435 | 0.44 | 2.6 | 240 | never | 261 | 322 | 18 | 251 | 0.53 | 0.3 |

### RD request drop mid-turn (hold at A/2)

| cand | 3: T_pre | 3: T +50 ms | 3: T +150 ms | 3: ω pk | 3: Δθ 1 s | 8: T_pre | 8: T +50 ms | 8: T +150 ms | 8: ω pk | 8: Δθ 1 s |
|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 442 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D1c | 428 | 77 | 0 | 23.4 | 14.6 | 397 | 72 | 0 | 31.1 | 10.5 |
| D1a | 428 | 77 | 0 | 23.4 | 14.6 | 397 | 72 | 0 | 31.1 | 10.5 |
| D1c+G0 | 427 | 77 | 0 | 23.4 | 14.6 | 397 | 72 | 0 | 31.1 | 10.5 |
| D2a | 442 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D2b | 442 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D3a | 441 | 80 | 0 | 23.3 | 14.5 | 379 | 69 | 0 | 31.3 | 10.6 |
| D3b | 441 | 80 | 0 | 23.3 | 14.5 | 379 | 69 | 0 | 31.3 | 10.6 |
| D4b | 443 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D4a | 442 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D4b+S13 | 443 | 80 | 0 | 23.3 | 14.5 | 378 | 69 | 0 | 31.3 | 10.6 |
| D5b | 436 | 79 | 0 | 23.4 | 14.6 | 379 | 69 | 0 | 31.3 | 10.6 |
| D5a | 446 | 81 | 0 | 23.2 | 14.4 | 388 | 70 | 0 | 31.1 | 10.5 |
| G:D1c+D3fork | 436 | 79 | 0 | 23.4 | 14.6 | 379 | 69 | 0 | 31.3 | 10.6 |
| G:D1c+D5fork | 436 | 79 | 0 | 23.4 | 14.6 | 379 | 69 | 0 | 31.3 | 10.6 |
| G:D1c+D2bfork | 436 | 79 | 0 | 23.4 | 14.6 | 379 | 69 | 0 | 31.3 | 10.6 |

walls (s): TI 8.9, C2 10.2, LH 12.1, OV 10.4, RD 6.3; report 0.12 s
