# HARNESS-TIME 2026-09-30 -- the zero-cave ANGLE LOOP, closed on the identified plant, exact at 1 kHz

**Agent:** `harness-time` (subagent). **Analysis only:** nothing was built, flashed or sent; no fork or firmware file was
touched; no Ghidra state was changed (one read-only `disassemble_bytes dry_run` of `0x29CF6-0x29EE4` on the V294 program).
**Script:** `analysis-2020accord/studies/angle_loop/harness_time.py` (this report's tables are written by
`harness_time_report.py` from its caches in `_scratch/angle_loop/harness-time/`). Fixed seeds, no network.
**Image:** V295 cal, hash-checked by `lane_mirror_v295.load_cal()` (sha256 `5c044d65...`), with the angle-loop cal edits
a `0xC63E8` = 0, b `0xC63EA` = 8192, C `0xC62E6` = 65535 and the in-place code edits (1)-(4) [+ (5) where Kd > 0, (6) where named].
Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**.

## 0. Bottom line

1. **The harness is exact where it claims to be.** EVIDENCE: the vectorised lane equals the byte-exact scalar mirror
   `lane_mirror_v295.lane_tick` (angle switches, pol = -1) on **144,000 ticks, 0 mismatches**, over 12 random configurations and
   every branch (skips, input bail, 0x7FFF sentinel, sign-hold gate blocks, driver fade, rail, int32 wraps, scalar and vector
   setpoint paths). Karnopp stick (39 < Fs 40 stays stuck, 41 moves), linear static gain and damped frequency to 0.001, the
   record's V295 20 Hz comparator (3.85) reproduced. **No int32 wrap occurred in any of the 1,000+ runs.**
2. **Without a cave the goal is NOT met.** EVIDENCE (sim, nominal family, 615 cal configurations incl. the brief's full grid):
   - **FLAT Kp** -- the best flat set (Kp 2500, Ki 1024, ICL 4096, DB 0, Kd 16) passes 12.5-30 m/s but at **3-8 m/s it is a
     3.9 Hz limit cycle of 10-14 deg peak-to-peak with ~1,900-2,700 T counts peak-to-peak** (section 5). Any flat Kp that is stable at
     3-8 m/s (Kp <= 1200-1500 with Kd 24-28) under-tracks at speed (0.2 Hz gain 0.72-0.89 at 19-30 m/s).
     **0 of 615 configurations pass every gate at 3 m/s under the strict reading; at most 4 of 7 speeds pass for any flat set
     (line-only).**
   - **ANGLE-INDEXED Kp** (cal-only, 5 knots on idx = |theta_sp|/1.61 deg) -- **at most 3/7 speeds** (line-only), 0-1/7 strict:
     |theta_sp| does not identify speed. A small-angle command at 3-8 m/s gets the highway knot and stick-slips or goes unstable
     (8 m/s: 4.6-4.8 counts rms 5-30 Hz in the holds); lowering the small-angle knot to the low-speed value breaks highway
     tracking (0.5 Hz gain 1.11-1.13 at 26-30 m/s, PI peaking).
3. **A SPEED schedule of Kp AND Kd is the first thing a cave must buy.** EVIDENCE (sim): SPEED-1 (Kp 1500/1200/1800/1500/2500
   at 3/5/12.5/19/26 m/s, Kd 28/24/24/0 at 3/5/8/12.5 m/s, Ki 1024, ICL 4096, DB 0) passes **6/7 speeds** under the line-only
   reading on the nominal plant; 8 m/s misses only the 0.5 Hz tracking gain (1.061 vs <= 1.05) by PI peaking -- curing that
   needs Ki scheduled too (no in-place Ki schedule exists). **BELIEF, needs a trace:** the Kp and Kd LERPs could be re-keyed on
   speed with two more in-place edits inside the map LERP that edit (4) makes dead (section 11) -- no cave.
4. **No candidate is robust across the identified family.** EVIDENCE (sim): SPEED-1 passes 6/7 on nominal, `tau0`, `+mode20Hz`,
   5/7 on `J_lo`, `+mode13Hz`, but only **1-3/7 on `J_hi`, `J_hi2`, `b_lo`, `b_hi`, `F_lo`, `F_hi`, `tau6`, `ms_free`, and 0/7 on
   `light_b`**. The failures are stick-slip at 3-5 m/s and the +-5 % tracking window. The full-resolution cave option (below)
   does **not** buy this margin back. The record's rule applies: a gain tuned to one member is not supported by this drive.
5. **TEXTURE: the 0.1 deg setpoint and the 0.1 deg feedback, times Kp, put 2-7 counts rms of 5-30 Hz torque into ordinary
   lane-keeping motion.** EVIDENCE (arithmetic + sim): one angle LSB is **0.01 x Kp T counts** (25 counts at Kp 2500; selftest 2:
   Kp 1000 gives 100 T per deg). SPEED-1 carries 4.1-4.6 counts rms at 26-30 m/s during a +-0.9 deg / 0.2 Hz correction.
   Neither fix alone removes it (0.025 deg setpoint: 2.3; 8x finer angle: 3.0; 1 kHz fresh operands: 4.2). **Only all four
   together -- a 0.025 deg setpoint, 1 kHz setpoint interpolation, an 8x finer angle and fresh 1 kHz operands -- bring it to
   0.6 counts** (section 10). Whether 4 counts rms is felt is UNKNOWN (no N.m scale exists in the kit; BELIEF threshold 2 counts,
   the record's quiet-cruise tap residual is 0.66-0.87 counts per 5 Hz band). Under the STRICT reading only 19 m/s passes for
   SPEED-1.
6. **Safety.** EVIDENCE (sim, lane-level): the **0xE4 fault sentinel** with the angle loop rails the lane for the whole ramp-down
   when it was already pushing that way: **0xC63F6 = 16: 2,100-2,290 T for 2.01 s, a 30-180 deg wheel excursion** (36.6 deg at
   26 m/s); **0xC63F6 = 328: ~1,100 T for 0.10 s, 2.1-6.6 deg**. Pushing the other way, the sign-hold gate blocks it (T <= 272).
   (The brief's "sp = 16384" is wrong: with edit (4) the sentinel loads as sp = **32767**, EVIDENCE `lane_mirror_v295 _claims`;
   P rails either way.) A parallel trace (`docs/traces/TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md`, NOT
   re-verified here) finds the pulse IS delivered and proposes **Fix A2, `0x29A56` `da 05` -> `b2 05`** (the PID runs iff ramp != 0
   AND request == 1). Simulated here (BELIEF on the byte semantics, EVIDENCE on the arithmetic): **A2 removes the pulse at every
   speed -- peak T = the pre-fault hold torque decaying (69-326 counts), <= 0.06 s above 50 counts, 0.0 deg excursion** -- and equals
   edit (6) on the latch path; it does not touch the reachable fade-only override. **The override release lurch is set by ICL, not by edit (6):** after a 1 s override holding the wheel 1.5 deg off
   at 26 m/s, ICL 1024 / 4096 / 10240 give 0.24 / 1.69 / 3.55 deg of overshoot past the setpoint; ICL 1024 costs 0.6-3.4 deg of
   hold error at 3-19 m/s. Edit (6) acts only on the latch path (STEER_STATUS 4/7, never seen engaged in the record) and halves
   that overshoot at 26-30 m/s (1.1-1.2 -> 0.5 deg).

**Verdict for the brief's question:** the goal's dead-zone / stick-slip and tracking criteria are **not met WITHOUT a cave** (flat or
angle-indexed Kp, Ki + ICL as the bound), on any reading. **WITH a speed schedule** they are met at 6 of 7 speeds on the nominal
plant (line-only reading), at 1 of 7 under the strict texture reading, and robustly on none. **Do not fly any of these as a
flight candidate.** FLAT-T in particular is a 3.9 Hz, +-5-7 deg oscillation below 8 m/s.

## 1. What the harness simulates

```
fork (100 Hz)            th_sp(t) = scenario reference, 100 Hz ZOH (outer = 'ff', stock LatControlAngle is a feedforward of
                         the planner's angle; nothing is fed back, so the 60 ms round trip does not act)
                         outer = 'pi' (section 8 only): th_sp = th_ref + c, c += (10 ms / 1.0 s) * (th_ref - th_wire[k-6]),
                         th_wire = the 0x14A angle ~60 ms old -- a stand-in for the path-level loop (BELIEF on its form)
                         inactive (disengage): sends the measured angle th_wire[k-6] (or 0 in 'dis_zero')
0xE4 -> FUN_00052676     raw = -round(10 th_sp); gp-0x69ae = clamp(-4 raw, +-16384); fault: 0x7FFF   (frame on tick % 10 == 0, BELIEF)
LKAS lane, 1 kHz         LaneVec == lane_mirror_v295.lane_tick(x_src='angle', fb_op='sum', sp_src='69ae', d_src 'E'|'rate',
                         i_reset_on_ramp0), pol = gp-0x6752 = -1, every cal LE from the V295 image, angle-loop cals a/b/C
                         E = 16 (th_sp - th) ; I, P (Kp LERP on idx), D, fade f, sum clamp, output lag 5.05 Hz, sign-hold gate,
                         x ramp, x 5346/32768, lane clamp 3072 -> T = gp-0x6b38 (rail 2461)
engage SM                ramp gp-0x69b0 / gp-0x6806 / gp-0x6805 per scenario: engaged 0x8000; disengage and fault -0xC63F6/tick;
                         override latch -0xC63F4 (328)/tick with the request held; re-engage +0xC63F8 (33)/tick
transport                2 ms (nominal member), u = -T  (T counts, + = left)
plant, 10 kHz sub-steps  J th'' + b th' + k sat tanh(th/sat) + Fc sgn(th') = u (+ hand), Karnopp: stuck while th' == 0 and
                         |u - spring| <= Fs; optional collocated two-mass mode (stress members)
sensors (slot 4)         gp-0x6a00 = round(10 th) (0.1 deg quantiser, BELIEF on its exact staircase -- the firmware is
                         ceil(linear) + trunc(VGR correction) on 1/32-LSB motor counts); gp-0x6a56 = round(8 (th[n]-th[n-3])/3 ms)
                         + N(0, 1.93 counts) (the record's standstill floor; the 3 ms former is the record's BELIEF);
                         BOTH sampled on tick % 10 == 4 AFTER the lane ran -> the lane sees a 100 Hz hold, age 1-10 ms
```

**Exactness evidence** (`python harness_time.py --selftest`, output verbatim):

```
SELFTEST 1  LaneVec vs lane_mirror_v295.lane_tick (angle edits, pol -1): 0 mismatching ticks of 144000  PASS   [branch coverage {'skip': 72978, 'invalid': 51492, 'sentinel': 16800, 'gate_block': 46702, 'fade': 63006, 'rail': 1103}]  (9 s)
SELFTEST 2  Kp 1000, error 1.0 deg, hands off: E = 160 (want 160), T = -100 (record: ~100 per deg)
SELFTEST 3  plant: |u| 39 < Fs 40 -> th 0.0000 (want 0); |u| 41 -> th 0.6396 (want > 0)
SELFTEST 4  plant: static th 5.000 (want 5.000), damped f 1.589 Hz (want 1.590)
SELFTEST 5  |P/x| at 20 Hz: V295 recomputed 3.85 (record 3.85); angle loop Kp 6000 -> 3.72, Kd 16 -> 2.00
SELFTEST 6  speed-keyed Kp == LERP(kp, speed>>8) over 0-40 m/s: 0 mismatches  PASS
SELFTEST PASS
```

## 2. The plant used, per speed (`v294_plant.family()['nominal'].at(v)`, linear in speed between the fit knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9 m/s, flat outside; the spring saturation is the record's prior sat(v))

| speed m/s | J T/(deg/s^2) | b T/(deg/s) | k T/deg | Fc T | Fs T | spring sat deg | transport ms | 2Fs/k deg |
|---|---|---|---|---|---|---|---|---|
| 3 | 0.20 | 4.94 | 6.5 | 76.2 | 94.7 | 220.8 | 2 | 29.37 |
| 5 | 0.20 | 5.05 | 11.8 | 51.9 | 65.3 | 123.0 | 2 | 11.08 |
| 8 | 0.20 | 5.24 | 20.2 | 13.5 | 18.9 | 57.6 | 2 | 1.87 |
| 12.5 | 0.20 | 11.04 | 30.8 | 14.9 | 17.6 | 27.9 | 2 | 1.14 |
| 19 | 0.20 | 21.82 | 74.9 | 7.2 | 9.1 | 20.3 | 2 | 0.24 |
| 26 | 0.20 | 25.89 | 57.9 | 4.7 | 6.0 | 19.4 | 2 | 0.21 |
| 30 | 0.20 | 26.41 | 55.8 | 4.4 | 5.6 | 19.3 | 2 | 0.20 |

## 3. Scenarios, metrics and the gates

Turn amplitude A per speed (deg of wheel): the brief's 90 / 30 / 3 at 3 / 8 / 26 m/s; interpolated at a similar lateral
acceleration elsewhere: **3: 90, 5: 50, 8: 30, 12.5: 12, 19: 5, 26: 3, 30: 2.5** (BELIEF on "hand-sized").

| scenario | what | length |
|---|---|---|
| `rh` ramp-and-hold | 0 -> +A (ramp 1 s; 2 s at 5 m/s; 3 s at 3 m/s), hold 3 s, -> -A, hold 3 s, -> 0, hold 2 s | 12.5-20.5 s |
| `s02`, `s05` | lane-keeping sinusoid +-0.3 A (27 / 15 / 9 / 3.6 / 1.5 / 0.9 / 0.75 deg) at 0.2 and 0.5 Hz, scored after the first cycle | 13 / 9.2 s |
| `ssm` | the straight-road correction: +-1 deg at 0.3 Hz at every speed | 10.3 s |
| `st` | step 0 -> A/2 and a 2.5 s hold | 3 s |
| `ov_fade` | hold A/2; driver grabs (hand 2000 T/deg, 30 T/(deg/s)) and pulls the wheel to 0 over 0.3 s, holds 1 s, releases; driver-torque word ramps to 2400 (fade at its 76/256 floor); request held; ramp stays 0x8000 | 6.8 s |
| `ov_latch`, `ov_latch_e6` | the same with the override LATCH: ramp -328/tick to 0 with the request held, +33/tick after release; without / with edit (6) | 6.8 s |
| `sen_L16`, `sen_L328`, `sen_R16`, `sen_R328` | hold +-A/2, then the 0xE4 fault sentinel (gp-0x69ae = 0x7FFF, request 0xFF, act 0, ramp -0xC63F6/tick) with 0xC63F6 = 16 or 328 | 6 s |
| `dis_meas`, `dis_zero` | hold A/2, then request drop (ramp -16/tick); the fork sends the measured angle / sends 0 | 5.5 s |

**Gates (per speed).** `stable`: no divergence, no hunting in the holds (theta p2p >= 0.2 deg with >= 2 reversals), and T rms in
5-30 Hz during the holds <= 2.0 counts (a lane-made LINE). `texture`: T rms 5-30 Hz during the three sinusoids <= 2.0 counts.
`stick`: zero stick-slip events -- the dwell-then-jump detector on the sinusoids (a 0.10 s-smoothed |rate| < 0.25 deg/s for
>= 100 ms while the reference moved >= 0.1 deg, then a snap to the next dwell >= max(2x the reference's change, 0.2 deg)) plus
slips inside the holds (stuck >= 100 ms, then >= 0.1 deg of motion). `deadzone`: hold error <= max(0.3 deg, 3 % of A) and the
+-1 deg correction executed (fit gain >= 0.8). `track` (>= 8 m/s): tracking gain (slope of the 100 Hz wire angle on the received
setpoint) in 0.95-1.05 at 0.2 AND 0.5 Hz. `hold` (>= 8 m/s): min hold ratio over the two turns >= 0.90. `hf20`: the record's
|(P+D)/x| at 20 Hz <= V295's 3.85. **STRICT** = all gates; **LINE-ONLY** = texture reported but not gated.
The goal's "<= V282" terms (dwell-then-jump, 1.6-3 Hz hard-turn energy) cannot be referenced in this sim (V282 is a rate loop
under the fork's torque controller, not simulated); the harness gates stick-slip at ZERO events and reports the 1.6-3 Hz energy
against the reference trajectory's own (BELIEF: zero events in a noise-free sim is a necessary, not a sufficient, condition).

## 4. The sweeps: which gate binds at which speed

The brief's grid (6 Kp x {Ki 0; Ki 256/1024 x ICL 1024/4096/10240 x DB 0/1/4} x Kd {0, 8, 16, 32} = 456) plus a refinement
(159: Kd 20-28 with Kp 1200-2000 at low speed, Kp 1800-3000 with Ki 512-2048 at speed, and a diagnostic output-lag pole of 10 / 20 Hz
-- a STRUCK lever in the record, BUILD-LINEAGE V287 "fires Honda's oscillation detector", run only to see what binds). The
lag-pole variants did **not** rescue 3-8 m/s (hold slips up to 13, hunting 0.2-23 deg) -- the 5 Hz output pole is not the
binding element (EVIDENCE, `refined_sweep.json`). Kd 32 always fails `hf20` (D alone is 4.0 > 3.85).

**STRICT reading** (615 configurations; a cell counts the configurations that pass that gate at that speed)

| speed | stable | texture | stick | deadzone | track | hold | hf20 | **all gates** | best configuration (cost-ranked) |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 144 | 18 | 128 | 380 | 615 | 615 | 463 | **0** | Kp1200 Ki1024 ICL4096 DB1 Kd24 (fails: texture) |
| 5 | 162 | 79 | 259 | 298 | 615 | 615 | 463 | **1** | Kp500 Ki256 ICL10240 DB0 Kd16 |
| 8 | 176 | 172 | 478 | 252 | 214 | 492 | 463 | **12** | Kp500 Ki256 ICL10240 DB0 Kd16 |
| 12.5 | 424 | 259 | 417 | 285 | 160 | 530 | 463 | **5** | Kp1500 Ki1024 ICL4096 DB1 Kd16 |
| 19 | 405 | 266 | 502 | 165 | 61 | 321 | 463 | **10** | Kp1500 Ki1024 ICL4096 DB0 Kd0 |
| 26 | 335 | 185 | 571 | 389 | 40 | 429 | 463 | **0** | Kp2500 Ki1024 ICL1024 DB0 Kd0 (fails: texture) |
| 30 | 352 | 179 | 595 | 410 | 37 | 428 | 463 | **0** | Kp2500 Ki1024 ICL1024 DB0 Kd16 (fails: texture) |

**LINE-ONLY reading** (615 configurations; a cell counts the configurations that pass that gate at that speed)

| speed | stable | texture | stick | deadzone | track | hold | hf20 | **all gates** | best configuration (cost-ranked) |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 144 | 615 | 128 | 380 | 615 | 615 | 463 | **6** | Kp1200 Ki1024 ICL4096 DB1 Kd24 |
| 5 | 162 | 615 | 259 | 298 | 615 | 615 | 463 | **6** | Kp1200 Ki1024 ICL4096 DB1 Kd24 |
| 8 | 176 | 615 | 478 | 252 | 214 | 492 | 463 | **12** | Kp500 Ki256 ICL10240 DB0 Kd16 |
| 12.5 | 424 | 615 | 417 | 285 | 160 | 530 | 463 | **33** | Kp1800 Ki512 ICL4096 DB0 Kd16 |
| 19 | 405 | 615 | 502 | 165 | 61 | 321 | 463 | **21** | Kp1500 Ki1024 ICL4096 DB0 Kd0 |
| 26 | 335 | 615 | 571 | 389 | 40 | 429 | 463 | **14** | Kp2500 Ki1024 ICL1024 DB0 Kd0 |
| 30 | 352 | 615 | 595 | 410 | 37 | 428 | 463 | **12** | Kp2500 Ki1024 ICL1024 DB0 Kd16 |

### 4.1 The Kp landscape for four (Ki, ICL, DB, Kd) settings (line-only reading; the brief's grid)

**Ki 0, ICL 0, DB 0, Kd 0** -- per cell: tracking gain 0.2 Hz / 0.5 Hz · hold ratio · steady error deg · T 5-30 Hz rms in holds / in sinusoids (counts) · stick-slip events (sinusoid dwell-then-jump + hold slips)

| speed | Kp 500 | Kp 900 | Kp 1500 | Kp 2500 | Kp 4000 | Kp 6000 |
|---|---|---|---|---|---|---|
| 3 | 0.85/0.84 · 0.88 · 10.58 · 0.4/0.9 · 0 | 0.92/0.93 · 0.94 · 5.55 · 2.9/2.2 · 0 | UNSTABLE (T hf 34) 0.95/0.97 · 0.96 · 3.19 · 34.2/6.8 · 0 | UNSTABLE (T hf 342) 0.98/0.98 · 0.97 · 2.27 · 341.7/337.5 · 1 | UNSTABLE (T hf 443) 0.95/0.96 · 0.96 · 4.45 · 442.6/421.1 · 3 | UNSTABLE (T hf 473) 0.95/0.96 · 0.94 · 5.71 · 473.0/449.7 · 2 |
| 5 | 0.77/0.76 · 0.81 · 9.63 · 0.3/0.7 · 0 | 0.87/0.88 · 0.89 · 5.34 · 2.0/1.5 · 0 | UNSTABLE (T hf 24) 0.92/0.94 · 0.93 · 3.35 · 23.8/4.1 · 0 | UNSTABLE (T hf 345) 0.96/0.97 · 0.95 · 2.33 · 345.2/64.2 · 0 | UNSTABLE (T hf 449) 0.91/0.92 · 0.91 · 4.81 · 449.2/423.3 · 2 | UNSTABLE (T hf 480) 0.92/0.92 · 0.90 · 4.39 · 479.8/453.1 · 1 |
| 8 | 0.70/0.69 · 0.73 · 8.07 · 0.4/0.5 · 0 | 0.81/0.82 · 0.82 · 5.35 · 1.2/1.0 · 0 | 0.88/0.89 · 0.89 · 3.40 · 16.0/1.9 · 0 | UNSTABLE (T hf 370) 0.93/0.91 · 0.91 · 2.73 · 370.4/276.6 · 0 | UNSTABLE (T hf 469) 0.87/0.88 · 0.88 · 3.42 · 468.7/449.0 · 0 | UNSTABLE (T hf 501) 0.87/0.86 · 0.88 · 3.54 · 500.6/476.0 · 0 |
| 12.5 | 0.56/0.48 · 0.61 · 4.69 · 0.2/0.6 · 0 | 0.72/0.68 · 0.75 · 3.04 · 0.3/1.0 · 0 | 0.81/0.81 · 0.84 · 1.90 · 0.5/1.7 · 0 | 0.89/0.89 · 0.89 · 1.26 · 1.0/3.3 · 0 | 0.93/0.93 · 0.94 · 0.77 · 18.0/6.4 · 0 | UNSTABLE (T hf 540) 0.95/0.96 · 0.95 · 0.55 · 540.3/21.2 · 0 |
| 19 | 0.33/0.26 · 0.39 · 3.05 · 0.2/0.6 · 0 | 0.51/0.43 · 0.54 · 2.32 · 0.3/1.2 · 0 | 0.65/0.61 · 0.67 · 1.65 · 0.4/1.9 · 0 | 0.76/0.74 · 0.77 · 1.15 · 3.3/3.3 · 0 | 0.84/0.84 · 0.85 · 0.77 · 1.1/5.8 · 0 | 0.89/0.89 · 0.89 · 0.55 · 11.8/8.7 · 0 |
| 26 | 0.38/0.23 · 0.45 · 1.65 · 0.2/0.6 · 0 | 0.55/0.44 · 0.60 · 1.21 · 0.2/1.2 · 0 | 0.68/0.62 · 0.72 · 0.85 · 0.1/2.2 · 0 | 0.79/0.76 · 0.82 · 0.55 · 4.0/3.5 · 0 | 0.87/0.86 · 0.88 · 0.36 · 4.3/5.9 · 0 | 0.90/0.91 · 0.91 · 0.26 · 11.2/8.3 · 0 |
| 30 | 0.38/0.20 · 0.46 · 1.35 · 0.2/0.6 · 0 | 0.55/0.43 · 0.62 · 0.96 · 0.3/1.2 · 0 | 0.69/0.62 · 0.72 · 0.69 · 2.5/2.1 · 0 | 0.81/0.77 · 0.82 · 0.45 · 4.8/3.7 · 0 | 0.86/0.85 · 0.88 · 0.30 · 8.7/5.4 · 0 | 0.91/0.91 · 0.90 · 0.24 · 1.7/11.7 · 0 |

**Ki 256, ICL 4096, DB 0, Kd 16 (edit 5)** -- per cell: tracking gain 0.2 Hz / 0.5 Hz · hold ratio · steady error deg · T 5-30 Hz rms in holds / in sinusoids (counts) · stick-slip events (sinusoid dwell-then-jump + hold slips)

| speed | Kp 500 | Kp 900 | Kp 1500 | Kp 2500 | Kp 4000 | Kp 6000 |
|---|---|---|---|---|---|---|
| 3 | 1.06/1.19 · 1.00 · 0.16 · 0.6/2.4 · 7 | 1.04/1.08 · 1.00 · 0.08 · 1.0/3.2 · 8 | 1.02/1.03 · 1.00 · 0.08 · 5.9/5.9 · 9 | UNSTABLE (T hf 113) 1.00/1.01 · 1.00 · 0.08 · 112.5/22.9 · 4 | UNSTABLE (T hf 515) 1.00/1.00 · 0.99 · 1.46 · 515.5/536.1 · 2 | UNSTABLE (T hf 514) 1.00/1.00 · 0.99 · 1.29 · 514.1/541.3 · 1 |
| 5 | 1.05/1.13 · 1.00 · 0.06 · 0.5/1.4 · 2 | 1.02/1.03 · 1.00 · 0.11 · 0.9/1.8 · 5 | 1.00/0.99 · 1.00 · 0.05 · 3.2/3.8 · 5 | UNSTABLE (T hf 111) 0.99/0.99 · 1.00 · 0.07 · 110.7/13.2 · 5 | UNSTABLE (T hf 537) 0.98/0.97 · 0.98 · 0.11 · 536.8/560.1 · 0 | UNSTABLE (T hf 535) 0.97/0.97 · 0.98 · 1.63 · 534.6/553.5 · 4 |
| 8 | 1.01/0.99 · 1.00 · 0.06 · 0.5/0.8 · 0 | 0.99/0.95 · 1.00 · 0.13 · 0.8/1.3 · 1 | 0.97/0.94 · 1.00 · 0.10 · 3.4/2.4 · 8 | UNSTABLE (T hf 93) 0.96/0.96 · 0.99 · 0.19 · 93.3/5.8 · 8 | UNSTABLE (T hf 569) 0.93/0.93 · 0.97 · 0.35 · 569.0/593.8 · 0 | UNSTABLE (T hf 573) 0.94/0.91 · 0.97 · 1.39 · 572.7/593.3 · 0 |
| 12.5 | 1.02/0.80 · 0.99 · 0.07 · 0.4/0.5 · 4 | 0.98/0.84 · 1.00 · 0.08 · 0.5/1.1 · 0 | 0.95/0.89 · 0.99 · 0.13 · 0.9/1.8 · 4 | 0.94/0.92 · 0.99 · 0.13 · 1.7/2.9 · 6 | 0.95/0.95 · 0.98 · 0.22 · 4.8/6.4 · 5 | UNSTABLE (T hf 119) 0.96/0.96 · 0.98 · 0.23 · 119.0/14.3 · 0 |
| 19 | 0.83/0.27 · 1.00 · 0.11 · 0.4/0.7 · 0 | 0.81/0.49 · 0.97 · 0.13 · 0.6/1.2 · 0 | 0.80/0.66 · 0.97 · 0.14 · 1.0/1.9 · 3 | 0.84/0.77 · 0.95 · 0.16 · 1.6/3.1 · 2 | 0.87/0.85 · 0.94 · 0.24 · 4.9/6.0 · 4 | 0.90/0.90 · 0.94 · 0.24 · 9.7/8.4 · 0 |
| 26 | 0.95/0.20 · 0.99 · 0.05 · 0.3/0.8 · 3 | 0.89/0.48 · 0.98 · 0.05 · 0.5/1.2 · 0 | 0.85/0.68 · 0.95 · 0.14 · 0.6/2.0 · 0 | 0.89/0.80 · 0.95 · 0.15 · 2.5/3.7 · 1 | 0.91/0.88 · 0.95 · 0.14 · 6.0/6.0 · 0 | 0.92/0.92 · 0.95 · 0.14 · 10.3/10.0 · 0 |
| 30 | 0.96/0.17 · 0.99 · 0.05 · 0.4/0.7 · 3 | 0.87/0.47 · 0.98 · 0.06 · 0.5/1.4 · 0 | 0.87/0.66 · 0.95 · 0.14 · 0.5/2.6 · 0 | 0.90/0.81 · 0.94 · 0.15 · 2.0/3.4 · 1 | 0.90/0.89 · 0.94 · 0.15 · 6.5/6.7 · 0 | 0.92/0.92 · 0.94 · 0.14 · 9.7/8.6 · 0 |

**Ki 1024, ICL 4096, DB 0, Kd 0** -- per cell: tracking gain 0.2 Hz / 0.5 Hz · hold ratio · steady error deg · T 5-30 Hz rms in holds / in sinusoids (counts) · stick-slip events (sinusoid dwell-then-jump + hold slips)

| speed | Kp 500 | Kp 900 | Kp 1500 | Kp 2500 | Kp 4000 | Kp 6000 |
|---|---|---|---|---|---|---|
| 3 | UNSTABLE (T hf 21) 0.96/1.05 · 1.00 · 0.50 · 21.4/21.1 · 11 | UNSTABLE (T hf 30) 1.01/1.06 · 1.00 · 0.42 · 29.5/7.2 · 15 | UNSTABLE (T hf 152) 1.01/1.05 · 1.00 · 0.03 · 151.6/39.7 · 15 | UNSTABLE (T hf 313) 0.96/0.98 · 0.96 · 1.87 · 312.6/289.0 · 7 | UNSTABLE (T hf 378) 0.95/0.99 · 0.95 · 3.96 · 378.1/344.8 · 7 | UNSTABLE (T hf 404) 0.96/0.98 · 0.95 · 6.09 · 403.7/373.3 · 5 |
| 5 | UNSTABLE (T hf 16) 0.93/1.01 · 1.00 · 0.34 · 15.9/17.4 · 5 | UNSTABLE (T hf 21) 1.01/1.06 · 1.00 · 0.15 · 21.0/3.5 · 11 | UNSTABLE (T hf 151) 1.01/1.05 · 1.00 · 0.11 · 150.9/8.9 · 11 | UNSTABLE (T hf 313) 0.96/0.94 · 0.93 · 2.00 · 313.5/281.6 · 1 | UNSTABLE (T hf 382) 0.93/0.96 · 0.92 · 3.45 · 382.2/338.5 · 1 | UNSTABLE (T hf 411) 0.92/0.95 · 0.91 · 5.27 · 411.3/364.1 · 0 |
| 8 | UNSTABLE (T hf 9) 1.01/1.06 · 1.00 · 0.05 · 9.2/2.3 · 3 | UNSTABLE (T hf 12) 1.01/1.05 · 1.00 · 0.04 · 12.4/1.3 · 2 | UNSTABLE (T hf 124) 1.00/1.03 · 1.00 · 0.11 · 123.9/3.5 · 0 | UNSTABLE (T hf 319) 0.95/0.96 · 0.91 · 3.91 · 319.4/294.3 · 0 | UNSTABLE (T hf 395) 0.91/0.92 · 0.90 · 1.92 · 394.6/355.2 · 0 | UNSTABLE (T hf 420) 0.92/0.93 · 0.89 · 2.34 · 420.2/381.4 · 0 |
| 12.5 | UNSTABLE (T hf 1) 1.02/1.14 · 1.00 · 0.02 · 0.6/0.6 · 6 | 1.02/1.11 · 1.00 · 0.11 · 0.7/1.0 · 4 | 1.01/1.07 · 1.00 · 0.07 · 0.6/1.8 · 0 | 1.00/1.02 · 1.00 · 0.06 · 1.6/3.6 · 0 | UNSTABLE (T hf 30) 1.00/1.00 · 0.99 · 0.07 · 30.2/7.9 · 0 | UNSTABLE (T hf 670) 0.99/0.99 · 0.99 · 0.12 · 670.2/31.6 · 0 |
| 19 | 1.02/1.17 · 1.01 · 0.14 · 0.4/0.6 · 0 | 1.01/1.07 · 0.98 · 0.11 · 0.5/1.0 · 0 | 1.00/1.02 · 0.99 · 0.05 · 0.8/1.8 · 0 | 0.99/0.95 · 0.99 · 0.05 · 3.4/3.1 · 0 | 0.98/0.94 · 0.97 · 0.13 · 1.5/4.8 · 0 | 0.96/0.94 · 0.97 · 0.13 · 4.7/8.5 · 0 |
| 26 | 1.02/1.30 · 1.01 · 0.05 · 0.6/0.7 · 0 | 1.01/1.20 · 0.97 · 0.09 · 0.7/1.3 · 0 | 1.01/1.10 · 0.98 · 0.06 · 0.8/2.3 · 0 | 0.98/1.00 · 1.00 · 0.14 · 0.3/4.1 · 0 | 0.96/0.99 · 0.98 · 0.05 · 8.7/5.8 · 0 | 0.95/0.97 · 0.98 · 0.06 · 14.0/8.8 · 0 |
| 30 | 1.04/1.32 · 1.01 · 0.03 · 0.5/0.8 · 0 | 1.03/1.23 · 0.95 · 0.13 · 0.7/1.3 · 0 | 1.02/1.10 · 0.98 · 0.06 · 0.9/2.2 · 0 | 0.98/1.01 · 1.01 · 0.13 · 0.2/4.6 · 0 | 0.95/1.00 · 0.98 · 0.05 · 8.5/5.9 · 0 | 0.95/0.97 · 0.98 · 0.06 · 13.2/10.0 · 0 |

**Ki 1024, ICL 4096, DB 0, Kd 16 (edit 5)** -- per cell: tracking gain 0.2 Hz / 0.5 Hz · hold ratio · steady error deg · T 5-30 Hz rms in holds / in sinusoids (counts) · stick-slip events (sinusoid dwell-then-jump + hold slips)

| speed | Kp 500 | Kp 900 | Kp 1500 | Kp 2500 | Kp 4000 | Kp 6000 |
|---|---|---|---|---|---|---|
| 3 | 1.02/1.10 · 1.00 · 0.47 · 2.6/2.7 · 11 | 1.02/1.09 · 1.00 · 0.29 · 2.2/3.4 · 13 | 1.02/1.08 · 1.00 · 0.07 · 11.7/6.1 · 1 | UNSTABLE (T hf 233) 1.01/1.05 · 1.00 · 0.13 · 233.3/29.6 · 3 | UNSTABLE (T hf 467) 1.00/1.02 · 0.98 · 1.38 · 466.8/481.9 · 0 | UNSTABLE (T hf 486) 1.01/1.01 · 0.98 · 2.17 · 485.7/491.3 · 2 |
| 5 | 1.02/1.11 · 1.00 · 0.20 · 1.9/1.4 · 17 | 1.02/1.10 · 1.00 · 0.17 · 1.5/1.9 · 10 | 1.02/1.07 · 1.00 · 0.07 · 7.0/4.3 · 1 | UNSTABLE (T hf 215) 1.01/1.04 · 1.00 · 0.09 · 214.6/15.7 · 0 | UNSTABLE (T hf 492) 1.01/1.03 · 0.96 · 2.22 · 492.5/495.1 · 1 | UNSTABLE (T hf 503) 1.00/1.02 · 0.95 · 2.33 · 503.1/501.3 · 0 |
| 8 | UNSTABLE (T hf 1) 1.02/1.10 · 1.00 · 0.08 · 0.9/0.7 · 7 | 1.01/1.08 · 1.00 · 0.11 · 1.0/1.2 · 1 | 1.01/1.05 · 1.00 · 0.13 · 5.7/2.3 · 0 | UNSTABLE (T hf 199) 1.00/1.02 · 1.00 · 0.14 · 198.6/7.5 · 0 | UNSTABLE (T hf 516) 1.00/1.02 · 0.94 · 2.21 · 515.5/533.5 · 0 | UNSTABLE (T hf 529) 0.99/1.03 · 0.93 · 2.40 · 528.9/539.8 · 0 |
| 12.5 | 1.03/1.18 · 0.99 · 0.13 · 0.7/0.7 · 6 | 1.02/1.14 · 1.00 · 0.10 · 0.7/1.1 · 4 | 1.02/1.09 · 1.00 · 0.05 · 0.8/1.8 · 0 | 1.01/1.03 · 1.00 · 0.10 · 0.9/3.3 · 0 | 1.00/1.00 · 1.00 · 0.05 · 7.8/6.3 · 0 | UNSTABLE (T hf 167) 0.99/0.99 · 0.99 · 0.10 · 167.2/19.6 · 0 |
| 19 | 1.03/1.18 · 1.00 · 0.08 · 0.6/0.6 · 1 | 1.01/1.10 · 0.97 · 0.14 · 0.7/1.0 · 0 | 1.01/1.02 · 0.99 · 0.06 · 0.9/1.8 · 0 | 0.99/0.95 · 0.99 · 0.08 · 0.4/2.9 · 0 | 0.98/0.94 · 0.97 · 0.13 · 0.7/5.3 · 0 | 0.97/0.94 · 0.97 · 0.13 · 4.0/8.4 · 0 |
| 26 | 1.02/1.33 · 0.99 · 0.05 · 0.6/0.8 · 0 | 1.01/1.22 · 0.98 · 0.06 · 0.7/1.3 · 0 | 1.01/1.11 · 0.98 · 0.06 · 0.8/2.3 · 0 | 0.99/1.01 · 1.01 · 0.14 · 0.4/4.3 · 0 | 0.97/0.98 · 0.98 · 0.04 · 7.3/6.1 · 0 | 0.95/0.98 · 0.98 · 0.06 · 14.1/8.6 · 0 |
| 30 | 1.05/1.36 · 1.00 · 0.05 · 0.6/0.8 · 0 | 1.03/1.25 · 0.96 · 0.11 · 0.8/1.4 · 0 | 1.02/1.12 · 0.97 · 0.06 · 0.9/2.2 · 0 | 0.99/1.01 · 1.01 · 0.13 · 0.4/4.7 · 0 | 0.96/1.00 · 1.00 · 0.10 · 5.5/6.8 · 0 | 0.94/0.97 · 0.98 · 0.05 · 14.0/8.4 · 0 |

Reading the landscape (EVIDENCE, sim): **without D, Kp >= 1500 is a ~4 Hz limit cycle at 3-8 m/s** (3.9 Hz measured on FLAT-T) (T 5-30 Hz 16-500 counts rms);
**Kp <= 900 is stable there but leaves a 5-10 deg hold error (P-only) or stick-slips (with I)**; at 19-30 m/s the P-only hold ratio
is 0.39-0.91 and only Ki ~1024 with Kp ~2500 tracks within +-5 %; **at Kp >= 4000 the highway holds limit-cycle on the angle LSB**
(1 LSB, 17-21 reversals per 1.5 s, T 5-30 Hz 6-14 counts). The binding pair is low-speed stability/stick-slip against highway
tracking, which no single (flat) gain satisfies.

## 5. The candidates, one scorecard per schedule type

Seven candidates were built from the sweeps and run through every scenario at every speed (`final.json`):
FLAT-T / FLAT-S are the best flat sets under the line-only / strict readings; FLAT-L is the 3 m/s winner flown flat;
ANGLE-1/2/3 are cal-only |theta_sp| schedules (knots at idx 0/3/7/18/31 = 0/5/12/30/50 deg) with the low-angle knot at the
highway (2500) or the low-speed (1500) value and Kd 24 or 28; SPEED-1/2 key Kp and Kd on gp-0x6a5e >> 8 (4 km/h per count;
3/5/8/12.5/19/26/30 m/s = keys 2/4/7/11/17/23/27), Ki 1024 / 640.

### 5.1 STRICT reading (texture gated)

| candidate | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s | speeds passing |
|---|---|---|---|---|---|---|---|---|
| FLAT-T  Kp2500 Ki1024 ICL4096 DB0 Kd16 (best flat, line-only reading) | fail: stable, texture, stick | fail: stable, texture, stick | fail: stable, texture | fail: texture | fail: texture | fail: texture | fail: texture | **0 / 7** |
| FLAT-S  Kp500 Ki256 ICL10240 DB0 Kd16 (best flat, strict reading) | fail: texture, stick | PASS | PASS | fail: stick, track | fail: track | fail: stick, track | fail: stick, track | **2 / 7** |
| FLAT-L  Kp1200 Ki1024 ICL4096 DB1 Kd24 (the 3 m/s winner, flown flat) | fail: texture | fail: texture | fail: track | fail: track | fail: track | fail: track | fail: track | **0 / 7** |
| ANGLE-1 Kp(|th_sp|) 2500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24 | fail: texture, stick | fail: texture, stick | fail: stable, texture | fail: texture, track | fail: texture | fail: texture | fail: texture | **0 / 7** |
| ANGLE-2 Kp(|th_sp|) 1500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24 | fail: texture, stick | fail: texture, stick | fail: stable, texture, track | fail: texture, track | PASS | fail: texture, track | fail: texture, track | **1 / 7** |
| ANGLE-3 = ANGLE-1 with Kd28 | fail: texture, stick | fail: texture, stick | fail: stable, texture, track | fail: texture, track | fail: texture | fail: stable, texture | fail: texture | **0 / 7** |
| SPEED-1 Kp(v) 1500/1200/1800/1500/2500 @ 3/5/12.5/19/26 m/s, Kd(v) 28/24/24/0 @ 3/5/8/12.5 | fail: texture | fail: texture | fail: texture, track | fail: texture | PASS | fail: texture | fail: texture | **1 / 7** |
| SPEED-2 = SPEED-1 with Ki 640 | fail: texture, stick | fail: texture, stick | fail: stick | fail: texture | fail: track | fail: stable, texture, track | fail: stable, texture, track | **0 / 7** |

### 5.2 LINE-ONLY reading (texture reported, not gated)

| candidate | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s | speeds passing |
|---|---|---|---|---|---|---|---|---|
| FLAT-T  Kp2500 Ki1024 ICL4096 DB0 Kd16 (best flat, line-only reading) | fail: stable, stick | fail: stable, stick | fail: stable | PASS | PASS | PASS | PASS | **4 / 7** |
| FLAT-S  Kp500 Ki256 ICL10240 DB0 Kd16 (best flat, strict reading) | fail: stick | PASS | PASS | fail: stick, track | fail: track | fail: stick, track | fail: stick, track | **2 / 7** |
| FLAT-L  Kp1200 Ki1024 ICL4096 DB1 Kd24 (the 3 m/s winner, flown flat) | PASS | PASS | fail: track | fail: track | fail: track | fail: track | fail: track | **2 / 7** |
| ANGLE-1 Kp(|th_sp|) 2500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24 | fail: stick | fail: stick | fail: stable | fail: track | PASS | PASS | PASS | **3 / 7** |
| ANGLE-2 Kp(|th_sp|) 1500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24 | fail: stick | fail: stick | fail: stable, track | fail: track | PASS | fail: track | fail: track | **1 / 7** |
| ANGLE-3 = ANGLE-1 with Kd28 | fail: stick | fail: stick | fail: stable, track | fail: track | PASS | fail: stable | PASS | **2 / 7** |
| SPEED-1 Kp(v) 1500/1200/1800/1500/2500 @ 3/5/12.5/19/26 m/s, Kd(v) 28/24/24/0 @ 3/5/8/12.5 | PASS | PASS | fail: track | PASS | PASS | PASS | PASS | **6 / 7** |
| SPEED-2 = SPEED-1 with Ki 640 | fail: stick | fail: stick | fail: stick | PASS | fail: track | fail: stable, track | fail: stable, track | **1 / 7** |

**The best cal set per schedule type** (the cells as they would be written; record addresses read LE from the V295 image:
Kp = `0xCB994[7]` -> record `0xE5378` (count 5, X at `0xE537A`, Y at `0xE5384`; V295: X 0/68/112/136/208, Y 960 flat), Kd =
`0xCB7D4[7]` -> record `0xE511C` (count 4, X at `0xE511E`, Y at `0xE5126`; V295 Y 0). Common to all: a `0xC63E8` 0, b `0xC63EA`
8192, C `0xC62E6` 65535, edits (1)-(4) (+ (5) for Kd > 0), DCL `0xC61B6` 10240 when Kd > 0, and **`0xC63F6` 16 -> 328** for the
sentinel (section 6):

| schedule type | Kp record X / Y | Kd record X / Y | Ki `0xC63E6` | ICL `0xC61BA` | DB `0xC62E4` | nominal speeds passing (line-only / strict) |
|---|---|---|---|---|---|---|
| FLAT (line-only best) | any / 2500 flat | any / 16 flat | 1024 | 4096 | 0 | 4 / 0 -- 3.9 Hz limit cycle at 3-8 m/s |
| FLAT (strict best) | any / 500 flat | any / 16 flat | 256 | 10240 | 0 | 2 / 2 -- under-tracks at >= 12.5 m/s (0.5 Hz gain 0.17-0.80) |
| ANGLE-INDEXED (ANGLE-1) | idx 0/3/7/18/31 / 2500/1500/1800/1200/1200 | any / 24 flat | 1024 | 4096 | 0 | 3 / 0 |
| SPEED (SPEED-1; key = gp-0x6a5e >> 8) | 2/4/11/17/23 / 1500/1200/1800/1500/2500 | 2/4/7/11 / 28/24/24/0 | 1024 | 4096 | 0 | 6 / 1 |
| FULL per-speed cave (any gain per speed) | -- | -- | per speed | per speed | per speed | 7 / 4 (the per-speed bests in section 4) |

**What the two scorecards say.** No flat and no angle-indexed set passes more than 4/7 (line-only) or 2/7 (strict).
SPEED-1 is the only candidate that passes every speed band but one under the line-only reading. Lowering Ki to 640 (SPEED-2) to
remove the 8 m/s peaking breaks 3-8 m/s (stick-slip) and 19-30 m/s (tracking 0.86-0.91): **Ki is the one gain the speed
schedule cannot reach in place, and it is the one 8 m/s needs**.

### 5.3 Per-speed detail of every candidate

Columns: `ess` hold error at the end of the turns (deg); `hold` min hold ratio; `tg` tracking gain at 0.2 / 0.5 Hz; `ph 0.5` the
fitted phase of the wheel at 0.5 Hz (deg, negative = lag); `+-1deg fit` fitted gain on the +-1 deg correction; `dj ev` stick-slip
events (all detectors); `max snap` largest dwell-then-jump snap (deg); `stick %` frames stuck while the +-1 deg reference moves;
`T hf hold / sin` T rms 5-30 Hz in the holds / sinusoids (counts); `hunt p2p` angle p2p in the last 1.5 s of the holds; `step ov %`
and `settle s` of the A/2 step (band max(5 %, 0.2 deg)); `peak T`, `rail %` of `rh`; `hard16` 1.6-3 Hz wheel-rate rms over `rh`
(deg/s) and the reference's own (`hard16 ref`).

**FLAT-T  Kp2500 Ki1024 ICL4096 DB0 Kd16 (best flat, line-only reading)**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.13 | 0.999 | 1.014 | 1.049 | -2.3 | 1.10 | 3 | 0.40 | 49 | 237.1 | 31.4 | 13.94 | 28 | 2.04 | 930 | 0.0 | 3.00 | 1.80 |
| 5 | 0.01 | 1.000 | 1.013 | 1.041 | -3.1 | 1.04 | 2 | 0.00 | 45 | 215.8 | 14.9 | 12.53 | 48 | 2.20 | 854 | 0.0 | 2.71 | 1.69 |
| 8 | 0.14 | 1.001 | 1.004 | 1.018 | -4.0 | 0.99 | 0 | 0.00 | 23 | 198.9 | 6.7 | 9.81 | 69 | inf | 818 | 0.0 | 3.18 | 2.26 |
| 12.5 | 0.11 | 1.001 | 1.009 | 1.033 | -7.9 | 0.98 | 0 | 0.00 | 6 | 0.9 | 3.4 | 0.00 | 32 | 0.32 | 491 | 0.0 | 1.17 | 0.91 |
| 19 | 0.08 | 0.993 | 0.995 | 0.952 | -17.5 | 0.98 | 0 | 0.00 | 1 | 0.4 | 2.9 | 0.00 | 1 | 0.17 | 463 | 0.0 | 0.32 | 0.38 |
| 26 | 0.14 | 1.013 | 0.988 | 1.013 | -18.2 | 1.00 | 0 | 0.00 | 5 | 0.4 | 4.3 | 0.00 | 6 | 0.16 | 246 | 0.0 | 0.18 | 0.23 |
| 30 | 0.13 | 1.016 | 0.990 | 1.008 | -19.9 | 1.00 | 0 | 0.00 | 5 | 0.3 | 4.6 | 0.00 | 11 | 0.15 | 209 | 0.0 | 0.16 | 0.19 |

**FLAT-S  Kp500 Ki256 ICL10240 DB0 Kd16 (best flat, strict reading)**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.19 | 0.998 | 1.061 | 1.214 | -16.1 | 1.39 | 5 | 2.13 | 59 | 0.6 | 2.0 | 2.84 | 27 | 0.77 | 775 | 0.0 | 1.81 | 1.80 |
| 5 | 0.08 | 0.998 | 1.049 | 1.128 | -20.1 | 1.27 | 0 | 0.00 | 43 | 0.5 | 1.2 | 1.74 | 18 | 0.81 | 728 | 0.0 | 1.51 | 1.69 |
| 8 | 0.06 | 0.998 | 1.012 | 0.993 | -23.4 | 1.07 | 0 | 0.00 | 19 | 0.5 | 0.8 | 0.86 | 8 | 0.72 | 697 | 0.0 | 1.61 | 2.26 |
| 12.5 | 0.07 | 0.995 | 1.020 | 0.802 | -42.8 | 1.12 | 4 | 0.00 | 15 | 0.4 | 0.6 | 0.61 | 8 | 1.20 | 463 | 0.0 | 0.35 | 0.91 |
| 19 | 0.11 | 0.999 | 0.834 | 0.273 | -67.9 | 0.90 | 0 | 0.00 | 9 | 0.3 | 0.7 | 0.33 | -2 | 0.89 | 390 | 0.0 | 0.07 | 0.38 |
| 26 | 0.05 | 0.989 | 0.952 | 0.197 | -77.0 | 1.03 | 3 | 0.00 | 5 | 0.4 | 0.8 | 0.15 | 4 | 0.66 | 217 | 0.0 | 0.04 | 0.23 |
| 30 | 0.05 | 0.986 | 0.963 | 0.166 | -79.2 | 1.04 | 2 | 0.00 | 5 | 0.5 | 0.7 | 0.13 | 9 | 0.59 | 182 | 0.0 | 0.04 | 0.19 |

**FLAT-L  Kp1200 Ki1024 ICL4096 DB1 Kd24 (the 3 m/s winner, flown flat)**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.18 | 1.001 | 1.025 | 1.086 | -3.7 | 1.02 | 0 | 0.00 | 40 | 1.2 | 5.5 | 0.00 | 14 | 0.32 | 759 | 0.0 | 2.86 | 1.80 |
| 5 | 0.19 | 1.002 | 1.021 | 1.100 | -4.4 | 0.93 | 0 | 0.00 | 37 | 1.0 | 2.9 | 0.00 | 26 | 0.42 | 717 | 0.0 | 2.47 | 1.69 |
| 8 | 0.25 | 1.005 | 1.004 | 1.070 | -6.7 | 0.84 | 0 | 0.00 | 14 | 1.2 | 1.4 | 0.00 | 34 | 0.36 | 695 | 0.0 | 3.16 | 2.26 |
| 12.5 | 0.21 | 1.009 | 0.992 | 1.097 | -13.4 | 0.86 | 0 | 0.00 | 14 | 0.6 | 1.4 | 0.12 | 26 | 0.57 | 486 | 0.0 | 0.78 | 0.91 |
| 19 | 0.24 | 1.030 | 0.886 | 0.905 | -31.8 | 0.88 | 0 | 0.00 | 5 | 0.6 | 1.5 | 0.03 | 11 | 0.89 | 446 | 0.0 | 0.20 | 0.38 |
| 26 | 0.16 | 1.045 | 0.770 | 0.893 | -36.9 | 0.94 | 0 | 0.00 | 1 | 0.5 | 1.7 | 0.03 | 17 | 1.50 | 236 | 0.0 | 0.10 | 0.23 |
| 30 | 0.22 | 1.026 | 0.723 | 0.864 | -39.4 | 0.95 | 0 | 0.00 | 3 | 0.8 | 1.8 | 0.01 | 24 | inf | 200 | 0.0 | 0.08 | 0.19 |

**ANGLE-1 Kp(|th_sp|) 2500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.11 | 0.999 | 1.020 | 1.079 | -2.6 | 1.07 | 1 | 0.00 | 42 | 1.5 | 18.2 | 0.50 | 14 | 0.32 | 759 | 0.0 | 2.67 | 1.80 |
| 5 | 0.11 | 0.998 | 1.017 | 1.071 | -3.8 | 1.06 | 2 | 0.00 | 27 | 1.2 | 13.5 | 0.28 | 29 | 0.40 | 718 | 0.0 | 2.37 | 1.69 |
| 8 | 0.06 | 0.998 | 1.010 | 1.048 | -4.9 | 0.99 | 0 | 0.00 | 11 | 4.8 | 4.2 | 0.11 | 48 | 0.46 | 695 | 0.0 | 3.17 | 2.26 |
| 12.5 | 0.10 | 0.996 | 1.015 | 1.058 | -8.7 | 0.99 | 0 | 0.00 | 7 | 0.9 | 4.1 | 0.11 | 23 | 0.48 | 491 | 0.0 | 1.05 | 0.91 |
| 19 | 0.05 | 0.990 | 0.999 | 0.966 | -18.6 | 0.98 | 0 | 0.00 | 3 | 0.6 | 2.6 | 0.00 | 3 | 0.20 | 469 | 0.0 | 0.28 | 0.38 |
| 26 | 0.05 | 1.012 | 0.992 | 1.036 | -18.8 | 1.00 | 0 | 0.00 | 5 | 2.0 | 4.1 | 0.01 | 6 | 0.17 | 248 | 0.0 | 0.18 | 0.23 |
| 30 | 0.05 | 1.014 | 0.998 | 1.032 | -20.1 | 1.01 | 0 | 0.00 | 4 | 1.8 | 4.1 | 0.00 | 11 | 0.15 | 208 | 0.0 | 0.15 | 0.19 |

**ANGLE-2 Kp(|th_sp|) 1500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.11 | 0.999 | 1.020 | 1.079 | -2.9 | 1.14 | 2 | 0.00 | 24 | 1.5 | 6.6 | 0.29 | 14 | 0.32 | 762 | 0.0 | 2.81 | 1.80 |
| 5 | 0.09 | 0.998 | 1.018 | 1.077 | -4.0 | 1.05 | 1 | 0.00 | 23 | 1.2 | 4.5 | 0.27 | 29 | 0.40 | 718 | 0.0 | 2.49 | 1.69 |
| 8 | 0.07 | 0.998 | 1.012 | 1.057 | -5.2 | 0.98 | 0 | 0.00 | 5 | 4.8 | 2.4 | 0.12 | 48 | 0.46 | 695 | 0.0 | 3.26 | 2.26 |
| 12.5 | 0.06 | 1.001 | 1.021 | 1.097 | -9.7 | 1.00 | 0 | 0.00 | 5 | 0.7 | 2.1 | 0.07 | 23 | 0.48 | 490 | 0.0 | 0.97 | 0.91 |
| 19 | 0.05 | 0.989 | 1.009 | 1.016 | -22.9 | 1.01 | 0 | 0.00 | 5 | 1.1 | 1.8 | 0.16 | 10 | 0.61 | 467 | 0.0 | 0.25 | 0.38 |
| 26 | 0.06 | 0.981 | 1.009 | 1.106 | -22.2 | 1.06 | 0 | 0.00 | 1 | 0.9 | 2.2 | 0.15 | 16 | 0.69 | 247 | 0.0 | 0.13 | 0.23 |
| 30 | 0.06 | 0.976 | 1.024 | 1.125 | -20.7 | 1.06 | 0 | 0.00 | 1 | 0.9 | 2.3 | 0.14 | 21 | 0.70 | 211 | 0.0 | 0.11 | 0.19 |

**ANGLE-3 = ANGLE-1 with Kd28**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.15 | 0.999 | 1.021 | 1.078 | -3.2 | 1.04 | 3 | 0.00 | 35 | 1.6 | 21.2 | 0.23 | 10 | 0.33 | 761 | 0.0 | 2.73 | 1.80 |
| 5 | 0.08 | 0.998 | 1.019 | 1.077 | -4.0 | 1.04 | 1 | 0.00 | 18 | 1.1 | 13.3 | 0.24 | 24 | 0.26 | 717 | 0.0 | 2.23 | 1.69 |
| 8 | 0.06 | 0.998 | 1.011 | 1.053 | -5.2 | 0.99 | 0 | 0.00 | 6 | 2.9 | 4.3 | 0.06 | 42 | 0.43 | 692 | 0.0 | 2.98 | 2.26 |
| 12.5 | 0.05 | 0.996 | 1.017 | 1.062 | -8.9 | 0.99 | 0 | 0.00 | 5 | 1.0 | 4.0 | 0.10 | 21 | 0.50 | 491 | 0.0 | 1.01 | 0.91 |
| 19 | 0.05 | 0.989 | 0.999 | 0.968 | -18.9 | 0.99 | 0 | 0.00 | 4 | 0.7 | 2.7 | 0.00 | 3 | 0.20 | 462 | 0.0 | 0.28 | 0.38 |
| 26 | 0.05 | 1.011 | 0.994 | 1.038 | -19.2 | 1.01 | 0 | 0.00 | 5 | 2.1 | 4.1 | 0.01 | 6 | 0.17 | 250 | 0.0 | 0.16 | 0.23 |
| 30 | 0.05 | 1.016 | 1.001 | 1.037 | -20.1 | 1.01 | 0 | 0.00 | 2 | 1.5 | 4.2 | 0.00 | 10 | 0.16 | 209 | 0.0 | 0.14 | 0.19 |

**SPEED-1 Kp(v) 1500/1200/1800/1500/2500 @ 3/5/12.5/19/26 m/s, Kd(v) 28/24/24/0 @ 3/5/8/12.5**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.07 | 1.000 | 1.021 | 1.075 | -3.7 | 1.13 | 0 | 0.00 | 25 | 1.5 | 7.0 | 0.23 | 13 | 0.31 | 762 | 0.0 | 2.59 | 1.80 |
| 5 | 0.08 | 0.998 | 1.020 | 1.097 | -3.6 | 1.08 | 0 | 0.00 | 20 | 1.0 | 3.3 | 0.00 | 26 | 0.43 | 718 | 0.0 | 2.52 | 1.69 |
| 8 | 0.09 | 0.999 | 1.012 | 1.061 | -5.1 | 0.99 | 0 | 0.00 | 5 | 1.4 | 2.2 | 0.04 | 42 | 0.36 | 702 | 0.0 | 3.23 | 2.26 |
| 12.5 | 0.10 | 1.000 | 1.010 | 1.049 | -7.7 | 0.98 | 0 | 0.00 | 5 | 0.7 | 2.0 | 0.00 | 39 | 0.44 | 492 | 0.0 | 1.36 | 0.91 |
| 19 | 0.05 | 0.989 | 1.002 | 1.016 | -20.1 | 1.00 | 0 | 0.00 | 5 | 0.8 | 1.8 | 0.06 | 8 | 0.46 | 465 | 0.0 | 0.26 | 0.38 |
| 26 | 0.14 | 1.003 | 0.983 | 1.003 | -17.1 | 0.99 | 0 | 0.00 | 1 | 0.3 | 4.1 | 0.01 | 7 | 0.15 | 247 | 0.0 | 0.21 | 0.23 |
| 30 | 0.13 | 1.013 | 0.981 | 1.008 | -18.3 | 0.99 | 0 | 0.00 | 2 | 0.2 | 4.6 | 0.01 | 12 | 0.14 | 209 | 0.0 | 0.18 | 0.19 |

**SPEED-2 = SPEED-1 with Ki 640**

| m/s | ess | hold | tg 0.2 | tg 0.5 | ph 0.5 deg | +-1deg fit | dj ev | max snap | stick % | T hf hold | T hf sin | hunt p2p | step ov % | settle s | peak T | rail % | hard16 | hard16 ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.02 | 1.000 | 1.028 | 1.090 | -6.1 | 1.13 | 1 | 0.00 | 32 | 1.6 | 6.6 | 0.56 | 13 | 0.32 | 762 | 0.0 | 2.23 | 1.80 |
| 5 | 0.13 | 0.999 | 1.026 | 1.100 | -7.3 | 1.11 | 1 | 0.00 | 23 | 1.1 | 3.1 | 0.25 | 26 | 0.29 | 717 | 0.0 | 2.08 | 1.69 |
| 8 | 0.12 | 1.001 | 1.010 | 1.037 | -8.5 | 0.99 | 1 | 0.00 | 5 | 1.5 | 1.9 | 0.12 | 35 | 0.32 | 708 | 0.0 | 2.88 | 2.26 |
| 12.5 | 0.12 | 1.002 | 1.000 | 1.003 | -10.9 | 0.99 | 0 | 0.00 | 5 | 0.7 | 2.4 | 0.00 | 27 | 0.42 | 488 | 0.0 | 1.17 | 0.91 |
| 19 | 0.06 | 0.991 | 0.965 | 0.857 | -27.4 | 0.96 | 0 | 0.00 | 5 | 0.4 | 1.9 | 0.01 | -2 | 0.29 | 445 | 0.0 | 0.24 | 0.38 |
| 26 | 0.05 | 0.983 | 0.971 | 0.914 | -20.1 | 0.97 | 0 | 0.00 | 4 | 5.3 | 4.4 | 0.01 | -1 | 0.17 | 242 | 0.0 | 0.19 | 0.23 |
| 30 | 0.05 | 0.979 | 0.970 | 0.903 | -20.5 | 0.97 | 0 | 0.00 | 1 | 4.7 | 5.1 | 0.01 | 4 | 0.15 | 201 | 0.0 | 0.15 | 0.19 |

## 6. Override, fault sentinel and disengage

EVIDENCE (sim, lane level). Columns per speed: the release lurch of a 1 s override with the fade at its floor (the reachable
case on this car: STEER_STATUS was measured identically 0 engaged, kit memory `accord-the-authority-ramp-five-rates`); the
override LATCH variant without / with edit (6); the 0xE4 fault sentinel with 0xC63F6 = 16 and 328 while holding a LEFT turn
(the lane pushing the sentinel's way) and a RIGHT turn; the disengage excursion (the wheel relaxing toward centre as the lane
fades -- a "send 0" fork is neutralised by the sign-hold gate, the two columns differ by <= 5 deg at 3 m/s and <= 0.1 deg at speed).

| candidate | m/s | override (fade-only) peak T / overshoot deg / swing deg | override latch: overshoot no-e6 / e6 deg | sentinel L, 0xC63F6=16: peak T / s / excursion deg | sentinel L, =328 | sentinel R, =16: peak T / excursion | disengage excursion: send measured / send 0 |
|---|---|---|---|---|---|---|---|
| FLAT-T | 3 | 2299 / 12.39 / 56.94 | 5.27 / 5.28 | 2254 / 2.01 / 179.2 | 1149 / 0.10 / 6.5 | 262 / 33.0 | 27.25 / 32.54 |
| FLAT-T | 5 | 2304 / 11.95 / 36.54 | 2.76 / 2.78 | 2255 / 2.01 / 143.1 | 1133 / 0.10 / 6.3 | 221 / 20.6 | 19.76 / 20.51 |
| FLAT-T | 8 | 2147 / 10.08 / 24.57 | 1.08 / 1.11 | 2262 / 2.01 / 149.3 | 1140 / 0.10 / 6.5 | 253 / 14.5 | 14.32 / 14.37 |
| FLAT-T | 12.5 | 1381 / 3.40 / 9.08 | 0.88 / 0.88 | 2289 / 2.01 / 99.6 | 1111 / 0.10 / 4.2 | 131 / 5.6 | 5.43 / 5.52 |
| FLAT-T | 19 | 898 / 1.49 / 3.86 | 0.81 / 0.76 | 2289 / 2.01 / 29.6 | 1116 / 0.10 / 2.2 | 158 / 2.5 | 2.34 / 2.35 |
| FLAT-T | 26 | 728 / 1.69 / 3.05 | 1.09 / 0.54 | 2287 / 2.01 / 36.6 | 1093 / 0.10 / 2.1 | 58 / 1.5 | 1.37 / 1.41 |
| FLAT-T | 30 | 690 / 1.78 / 2.87 | 1.18 / 0.52 | 2287 / 2.01 / 37.5 | 1089 / 0.10 / 2.1 | 34 / 1.2 | 1.16 / 1.20 |
| FLAT-S | 3 | 2354 / 20.01 / 64.63 | 15.10 / 15.10 | 2289 / 2.01 / 182.3 | 1120 / 0.10 / 6.1 | 169 / 32.8 | 28.78 / 32.39 |
| FLAT-S | 5 | 2028 / 19.04 / 43.61 | 12.82 / 13.26 | 2290 / 2.01 / 144.7 | 1126 / 0.10 / 6.2 | 195 / 20.7 | 20.11 / 20.62 |
| FLAT-S | 8 | 1694 / 17.86 / 32.51 | 11.13 / 6.34 | 2291 / 2.01 / 150.8 | 1137 / 0.10 / 6.4 | 243 / 14.4 | 14.30 / 14.33 |
| FLAT-S | 12.5 | 1340 / 12.70 / 18.27 | 10.47 / 2.73 | 2289 / 2.01 / 99.5 | 1110 / 0.10 / 4.1 | 130 / 5.8 | 5.64 / 5.71 |
| FLAT-S | 19 | 724 / 3.48 / 5.91 | 3.58 / 0.58 | 2289 / 2.01 / 29.6 | 1115 / 0.10 / 2.2 | 156 / 2.5 | 2.35 / 2.36 |
| FLAT-S | 26 | 408 / 2.11 / 3.49 | 2.25 / 0.48 | 2287 / 2.01 / 36.5 | 1092 / 0.10 / 2.1 | 53 / 1.6 | 1.43 / 1.47 |
| FLAT-S | 30 | 350 / 1.88 / 2.98 | 2.01 / 0.47 | 2287 / 2.01 / 37.5 | 1091 / 0.10 / 2.1 | 37 / 1.3 | 1.23 / 1.27 |
| FLAT-L | 3 | 2145 / 6.24 / 50.77 | 1.38 / 1.36 | 2153 / 2.01 / 169.4 | 1123 / 0.10 / 6.2 | 182 / 33.0 | 28.31 / 32.57 |
| FLAT-L | 5 | 2104 / 6.43 / 30.83 | 1.16 / 1.16 | 2155 / 2.01 / 136.3 | 1129 / 0.10 / 6.3 | 208 / 20.8 | 20.09 / 20.71 |
| FLAT-L | 8 | 1545 / 5.16 / 19.65 | 1.21 / 1.21 | 2156 / 2.01 / 141.5 | 1140 / 0.10 / 6.5 | 255 / 14.6 | 14.44 / 14.48 |
| FLAT-L | 12.5 | 918 / 2.73 / 8.36 | 1.64 / 1.66 | 2289 / 2.01 / 99.6 | 1117 / 0.10 / 4.2 | 159 / 5.8 | 5.59 / 5.68 |
| FLAT-L | 19 | 711 / 1.82 / 4.27 | 1.32 / 1.31 | 2289 / 2.01 / 29.6 | 1114 / 0.10 / 2.2 | 154 / 2.4 | 2.31 / 2.32 |
| FLAT-L | 26 | 634 / 2.22 / 3.65 | 1.63 / 0.88 | 2287 / 2.01 / 36.6 | 1090 / 0.10 / 2.1 | 53 / 1.4 | 1.33 / 1.37 |
| FLAT-L | 30 | 617 / 2.35 / 3.53 | 1.73 / 0.80 | 2287 / 2.01 / 37.6 | 1089 / 0.10 / 2.2 | 29 / 1.1 | 1.09 / 1.12 |
| ANGLE-1 | 3 | 2145 / 6.25 / 50.99 | 1.36 / 1.38 | 2153 / 2.01 / 169.7 | 1145 / 0.10 / 6.5 | 272 / 32.7 | 27.28 / 32.37 |
| ANGLE-1 | 5 | 2145 / 7.25 / 31.75 | 0.84 / 0.86 | 2154 / 2.01 / 136.4 | 1127 / 0.10 / 6.2 | 202 / 20.7 | 19.87 / 20.60 |
| ANGLE-1 | 8 | 1911 / 7.07 / 21.61 | 0.86 / 0.86 | 2155 / 2.01 / 141.5 | 1138 / 0.10 / 6.5 | 241 / 14.4 | 14.28 / 14.33 |
| ANGLE-1 | 12.5 | 1029 / 2.63 / 8.45 | 1.35 / 1.36 | 2289 / 2.01 / 99.6 | 1112 / 0.10 / 4.2 | 139 / 5.6 | 5.39 / 5.46 |
| ANGLE-1 | 19 | 827 / 1.48 / 3.85 | 0.89 / 0.87 | 2289 / 2.01 / 29.5 | 1114 / 0.10 / 2.1 | 161 / 2.5 | 2.36 / 2.37 |
| ANGLE-1 | 26 | 706 / 1.65 / 2.99 | 1.09 / 0.54 | 2287 / 2.01 / 36.6 | 1093 / 0.10 / 2.1 | 54 / 1.6 | 1.40 / 1.44 |
| ANGLE-1 | 30 | 669 / 1.72 / 2.80 | 1.18 / 0.52 | 2287 / 2.01 / 37.5 | 1090 / 0.10 / 2.1 | 40 / 1.3 | 1.16 / 1.20 |
| ANGLE-2 | 3 | 2145 / 6.24 / 51.00 | 1.37 / 1.40 | 2154 / 2.01 / 169.8 | 1148 / 0.10 / 6.6 | 271 / 32.8 | 27.27 / 32.35 |
| ANGLE-2 | 5 | 2146 / 7.25 / 31.74 | 0.84 / 0.87 | 2155 / 2.01 / 136.4 | 1129 / 0.10 / 6.3 | 204 / 20.7 | 19.86 / 20.60 |
| ANGLE-2 | 8 | 1912 / 7.09 / 21.66 | 0.86 / 0.86 | 2156 / 2.01 / 141.5 | 1137 / 0.10 / 6.5 | 241 / 14.4 | 14.25 / 14.30 |
| ANGLE-2 | 12.5 | 1030 / 2.63 / 8.45 | 1.35 / 1.36 | 2289 / 2.01 / 99.6 | 1112 / 0.10 / 4.2 | 139 / 5.6 | 5.38 / 5.46 |
| ANGLE-2 | 19 | 739 / 1.66 / 3.98 | 1.08 / 1.12 | 2289 / 2.01 / 29.5 | 1114 / 0.10 / 2.1 | 148 / 2.5 | 2.43 / 2.44 |
| ANGLE-2 | 26 | 647 / 2.01 / 3.36 | 1.39 / 0.81 | 2287 / 2.01 / 36.6 | 1091 / 0.10 / 2.1 | 47 / 1.5 | 1.40 / 1.44 |
| ANGLE-2 | 30 | 620 / 2.10 / 3.15 | 1.48 / 0.74 | 2287 / 2.01 / 37.5 | 1088 / 0.10 / 2.1 | 30 / 1.3 | 1.22 / 1.26 |
| ANGLE-3 | 3 | 2084 / 4.62 / 49.31 | 0.99 / 1.00 | 2103 / 2.01 / 164.5 | 1143 / 0.10 / 6.5 | 261 / 32.8 | 27.34 / 32.41 |
| ANGLE-3 | 5 | 2085 / 6.02 / 30.50 | 0.90 / 0.90 | 2102 / 2.01 / 132.6 | 1127 / 0.10 / 6.2 | 198 / 20.7 | 19.89 / 20.62 |
| ANGLE-3 | 8 | 1887 / 6.28 / 20.86 | 0.82 / 0.85 | 2102 / 2.01 / 136.8 | 1140 / 0.10 / 6.5 | 253 / 14.4 | 14.24 / 14.28 |
| ANGLE-3 | 12.5 | 1009 / 2.46 / 8.28 | 1.35 / 1.35 | 2243 / 2.01 / 99.2 | 1112 / 0.10 / 4.2 | 140 / 5.6 | 5.38 / 5.46 |
| ANGLE-3 | 19 | 817 / 1.44 / 3.80 | 0.89 / 0.87 | 2289 / 2.01 / 29.5 | 1114 / 0.10 / 2.1 | 162 / 2.5 | 2.36 / 2.37 |
| ANGLE-3 | 26 | 696 / 1.61 / 2.93 | 1.09 / 0.53 | 2287 / 2.01 / 36.6 | 1093 / 0.10 / 2.1 | 55 / 1.6 | 1.41 / 1.46 |
| ANGLE-3 | 30 | 661 / 1.71 / 2.79 | 1.18 / 0.52 | 2287 / 2.01 / 37.5 | 1089 / 0.10 / 2.1 | 40 / 1.3 | 1.16 / 1.20 |
| SPEED-1 | 3 | 2084 / 5.88 / 50.38 | 1.85 / 1.85 | 2102 / 2.01 / 164.2 | 1120 / 0.10 / 6.1 | 177 / 32.9 | 27.77 / 32.60 |
| SPEED-1 | 5 | 2107 / 6.45 / 31.06 | 0.98 / 0.97 | 2154 / 2.01 / 136.4 | 1128 / 0.10 / 6.3 | 206 / 20.6 | 19.78 / 20.49 |
| SPEED-1 | 8 | 1762 / 6.23 / 20.77 | 0.92 / 0.92 | 2155 / 2.01 / 141.5 | 1139 / 0.10 / 6.5 | 250 / 14.5 | 14.32 / 14.37 |
| SPEED-1 | 12.5 | 1261 / 4.07 / 9.81 | 1.19 / 1.19 | 2289 / 2.01 / 99.6 | 1110 / 0.10 / 4.2 | 132 / 5.6 | 5.44 / 5.51 |
| SPEED-1 | 19 | 811 / 1.87 / 4.19 | 1.09 / 1.14 | 2289 / 2.01 / 29.5 | 1117 / 0.10 / 2.1 | 162 / 2.5 | 2.42 / 2.44 |
| SPEED-1 | 26 | 766 / 1.83 / 3.19 | 1.11 / 0.55 | 2287 / 2.01 / 36.6 | 1092 / 0.10 / 2.1 | 54 / 1.5 | 1.37 / 1.41 |
| SPEED-1 | 30 | 727 / 1.87 / 2.96 | 1.20 / 0.52 | 2287 / 2.01 / 37.5 | 1088 / 0.10 / 2.1 | 30 / 1.2 | 1.16 / 1.20 |
| SPEED-2 | 3 | 2084 / 5.89 / 50.39 | 1.85 / 1.85 | 2102 / 2.01 / 164.2 | 1120 / 0.10 / 6.1 | 173 / 33.0 | 28.07 / 32.61 |
| SPEED-2 | 5 | 2106 / 6.46 / 30.98 | 1.21 / 1.20 | 2154 / 2.01 / 136.4 | 1126 / 0.10 / 6.2 | 198 / 20.7 | 19.93 / 20.58 |
| SPEED-2 | 8 | 1770 / 6.28 / 20.86 | 1.09 / 1.09 | 2155 / 2.01 / 141.5 | 1137 / 0.10 / 6.5 | 245 / 14.4 | 14.28 / 14.32 |
| SPEED-2 | 12.5 | 1261 / 4.09 / 9.83 | 1.29 / 1.30 | 2289 / 2.01 / 99.6 | 1111 / 0.10 / 4.2 | 135 / 5.6 | 5.46 / 5.53 |
| SPEED-2 | 19 | 818 / 1.93 / 4.33 | 1.25 / 0.79 | 2289 / 2.01 / 29.5 | 1113 / 0.10 / 2.1 | 146 / 2.5 | 2.35 / 2.36 |
| SPEED-2 | 26 | 773 / 1.86 / 3.26 | 1.23 / 0.36 | 2287 / 2.01 / 36.6 | 1090 / 0.10 / 2.1 | 51 / 1.5 | 1.33 / 1.37 |
| SPEED-2 | 30 | 728 / 1.92 / 3.03 | 1.32 / 0.34 | 2287 / 2.01 / 37.6 | 1089 / 0.10 / 2.1 | 32 / 1.2 | 1.14 / 1.17 |


**The override lurch is an ICL question** (EVIDENCE, flat sweep; cells = overshoot past the setpoint after release, its peak T,
and the same set's turn-hold error):

| family | ICL | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s |
|---|---|---|---|---|---|---|---|---|
| Kp 2500 Ki 1024 DB 0 Kd 16 | 1024 | 8.46 deg / 2032 T / hold err 1.41 | 8.53 deg / 2023 T / hold err 1.59 | 7.61 deg / 1978 T / hold err 1.49 | 1.23 deg / 1064 T / hold err 0.65 | -0.01 deg / 557 T / hold err 0.64 | 0.24 deg / 376 T / hold err 0.05 | 0.33 deg / 335 T / hold err 0.07 |
| Kp 2500 Ki 1024 DB 0 Kd 16 | 4096 | 12.37 deg / 2299 T / hold err 0.13 | 11.91 deg / 2304 T / hold err 0.09 | 10.12 deg / 2153 T / hold err 0.14 | 3.40 deg / 1382 T / hold err 0.10 | 1.49 deg / 899 T / hold err 0.08 | 1.69 deg / 728 T / hold err 0.14 | 1.78 deg / 690 T / hold err 0.13 |
| Kp 2500 Ki 1024 DB 0 Kd 16 | 10240 | 17.88 deg / 2466 T / hold err 0.14 | 16.29 deg / 2403 T / hold err 0.08 | 14.47 deg / 2283 T / hold err 0.13 | 7.55 deg / 1956 T / hold err 0.11 | 4.40 deg / 1565 T / hold err 0.08 | 3.55 deg / 1178 T / hold err 0.14 | 2.99 deg / 978 T / hold err 0.13 |
| Kp 1500 Ki 1024 DB 0 Kd 0 | 1024 | 14.95 deg / 2449 T / hold err 2.14 | 12.41 deg / 2300 T / hold err 2.35 | 8.59 deg / 1818 T / hold err 2.41 | 0.86 deg / 807 T / hold err 0.97 | -0.11 deg / 439 T / hold err 0.94 | 0.28 deg / 309 T / hold err 0.05 | 0.39 deg / 278 T / hold err 0.11 |
| Kp 1500 Ki 1024 DB 0 Kd 0 | 4096 | 18.03 deg / 2454 T / hold err 0.03 | 15.67 deg / 2344 T / hold err 0.11 | 12.63 deg / 2055 T / hold err 0.11 | 3.98 deg / 1169 T / hold err 0.07 | 1.87 deg / 811 T / hold err 0.05 | 2.18 deg / 701 T / hold err 0.06 | 2.28 deg / 669 T / hold err 0.06 |
| Kp 1500 Ki 1024 DB 0 Kd 0 | 10240 | 24.31 deg / 2466 T / hold err 0.25 | 22.11 deg / 2406 T / hold err 0.09 | 19.68 deg / 2301 T / hold err 0.13 | 10.06 deg / 1904 T / hold err 0.07 | 5.72 deg / 1590 T / hold err 0.05 | 4.58 deg / 1203 T / hold err 0.06 | 3.66 deg / 960 T / hold err 0.06 |
| Kp 1200 Ki 1024 DB 0 Kd 24 | 1024 | 1.57 deg / 1851 T / hold err 3.35 | 2.25 deg / 1845 T / hold err 3.18 | 1.28 deg / 1306 T / hold err 2.82 | -0.22 deg / 614 T / hold err 1.34 | -0.14 deg / 353 T / hold err 1.11 | 0.27 deg / 261 T / hold err 0.05 | 0.37 deg / 239 T / hold err 0.14 |
| Kp 1200 Ki 1024 DB 0 Kd 24 | 4096 | 6.25 deg / 2145 T / hold err 0.10 | 6.45 deg / 2106 T / hold err 0.09 | 5.21 deg / 1557 T / hold err 0.07 | 2.68 deg / 934 T / hold err 0.05 | 1.78 deg / 706 T / hold err 0.06 | 2.16 deg / 633 T / hold err 0.11 | 2.27 deg / 608 T / hold err 0.08 |

Reading: the lurch is P (the full position error returns at release -- 45 deg at 3 m/s) plus the integrator wound behind the fade
(the fade multiplies the whole sum, not the accumulator). A small ICL removes the wound part at speed and costs the low-speed hold;
**an ICL that depends on speed, or an I that bleeds on driver torque, is a cave** (the trace's section 3.6). BELIEF: the fork
should also send the measured angle while the driver overrides and rate-limit back to the plan afterwards; that removes the P part.
The sentinel result does not depend on the tuning (P rails for any Kp >= 30): **0xC63F6 16 -> 328 cuts it from 2 s / 30-180 deg to
0.1 s / 2-7 deg** and also shortens every normal disengage to 0.1 s (the hold torque then drops in 0.1 s -- the dis columns
above are with 16).

### 6.1 Fix A2 of the parallel sentinel trace (`0x29A56` bne -> be; run iff ramp != 0 AND request == 1), simulated

EVIDENCE (sim, `guard_a2.json`; the guard's byte semantics are the parallel trace's, BELIEF here). Same scenarios, stock guard
versus A2, 0xC63F6 = 16 except where named:

| candidate / guard | m/s | override fade-only: overshoot deg | override latch: overshoot deg | sentinel L 16: peak T / s > 50 / excursion deg | sentinel L 328 | sentinel R 16: peak T | disengage excursion: measured / 0 |
|---|---|---|---|---|---|---|---|
| FLAT-T stock-guard | 3 | 12.37 | 5.26 | 2254 / 2.01 / 179.3 | 1149 / 0.10 / 6.6 | 264 | 27.22 / 32.52 |
| FLAT-T stock-guard | 5 | 11.94 | 2.76 | 2255 / 2.01 / 143.1 | 1133 / 0.10 / 6.3 | 224 | 19.76 / 20.50 |
| FLAT-T stock-guard | 8 | 10.14 | 1.09 | 2262 / 2.01 / 149.5 | 1143 / 0.10 / 6.6 | 266 | 14.15 / 14.20 |
| FLAT-T stock-guard | 12.5 | 3.40 | 0.88 | 2289 / 2.01 / 99.6 | 1110 / 0.10 / 4.2 | 131 | 5.42 / 5.51 |
| FLAT-T stock-guard | 19 | 1.49 | 0.81 | 2289 / 2.01 / 29.6 | 1116 / 0.10 / 2.2 | 155 | 2.34 / 2.35 |
| FLAT-T stock-guard | 26 | 1.69 | 1.09 | 2287 / 2.01 / 36.6 | 1093 / 0.10 / 2.1 | 57 | 1.37 / 1.41 |
| FLAT-T stock-guard | 30 | 1.78 | 1.18 | 2287 / 2.01 / 37.5 | 1089 / 0.10 / 2.1 | 34 | 1.16 / 1.20 |
| ANGLE-1 stock-guard | 3 | 6.25 | 1.36 | 2153 / 2.01 / 169.7 | 1145 / 0.10 / 6.5 | 271 | 27.29 / 32.37 |
| ANGLE-1 stock-guard | 5 | 7.24 | 0.86 | 2155 / 2.01 / 136.4 | 1127 / 0.10 / 6.2 | 202 | 19.88 / 20.61 |
| ANGLE-1 stock-guard | 8 | 7.07 | 0.85 | 2156 / 2.01 / 141.5 | 1138 / 0.10 / 6.5 | 241 | 14.30 / 14.34 |
| ANGLE-1 stock-guard | 12.5 | 2.63 | 1.34 | 2289 / 2.01 / 99.6 | 1112 / 0.10 / 4.2 | 139 | 5.38 / 5.46 |
| ANGLE-1 stock-guard | 19 | 1.48 | 0.89 | 2289 / 2.01 / 29.5 | 1114 / 0.10 / 2.1 | 160 | 2.36 / 2.37 |
| ANGLE-1 stock-guard | 26 | 1.65 | 1.09 | 2287 / 2.01 / 36.6 | 1093 / 0.10 / 2.1 | 54 | 1.39 / 1.43 |
| ANGLE-1 stock-guard | 30 | 1.72 | 1.18 | 2287 / 2.01 / 37.5 | 1090 / 0.10 / 2.1 | 39 | 1.16 / 1.20 |
| SPEED-1 stock-guard | 3 | 5.87 | 1.87 | 2101 / 2.01 / 164.3 | 1123 / 0.10 / 6.2 | 168 | 27.75 / 32.55 |
| SPEED-1 stock-guard | 5 | 6.46 | 0.98 | 2154 / 2.01 / 136.4 | 1128 / 0.10 / 6.3 | 206 | 19.77 / 20.47 |
| SPEED-1 stock-guard | 8 | 6.23 | 0.93 | 2156 / 2.01 / 141.5 | 1138 / 0.10 / 6.5 | 248 | 14.31 / 14.36 |
| SPEED-1 stock-guard | 12.5 | 4.07 | 1.19 | 2289 / 2.01 / 99.6 | 1110 / 0.10 / 4.2 | 132 | 5.44 / 5.51 |
| SPEED-1 stock-guard | 19 | 1.87 | 1.09 | 2289 / 2.01 / 29.5 | 1117 / 0.10 / 2.1 | 162 | 2.42 / 2.44 |
| SPEED-1 stock-guard | 26 | 1.83 | 1.11 | 2287 / 2.01 / 36.6 | 1092 / 0.10 / 2.1 | 54 | 1.37 / 1.41 |
| SPEED-1 stock-guard | 30 | 1.87 | 1.20 | 2287 / 2.01 / 37.5 | 1088 / 0.10 / 2.1 | 30 | 1.16 / 1.20 |
| FLAT-T guard-A2 | 3 | 12.36 | 5.28 | 326 / 0.06 / 0.0 | 323 / 0.04 / 0.0 | 298 | 32.46 / 32.46 |
| FLAT-T guard-A2 | 5 | 11.92 | 2.78 | 261 / 0.05 / 0.0 | 258 / 0.04 / 0.0 | 260 | 20.51 / 20.51 |
| FLAT-T guard-A2 | 8 | 10.11 | 1.12 | 299 / 0.06 / 0.0 | 296 / 0.04 / 0.0 | 304 | 14.22 / 14.22 |
| FLAT-T guard-A2 | 12.5 | 3.39 | 0.88 | 168 / 0.04 / 0.0 | 166 / 0.03 / 0.0 | 171 | 5.52 / 5.52 |
| FLAT-T guard-A2 | 19 | 1.49 | 0.76 | 190 / 0.04 / 0.0 | 189 / 0.03 / 0.0 | 179 | 2.35 / 2.35 |
| FLAT-T guard-A2 | 26 | 1.69 | 0.54 | 90 / 0.02 / 0.0 | 89 / 0.01 / 0.0 | 97 | 1.41 / 1.41 |
| FLAT-T guard-A2 | 30 | 1.78 | 0.52 | 73 / 0.01 / 0.0 | 72 / 0.01 / 0.0 | 72 | 1.20 / 1.20 |
| ANGLE-1 guard-A2 | 3 | 6.24 | 1.38 | 310 / 0.06 / 0.0 | 307 / 0.04 / 0.0 | 311 | 32.34 / 32.34 |
| ANGLE-1 guard-A2 | 5 | 7.24 | 0.88 | 234 / 0.05 / 0.0 | 232 / 0.04 / 0.0 | 240 | 20.56 / 20.56 |
| ANGLE-1 guard-A2 | 8 | 7.07 | 0.86 | 281 / 0.05 / 0.0 | 278 / 0.04 / 0.0 | 280 | 14.33 / 14.33 |
| ANGLE-1 guard-A2 | 12.5 | 2.63 | 1.36 | 174 / 0.04 / 0.0 | 172 / 0.03 / 0.0 | 179 | 5.46 / 5.46 |
| ANGLE-1 guard-A2 | 19 | 1.48 | 0.87 | 180 / 0.04 / 0.0 | 179 / 0.03 / 0.0 | 199 | 2.37 / 2.37 |
| ANGLE-1 guard-A2 | 26 | 1.65 | 0.54 | 91 / 0.02 / 0.0 | 90 / 0.01 / 0.0 | 93 | 1.44 / 1.44 |
| ANGLE-1 guard-A2 | 30 | 1.72 | 0.51 | 74 / 0.01 / 0.0 | 73 / 0.01 / 0.0 | 79 | 1.20 / 1.20 |
| SPEED-1 guard-A2 | 3 | 5.88 | 1.84 | 207 / 0.04 / 0.0 | 205 / 0.03 / 0.0 | 215 | 32.58 / 32.58 |
| SPEED-1 guard-A2 | 5 | 6.46 | 0.97 | 240 / 0.05 / 0.0 | 238 / 0.04 / 0.0 | 245 | 20.48 / 20.48 |
| SPEED-1 guard-A2 | 8 | 6.23 | 0.92 | 282 / 0.05 / 0.0 | 279 / 0.04 / 0.0 | 289 | 14.36 / 14.36 |
| SPEED-1 guard-A2 | 12.5 | 4.07 | 1.19 | 166 / 0.04 / 0.0 | 164 / 0.03 / 0.0 | 170 | 5.51 / 5.51 |
| SPEED-1 guard-A2 | 19 | 1.87 | 1.14 | 193 / 0.04 / 0.0 | 191 / 0.03 / 0.0 | 201 | 2.44 / 2.44 |
| SPEED-1 guard-A2 | 26 | 1.83 | 0.55 | 87 / 0.02 / 0.0 | 86 / 0.01 / 0.0 | 92 | 1.41 / 1.41 |
| SPEED-1 guard-A2 | 30 | 1.87 | 0.52 | 69 / 0.01 / 0.0 | 69 / 0.01 / 0.0 | 69 | 1.20 / 1.20 |

Reading: with A2 the sentinel never reaches P (request 0xFF != 1), the lane skips, I is zeroed and the 5.05 Hz output lag decays
the pre-fault torque in ~0.1 s; a request drop does the same, so "send 0 vs send measured" stops mattering (identical columns) and
the wheel relaxes as the lane releases. **A2 is the better sentinel fix than 0xC63F6 = 328** (which still delivers ~1,100 T for
0.1 s, 2-7 deg). It does nothing for the fade-only override (request held, ramp full) -- that lurch stays an ICL question.

## 7. Robustness across the plant family (tracking scenarios; gates U stable, S stick-slip, D dead zone, T tracking, H hold; texture not gated)

| member | FLAT-T | FLAT-S | FLAT-L | ANGLE-1 | ANGLE-2 | ANGLE-3 | SPEED-1 | SPEED-2 |
|---|---|---|---|---|---|---|---|---|
| J_lo | 3/7 3:US 5:U 8:U 19:T | 0/7 3:S 5:S 8:S 12.5:ST 19:T 26:ST 30:ST | 0/7 3:S 5:S 8:T 12.5:T 19:T 26:T 30:T | 3/7 3:S 5:S 12.5:T 26:U | 2/7 3:S 8:T 12.5:T 26:T 30:T | 2/7 3:S 5:S 8:T 12.5:T 26:U | 5/7 8:T 12.5:T | 2/7 3:S 5:S 19:T 26:UT 30:UT |
| J_hi | 2/7 3:U 5:US 8:UD 12.5:U 30:U | 1/7 3:S 5:S 12.5:ST 19:T 26:ST 30:ST | 0/7 3:US 5:US 8:UT 12.5:T 19:T 26:T 30:T | 2/7 3:US 5:US 8:UT 12.5:T 26:U | 1/7 3:US 5:US 8:UT 12.5:T 26:T 30:T | 2/7 3:US 5:US 8:UT 12.5:ST 26:UT | 3/7 3:US 5:US 8:UT 12.5:U | 0/7 3:US 5:S 8:U 12.5:U 19:T 26:UT 30:UT |
| J_hi2 | 2/7 3:U 5:US 8:U 12.5:US 19:U | 0/7 3:US 5:S 8:ST 12.5:T 19:T 26:ST 30:ST | 0/7 3:U 5:USD 8:UDT 12.5:T 19:T 26:T 30:T | 1/7 3:U 5:UD 8:UDT 12.5:UT 26:UT 30:UT | 1/7 3:US 5:USD 8:UDT 12.5:UT 26:T 30:T | 1/7 3:US 5:UD 8:UDT 12.5:UST 26:UT 30:UT | 3/7 3:US 5:USD 8:UDT 12.5:USDTH | 0/7 3:U 5:USD 8:UD 12.5:US 19:T 26:UT 30:UT |
| b_lo | 0/7 3:USD 5:USD 8:UD 12.5:U 19:T 26:U 30:U | 1/7 3:S 5:S 12.5:ST 19:T 26:T 30:T | 1/7 3:US 5:U 8:U 19:T 26:T 30:T | 1/7 3:US 5:US 8:U 19:T 26:U 30:U | 1/7 3:US 5:US 8:U 12.5:T 26:U 30:U | 3/7 3:S 5:US 8:U 19:T | 1/7 3:US 5:US 8:U 12.5:U 26:U 30:UT | 0/7 3:US 5:US 8:US 12.5:U 19:T 26:T 30:T |
| b_hi | 1/7 3:US 5:US 8:U 12.5:T 26:U 30:UT | 0/7 3:S 5:S 8:S 12.5:ST 19:ST 26:ST 30:ST | 0/7 3:S 5:S 8:T 12.5:T 19:T 26:T 30:T | 0/7 3:S 5:S 8:T 12.5:T 19:U 26:UT 30:UT | 0/7 3:S 5:S 8:T 12.5:T 19:T 26:T 30:T | 0/7 3:S 5:S 8:T 12.5:T 19:U 26:UT 30:UT | 1/7 5:S 8:T 12.5:T 19:T 26:UT 30:UT | 1/7 3:S 5:S 8:T 19:T 26:T 30:T |
| F_lo | 3/7 3:U 5:U 8:U 19:U | 2/7 3:S 12.5:ST 19:T 26:ST 30:ST | 2/7 8:T 12.5:T 19:T 26:T 30:T | 3/7 8:U 12.5:T 19:U 30:U | 2/7 8:UT 12.5:T 19:U 26:T 30:T | 0/7 3:S 5:S 8:UT 12.5:T 19:U 26:U 30:U | 3/7 3:S 5:S 8:T 19:U | 2/7 3:S 5:S 19:UT 26:UT 30:UT |
| F_hi | 4/7 3:US 5:US 8:U | 0/7 3:S 5:S 8:S 12.5:ST 19:T 26:ST 30:ST | 0/7 3:S 5:S 8:T 12.5:T 19:T 26:T 30:T | 3/7 3:S 5:S 8:UT 12.5:T | 0/7 3:S 5:S 8:UT 12.5:T 19:S 26:ST 30:T | 3/7 3:S 5:S 8:ST 12.5:T | 3/7 3:S 5:S 8:T 12.5:T | 1/7 3:S 5:S 8:S 19:T 26:T 30:UT |
| tau0 | 4/7 3:US 5:U 8:U | 2/7 3:S 12.5:ST 19:T 26:ST 30:ST | 1/7 3:S 8:T 12.5:T 19:T 26:T 30:T | 2/7 3:S 5:S 8:U 12.5:T 30:U | 2/7 3:S 8:UT 12.5:T 26:T 30:T | 2/7 3:S 5:S 8:ST 12.5:T 30:U | 6/7 8:T | 1/7 3:S 5:S 8:S 19:T 26:UT 30:UT |
| tau6 | 4/7 3:US 5:US 8:UD | 2/7 3:S 12.5:ST 19:T 26:ST 30:ST | 2/7 8:T 12.5:T 19:T 26:T 30:T | 3/7 3:S 5:S 8:U 12.5:T | 2/7 3:S 8:UT 12.5:T 26:T 30:T | 3/7 3:S 5:S 8:UT 12.5:T | 1/7 3:US 5:S 8:UT 12.5:T 26:U 30:U | 2/7 3:S 8:U 19:T 26:UT 30:UT |
| light_b | 0/7 3:UD 5:USD 8:USDTH 12.5:USDTH 19:USDT 26:US 30:US | 0/7 3:US 5:S 8:S 12.5:ST 19:ST 26:ST 30:ST | 0/7 3:US 5:US 8:UST 12.5:US 19:SDT 26:ST 30:ST | 0/7 3:USD 5:USD 8:USDTH 12.5:UST 19:US 26:US 30:US | 0/7 3:USD 5:USD 8:USTH 12.5:US 19:UST 26:UST 30:UST | 0/7 3:US 5:US 8:UST 12.5:US 19:US 26:US 30:US | 0/7 3:US 5:US 8:USDH 12.5:UDTH 19:UDTH 26:UDT 30:UDT | 0/7 3:US 5:US 8:US 12.5:USDTH 19:USDTH 26:USDT 30:USDT |
| ms_free | 2/7 3:US 5:US 8:U 12.5:UDTH 30:U | 2/7 3:S 12.5:US 19:T 26:ST 30:ST | 0/7 3:S 5:U 8:T 12.5:USDTH 19:T 26:T 30:T | 2/7 3:S 5:US 8:UT 12.5:USDTH 26:UT | 1/7 3:S 5:U 8:UT 12.5:USDTH 26:T 30:T | 1/7 3:S 5:US 8:UT 12.5:UDTH 26:UT 30:U | 3/7 3:US 5:US 8:UT 12.5:UDTH | 0/7 3:US 5:S 8:US 12.5:USDTH 19:T 26:UT 30:UT |
| nominal+mode13Hz | 4/7 3:US 5:U 8:U | 2/7 3:S 12.5:ST 19:T 26:ST 30:ST | 2/7 8:T 12.5:T 19:T 26:T 30:T | 3/7 3:S 5:S 8:U 12.5:T | 2/7 5:S 8:UT 12.5:T 26:T 30:T | 2/7 3:S 5:S 8:UST 12.5:T 26:U | 5/7 3:S 8:T | 2/7 3:S 8:S 19:T 26:UT 30:UT |
| nominal+mode20Hz | 4/7 3:US 5:U 8:U | 2/7 3:S 12.5:ST 19:T 26:ST 30:ST | 2/7 8:T 12.5:T 19:T 26:T 30:T | 3/7 3:S 5:S 8:U 12.5:T | 1/7 3:S 5:S 8:UT 12.5:T 26:T 30:T | 2/7 3:S 5:S 8:UT 12.5:T 26:U | 6/7 8:T | 1/7 3:S 5:S 8:S 19:T 26:UT 30:UT |


Reading (EVIDENCE, sim): the in-place candidates are tuned on the nominal member and lose 3-6 speed bands on the stiffer-inertia,
lower-damping, higher/lower-friction and 6 ms-delay members; `light_b` (the PRIOR world, BELIEF) fails everywhere. Most failures are
`S` at 3-5 m/s and `T` (the +-5 % window) at 8-30 m/s. The 13 / 20 Hz two-mass stress modes cost little (SPEED-1 5-6/7).

**7.1 The same with the full-resolution cave option** (0.025 deg setpoint + 1 kHz interpolation + 8x angle + fresh 1 kHz operands,
`robust_cave.json`): it does **not** buy robustness back (SPEED-1 2-4/7 on the off-nominal members).

| member | FLAT-T | ANGLE-1 | SPEED-1 |
|---|---|---|---|
| J_lo | 3/7 3:US 5:US 8:U 19:T | 5/7 3:S 12.5:T | 4/7 3:S 8:T 30:T |
| J_hi | 2/7 3:US 5:US 8:U 12.5:U 26:T | 2/7 3:US 5:US 8:UT 12.5:S 26:T | 2/7 3:US 5:US 8:UT 12.5:U 26:T |
| J_hi2 | 3/7 3:U 5:U 8:U 12.5:U | 2/7 3:U 5:UD 8:UDT 12.5:UST 26:T | 3/7 3:US 5:USD 8:UDT 12.5:USD |
| b_lo | 0/7 3:US 5:US 8:UD 12.5:U 19:T 26:T 30:T | 1/7 3:US 5:US 8:U 19:T 26:T 30:T | 2/7 3:US 8:U 12.5:U 26:T 30:T |
| b_hi | 2/7 3:US 5:US 8:U 12.5:T 30:T | 2/7 3:S 5:S 8:T 12.5:T 30:T | 2/7 3:S 5:S 8:T 12.5:T 30:T |
| F_lo | 1/7 3:US 5:U 8:U 19:T 26:T 30:T | 2/7 3:S 5:S 8:U 12.5:T 26:T | 4/7 8:T 26:T 30:T |
| F_hi | 2/7 3:US 5:US 8:US 19:T 26:T | 2/7 3:S 5:S 8:S 12.5:T 26:T | 2/7 3:S 5:S 8:ST 12.5:T 26:T |
| tau0 | 2/7 3:US 5:US 8:U 19:T 30:T | 4/7 3:S 5:S 12.5:T | 4/7 8:T 26:T 30:T |
| tau6 | 3/7 3:US 5:US 8:U 19:T | 3/7 3:S 5:S 8:US 12.5:T | 4/7 8:T 12.5:T 26:T |
| light_b | 0/7 3:USD 5:USD 8:USDTH 12.5:USDTH 19:US 26:US 30:US | 0/7 3:US 5:US 8:US 12.5:US 19:US 26:US 30:UST | 0/7 3:US 5:US 8:US 12.5:USDTH 19:USDTH 26:USDTH 30:USDH |
| ms_free | 3/7 3:US 5:U 8:U 12.5:USDTH | 2/7 3:S 5:US 8:UT 12.5:UDTH 26:T | 3/7 3:S 5:S 8:UT 12.5:UDTH |
| nominal+mode13Hz | 3/7 3:US 5:US 8:U 19:T | 3/7 3:S 5:S 8:U 12.5:T | 3/7 3:S 8:T 26:T 30:T |
| nominal+mode20Hz | 3/7 3:US 5:US 8:U 19:T | 3/7 3:S 5:S 8:U 12.5:T | 3/7 3:S 8:T 26:T 30:T |

## 8. The fork's outer loop closed (outer = 'pi', tau_o 1.0 s, 60 ms-old wire angle)

| candidate | m/s | tg 0.2 / 0.5 (inner, th vs th_sp received) | hold | T hf hold / sin | stick-slip events |
|---|---|---|---|---|---|
| FLAT-T | 3 | 1.01 / 1.05 | 1.00 | 184.3 / 22.1 | 13 |
| FLAT-T | 5 | 1.01 / 1.04 | 1.00 | 160.8 / 13.2 | 13 |
| FLAT-T | 8 | 1.00 / 1.02 | 1.01 | 153.1 / 5.4 | 5 |
| FLAT-T | 12.5 | 1.01 / 1.03 | 1.01 | 2.4 / 3.0 | 2 |
| FLAT-T | 19 | 0.99 / 0.96 | 1.00 | 2.5 / 2.9 | 0 |
| FLAT-T | 26 | 1.00 / 1.03 | 1.00 | 4.1 / 4.0 | 0 |
| FLAT-T | 30 | 0.98 / 1.02 | 1.00 | 4.8 / 4.0 | 1 |
| FLAT-S | 3 | 1.06 / 1.21 | 1.00 | 0.9 / 2.1 | 8 |
| FLAT-S | 5 | 1.05 / 1.12 | 1.00 | 0.8 / 1.3 | 3 |
| FLAT-S | 8 | 1.01 / 0.99 | 1.01 | 0.8 / 0.6 | 3 |
| FLAT-S | 12.5 | 1.01 / 0.81 | 1.00 | 0.5 / 0.6 | 3 |
| FLAT-S | 19 | 0.82 / 0.29 | 1.02 | 0.8 / 0.5 | 3 |
| FLAT-S | 26 | 0.93 / 0.24 | 0.97 | 0.6 / 0.6 | 2 |
| FLAT-S | 30 | 0.93 / 0.21 | 0.96 | 0.7 / 0.7 | 3 |
| FLAT-L | 3 | 1.02 / 1.08 | 1.00 | 2.1 / 5.4 | 5 |
| FLAT-L | 5 | 1.02 / 1.10 | 1.00 | 1.8 / 3.4 | 8 |
| FLAT-L | 8 | 1.01 / 1.07 | 1.01 | 1.8 / 1.8 | 3 |
| FLAT-L | 12.5 | 0.99 / 1.10 | 1.01 | 1.2 / 1.5 | 2 |
| FLAT-L | 19 | 0.91 / 0.94 | 1.02 | 1.4 / 1.4 | 0 |
| FLAT-L | 26 | 0.84 / 0.98 | 1.02 | 1.2 / 1.4 | 0 |
| FLAT-L | 30 | 0.79 / 0.94 | 1.02 | 1.1 / 1.6 | 1 |
| ANGLE-1 | 3 | 1.02 / 1.07 | 1.00 | 2.8 / 20.6 | 10 |
| ANGLE-1 | 5 | 1.02 / 1.07 | 1.00 | 2.5 / 14.9 | 9 |
| ANGLE-1 | 8 | 1.01 / 1.05 | 1.01 | 3.7 / 5.3 | 7 |
| ANGLE-1 | 12.5 | 1.01 / 1.06 | 1.01 | 1.9 / 3.5 | 1 |
| ANGLE-1 | 19 | 0.99 / 0.97 | 1.01 | 1.6 / 2.7 | 1 |
| ANGLE-1 | 26 | 1.00 / 1.04 | 1.02 | 4.1 / 3.8 | 0 |
| ANGLE-1 | 30 | 0.99 / 1.05 | 1.01 | 4.9 / 4.0 | 1 |
| ANGLE-2 | 3 | 1.02 / 1.07 | 1.00 | 2.2 / 6.1 | 5 |
| ANGLE-2 | 5 | 1.02 / 1.08 | 1.00 | 2.1 / 4.6 | 7 |
| ANGLE-2 | 8 | 1.01 / 1.06 | 1.01 | 3.7 / 2.6 | 7 |
| ANGLE-2 | 12.5 | 1.02 / 1.10 | 1.01 | 1.5 / 1.7 | 0 |
| ANGLE-2 | 19 | 1.01 / 1.02 | 1.01 | 1.3 / 1.6 | 0 |
| ANGLE-2 | 26 | 1.02 / 1.11 | 0.99 | 1.7 / 2.2 | 0 |
| ANGLE-2 | 30 | 0.99 / 1.12 | 0.99 | 1.5 / 2.4 | 1 |
| ANGLE-3 | 3 | 1.02 / 1.07 | 1.00 | 3.0 / 20.9 | 8 |
| ANGLE-3 | 5 | 1.02 / 1.08 | 1.00 | 2.3 / 14.4 | 6 |
| ANGLE-3 | 8 | 1.01 / 1.05 | 1.01 | 2.8 / 4.7 | 6 |
| ANGLE-3 | 12.5 | 1.02 / 1.06 | 1.01 | 1.7 / 3.5 | 1 |
| ANGLE-3 | 19 | 0.99 / 0.97 | 1.01 | 1.7 / 2.8 | 0 |
| ANGLE-3 | 26 | 1.01 / 1.04 | 1.02 | 4.2 / 3.7 | 0 |
| ANGLE-3 | 30 | 0.99 / 1.05 | 1.01 | 4.9 / 3.9 | 1 |
| SPEED-1 | 3 | 1.02 / 1.07 | 1.00 | 2.6 / 7.0 | 4 |
| SPEED-1 | 5 | 1.02 / 1.10 | 1.00 | 1.9 / 3.1 | 7 |
| SPEED-1 | 8 | 1.01 / 1.06 | 1.01 | 2.2 / 2.2 | 3 |
| SPEED-1 | 12.5 | 1.01 / 1.05 | 1.01 | 1.6 / 1.7 | 2 |
| SPEED-1 | 19 | 1.00 / 1.01 | 1.01 | 1.2 / 1.6 | 0 |
| SPEED-1 | 26 | 0.99 / 1.01 | 1.00 | 4.6 / 4.1 | 0 |
| SPEED-1 | 30 | 0.98 / 1.01 | 1.00 | 4.7 / 4.0 | 0 |
| SPEED-2 | 3 | 1.03 / 1.08 | 1.00 | 3.2 / 7.2 | 5 |
| SPEED-2 | 5 | 1.03 / 1.10 | 1.00 | 1.7 / 2.8 | 4 |
| SPEED-2 | 8 | 1.01 / 1.04 | 1.01 | 2.1 / 2.6 | 4 |
| SPEED-2 | 12.5 | 1.00 / 1.00 | 1.01 | 1.8 / 1.8 | 3 |
| SPEED-2 | 19 | 0.96 / 0.86 | 1.01 | 1.7 / 1.9 | 1 |
| SPEED-2 | 26 | 0.98 / 0.93 | 1.01 | 2.9 / 3.9 | 0 |
| SPEED-2 | 30 | 0.97 / 0.92 | 1.00 | 2.7 / 4.4 | 0 |

Reading (EVIDENCE within the stand-in, BELIEF on the stand-in itself): closing an integrating outer loop on the 60 ms-old wire
angle leaves tracking and hold intact but **adds stick-slip events at <= 12.5 m/s for every candidate** (SPEED-1: 4 / 7 / 3 / 2 at
3 / 5 / 8 / 12.5 m/s, against 0 open) -- two integrators against static friction. The fork side should not integrate angle error
at low speed.

## 9. The record's 20 Hz comparator per candidate

| candidate | max Kp | max Kd | P part | D part | |(P+D)/x| at 20 Hz | vs V295 3.85 |
|---|---|---|---|---|---|---|
| FLAT-T | 2500 | 16 | 1.55 | 2.00 | 2.53 | <= |
| FLAT-S | 500 | 16 | 0.31 | 2.00 | 2.02 | <= |
| FLAT-L | 1200 | 24 | 0.74 | 3.00 | 3.09 | <= |
| ANGLE-1 | 2500 | 24 | 1.55 | 3.00 | 3.38 | <= |
| ANGLE-2 | 1800 | 24 | 1.12 | 3.00 | 3.20 | <= |
| ANGLE-3 | 2500 | 28 | 1.55 | 3.50 | 3.83 | <= |
| SPEED-1 | 2500 | 28 | 1.55 | 3.50 | 3.83 | <= |
| SPEED-2 | 2500 | 28 | 1.55 | 3.50 | 3.83 | <= |

EVIDENCE (arithmetic, `hf20()`; selftest 5 reproduces V295's 3.85): the angle loop's P costs Kp x 6.2e-4 per x count at 20 Hz
(Kp 2500: 1.55), so P is never the 20 Hz problem; D on the 100 Hz rate costs Kd/8 and in quadrature caps Kd at ~28 with Kp 2500.
This comparator omits the 100 Hz hold and the output stage, common to every build compared (the record's form).

## 10. What a cave buys: the texture, operand by operand

EVIDENCE (sim, nominal member, `payoff.json` / `payoff2.json`). Options: `ang_mult` = the lane's angle at 0.1/ang_mult deg with
b = 8192/ang_mult (r26 = 16 theta unchanged; the +-12000 input gate then caps |theta| at 1200/ang_mult deg -- 150 deg at x8);
`fresh` = angle and rate operands refreshed every tick (gp-0x69ca / gp-0x6abe class) instead of held by slot 4; `sp_fine` = the
setpoint at 0.025 deg (what the handler's `shl 2` discards; needs the fork to send 4x finer and the handler not to multiply,
BELIEF); `sp_interp` = the setpoint ramped across each 10 ms frame at 1 kHz (V288's class of cave; one frame of delay).

**FLAT-T** -- T rms in 5-30 Hz during the three sinusoids (max) · stick-slip events · tracking 0.2/0.5 Hz

| operand / setpoint option | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s |
|---|---|---|---|---|---|---|---|
| in-place (0.1 deg setpoint and angle, 100 Hz hold) | 31.4 · 3 · 1.01/1.05 | 14.9 · 2 · 1.01/1.04 | 6.7 · 0 · 1.00/1.02 | 3.4 · 0 · 1.01/1.03 | 2.9 · 0 · 0.99/0.95 | 4.3 · 0 · 0.99/1.01 | 4.6 · 0 · 0.99/1.01 |
| {"ang_mult": 4} | 29.6 · 4 · 1.01/1.05 | 14.3 · 1 · 1.01/1.04 | 6.8 · 0 · 1.00/1.02 | 2.4 · 0 · 1.01/1.03 | 2.4 · 0 · 1.00/0.95 | 2.9 · 0 · 1.00/1.02 | 3.1 · 0 · 0.99/1.01 |
| {"ang_mult": 8} | 29.8 · 2 · 1.01/1.05 | 14.5 · 2 · 1.01/1.04 | 6.8 · 0 · 1.00/1.02 | 2.4 · 0 · 1.01/1.03 | 2.3 · 0 · 1.00/0.95 | 2.9 · 0 · 1.00/1.01 | 3.0 · 0 · 0.99/1.02 |
| {"fresh": true} | 18.7 · 3 · 1.01/1.05 | 11.2 · 1 · 1.01/1.04 | 4.4 · 0 · 1.00/1.02 | 3.0 · 0 · 1.01/1.03 | 2.9 · 0 · 0.99/0.94 | 4.2 · 0 · 0.99/1.01 | 4.7 · 0 · 0.99/1.00 |
| {"ang_mult": 8, "fresh": true} | 19.2 · 2 · 1.01/1.05 | 11.2 · 2 · 1.01/1.04 | 4.3 · 0 · 1.00/1.02 | 2.4 · 0 · 1.01/1.03 | 2.3 · 0 · 1.00/0.95 | 2.9 · 0 · 1.00/1.00 | 3.0 · 0 · 0.99/1.00 |
| {"sp_fine": true} | 32.4 · 4 · 1.01/1.05 | 14.8 · 2 · 1.01/1.04 | 5.7 · 0 · 1.00/1.02 | 2.5 · 0 · 1.01/1.03 | 2.1 · 0 · 1.00/0.95 | 2.3 · 0 · 0.99/1.01 | 2.5 · 0 · 0.98/1.01 |
| {"sp_interp": true} | 29.8 · 2 · 1.01/1.05 | 15.1 · 3 · 1.01/1.04 | 5.7 · 0 · 1.00/1.02 | 3.3 · 0 · 1.01/1.03 | 3.0 · 0 · 1.00/0.95 | 4.3 · 0 · 0.99/1.02 | 4.5 · 0 · 0.99/1.01 |
| {"sp_fine": true, "sp_interp": true} | 29.4 · 3 · 1.01/1.05 | 13.7 · 1 · 1.01/1.04 | 6.7 · 0 · 1.00/1.02 | 2.8 · 0 · 1.01/1.03 | 2.0 · 0 · 1.00/0.95 | 2.4 · 0 · 1.00/1.01 | 2.6 · 0 · 0.98/1.01 |
| {"ang_mult": 8, "fresh": true, "sp_fine": true, "sp_interp": true} | 19.2 · 2 · 1.01/1.05 | 11.5 · 2 · 1.01/1.04 | 3.3 · 0 · 1.00/1.02 | 1.1 · 0 · 1.01/1.03 | 0.5 · 0 · 0.97/0.94 | 0.6 · 0 · 0.96/1.00 | 0.7 · 0 · 0.95/1.00 |

**ANGLE-1** -- T rms in 5-30 Hz during the three sinusoids (max) · stick-slip events · tracking 0.2/0.5 Hz

| operand / setpoint option | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s |
|---|---|---|---|---|---|---|---|
| in-place (0.1 deg setpoint and angle, 100 Hz hold) | 18.2 · 1 · 1.02/1.08 | 13.5 · 2 · 1.02/1.07 | 4.2 · 0 · 1.01/1.05 | 4.1 · 0 · 1.02/1.06 | 2.6 · 0 · 1.00/0.97 | 4.1 · 0 · 0.99/1.04 | 4.1 · 0 · 1.00/1.03 |
| {"ang_mult": 4} | 18.0 · 1 · 1.02/1.08 | 13.5 · 1 · 1.02/1.07 | 3.8 · 0 · 1.01/1.05 | 3.1 · 0 · 1.01/1.06 | 2.3 · 0 · 1.00/0.96 | 2.8 · 0 · 1.00/1.05 | 3.0 · 0 · 0.99/1.06 |
| {"ang_mult": 8} | 18.0 · 2 · 1.02/1.08 | 13.5 · 1 · 1.02/1.07 | 3.8 · 0 · 1.01/1.05 | 3.2 · 0 · 1.01/1.06 | 2.3 · 0 · 1.00/0.96 | 2.8 · 0 · 1.00/1.05 | 3.0 · 0 · 0.99/1.06 |
| {"fresh": true} | 16.6 · 2 · 1.02/1.08 | 11.9 · 1 · 1.02/1.07 | 3.5 · 0 · 1.01/1.05 | 3.2 · 0 · 1.01/1.05 | 2.6 · 0 · 1.00/0.96 | 3.9 · 0 · 0.99/1.03 | 4.2 · 0 · 0.99/1.02 |
| {"ang_mult": 8, "fresh": true} | 16.7 · 2 · 1.02/1.08 | 11.7 · 1 · 1.02/1.07 | 3.5 · 0 · 1.01/1.04 | 3.1 · 0 · 1.01/1.05 | 2.2 · 0 · 1.00/0.96 | 2.7 · 0 · 1.00/1.04 | 2.9 · 0 · 0.99/1.04 |
| {"sp_fine": true} | 17.9 · 3 · 1.02/1.08 | 13.8 · 1 · 1.02/1.07 | 3.9 · 0 · 1.01/1.05 | 3.2 · 0 · 1.01/1.06 | 2.0 · 0 · 1.00/0.97 | 2.2 · 0 · 1.00/1.04 | 2.5 · 0 · 0.98/1.04 |
| {"sp_interp": true} | 17.8 · 1 · 1.02/1.08 | 12.9 · 2 · 1.02/1.07 | 4.3 · 0 · 1.01/1.05 | 3.8 · 0 · 1.02/1.06 | 2.7 · 0 · 1.00/0.97 | 4.1 · 0 · 0.99/1.04 | 4.2 · 0 · 1.00/1.03 |
| {"sp_fine": true, "sp_interp": true} | 18.8 · 2 · 1.02/1.08 | 13.0 · 2 · 1.02/1.07 | 3.9 · 0 · 1.01/1.05 | 3.1 · 0 · 1.01/1.06 | 1.9 · 0 · 1.00/0.97 | 2.2 · 0 · 1.00/1.04 | 2.6 · 0 · 0.98/1.04 |
| {"ang_mult": 8, "fresh": true, "sp_fine": true, "sp_interp": true} | 17.2 · 2 · 1.02/1.08 | 10.9 · 1 · 1.02/1.07 | 3.2 · 0 · 1.01/1.04 | 2.5 · 0 · 1.01/1.05 | 1.2 · 0 · 0.98/0.96 | 0.9 · 0 · 0.95/1.05 | 0.9 · 0 · 0.96/1.00 |

**SPEED-1** -- T rms in 5-30 Hz during the three sinusoids (max) · stick-slip events · tracking 0.2/0.5 Hz

| operand / setpoint option | 3 m/s | 5 m/s | 8 m/s | 12.5 m/s | 19 m/s | 26 m/s | 30 m/s |
|---|---|---|---|---|---|---|---|
| in-place (0.1 deg setpoint and angle, 100 Hz hold) | 7.0 · 0 · 1.02/1.07 | 3.3 · 0 · 1.02/1.10 | 2.2 · 0 · 1.01/1.06 | 2.0 · 0 · 1.01/1.05 | 1.8 · 0 · 1.00/1.02 | 4.1 · 0 · 0.98/1.00 | 4.6 · 0 · 0.98/1.01 |
| {"ang_mult": 4} | 6.9 · 0 · 1.02/1.07 | 2.9 · 0 · 1.02/1.10 | 1.8 · 0 · 1.01/1.06 | 1.6 · 0 · 1.01/1.05 | 1.4 · 0 · 1.00/1.02 | 3.0 · 0 · 1.00/1.00 | 3.1 · 0 · 0.99/1.00 |
| {"ang_mult": 8} | 6.9 · 0 · 1.02/1.07 | 2.8 · 0 · 1.02/1.10 | 1.8 · 0 · 1.01/1.06 | 1.6 · 0 · 1.01/1.05 | 1.4 · 0 · 1.01/1.02 | 2.9 · 0 · 0.99/0.99 | 3.0 · 0 · 0.99/1.00 |
| {"fresh": true} | 6.3 · 1 · 1.02/1.07 | 2.8 · 0 · 1.02/1.09 | 1.7 · 0 · 1.01/1.06 | 2.0 · 0 · 1.01/1.05 | 1.8 · 0 · 1.00/1.01 | 4.2 · 0 · 0.98/0.99 | 4.7 · 0 · 0.98/1.00 |
| {"ang_mult": 8, "fresh": true} | 6.3 · 1 · 1.02/1.07 | 2.7 · 0 · 1.02/1.10 | 1.7 · 0 · 1.01/1.06 | 1.6 · 0 · 1.01/1.05 | 1.4 · 0 · 1.01/1.01 | 2.9 · 0 · 1.00/0.98 | 3.0 · 0 · 0.99/0.99 |
| {"sp_fine": true} | 7.0 · 0 · 1.02/1.07 | 2.8 · 0 · 1.02/1.10 | 1.9 · 0 · 1.01/1.06 | 1.5 · 0 · 1.01/1.05 | 1.2 · 0 · 1.00/1.01 | 2.3 · 0 · 0.99/1.00 | 2.4 · 0 · 0.98/1.02 |
| {"sp_interp": true} | 7.0 · 0 · 1.02/1.07 | 3.0 · 0 · 1.02/1.10 | 2.1 · 0 · 1.01/1.06 | 2.0 · 0 · 1.01/1.05 | 1.8 · 0 · 1.00/1.02 | 4.2 · 0 · 0.98/1.00 | 4.5 · 0 · 0.98/1.01 |
| {"sp_fine": true, "sp_interp": true} | 6.7 · 0 · 1.02/1.07 | 2.6 · 0 · 1.02/1.10 | 1.7 · 0 · 1.01/1.06 | 1.4 · 0 · 1.01/1.05 | 1.2 · 0 · 1.01/1.01 | 2.3 · 0 · 0.99/1.00 | 2.4 · 0 · 0.98/1.02 |
| {"ang_mult": 8, "fresh": true, "sp_fine": true, "sp_interp": true} | 6.3 · 1 · 1.02/1.07 | 2.5 · 0 · 1.02/1.10 | 1.1 · 0 · 1.01/1.06 | 0.8 · 0 · 1.01/1.05 | 0.6 · 0 · 0.99/1.01 | 0.6 · 0 · 0.95/0.97 | 0.6 · 0 · 0.95/1.02 |

Reading: at 19-30 m/s the texture is **setpoint quantisation and feedback quantisation together**: the finer setpoint alone removes
~45 %, the finer angle alone ~30 %, the fresh operand alone ~0; all four together leave 0.6 counts. At 3 m/s it is neither: 6-7 counts remain under every option -- that is the
plant's own stick-slip transients against the 76-count low-speed friction (EVIDENCE: identical across operand options).
The fresh 1 kHz operand alone shrinks FLAT-T's 3-8 m/s limit cycle (T hf 200 -> 63-79 counts, hunting 10-14 -> 1-1.6 deg) but
does not stabilise it.

## 11. Leads, caveats and what would change the verdict

**Lead (BELIEF, needs a trace before anyone relies on it): a speed schedule without a cave.** From the Ghidra listing of
`0x29CF6-0x29EE4` (V294 program = V295 code, read-only dry-run disassembly): the Kp LERP is keyed by `r7` (`zxh r7` at
`0x29DE8`), the Kd LERP by `r22` (`mov r7,r22 ; zxb r22` at `0x29D10`, moved to `r13` at `0x29E92`). With edit (4) the map LERP at
`0x29CFC-0x29D68` computes only `r13` (the map Y), which edit (4) makes dead. So replacing `mov 0xc9a88,r16` (6 bytes at
`0x29CFC`) by `ld.bu -0x6a5d[gp],r7` (the high byte of the speed word, 4 km/h per count) + `br 0x29d10`, and `sld.hu 0x2,ep,r10`
at `0x29D18` by `br 0x29d6a`, would key BOTH schedules on speed with 8 bytes in place. Unverified: the odd-displacement `ld.bu`
encoding, branch targets into `0x29D02-0x29D18`, liveness of `ep/r6/r10/r16/r2` on the new path (they appear to be rewritten
before use at `0x29D6E`, `0x29D9C`, `0x29DCC` -- BELIEF), the readers of `gp-0x674B` / `gp-0x697A` (they would carry speed>>8),
and the speed word's behaviour on a voter fault (slews to 80 km/h, `gp-0x67f4` = 0). The harness's SPEED-1/2 runs are exactly
this edit's arithmetic (`key = 'speed'`; selftest 6).

**Caveats (each would move numbers, none is known to flip the verdict):**
- The plant is the r71b identification: J is identified only at 0-5 m/s, b and friction at speed carry the estimator's bias,
  and **the 0-5 m/s friction CI is +-129 counts** (V294-PLANT-IDENT-r71b.md). Every low-speed number here rests on it.
- Nothing above ~8 Hz is identified; the 13 / 20 Hz modes are stress members only.
- The angle quantiser is uniform (BELIEF: the firmware staircase is 0.1 deg steps with an occasional 2-count step near centre
  where the VGR correction increments -- it can only add texture).
- The rate former (3 ms window) and its sampling inside slot 4 are the record's BELIEF; the 0xE4 RX phase (tick % 10 == 0) is not
  traced.
- The driver in the override scenario is a stiff position source; the driver-torque word is scripted (no N.m scale exists).
- The outer loop is either a pure feedforward or a 1 s integrator stand-in; the real path-level loop is not modelled.
- The texture threshold (2 counts rms) is a BELIEF; the operator scores symptoms.
- "<= V282" terms of the goal are not computable here (V282 is not simulated).

## 12. Reproduce

```
cd analysis-2020accord/studies/angle_loop
python harness_time.py --selftest        # ~20 s
python harness_time.py --all             # selftest, sweep, refined, final(+robust, outer), payoff, payoff2, robust-cave,
                                         # guard-a2, report (~35 min with 9 worker processes on this PC)
python harness_time_report.py            # rewrite this report from the caches
```
Caches: `_scratch/angle_loop/harness-time/{selftest_out.txt, flat_sweep, refined_sweep, final, final_robust, payoff, payoff2,
robust_cave, guard_a2}.json` (repo-root `_scratch/`, gitignored, regenerable).
