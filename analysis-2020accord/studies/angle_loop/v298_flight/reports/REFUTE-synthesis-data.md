# REFUTE (data): the route-79 V298 synthesis, attacked from the caches

**Target:** `docs/scoring/DRIVE-READ-V298-r79-2026-10-02.md` (top-ranked mechanisms, the R1/D-sign ruling, every decision-bearing number).
**Script:** `analysis-2020accord/studies/angle_loop/v298_flight/refute_synth_data.py`. **Measured wall time 1.1 s inside the script, 2.6 s including the Python start.** It reads only the caches `r79_a1f5d2_al.npz`, `r79_fork.npz`, `r6c`, `r39` and `r71b_v294`. It is vectorised: FFTs over stacked segments, `sosfiltfilt`, `cumsum`, `searchsorted`; there is no per-sample loop. It is independent of `judge_verify*.py` and of the M1–M6 code.
**Outputs:** `_scratch/out/r79/refute/refute_synth_data.{txt,json}`.
**Labels:** EVIDENCE means it survives my attack with my numbers. BELIEF means it does not reproduce within 10 %, or it rests on one method or one modelling choice. I score bands; **the operator scores the symptoms.** Nothing here proposes a design.

**Conventions, re-checked from the data:**
- Wire 0x18F torque = −`cs_tq`: corr −1.000 at lag 0. So gp-0x4f60 = −bar.
- w18 = −rate/8 has the sign of dθ/dt: corr +1.000 with `cs_rate` and +0.982 with dθ/dt.
- θsp = −raw/10. The 0x1AB field decodes as sign bit 9, |T|/8 in bits 0–8, so the LSB is T/8.
- The fork limiter pairs carOutput[i] with carState[i−1]. The max excess over the clip is +0.0000° for i−1, −0.0011° for i, and +5.6° for i−2.

---

## 1. Verdict table: each attacked claim

| # | synthesis claim | my number(s) | method | verdict |
|---|---|---|---|---|
| 1 | **D opposes motion in every band; R1 "INVERTED" withdrawn** | **Two-input FRF tap←(raw, θ):** D/P > 0 in **100 % of the 1–5 Hz bins in all five speed bands**. D/P is ×0.87 / 0.87 / 0.58 / 0.88 / 0.55 of design at <5 / 5–8 / 8–12.5 / 12.5–22 / >22 m/s; pooled ×0.86, which is c_D ≈ +0.49 tap/(deg/s). Moving raw ±10 ms against θ gives pooled ×0.73–0.94. **Time domain** (1–6 Hz, three ω sources): c_D +0.37 to +0.48 at the best-R² lag of +30/+40 ms. It is positive for every lag from −20/−40 ms to +100 ms, and negative only when the tap is assumed to lead the angle by ≥ 30–50 ms. | The FRF ratio cancels every LTI operation on the tap alone (output-lag pole, delay, ZOH, packer age, fade), which is the confound every time-domain regression shares. Three ω sources in the time domain. | **SURVIVES** (EVIDENCE). The sign is robust to the timing confound. The magnitude is **below design in every one of my estimators** (×0.55–0.88), weakest at 8–12.5 and above 22 m/s. |
| 2 | c_meas/c_raw = **−1.00 [−1.01, −1.00]** (M1 windowed replay) | FRF Re(H_θ/H_raw)/10 = 0.62 / 0.85 / 0.81 / 0.65 / 0.92 by band. Under ±10 ms raw/θ timing it spans 0.41–0.97. | FRF, 1–5 Hz | **Sign survives; the tight CI does not** (BELIEF). The −1.00 rests on one replay model. The raw-vs-θ timing within a 10 ms CAN batch is not identifiable from logMonoTime. |
| 3 | **Ki live at design strength, c_I/c_P 2.8 /s, "2.5–2.9 per band"** | Time domain (per-episode integral, tap +30 ms): **<8 m/s 0.95 (0.1–3 Hz) / 1.18 (0.3–3 Hz)**. 8–12.5: 2.81 / 2.90. 12.5–22: 2.50 / 2.77. >22: 2.45 / 2.91. Pooled >5: 2.59 / 2.55. FRF phase fit (PI + image lag pole 31.5 ms + delay): pooled 1.6 /s, per band 1.3–1.7 below 12.5 m/s. | Two methods | **Pooled and ≥ 8 m/s: survive** (EVIDENCE, within 4–12 %). **Below 8 m/s: REFUTED.** The integral the route delivered there is 1.0–1.2 /s, **0.34–0.42× design**. That is closer to the instrument's "half strength" (1.24) than to 2.8. M3 attributes the gap to freeze duty (its effective value is 1.45–1.62); I cannot separate the gain from the freeze here. |
| 4 | Camera: commanded 3906 frames in 2 episodes with arm 0; forwarded to bus 0; none on bus 1 after 38.39 s | `e4cam_req` 3906, arm {0}, 2 episodes (326.9–981.9 s), fork latActive on **100 %** of them. `e4tx0_req` 3906. Last `e4rx1` at 38.39 s, 0 after 39 s. 24 rejects on bus 1, all at start-up or shutdown. | Counts | **SURVIVES** (EVIDENCE). "Forwarded" is inferred from the src-128 TX echo count. The prerequisite was violated, and the EPS bus never saw the camera's 0xE4. |
| 5 | Error clip binding **0.10 %** of latActive time; M5's "never" is a pairing error | Binding 0.10 % overall, 0.30 % at <5 and 0.38 % at 5–8 m/s. Pairing i−1 confirmed (see the conventions above). | Recompute | **SURVIVES** (EVIDENCE) |
| 6 | O1: 415 episodes, 100.8 s, 15.1 % of latActive, 345 of 415 never pressed, 41.5 / 36.4 % below 5 / 5–8 m/s, 63 % of hard time | 415 · 100.75 s · 15.09 % · 345 · 41.5 / 36.5 % · **63.8 %** of hard time. **Validated:** co_ang equals clip(θ + 0.06 ω, ±emax) on **100 %** of reconstructed O1 frames with pairing i−1, and 95.95 % with same-row pairing. | Reconstruction plus a check against the fork's own output | **SURVIVES** (EVIDENCE) |
| 7 | **Note 2 #1: the 120 deg/s cap binds on 50–52 % of hands-off hard frames (61–67 % below 8 m/s), as a mechanism separate from O1** | The number reproduces: **53.5 %** overall and **67.6 %** below 8 m/s. **But 73.4 % of all cap-binding frames, and 70.1 % of those in hands-off hard time, fall within 0.3 s after an O1 release.** That window covers only 10.6 % of latActive time, so cap frames are **×7 enriched** in it. The fork resets `apply_angle_last` to the wheel at the O1 release (`carcontroller.py` `_update_angle`), and the limiter then re-slews toward the plan at 1.2 deg/frame. Cap binding with no O1 involvement is about **8 s of the 668 s** latActive. | Recompute plus an O1-release census | **Number: EVIDENCE. Ranking as an independent #1: REFUTED** (BELIEF). The cap is mostly the **second half of the O1 relay**, so it cannot be ranked apart from #2. |
| 8 | "The firmware follows what it receives: peak reach 0.998, rate 0.98, ≈ 100 ms behind"; "the driver feels a rate ceiling, not a torque ceiling" | On 84 cap runs of ≥ 100 ms (median 0.12 s, setpoint travel 14.4°), the wheel covers **0.37** of the setpoint travel during the run and **0.80** by 100 ms after it. On cap frames: \|θsp − θ\| p50 **5.5°**, p90 11.1°, under 3° on only 23 %. Wheel rate p50 **45 deg/s** against the setpoint's 120. The tap on cap frames is p50 **50**, p90 97 and max 177 LSB, which is 16 % / 32 % / 58 % of the 307.6 rail. | Event census | **REFUTED for slews** (BELIEF). While the cap binds, the wheel is not at the ceiling. It lags the setpoint by ~5° and the lane delivers ~16 % of the rail. **The capped setpoint is not what the wheel delivers; the error the loop lets build × the stiffness is.** "Reach 0.998" may hold for whole events (M6's metric), but it does not describe the slew. |
| 9 | C3: demand beyond the clip on 49–55 % of hands-off hard frames below 8 m/s | 51.4 % below 8 m/s; 31.7 % of all latActive time below 8 m/s. **73.8 % of it is post-O1 release.** | Recompute | **Number SURVIVES** (EVIDENCE). Most of it is the same O1 re-slew, so "lifting the cap exposes the clip" is partly an O1 statement. |
| 10 | Tap peak 183 LSB (59–60 % of the rail), p99 108, 0 frames ≥ 300; references 244 / 207 / 183 | r79 peak 183, p99 108, p99.9 141, ≥ 250: 0, ≥ 300: 0. r6c 244 / 106, r39 207 / 127, r71b 183 / 115. | Native 50 Hz instants | **SURVIVES** (EVIDENCE). The tap is the lane torque only; downstream clamps (EME, governor) are invisible to it. |
| 11 | Bar pinned on 59.7 % of engaged time, 42.5 % without roll, \|corr\| with \|tap\| 0.14, P(bar ≥ 0.9 \| tap < 25) 0.60 | 0.597 · 0.425 · 0.135 · 0.604. With the UI's FirstOrderFilter (rc 0.1 s), pinned ≥ 0.95 on 0.612. The source formula in `torque_bar.py` `TorqueBar._update_state` reduces to (desired lat accel − roll·g·interp(v, [5, 15], [0, 1])) / 0.3247. | Source formula, recomputed | **SURVIVES** (EVIDENCE) |
| 12 | Hands-off torque word p90 607–681 below 8 m/s | 607 / 674 (<5 / 5–8 m/s); > 512 on 13.6 / 15.1 %; > 614 on 9.9 / 11.7 % | Recompute | **SURVIVES** (EVIDENCE) |
| 13 | Freeze duty: hard 5.1 %, opposing 6.3 % | 5.1 % / 6.2 %. The flipped-sign rule would give 1.1 %. | Rule applied at 100 Hz | **SURVIVES** (EVIDENCE for duty). Which sign is live rests on M3's replay model selection alone. |
| 14 | 31 % of commanded integration discarded hands-off, 42–48 % below 8 m/s | **26.0 % / 36.9 %**, weighting by \|E·G\| under the hand rules only (no A3) | Vectorised census | **Not within 10 %** (BELIEF on the magnitude; −16 % and −12 to −23 %). The direction survives. The weighting differs from M3's replayed \|inc\|. |
| 15 | The freeze lands while \|e\| is closing (mean d\|e\|/dt −4.4 deg/s) | −17.5 deg/s frozen against +2.2 free | 100 Hz gradient | **Sign SURVIVES**; the magnitude does not reproduce (noisy derivative). |
| 16 | "I hard-frozen on 94 % of O1 frames" | — | — | **Vacuous.** O1 turns on at 614 gp, above the 512 hard freeze, and releases at 512 gp, the freeze threshold. The figure is entailed by the two thresholds and carries no information. |
| 17 | Tracking >22 m/s **0.895 FAIL** (pre-registered, "not decisive") | Hands-off, eroded mask, whole-series 0.5 Hz filtfilt: **0.978–0.987** (with intercept / through zero, ≥ 25 m/s 0.984). Dropping the last 1 s of each run gives 1.003. 8–15 m/s 1.010, 15–22 m/s 0.980. | An independent filter and mask | **The verdict does not reproduce** (BELIEF). Mine is a PASS on 86.7 s. The instrument's per-run filtfilt places a filter edge at the band exit, and the FAIL sits on that edge (the judge's drop-last-1 s = 0.951). The value differs by 9.5 %, but the verdict flips. |
| 18 | Note 4 #1, the ratchet: in-turn 4–8 Hz rate rms 7.09 at 5–10 m/s against V282 4.79–5.50 | Mine (engaged, \|0.5 s mean w18\| ≥ 10): r79 **6.48**; r6c 4.12, r39 3.74, r71b 2.84. At 0–5 m/s: r79 4.74 against r6c 4.82 and r39 3.65, **no excess**. **Away from O1** (> 0.3 s from any O1 frame): r79 **2.50 / 3.06**. **Near O1**: 5.01 / 6.99. O1 lies within 0.3 s of 83–86 % of turning frames. | My own detector, cross-route | **Direction SURVIVES at 5–10 m/s** (×1.6–1.7 the references), and the excess sits **only near O1**: away from it, r79 is *below* V282. The magnitudes differ from M4 by more than 10 % (references by 14–32 %). **The 0–5 m/s "3.1 trains/min" has no matching 4–8 Hz energy excess.** The trains are n = 9 on a detector defined on r79: single method. |
| 19 | The R3\* event at 1089.4 s is not a ring | 1088.6–1090.2 s: θ 8.6° → 1.4° with **0 upward steps**; w18 > +0.25 deg/s on 0.6 % of frames; \|bar\| ≤ 223 | Recompute | **SURVIVES** (EVIDENCE) |
| 20 | 0x14A-to-tap timing: "the torque word leads 0x18F by 10 ticks" | Not attacked directly. My FRF phase fit gives a **15 ms** pure delay on top of the 31.5 ms image lag pole (8–20 ms by band). The time-domain best lag is +30/+40 ms. | — | **Single method in the synthesis** (M3 replay scan). Not decision-bearing for the D sign, because the FRF cancels it. |

---

## 2. Where the synthesis breaks, decision-bearing

1. **Note-2 mechanism #1 (the rate cap) is not independent of #2 (O1).**
   - 73 % of the time the 120 deg/s cap binds is the 0.3 s after an O1 release, when the fork re-slews from the wheel back to the plan. That window is ×7 enriched over its base rate.
   - The cap binding for planner demand alone is about 8 s of the drive.
   - The ranking "rate cap #1, O1 #2" should read: **one O1 relay mechanism (snap to the wheel, then re-slew at the cap)**, with independent cap binding a small residual.
   - A design that raises `MAX_ANGLE_RATE` without touching O1 changes the second half of each relay cycle. On r79 it would mostly re-slew harder after each O1 release. That consequence is BELIEF, not measured.
2. **"The EPS follows the capped setpoint" is false during the slews that matter for note 2.**
   - On cap runs the wheel makes 0.37 of the setpoint's travel, lags by 5.5° (p50), moves at 45 deg/s, and the lane delivers 50 LSB (16 % of the rail).
   - What limits the wheel during a slew is the **stiffness × the error the fork allows**: the cap stops the error from building, and the gain converts a small error into little torque.
   - That fits the integral at 0.34–0.42× design below 8 m/s, D at 0.55–0.88×, and C8's 0.4–0.6 Hz bandwidth.
3. **"Ki at design strength in every band" fails below 8 m/s**, where notes 2 and 4 live.
   - By two methods, the effective integral there is 1.0–1.2 /s (time domain) and 1.3–2.0 /s (FRF).
   - The synthesis's own C6 / M3 effective-strength numbers (1.45–1.62) point the same way, but its headline line in §1 does not.
4. **The >22 m/s tracking FAIL does not reproduce** under an independent filter and mask (0.978–0.987). It is a filter-edge artefact on the instrument's per-run filtfilt.

## 3. What survives the attack

These are the strongest items on the page:
- the D sign, by the timing-immune FRF;
- the camera finding;
- the O1 reconstruction, validated against `co_ang` on 100 % of frames;
- the 0.10 % clip binding;
- the tap peak and rail;
- the bar formula and its pinned share;
- the freeze duty;
- R3\* not being a ring.

---

## 4. My re-ranked mechanisms (strength = evidence that it acts on r79; that it is what the operator *felt* is BELIEF)

| note | rank | mechanism | strength |
|---|---|---|---|
| 1 | 1 | A stable, damped loop. D opposes in every band (FRF, 100 % of bins) at ×0.55–0.88 of design. No ring; R3\* is monotone. | strong |
| 2 | 1 | **The O1 relay as one mechanism:** a 600/500 raw trip (345 of 415 episodes without steeringPressed), a snap to the wheel, then a re-slew at 1.2 deg/frame. It accounts for 73 % of cap binding and 74 % of demand beyond the clip, and covers 63.8 % of hard time. | strong |
| 2 | 2 | **Low loop stiffness at low speed**, while the fork caps the error. During slews: err 5.5°, tap 50 LSB, wheel 0.37 of setpoint travel. Effective integral 0.34–0.42× design below 8 m/s. D ×0.55–0.88. The peak tap is 59 % of the rail. | strong |
| 2 | 3 | Freeze duty (hard 5.1 %, opposing 6.2 %), discarding 26 % of integration hands-off and 37 % below 8 m/s | moderate |
| 2 | 4 | The 120 deg/s cap on planner demand alone, ≈ 8 s of the drive | weak |
| 2 | ✗ | The rail or clamp (0 frames ≥ 250 LSB); the error clip (0.10 %) | ruled out |
| 3 | 1 | The bar = (desired lat accel − roll) / 0.3247, pinned on 59.7 % (61 % filtered); \|corr\| with \|tap\| 0.135 | strong |
| 3 | 2 | Roll drives it on straights (42.5 % pinned without roll, 59.7 % with) | strong |
| 4 | 1 | O1-neighbourhood 4–8 Hz modulation at 5–10 m/s: 6.99 near O1 against 3.06 away; references 3.7–4.1 | moderate. The association is strong; the causal direction (O1 → modulation, or reaction twist → O1) is undecided. |
| 4 | 2 | The small-correction stick (M4) | moderate (not attacked) |
| 4 | 3 | Freeze chatter at 300/512 | weak |
| 4 | ✗ | A ring; inverted D | ruled out |

## 5. Out of scope, noticed
- The FRF's Re(H_θ/H_raw) of 0.62–0.92 × 10 suggests the raw and θ paths into the tap are not in the exact ratio 1:10 at 1–5 Hz. One candidate is the firmware's 100 Hz θ hold against a raw read at 1 kHz; another is the batch timing. This was not pursued.
- My time-domain D at 0.1–3 Hz drops to +0.03 at 8–12.5 m/s. Low-frequency D estimates are fragile, so do not size a D change from them.
- The single-stall and train detectors are defined on r79 (n = 9 trains). The 4–8 Hz-near-O1 split above is a detector-free cross-check that the next flight should carry.
