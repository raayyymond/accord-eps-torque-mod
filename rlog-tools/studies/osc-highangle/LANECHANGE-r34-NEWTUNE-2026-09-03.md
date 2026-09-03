# r34 on the NEW StarPilot tune — the lane-change ring read with the r32/r33 instrument (2026-09-03, subagent lanechange34)

Route r34 = `75604b0a432fdc89_00000034--e2d2d5381f` (18 segments, 1036 s, latActive 903 s, highway-engaged 88 s). **Same firmware
as r32/r33 (V280 rev 2: slot-7 line map to the ×6 top, 0xC62E6 = 46080, CAN-427 torque tap); NEW lateral tune** decoded from
`analysis-2020accord/reference/toggle-backup_20260902.decoded.json` (ForceAutoTuneOff ON, SteerFriction 0.03, SteerLatAccel 2.11,
SteerRatio 16.1, SteerKP 0.6, SteerDelay 0.2). Baseline = `LANECHANGE-V278R3-2026-09-02.md` (r32 / r33, old tune: LAF 1.689,
friction 0.212). Script `lanechange_r34.py` beside this note: **every statistic is the baseline's own code** (`lanechange_osc` /
`lanechange_windows` / `lanechange_chain` / `lanechange_loop` / `backcalc_laf_friction`) called on the r34 caches; **no threshold
moved**. Raw output: `LANECHANGE-r34.txt` (detector + strata), `LANECHANGE-r34-windows.txt` (everything below), `lanechange_r34.json`;
backcalc refit `../../../analysis-2020accord/studies/optune/_scratch/backcalc_out_r34.txt`. r34 was added to `lanechange_osc.ROUTES /
HAS_TAP / CHAIN_CFG`, `lanechange_events.json` and `backcalc_extract.ROUTES` / `backcalc_laf_friction.TAGS` (additive). EVIDENCE unless marked.

## 0. Prediction vs result

Pre-registered (orchestrator, before this read): Gc = (kp+lsf)/LAF + friction/0.30 goes 1.10 → 0.41 (0.37×); if the ring is the outer
loop, the 7–8 Hz lane-change ring count (6 of 6 on r32/r33) falls to ~0 and the hands-light 4–8 Hz wheel-rate power at 25–30 m/s
(210–320 wire² on r32/r33) falls ≳ 5×. FAIL = ring count ≥ 4 of ≥ 5 lane changes with 4–8 Hz power within 2× of r32/r33.

| readout | r32 / r33 (old tune) | r34 (new tune) | verdict |
|---|---|---|---|
| hands-light lane changes ≥ 17.7 m/s that ring | **6 of 6** | **0 of 2** (0 of 1 strictly hands-off) | consistent; count under-powered (only 2 such lane changes were driven) |
| OSC episodes on highway frames (env > 40 wire ≥ 0.6 s) | 4 in 224 s / 5 in 112 s | **0 in 88 s** | PASS |
| 4–8 Hz rate power, 25–32 m/s, \|cmd\| 100–300 (wire²) | **322** (r32; r33 none) | **29** | **0.09× — PASS (≥ 5× fall)** |
| 4–8 Hz rate power, 20–32 m/s, \|cmd\| 100–300 | 210 / 322 | **28** | 0.09–0.13× — PASS |
| 4–8 Hz rate power, 20–32 m/s, \|cmd\| 0–100 | 38 / 71 | 7 | 0.1–0.2× |
| 0xE4 command 4–8 Hz power, highway frames / \|cmd\| 100–300 | 1342, 1792 / 3010, 4123 | **162 / 233** | 0.09–0.13× / 0.06–0.08× |
| openpilot block H_op = cmd/angle at 7.81 Hz, highway | 866 ∠−66° (coh 0.94) / 875 ∠−69° (0.93) counts/deg | **317 ∠−60° (coh 0.83)** | **0.36× = the predicted Gc ratio 0.37** |
| lane-keeping OSC episodes outside any window at 25–30 m/s | 3 on r33 (460.5, 464.4, 491.6) | 0 | PASS |

**Verdict: PASS on the power criterion and on the count as far as it can be tested (EVIDENCE).** The FAIL sentence cannot fire: r34 has
2 hands-light highway lane changes, not ≥ 5, and neither rings; the 4–8 Hz power is 8–11× below r32/r33 at matched speed and |cmd|, not
within 2×. Fisher on the ring counts alone (0/2 vs 6/6) gives p = 0.036. The openpilot block's gain at the line fell by exactly the
predicted factor (0.36 vs 0.37), which is the direct signature of the outer-loop mechanism (EVIDENCE for the gain; BELIEF that
this alone explains the ring's disappearance — the tune also lowered the vehicle-model lat-accel per degree by 12 %, §1).

## 1. Build attribution and what the controller used

**Firmware = V280 rev 2, unchanged (EVIDENCE, tap).** Chain T_sim vs the CAN-427 T_meas on engaged idx > 0 frames:

| route | line/46080 corr / LS slope / sign agree | rev 3 ×2/15360 | stock ×1/7680 | hands-light idx ≥ 200: s, rate p90, push fraction > 60 deg/s | T sat / max field |
|---|---|---|---|---|---|
| r32 | 0.848 / 0.56 / 0.880 | 0.265 / 0.15 / 0.847 | 0.110 / 0.08 / 0.669 | 3.0 s, 152 deg/s, 0.32 (n 304) | 0.000 / 223 |
| r33 | 0.897 / 0.49 / 0.896 | 0.445 / 0.22 / 0.848 | 0.331 / 0.22 / 0.663 | 7.1 s, 145 deg/s, 0.40 (n 680) | 0.000 / 269 |
| **r34** | **0.894 / 0.47 / 0.946** | 0.481 / 0.25 / 0.881 | 0.310 / 0.21 / 0.660 | 7.8 s, 150 deg/s, 0.31 (n 777) | 0.000 / 271 |

**Controller (EVIDENCE, `backcalc_laf_friction.live_values` on r34):**
- `carParams.lateralTuning.torque` still logs LAF 1.6893 / friction 0.2120 / steerRatio 16.33 / actuatorDelay 0.10 (CarParams are not
  rewritten by the toggles); `liveDelay.lateralDelay` 0.200 engaged.
- `liveTorqueParameters.*Filtered` = **LAF 2.110 / friction 0.030 / offset 0.000** first-to-last tick (r32/r33: 1.689 / 0.212); Raw 4.83 /
  0.137 (the stale cache TLS, liveValid 0, 6653 points frozen — as on r32/r33; useParams 1).
- Identity **−(p+i+d+f)/output = 2.110** at p5 and p50 (p95 3.5 where the ±LAF clip acts; r32/r33: 1.689). **p/error = 0.600** at p50.
  f-regression **friction·LAF = 0.060 → friction 0.029** (r32/r33: 0.339 / 0.353 → 0.201 / 0.209). So the controller ran 2.11 / 0.03 / kp 0.6.
- `starpilotLateralState` is not in the logs (same as r32/r33 — debug-only publisher), so frictionThreshold is taken from the code (0.30).
- **Vehicle model:** `liveParameters.steerRatio` p50 **16.10** (r32/r33: 16.38 / 16.41), and the controller's `actualLateralAccel` per
  (angle_rad · v²) at v > 15, 2–30°: **0.0168 vs 0.0193 / 0.0190 → 0.88× (−12 %)**, matching the predicted 13 % from 14.0 → 16.1 (EVIDENCE).
- Gc at 27 m/s: old 1.090 → new 0.407, ratio 0.373 (arithmetic on the values above).

## 2. The lane-change census (same detector, same windows)

r34 laneChangeState census: off 20158 / pre 31 / starting 373 / finishing 80 (20 Hz); 4 windows. Highway frames (engaged, v ≥ 20, |ang| < 8):
88 s, v p50/max 27.3/32.1, |cmd| p50/p90 99/323 (r32/r33 63/160, 79/200 — the command is LARGER on the new tune, see §3), idx p50/p90/p99
6/17/48, 2–12 Hz envelope p95/p99/max 27/41/63 wire (r32 28/55/144, r33 38/69/125), rate power 2–4/4–8/8–15 = 18/25/94 wire² (r32
12/93/176, r33 23/121/107). Chain on highway frames: P-rail 0.0067 (one hand-assisted excursion), fb-clamp 0.000, |E| p50/p90 531/1391, Kp p50 271.

| r34 # | t0 | dur | dir | v | swing | cmd pk / idx pk / tq pk (tq p50, cliff %) | rate 4–12 amp deg/s | env pk | f Welch / Hilbert / T | T amp / \|T\|90 / sat / damp | cmd coh / ph | P-rail / fb-cl | \|E\| p50 / p90 | 2–4 / 4–8 / 8–12 wire² | ring |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 505.9 | 9.2 | L | 31.5 | 14.4° | 2171 / 118 / 3251 (287, 25 %) | 1.3 | 45 | 1.56 / 4.6 / 1.6 | 25 / 744 / 0 / 0.46 | 0.34 / +33 | 0.076 / 0 | 887 / 7094 | 170 / 30 / 30 | no (driver-assisted, tq past the cliff 25 %) |
| **1** | **561.2** | 7.2 | L | **26.6** | 14.7° | 540 / 33 / 743 (183, 0 %) | **1.4** | **20** | 1.56 / 7.4 / 1.6 | 31 / 353 / 0 / 0.34 | 0.88 / +46 | 0 / 0 | 653 / 1782 | 24 / **44** / 32 | **no** — the one strictly hands-off highway lane change |
| **2** | **569.2** | 7.5 | R | **27.2** | 8.9° | 504 / 32 / 2763 (136, 2 %) | **1.0** | **18** | 1.56 / 6.7 / 1.6 | 22 / 256 / 0 / 0.41 | 0.65 / +44 | 0 / 0 | 613 / 1482 | 33 / **14** / 18 | **no** — one 0.5 s hand nudge at onset (1926 raw), hands light after |
| 3 | 619.2 | 8.3 | L | 11.0 | 32.8° | 1011 / 62 / 2139 (229, 0 %) | 1.4 | 25 | 1.56 / 6.1 / 1.6 | 35 / 568 / 0 / 0.38 | 0.46 / +56 | 0 / 0 | 1396 / 4022 | 47 / 33 / 30 | no (11 m/s, not highway) |

Windows #1 and #2 are the same manoeuvre class as r32 #1/#3 and r33 #2 (26–28 m/s, cmd pk 500–850, idx pk 32–52, hands light): those
rang at **5.0–5.6 deg/s (9.6–14.6 in the ring), envelope 119–144, 4–8 Hz 679–1042 wire², f 7.0–7.8 Hz, T at the same f**; r34's read
**1.0–1.4 deg/s, envelope 18–20, 4–8 Hz 14–44 wire², no line (f_dom = the 1.56 Hz bin = the manoeuvre itself), T amplitude 22–31 vs 71–77.**
0.5 s-bin traces of both r34 windows are in `LANECHANGE-r34-windows.txt` (env never above 20 wire = 2.5 deg/s; |T| 25–390).

Automatic detector on r34 highway frames: **20 command excursions, 0 OSC episodes.** The excursions at 26–28 m/s with idx pk 20–45
(559.7, 563.1, 569.0, 578.2 …) ring at 0.9–2.0 deg/s with f_dom 1.56 Hz (no line); the 20 m/s ones (585.1, 588.0) show V112's 10.2 Hz
residual at 2.7–3.0 deg/s; nothing at 7–8 Hz. Baseline r32/r33 episodes: 5.4–11.4 deg/s at 7.0–8.9 Hz.

**Strata, 4–8 / 8–12 Hz rate power (wire²) on highway frames, Welch 1.28 s runs [seconds]:**

| stratum (v, \|cmd\| 1 Hz-LPF) | r34 NEW | r32 old | r33 old | r22 V112 |
|---|---|---|---|---|
| 20–25 m/s, 0–100 | 15 / 162 [6] | 29 / 151 [114] | 21 / 17 [52] | 7 / 86 [28] |
| 20–25, 100–300 | 28 / 334 [7] | 106 / 335 [19] | 37 / 41 [20] | 7 / 99 [41] |
| 25–32, 0–100 | **7 / 10 [41]** | 50 / 53 [77] | 166 / 94 [28] | — |
| 25–32, 100–300 | **29 / 33 [24]** | **322 / 680 [13]** | — | — |
| 20–32, 0–100 | 7 / 22 [48] | 38 / 110 [191] | 71 / 43 [80] | 7 / 86 [28] |
| 20–32, 100–300 | **28 / 179 [31]** | 210 / 501 [32] | 322 / 168 [30] | 7 / 99 [41] |
| 20–32, all | 19 / 52 [87] | 89 / 133 [224] | 143 / 68 [112] | 11 / 115 [78] |

r34 at 25–32 m/s is at V112's level (4–8 Hz 7–29 vs V112's 7–10 at 20–25); the 20–25 m/s rows on r34 are 6–7 s and carry the 10 Hz residual
(8–12 Hz 162–334), not the 7–8 Hz line. **Plain lane keeping at 25–30 m/s:** 72 s on r34 with 0 episodes (r33: 3 in 40 s).

**Loop blocks (`lanechange_loop.loop_table`, r34 highway frames, 86 s):** H_op = cmd/angle at 7.03 / 7.81 / 8.59 Hz = 334 ∠−52° (coh 0.77)
/ **317 ∠−60° (0.83)** / 322 ∠−67° (0.83) counts/deg — r32/r33 866 / 875 ∠−66…−69°, r22 V112 635, stock 792 — **openpilot's block is the
one that changed, by 0.36×.** H_eps = rate/cmd reads 0.40–0.60 wire/count (coh 0.58–0.64), above r32/r33's 0.27–0.29: ⚠ closed-loop
H1 with the loop's own excitation gone is biased toward 1/H_op and is not a plant reading (same caveat as the baseline).

## 3. Tune side effects (backcalc grids; latActive & active & v ≥ 20 & hands off)

| | r32 old (224 s) | r33 old (110 s) | **r34 new (85 s)** |
|---|---|---|---|
| torqueState.error RMS / p90 (m/s²) | 0.093 / 0.136 | 0.117 / 0.158 | **0.196 / 0.304** |
| desired − actual lat accel RMS | 0.082 | 0.105 | **0.181** |
| error RMS, straight (\|des\| < 0.3) / curve (0.3–1.5) | 0.079 / 0.161 | 0.088 / 0.186 | **0.142 / 0.320** |
| error RMS, v 20–25 / 25–33 | 0.093 / 0.092 | 0.107 / 0.133 | 0.158 / **0.204** |
| desiredCurvature − curvature RMS (× v²) | 0.089 m/s² | 0.115 | **0.201** |
| steering angle power 0.1–0.5 / 0.5–2 / 2–4 / 4–8 Hz (deg²) | 0.196 / 0.044 / 0.0006 / 0.0011 | 0.830 / 0.114 / 0.0009 / 0.0015 | 0.880 / **0.282** / 0.0010 / **0.0008** |
| torqueState.i: \|i\| p50 / p90 / max; signed p50 | 0.173 / 0.337 / 0.358; +0.173 | 0.228 / 0.397 / 0.424; +0.228 | 0.172 / **0.239** / 0.282; +0.172 |
| i drift: first vs last third (all-engaged signed p50) | +0.122 / +0.098 (+0.126) | +0.388 / +0.089 (+0.108) | +0.150 / +0.181 (+0.130) |
| friction-term input \|error + 0.22·jerk\| p50; saturation fraction (> 0.30) | 0.046; **0.012** | 0.054; **0.020** | 0.101; **0.106** |
| \|output\| p50 / p90 (torque units); 0xE4 \|cmd\| p50 / p90 | 0.016 / 0.040; 2 / 140 | 0.019 / 0.047; 21 / 196 | 0.023 / **0.069**; 22 / **329** |
| \|p\| p50 / \|f\| p50 (lat-accel units) | 0.026 / 0.227 | 0.031 / 0.252 | **0.060** / 0.197 |

Readings (EVIDENCE for the numbers; BELIEF where marked):
- **Lane-keeping error roughly doubled** (RMS 0.093–0.117 → 0.196; straight-road stratum 0.079–0.088 → 0.142, 1.6–1.8×), and the
  0.5–2 Hz steering activity rose 2.5–6× (0.044/0.114 → 0.28 deg²), while the 4–8 Hz activity fell. BELIEF: this is the expected
  price of a 0.37× outer gain — the P term now carries the correction (|p| p50 0.026 → 0.060) at twice the error. ⚠ r34's roads are
  curvier than r32's (0.1–0.5 Hz angle power 0.88 vs 0.20; r33 0.83), so the r33 column is the fairer comparison: still 1.6–1.7×.
- **Centring is unchanged**: i sits at the same +0.17 signed p50 (road crown / device roll on the operator's usual roads), p90 lower
  (0.24 vs 0.34/0.40), no drift within the route.
- **The friction term now saturates 10.6 % of the time** (was 1–2 %) because its input (the error) doubled; with friction 0.03 the relay
  is ±0.03 torque = ±123 counts, so the saturation is harmless. Before, the ±0.212 relay (±868 counts) saturated 1–2 % of the time.
- **The command is larger, not smaller** (|cmd| p90 140/196 → 329): the feedforward is divided by LAF (2.11 vs 1.689, −20 %) but P·error
  doubled; net |output| p90 0.040/0.047 → 0.069.

## 4. Backcalc refit of the car on r34 (control — same firmware, EVIDENCE)

| build (route) | n | OLS slope @0.2 s (r) | IV slope (lag 0.2 / 0.5 / 0.8) | FIR DC (cum. 0.2 / 0.5 / 1.0 / 1.5 s) | 1st-order K, τ, Td | coulomb (tq) | hyst (tq) | intercept |
|---|---|---|---|---|---|---|---|---|
| V280r2 r32 (old) | 3063 | 4.37 (0.62) | 8.31 / 8.32 / 7.89 | 10.81 (0.92 / 4.00 / 7.48 / 10.81) | 12.4, 1.0 s, 0.10 s | −0.006 | 0.013 | −0.26 |
| V280r2 r33 (old) | 2412 | 3.78 (0.56) | 9.40 / 8.86 / 7.59 | 9.62 (0.51 / 3.65 / 6.73 / 9.62) | 11.5, 1.0 s, 0.10 s | −0.008 | 0.030 | −0.32 |
| **V280r2 r34 (new tune)** | 1731 | 5.24 (0.71) | 7.66 / 8.40 / 7.64 | **10.28** (0.28 / 4.13 / 7.67 / 10.28) | 11.2, 0.70 s, 0.15 s | −0.020 | 0.043 | −0.23 |

Spectral |P(f)| (vm100): 9.2 / 4.9 / 3.8 / 2.4 / 1.75 / 1.72 at 0.1 / 0.2 / 0.3 / 0.5 / 0.7 / 1.0 Hz (r32 11.2 / 7.7 / 5.4 / 4.0 / 3.1 / 2.5;
r33 10.7 / 7.5 / 4.7 / 3.0 / 2.5 / 2.3). **The car reads the same: DC LAF ≈ 10 (FIR 10.3 vs 9.6–10.8), IV 7.6–8.4 vs 7.6–9.4, deadband ≈
0.02–0.04 tq, integrator-like plant.** torqued still cannot validate (buckets [0, 0, 9, 823, 843, 27, 0, 0], points frozen at 6653), so
the toggles are the only thing that changed. Note the 7–8 Hz |P| column now reads 1.4–1.6 with coh 0.87–0.93 (was 0.8–0.9): with Gc at
0.41, 1/Gc = 2.4 — the closed-loop artefact moved with the controller, as the baseline said it would (BELIEF, consistent).

## 5. What this licenses (BELIEF unless marked)

- The outer-loop verdict of the r32/r33 report stands: **the lane-change ring is openpilot's command gain at the column's 7–8 Hz
  resonance; lowering that gain 0.37× on the openpilot side removed it with no firmware change** (EVIDENCE for the removal on 2 lane
  changes + 88 s of highway; the ring count is under-powered and a longer highway drive with ≥ 5 hands-off lane changes at 25–30 m/s
  is the confirmation). The V280 rev 2 map's low-idx slope is still 1.9–3.6× V112's; the firmware-side alternative (map back to stock
  slope below idx ~64) remains untested.
- **The cost is tracking**: error RMS ~1.7–2× and 0.5–2 Hz steering activity 2.5–6× higher. If the operator reports "wandering" or
  "lazy" lane keeping, that is this. Levers that restore tracking without restoring the 7–8 Hz gain: raise LAF further (params.toml,
  since the toggle max is 2.53) so the feedforward does the work instead of P; the backcalc says the car's DC LAF is ≈ 10.
- The operator's own report of the drive (smooth lane changes or not) is the primary readout; the instrument says the band is gone.

## Files
`lanechange_r34.py`; `LANECHANGE-r34.txt`, `LANECHANGE-r34-windows.txt`, `lanechange_r34.json`; `_scratch/_ha_75604b0a432fdc89_00000034--e2d2d5381f.npz`,
`_scratch/_lc_r34.npz`; `analysis-2020accord/studies/optune/_scratch/r34_backcalc.npz`, `backcalc_out_r34.txt`, `backcalc_results.json` (r34 merged in).
Addendum §6: `curve_oversteer_r34.py`, `CURVE-OVERSTEER-r34.txt`, `curve_oversteer_r34.json`.

---

## 6. ADDENDUM — the operator's r34 note: "the car oversteers on everything outside of a straight lane" (curve tracking, `curve_oversteer_r34.py`)

Operator, on r34: highway lane changes feel better, but *"the car oversteers on everything outside of a straight lane"* and *"oversteering feels
related to the variable steer ratio"*. Script `curve_oversteer_r34.py` (raw `CURVE-OVERSTEER-r34.txt`, `curve_oversteer_r34.json`), backcalc grids.
CURVE = latActive & active & hands off & |desiredLateralAccel| > 0.3 m/s² for ≥ 1.5 s; ENTRY = first 1.0 s, STEADY = 1.5 s → end. Signed overshoot
(+ = more lat accel than asked, in the curve's direction) on three instruments: **m** = the controller's `actualLateralAccel` (angle → vehicle
model, SR 16.1 on r34 / 14.0 on r32–r33), **v·yaw** = livePose calibrated yaw × v (the true path lat accel, no roll term; straight-road bias
−0.03), **pose** = v·yaw − g·sin(roll_device) (torqued's; carries a −0.29…−0.43 crown/roll bias on straight road, so it is NOT used for the
verdict — it is in the txt for completeness). Counts: r32 21 curves / 81 s, r33 23 / 77 s, r34 30 / 129 s. EVIDENCE unless marked.

### 6.1 Sign and size of the tracking error (medians over curves; v·yaw is the true instrument)

| | r32 old | r33 old | **r34 new** |
|---|---|---|---|
| ENTRY (first 1 s): v·yaw − des / m − des | −0.030 / +0.065 | −0.018 / +0.032 | **−0.008 / +0.014** |
| STEADY: v·yaw − des (rel, \|des\| > 0.5) | −0.012 (+2 %) | +0.041 (+7 %) | **+0.047 (+6 %)** |
| STEADY: m − des (rel) | +0.072 (+13 %) | +0.126 (+16 %) | +0.056 (+8 %) |
| STEADY f / p / i (lat-accel units, on dir) | +0.048 / −0.063 / 0.000 | +0.158 / −0.291 / −0.034 | **+0.615 / −0.115 / −0.005** |
| FF share f/(p+i+f), steady | 0.88 | 0.49 | **0.85** |
| P fights f / I fights f (fraction of steady frames) | 0.56 / 0.40 | 0.75 / 0.50 | **0.80 / 0.77** |
| integrator excursion in-curve / 63 % time | 0.034 / 1.2 s | 0.049 / 0.6 s | **0.115 / 1.6 s** |
| aligned mean trajectory, v·yaw − des at t = 0 / 0.5 / 1 / 2 / 3 s after entry (curves ≥ 3 s) | −0.10 / −0.05 / −0.04 / −0.09 / +0.04 (n 12) | −0.08 / −0.04 / +0.02 / +0.05 / +0.10 (n 8) | **−0.08 / +0.03 / +0.07 / +0.08 / +0.14 (n 17)** |

- **There is no entry spike.** On all three routes the true lat accel LAGS the request at entry (−0.08…−0.10 at t = 0). On r34 it catches up in
  ~0.4 s (old tune: 1–3 s) and then **sits +0.07…+0.14 m/s² above the request from 0.5 s to 3 s** (+10–20 % of a 0.5–0.8 m/s² request); on r32 it
  never exceeds +0.04 within 3 s. So the operator's "oversteer" is a **sustained post-entry excess, not a transient**, and the new tune is also
  simply faster into the curve.
- **The controller's own instrument disagrees with the road.** m − des is POSITIVE on every route (+8…+16 %): the vehicle model says "too much"
  at the same moment the yaw says "about right" (old tune) or "+6 %" (new). On the 14.0 model m read ~19 % above v·yaw at |angle| < 20°; on the
  16.1 model it still reads ~10 % above (understeer-gradient / stiffness term in `VM.calc_curvature`, BELIEF). P and I therefore FIGHT the
  feedforward on every curve, on every tune — what changed is how much pull-back the fight produces.
- **Decomposition, r34 steady:** f = +0.62 (85 % of the sum), p = −0.12 sustained against it 80 % of the time, i winds against it too (77 %) but
  slowly (excursion 0.12, 63 % time 1.6 s; ki 0.15). On the old tune the friction relay ±0.212·LAF = ±0.36 lat-accel units flipped against the
  error within ~100 ms, which is why r32/r33's median f is only +0.05/+0.16 (relay subtracted from FF) and P shows −0.06/−0.29.

### 6.2 The discriminator: overshoot by |steering angle| and by speed (frame-pooled, all curve frames; v·yaw − des, rel at \|des\| > 0.5) [s]

| \|angle\| bin | r32 old (model 14.0) | r33 old (model 14.0) | **r34 new (model 16.1)** | ratio prediction old / new |
|---|---|---|---|---|
| 0–20° | −0.010 (+1 %) [53] | −0.026 (0 %) [37] | **+0.047 (+5 %) [54]** | −13 % / 0 |
| 20–50° | −0.095 (−14 %) [1] | −0.032 (+24 %) [6] | **+0.011 (+1 %) [32]** | −13 % / 0 |
| 50–120° | +0.017 (+2 %) [6] | +0.028 (+5 %) [11] | **+0.088 (+7 %) [14]** | ~−5 % / +4 % |
| > 120° | +0.110 (+7 %) [10] | +0.048 (+5 %) [12] | **+0.230 (+16 %) [15]** | ~0 / +7…+23 % |
| speed 0–10 m/s | +0.064 (+5 %) [18] | +0.021 (+5 %) [29] | +0.031 (+6 %) [69] | |
| speed 10–20 m/s | +0.001 (+2 %) [36] | −0.024 (+2 %) [15] | **+0.064 (+24 %) [36]** | |
| speed 20–30 m/s | −0.026 (−12 %) [17] | −0.030 (−5 %) [18] | −0.045 (−12 %) [8] | |
| across curves: steady v·yaw − des vs \|angle\|max | +0.0012/deg (r +0.80) | +0.0003/deg (r +0.26) | **+0.0015/deg (r +0.58)** | |
| across curves: entry v·yaw − des vs \|des\|max | +0.04 (r +0.18) | +0.21 (r +0.62) | **−0.03 (r −0.09)** | |

**Which pattern (EVIDENCE for the numbers, BELIEF for the attribution):**
1. **Highway (20–30 m/s, < 10°): no oversteer on any tune** — r34 reads −0.045 (slightly UNDER), the same as old. Consistent with "lane changes feel
   better".
2. **Ordinary curves at 10–20 m/s, |angle| < 20° (the operator's "everything outside a straight lane"): the new tune over-delivers by +0.06 m/s²
   (+24 % of a ~0.4 m/s² request); the old tune read 0.** The ratio hypothesis predicts ≈ 0 here on 16.1 (the rack IS 16.1 below 50°), so **this
   part is NOT the ratio.** It is the weak-P regime: f ≈ des/LAF over-delivers, P pulls back only 0.6·e/2.11 = 0.28 torque per m/s² of error
   (the old friction relay pulled 0.71 per m/s² up to ±0.212 torque within 100 ms) and I takes ~5 s. Entry over-delivery ∝ |des| is NOT seen
   (slope −0.03, r −0.09) — the excess is sustained, not an entry FF spike; the orchestrator's mechanism (friction removal exposed the FF error)
   fits the sustained form, the "within 100 ms" part does not.
3. **Hairpins / parking-lot turns > 120° at 2–6 m/s: +16 % on r34 vs +5–7 % on the old model** — the ratio-shaped signature (predicted +7 % at 120°,
   +23 % at lock for a 16.1 model against an effective 15.0→13.1 rack), and the r34 − old difference (+9–11 %) is what 16.1/14.0 = +15 % leaves
   after the rail. ⚠ Confounded: every one of these curves has the output pegged at ±1.0 (LSF ≈ 25–40 at 2–4 m/s multiplies the error, p = −3.0
   against f = +1.0) — the 0xE4 command is railed at 4096 and the ×6 map delivers whatever the rail gives; the old model also grew with angle
   (r32 +0.0012/deg, r +0.80) where the ratio story predicted ≈ 0. So the angle growth is partly the rail regime on both tunes and partly the
   ratio on r34.

### 6.3 What the operator can turn without a params.toml edit (EVIDENCE from the Dom source @ 3d4c625de)

- **No feedforward-scale toggle exists for the Accord.** The only Accord FF scale is hard-coded: `get_honda_accord_ff_scale(setpoint)`
  (`latcontrol_vehicle_tunes.py:2109`) = 1 − 0.10·sigmoid((|a_des| − 0.45)/0.12) — a fixed 10 % taper above 0.45 m/s², constants
  `HONDA_ACCORD_TURN_FF_{REDUCTION_MAX,ONSET,WIDTH}` at lines 79–81. `torque_ff_scale_pos/neg` (the HondaLateralPidKp/KiScale fields) are
  applied only `if self.is_bolt` (`latcontrol_torque.py:175–180`) — inert on this car.
- **`SteerRatio`** (0.5–1.5 × 16.33 = 8.2–24.5; `starpilot_variables.py:760`): when explicit (≠ CP by > 0.01, and ForceAutoTuneOff) the
  14/16.33 scale is skipped (`controlsd.py:469–478`), so **SteerRatio 14.0 reproduces the old vehicle model exactly**; ~15.0 splits the
  large-angle error (m per degree +7 % vs the 16.1 setting). This is the only lever for regime 3; it does nothing for regime 2 (angle < 20°).
  A speed- or angle-dependent ratio needs code — the hook is `get_honda_accord_steer_ratio_scale(v_ego)`, currently a constant.
- **`SteerLatAccel`** (max 1.5 × 1.689 = 2.53): FF = a_des/LAF, so 2.11 → 2.53 cuts the feedforward 17 % everywhere, including regime 2, at the
  cost of P doing more (tracking error already 2× the old tune, §3). The car's DC gain is ≈ 10 per unit torque (§4), so 2.53 is still ~4× low.
- **`SteerFriction`** back to 0.08–0.10: restores a third-to-half of the old relay trim (friction/0.30 = 0.27–0.33 vs 0.71) that masked the FF
  excess; outer gain at the 7–8 Hz line becomes ~0.55–0.60× old instead of 0.37× (BELIEF: the ring stays down — r32/r33's margin was ~2.7×).
- **`SteerOffset`** = latAccelOffset: a constant subtracted from FF (`latcontrol_torque.py:296`, faded by roll_offset_fade) — not a scale; useless here.
- Nothing in `starpilot_variables.py` scales curvature or a_des for the Accord; the LSF table (`LOW_SPEED_X/Y`) is code.

**Recommendation (BELIEF):** for the operator's complaint at road speeds (regime 2) try `SteerLatAccel 2.53` first, then `SteerFriction 0.08`
if the excess persists; for the hairpins (regime 3) `SteerRatio 15.0` (or 14.0 to restore the old model) — and read the same three bins on the
next route. The instrument is already on the wire (livePose yaw, torqueState).
