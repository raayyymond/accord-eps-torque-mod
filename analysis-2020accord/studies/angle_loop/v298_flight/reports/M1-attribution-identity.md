# M1: which build ran on route 79, whether the angle loop is live, and which way the D term acts

**Wall times (measured):** `m1_loop_identity.py` 20.3 s · `m1_attrib_interlocks.py` 0.55 s · `m1_integrator_track.py` 1.7 s.
All three run on the caches only. None of them reads an rlog. The only per-tick Python loop is the exact-integer validation, which runs on 3 windows × 5 s.

**Route:** 79 = `75604b0a432fdc89_00000079--a1f5d2a272`, V298 first flight. Analysis only: nothing was sent, flashed or edited.

**Outputs:** `_scratch/out/r79/m1/m1_{attrib_interlocks,loop_identity}.{txt,json}` and `m1_integrator_track.txt`.

**Labels:** EVIDENCE means measured on the wire, read from the image or read from source. BELIEF means modelled or inherited. Results are score bands only. The operator scores the symptoms.

---

## 0. Answer

| question | result | status |
|---|---|---|
| Which firmware and fork ran | EPS carFw `39990-TVA,A16A` (bus 1). `steerControlType` angle. Fork Dom `2712e133696d…`, `AccordEpsAngleLoop` 1. learned SR pinned at 16.84 | EVIDENCE |
| Is the loop live and the right way round | Yes. The setpoint-to-tap (θsp) and measured-angle-to-tap (θ) paths have equal and opposite gain: **c_meas/c_raw −1.00 [−1.01, −1.00]** pooled, −0.97 to −1.01 in every band. d(tap)/d(θsp−θ) is negative in every band at **0.93–0.96 × the image's predicted P**. | EVIDENCE |
| **The sign of D** | **D OPPOSES motion (the design sign) in every band, by three independent methods.** Measured size is **0.79–0.95 × design**. A clean inversion (d ≈ −1) is **REFUTED** in every band. The pre-registered R1 "INVERTED" verdict in the drive-read came from a regression that cannot identify D (see §3.4). | EVIDENCE |
| Ki | The integrator increments at **0.95–0.97 × design** inside 5 s windows. The drive-read's "integral about half strength" (c_I/c_P 1.24) is an artifact of its integral regressor (§3.4). | EVIDENCE (rate) / BELIEF (cause of the artifact) |
| Replay identity | The image arithmetic reproduces the tap at **R² 0.997–0.999 in every band** once the integrator state is re-anchored once per 5 s. The continuous replay fails only through a slowly varying integrator **offset** that appears after hands-on manoeuvres. At >22 m/s that offset is a constant +24.7 LSB and the scatter is 0.7 LSB. | EVIDENCE |
| Interlocks | STEER_STATUS 0 and 0x14A byte 4 bits 0–2 = 7 on **100 %** of 67 073 engaged frames. **0** 0xE4 counter skips. Fork arm (byte 2 bits 3:2) = 2 on **120 763/120 763** frames. 8 request drops, all deliberate disengages, tap = 0 within 150 ms. | EVIDENCE |
| The camera | Commanded (request = 1) on **3906 frames in 2 episodes**: 326.9 s for 19 s and 961.9 s for 20 s, all while the fork was engaged, with arm = 0. **The panda did NOT block those frames. It forwarded all 3906 to bus 0** (radar side), byte-identical. **None reached bus 1, the EPS's bus.** The drive-read's wording "blocked by the panda" is wrong. Its consequence, that the EPS never saw the camera's frames, holds. | EVIDENCE (bus 0 / bus 1 facts) / BELIEF (radar disabled) |

---

## 1. (a) Attribution (EVIDENCE: fork cache `carparams_json` / `initdata_params_json`, drive-read extras `meta.carfw`)

| field | value |
|---|---|
| EPS carFw (F181) | `39990-TVA,A16A` plus `\x11L-130520-03461268`. ECU address 0x18DA30F1, **bus 1** |
| carParams | HONDA_ACCORD · steerControlType **angle** · openpilotLongitudinalControl **true** · safety hondaBosch param 3 · maxLateralAccel 0.3247 · steerActuatorDelay 0.15 · CP steerRatio 16.33 · lateralTuning `pid` (the angle controller does not use it) |
| initData params | AccordEpsAngleLoop 1 · GitCommit `2712e133696d1a38c8fc5255e5afb2c92b00737f` · GitBranch Dom · Version 0.11.2 · SteerRatio 16.84 · AccordVariableSteerRatio 1 · AlwaysOnLateral 1 · AlwaysOnLateralLKAS 1 · ForceTorqueController 1 · UseAutoSteerDelay 1 · SteerDelay 0.2 · HondaBoschARadar 1 |
| liveParameters steerRatio | 16.84 for the whole route (min = max) |
| controlsState lateral type | angleState on 100 % of rows |
| GitDiff | not empty. The head shows `common/libcommon.a` and `params_pyx.cpp`, which are build artifacts. The rest is not inspected (open question) |
| Image read for every number below | `_v298_V298-ANGLELOOP.C3REV2P…A16A_plain_image.bin`. F181 at 0x13100 = `39990-TVA,A16A` |

Cells read LE from the built image (EVIDENCE):

- Lane cells: Ki 40 · ICL 8192 · DCL 10240 · PCL = SCL 15360 · output lag oa 992 / ob 507 · fwd 5346 · OCL 3072 · a 0 · b 8192 · C 65535 · DB 0 · Kp 112 ×5 · Kd 48 ×4.
- GB-P rows at 0xC4CDA through the relinked pointer 0xC4C1E: `(714,1178,1041) (1843,1465,−6264) (2304,760,−2033) (2707,560,1570) (4032,1068,2118) (6198,2188,0)`.
- fadeB2 = fadeB (the neutralisation is in the image). fadeA2 Y[0] = 255.
- Ramp cells 0xC63F6..FC = **16 / 33 / 66 / 328**.
- Chain DC gain: f 254, lag DC 0.990, **0.02003 tap LSB per S unit**.
- Design values derived from those cells: **c_D = 0.566 tap/(deg/s)** and **c_P = 5.477e-4 × G tap per wire count**.

---

## 2. (b) Loop identity: is the loop live and the right way round?

### 2.1 Method W: windowed replay of the image's lane arithmetic (independent of the drive-read code)

**The replay itself:**

- It uses its own loader: ZOH by `np.searchsorted` on the raw cache streams, with no de-jitter grid.
- It uses its own reads of the image.
- It runs the lane of design §1.4 at 1 kHz, vectorised: the error E, then E′ = (E·G)>>8, then P, the fresh-rate D (48·abe)>>3, I by `np.cumsum`, the hard and opposing-hand freezes, the fade, and the output lag by `lfilter`.

**The fit:**

- Windows are hands-off (|bar| < 500), engaged, at least 1.2 s after engage, and 5 s long. There are **55 windows**, and none below 5 m/s qualifies.
- The free parameters are one integrator offset I0 per window, plus gains p (on P), d (on D) and i (on the I increments).
- At the design point p = d = i = 1.
- CIs come from a bootstrap over windows (40 draws). The latency scan picked 0.00 s.

**Validation of the vectorised chain against an exact per-tick integer loop:**

| window | A3-bound violation | max \|ΔT\| | rms ΔT | rms T |
|---|---|---|---|---|
| 13.2 m/s | 0 | 0.9 T | 0.30 T | 304 T |
| 31.4 m/s | 0 | 0.9 T | 0.30 T | 32 T |
| 15.6 m/s | 0.56 | 168 T | 101 T | 370 T |

On the third window the A3 bound binds. **The only unmirrored nonlinearity is the state-dependent A3 bound.** The per-window I0 absorbs it in the fits below.

| band | win | R² D=+1 | R² D=0 | R² D=−1 | **p** [CI] | **d** [CI] | **i** [CI] | R² free | **c_meas/c_raw** [CI] | d(tap)/d(θsp−θ) tap LSB/deg |
|---|---|---|---|---|---|---|---|---|---|---|
| 5-8 | 3 | **0.998** | 0.805 | 0.241 | 0.95 [0.94,0.95] | **+0.95** [0.94,1.02] | 0.96 [0.96,0.98] | 0.999 | −1.01 [−1.01,−0.96] | −7.1 |
| 8-10 | 4 | **0.997** | 0.977 | 0.919 | 0.96 [0.94,0.96] | **+0.92** [0.90,1.06] | 0.96 [0.94,0.98] | 0.998 | −0.99 [−1.00,−0.97] | −6.1 |
| 10-12.5 | 6 | **0.999** | 0.990 | 0.966 | 0.95 [0.93,0.96] | **+0.91** [0.83,0.95] | 0.97 [0.96,0.98] | 0.999 | −1.00 [−1.02,−0.97] | −3.3 |
| 12.5-15 | 5 | **0.999** | 0.993 | 0.975 | 0.96 [0.95,0.98] | **+0.92** [0.89,0.98] | 0.97 [0.96,0.98] | 0.999 | −0.97 [−1.02,−0.94] | −3.9 |
| 15-22 | 22 | **0.999** | 0.997 | 0.991 | 0.96 [0.95,0.97] | **+0.93** [0.89,0.96] | 0.97 [0.97,0.98] | 1.000 | −1.00 [−1.02,−0.99] | −5.7 |
| >22 | 14 | **0.997** | 0.994 | 0.986 | 0.93 [0.90,0.94] | **+0.79** [0.71,0.85] | 0.95 [0.94,0.96] | 0.998 | −0.98 [−1.00,−0.95] | −11.0 |
| pooled >5 | 54 | **0.999** | 0.973 | 0.896 | 0.96 [0.95,0.96] | **+0.95** [0.91,0.96] | 0.97 [0.96,0.97] | 0.999 | **−1.00** [−1.01,−1.00] | — |

**What the table means:**

- **Sign:** tap ∝ −S, and S ∝ +(θsp − θ) through P. So the setpoint-to-tap slope is **negative**, as designed.
- **Units:** 1 tap LSB = 8 T. So −5.7 LSB/deg at 15–22 m/s is −45.4 T per degree of error.
- **Magnitude:** P is delivered at 0.93–0.96 of the image's arithmetic. The speed schedule G(v) is live. The slope dips at 10–15 m/s (G 560–760) and is highest at >22 m/s (G 2188), as the GB-P table says.
- **Single-method caveat on the low bands:** 5–12.5 m/s rests on only 3–6 windows. The F and T methods below cover those bands for D.

### 2.2 The continuous replay: no free parameters, I starts from 0 at each engage, ramp-in from the image's 328/tick cell, A3 bound NOT mirrored

| band | n | R² | rms tap | rms resid | **mean resid** | I>>7 replay median | I>>7 implied-real median |
|---|---|---|---|---|---|---|---|
| <5 | 2569 | 0.32 | 41.0 | 33.0 | −7.2 | −175 | −196 |
| 5-8 | 2734 | −0.49 | 40.0 | 42.1 | −24.7 | −1088 | −90 |
| 8-10 | 2979 | −1.66 | 42.2 | 58.3 | −36.6 | −884 | +243 |
| 10-12.5 | 3003 | −3.85 | 23.5 | 47.9 | −19.7 | −654 | −171 |
| 12.5-15 | 1961 | 0.88 | 27.6 | 9.2 | +2.4 | +25 | −55 |
| 15-22 | 9898 | 0.93 | 26.2 | 5.3 | +4.3 | +127 | +43 |
| **>22** | 4611 | **−3.86** | 11.2 | **0.7** | **+24.7** | +1450 | +207 |

- The drive-read's exact march, which does mirror the bound, reports R² 0.757 pooled and −3.1 above 22 m/s.
- At >22 m/s the replay misses by a **constant**: the scatter is 0.7 LSB against an offset of 24.7 LSB.
- `m1_integrator_track.txt` gives the real I. It is fitted every 4 s with P and D fixed at the image arithmetic. **The real I and the replayed I move in parallel** (the same increments), and **they step apart after hands-on, large-angle manoeuvres**:
  - At t 944–952 s (|bar| 2774–2859, angle up to −172°) the gap opens.
  - From 960 to 1040 s at 31 m/s the replay holds about +1200 to +2200 while the real I holds about +30 to +1100.
- So **the replay "fails" on the integrator's long-horizon state, not on the loop structure.**

The real integrator at highway sits at |I>>7| ≲ 1100 S, which is ≲ 22 tap LSB. The A3 bound and the freezes during the hands-on manoeuvres are the candidate cause. That is BELIEF: the drive-read's own exact march, which does have the bound, still reports R² −3.1 there, so the freeze inputs (the gp-0x4f68 word against |bar|) are unproven.

---

## 3. (c) Settling the D sign

The tap is modelled as tap ≈ k[0.02734·G·e_w + 28.27·ω18 + I], with e_w = raw + 10θ = −10(θsp − θ).

- The D gain c_D = 28.27·k = **0.566 tap/(deg/s)** is the design value. **c_D > 0 means D opposes motion.**
- The D-to-P ratio is a pure lead time: τ = c_D / (10·c_P) = **103.4/G s**, which is 47–185 ms across the bands.

### 3.1 Method F: two-input frequency response, raw and θ to tap. Needs no lag model.

**The quantity:** R(ω) = H_θ/H_raw = 1 + jωτ / (1 − jκ/ω), where κ = c_I/c_P.

- Everything downstream cancels in this ratio: the output lag, the transport delay, the CAN and USB timing, and the tap's 50 Hz hold.
- A relative delay δ of 0x14A against 0xE4 only rotates arg R. **|R| measures |τ| independent of δ.**

**The data:** 140 hands-off settled segments of 4 s (Hann window). The fit is over 0.5–5 Hz on a (τ, δ, κ) grid. CIs come from a segment bootstrap with 40 draws.

| band | s | τ design | **τ fit** [CI] | **\|τ\| from \|R\| only** [CI] | δ fit [CI] (s) | κ fit | cost τ>0 / τ<0 | P_boot(τ>0) |
|---|---|---|---|---|---|---|---|---|
| 8-10 | 18 | 0.089 | **+0.070** [0.055,0.085] | 0.065 [0.045,0.080] | +0.002 [−0.008,0.010] | 3.5 | 27 / 227 | 1.00 |
| 10-12.5 | 26 | 0.164 | **+0.130** [0.115,0.165] | 0.130 [0.115,0.171] | −0.002 [−0.008,0.019] | 4.0 | 124 / 970 | 1.00 |
| 12.5-15 | 24 | 0.141 | **+0.125** [0.084,0.150] | 0.120 [0.090,0.181] | +0.002 [−0.016,0.016] | 3.5 | 69 / 552 | 1.00 |
| 15-22 | 122 | 0.095 | **+0.075** [0.065,0.080] | 0.070 [0.060,0.075] | −0.004 [−0.008,0.000] | 3.0 | 6.3 / 66 | 1.00 |
| >22 | 70 | 0.048 | **+0.020** [0.010,0.035] | 0.015 [0.005,0.030] | −0.006 [−0.022,0.010] | 3.5 | 5.7 / 6.4 | 1.00 |
| pooled >5 | 270 | 0.087 | **+0.080** [0.070,0.085] | 0.070 [0.060,0.080] | 0.000 [−0.004,0.004] | 4.0 | 5.3 / 65 | 1.00 |

**Example at 3 Hz, 15–22 m/s:** measured |R| 1.38 at 69°. The design predicts 2.06 at 61°. **An inverted D would put arg R at −61°.**

**What the table shows:**

- The fitted δ is 0 ± 10 ms. It is identified jointly with τ and lies well inside the physical prior.
- At >22 m/s the sign discrimination is weak (cost 5.7 against 6.4) because τ is short there.
- κ, the ratio of integral to proportional gain, fits at 3.0–4.0 /s against a design value of 2.79. The grid step is 0.5, so this is coarse.

### 3.2 Method T: time-domain regression, band-passed. All three regressors pass through the image's lag pole at 100 Hz, and the common latency is scanned.

| band | **2–5 Hz c_D** [CI] | 1–3 Hz c_D [CI] | 0.3–3 Hz c_D [CI] (the drive-read's literal band) |
|---|---|---|---|
| 8-10 | **+0.43** [0.30,0.66] | +0.22 [−0.13,0.38] | +0.26 [−0.11,0.47] |
| 10-12.5 | **+0.54** [0.48,0.59] | +0.56 [0.42,0.63] | +0.34 [−0.02,0.50] |
| 12.5-15 | **+0.52** [0.50,0.55] | +0.55 [0.53,0.59] | +0.49 [0.10,0.77] |
| 15-22 | **+0.57** [0.56,0.61] | +0.57 [0.52,0.62] | +0.24 [−0.22,0.48] |
| >22 | **+0.55** [0.51,0.72] | +0.50 [0.42,0.57] | +0.63 [0.44,0.78] |
| pooled >5 | **+0.46** [0.40,0.58] | +0.39 [0.36,0.50] | +0.10 [0.06,0.35] |

- The design value is 0.566.
- **At 2–5 Hz every band is positive with P_boot = 1.00.**
- At 0.3–3 Hz several CIs cross zero. In that band D is a small quadrature term beside P and I, so the band cannot identify it.
- The c_P from method T is 0.5–0.9 of the prediction. That comes from the crude 100 Hz lag model and is not decision-bearing; method W has the exact chain.

**Timing sensitivity:** shifting the 0x14A stream by ±10 ms, with d(ang)/dt as the D regressor, moves the pooled 2–5 Hz c_D through 0.37 / 0.41 / 0.42. **The sign is unmoved.**

### 3.3 Method W (from §2.1)

- R² ranks D = +1 > D = 0 > D = −1 in **every** band. At 5–8 m/s the three values are 0.998 / 0.805 / 0.241.
- The free d is **+0.79 to +0.95**.

### 3.4 Verdict, and why the drive-read disagreed

**A clean inversion (d ≈ −1 everywhere) is REFUTED in every band by three independent methods (EVIDENCE).**

- **Magnitude:** D is **0.79–0.95 × design** relative to the image arithmetic. In absolute terms c_D ≈ 0.43–0.57 tap/(deg/s), against the design band [0.45, 0.70].
- **Above 22 m/s** D is the weakest, at 0.79 [0.71, 0.85]. The likely cause is that the replay uses the 100 Hz-held rate where the firmware uses the fresh 1 kHz rate after an EMA. That is BELIEF.

**Why the drive-read disagreed (BELIEF, with the measured support named):**

1. Its structural regression carries the **marched integrator** as a regressor. §2.2 shows that integrator drifting away from the real one by up to about 1200 S after hands-on manoeuvres. A slowly wrong regressor drags its coefficient c down to 0.19–0.93 (hence "c_I/c_P 1.24, half strength") and moves the error into P_meas (hence "c_meas/c_raw −0.69") and into d.
2. Its band, 0.3–3 Hz, is where D is unidentifiable. Method T reproduces the scatter there: its 0.3–3 Hz CIs cross zero in 3 of 5 bands.

The decision-bearing R1 therefore fired on an estimator that cannot see D. **The literal reading (−1.08 ratio, c_D +0.566) is the one the windowed replay and the frequency response confirm.**

**What exposure would tighten it:** at least 60 s of hands-off driving per band at 5–12.5 m/s, with 2–5 Hz content in the wheel angle. Mild road texture is enough; the 8–10 m/s band currently has only 18 s. Also a mirror of the fresh 1 kHz rate operand, to explain the 0.79 at >22 m/s.

---

## 4. (d) Interlocks on the wire (EVIDENCE: `m1_attrib_interlocks.py`)

| check | result |
|---|---|
| STEER_STATUS (0x18F byte 4 bits 7:4) while engaged | **0 on 67 073 / 67 073 frames**. Value 3 occurs on 3 frames at 1252.01–1252.03 s (shutdown, not engaged). Byte 4 bit 3 = the wire SCA exactly |
| 0x14A byte 4 bits 0–2 while engaged | **7 on 67 073 / 67 073 frames**. Every 0x14A frame on the route reads 7 |
| carState steerFaultTemporary / Permanent | 1 row at 32.30 s (pre-safety-mode) / 0 rows |
| R8 | **clean** |
| Lateral engaged (request & SCA) | 670.7 s in 8 episodes. Request = 1 with SCA = 0 totals 0.09 s, which is the engage edges |
| 0xE4 frame loss (Honda 2-bit counter on the bus-129 echo) | **0 skips** over 120 763 frames. 120 788 sent − 120 763 echoed − 24 rejected = 1 frame unaccounted for |
| 0xE4 echo spacing | median 9.85 ms. 5315 gaps > 20 ms, of which 2953 fall inside a request, max 42 ms. These are USB-batch receipt jitter: the counter shows no frame missing. The fork's sendcan has 31 gaps > 20 ms, max 42.9 ms |
| 0x14A / 0x1AB gaps | max 1228 ms at 29.12 s, before any engagement |
| panda safetyTxBlocked | 0 → 14 at 38.54 s (start-up: 13 rejected 0xE4 at 38.50–38.64 s, requests 0) and 14 → 8 at 38.67 s (counter reset on the mode change). **8 → 9 at 1040.97 s while engaged at about 31 m/s: one blocked frame, not a 0xE4** (no bus-1 0xE4 rejection then). Its address is unknown; see open questions |
| 0xE4 rejected on bus 1 | 24 frames: 13 at start-up, 11 at 1251.95–1252.03 s (shutdown). All with request 0 |
| Fork byte 2 bits 3:2 | **2 on 120 763 / 120 763** echoed frames and on 120 788 / 120 788 sendcan frames. The other byte-2 bits are 0. The request bit equals the wire's request bit row for row |
| Camera bus-2 0xE4 | 122 377 frames. Arm: 0 on 112 767, 1 on 9610. **Request = 1 on 3906 frames in 2 episodes** (326.94 s for 19.0 s, 961.88 s for 20.1 s), **arm 0 on every one**, max \|field\| 1453. **All 3906 occurred while the fork was engaged** |
| Did the panda forward the camera's 0xE4 to bus 0? | **Yes, all of them.** 121 329 bus-0 TX echoes (src 128) between 38.58 and 1251.87 s, **99.99 % byte-identical** to the camera frame, **including all 3906 request = 1 frames** |
| The source behind that (EVIDENCE) | `opendbc/safety/safety.h` `safety_fwd_hook` blocks a forward only when the destination bus equals the TX-list bus of a `check_relay` message. `honda.h` `HONDA_BOSCH_LONG_TX_MSGS` lists 0xE4 on **bus 1**, so 2 → 0 is not blocked. `honda_bosch_fwd_hook` blocks nothing for 0xE4 |
| Did any camera 0xE4 reach the EPS's bus (1)? | **No.** The panda saw 0xE4 on bus 1 from other nodes only at 28.07–38.39 s (865 frames, relay pass-through, before the safety mode). After that, nothing but its own echo. The EPS answered its F181 on bus 1 |
| Why bus 0 did not gateway them | `hondacan.py` `CanBus` says steering is sent to the radar, which forwards it to the powertrain bus, and that with openpilot long the radar is disabled and 0xE4 goes direct to the powertrain bus. op_long is true, so BELIEF: the radar was off and nothing gatewayed the frames |
| Second line of defence | The camera's arm 0 ≠ 2 would make the lane inert through V298's camera gate. BELIEF: this is the design, and it was not exercised, because no camera frame reached the EPS |

---

## 5. (e) Engage, disengage and override events, with the 2 s after each (EVIDENCE)

| t (s) | edge | v (m/s) | err0 (deg) | tap max (2 s) | tap +150 ms | tap +500 ms | Δangle (2 s) | max \|θsp−θ\| | max \|bar\| | what ended it |
|---|---|---|---|---|---|---|---|---|---|---|
| 42.60 | engage | 1.3 | −1.2 | 41 | +11 | +27 | −10.4 | 10.8 | 988 | — |
| 81.04 | drop | 0.3 | +0.9 | 0 | 0 | 0 | +0.1 | 0.1 | 123 | pedalPressed, preEnableStandstill |
| 93.74 | engage | 0.3 | +0.7 | 34 | −22 | −25 | +5.9 | 5.3 | 402 | — |
| 264.68 | drop | 0.2 | +1.8 | 0 | 0 | 0 | 0.0 | 0.1 | 47 | pedal / standstill |
| 299.52 | engage | 0.3 | +1.2 | 35 | −13 | −16 | −4.0 | 4.8 | 309 | — |
| 391.32 | drop | 0.3 | +11.5 | 114† | 0 | 0 | −9.9 | 0.8 | 877 | pedal / standstill (tap −111 just before) |
| 394.76 | engage | 0.3 | −1.2 | 54 | +33 | −3 | −175 | 13.5 | 2850 | — (the driver is turning) |
| 455.41 | drop | 0.3 | +1.3 | 20† | 0 | 0 | +0.8 | 0.1 | 160 | preEnableStandstill |
| 464.89 | engage | 0.3 | +0.5 | 25 | −12 | −16 | +32.2 | 3.1 | 1922 | — |
| 484.41 | drop | 1.5 | +14.2 | 11† | 0 | 0 | +74.7 | 2.8 | 2821 | gasPressedOverride, **lkasDisable** |
| 914.65 | engage | 5.4 | −1.2 | 60 | +14 | +40 | −7.9 | 12.6 | 1141 | — |
| 1074.74 | drop | 0.3 | +0.7 | 43† | 0 | 0 | −0.6 | 0.3 | 234 | pedal / standstill |
| 1077.71 | engage | 0.3 | +1.2 | 69 | −29 | +7 | +26.3 | 13.2 | 973 | — |
| 1103.87 | drop | 0.3 | +1.0 | 12† | 0 | 0 | −0.4 | 0.1 | 86 | pedal / standstill |
| 1113.67 | engage | 0.4 | +1.2 | 34 | −8 | −15 | −0.6 | 2.3 | 486 | — |
| 1216.88 | drop | 6.7 | 0.0 | 26† | 0 | 0 | +184 | 3.0 | 2865 | pedalPressed, steerOverride, **lkasDisable** |

† The tap maximum in the window is the residual before the edge. **At every request drop the tap is exactly 0 by +150 ms**, and the 0x1AB frame of the drop already reads 0. **A2 is clean 8/8.**

**Engagement pattern:**
- 7 of 8 engagements happen at ≤ 1.3 m/s, and one at 5.4 m/s.
- 6 of 8 drops are standstill pedal events. 2 are LKAS-button disables, at 484.4 s and 1216.9 s.
- steerSaturated ("turn exceeds limit") fired at 166.9, 167.1–167.3, 232.3–232.5 and 1057.3 s.

**Fork O1 override:** 415 rising edges of |carState steering torque| > 600 (hysteresis 500) while requested.
- 308 of them are above 5 m/s, but only **17 above 5 m/s last longer than 0.5 s**. The median duration is 0.04 s, so these are brief bar spikes.
- steerOverride shows 386 event frames in 358 episodes.
- The large post-release angle changes (up to 349°) all fall in driver-steered manoeuvres at 4–7 m/s (t 131–137 s). They are not loop lurches. This was not separated further.

---

## 6. Out of scope, noticed

1. **The ramp arm.** The fork's arm = 2 selects the direction-2 ramp cells (ramp-in 328, ramp-out 66; image cells EVIDENCE; the arm mapping is BELIEF from the build docstring). `drive_read_fastlane.ramp_ticks` / `components._ramp` use the direction-0 cells (+33/−16). That affects only the first ~1 s after an engage and the replay's ramp-out, but the drive-read's replay is not the arm that ran.
2. **The highway integrator is small.** It sits at |I>>7| ≈ 30–1100 S, about 0.6–22 tap LSB, while the unbounded Ki-40 march would hold 1200–2200 (`m1_integrator_track.txt`). Its per-window rate is at design, so whatever limits it is a state limit: the A3 bound or the freezes after hands-on manoeuvres (BELIEF). This bears on note 2 (lacking authority in sustained turns) and on the tracking FAIL above 22 m/s (0.895).
3. **D at >22 m/s** is 0.79 of design while P is at 0.93. D is the weakest term exactly where the GB-P gain is highest.
4. **The camera-command windows do not overlap the drive-read's R3\* event.** The camera commanded during 326.9–345.9 s and 961.9–981.9 s, both inside fork-engaged episodes. The R3\* ring event is near t = 1089 s. Neither camera window touched the EPS (§4). If any on-car feel is attributed to those windows, it was not the camera.
5. **The tap is far from its rail when hands-off.** rms tap is 11–42 LSB (90–340 T) against OCL 3072 T, and the rail fraction is 0. I take no view on note 2's authority question beyond this; M2's budget covers it.

---

## 7. Mechanisms checked against the operator's notes (one line each; the operator scores the symptoms)

- **Note 2 (lacking authority), and note 4 (stutter):** *the loop or D is inverted.* RULED OUT. P sign and ratio −1.00. D opposing in every band, three methods.
- **Note 2:** *the lane under-delivers its own arithmetic.* RULED OUT as a gain deficit. p 0.93–0.96, i 0.95–0.97, d 0.79–0.95.
- **Note 2:** *the integral state is held small after manoeuvres.* WEAK; a measured state, cause BELIEF.
- **Notes 2 and 4:** *interlock drops, frame loss, or the camera's 0xE4 reaching the EPS.* RULED OUT. 0 counter skips, STEER_STATUS 0, arm 2 on 100 % of frames, no camera 0xE4 on bus 1.
- **Note 4:** *D weak at >22 m/s (0.79).* WEAK candidate for reduced damping at highway. Not linked to any symptom here.
