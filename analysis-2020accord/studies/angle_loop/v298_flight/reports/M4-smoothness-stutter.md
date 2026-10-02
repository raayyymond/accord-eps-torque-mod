# M4: smoothness and stutter on route 79 (V298, the first angle-loop flight)

**Route:** `75604b0a432fdc89_00000079--a1f5d2a272`. 670.7 s engaged (lateral: 0xE4 request and 0x18F STEER_CONTROL_ACTIVE).
**Question:** the operator's note (4), *"steering would feel stuttery/ratchety at times, instead of smooth, strongly, and confidently controlled."*
**Status:** analysis only. Nothing was sent, flashed or edited outside `v298_flight/` and `_scratch/`.

**Wall times, measured, cold grid cache:**

| script | wall |
|---|---|
| `m4_dwell.py` | 8.6 s (builds the four 100 Hz grids once; 2.6 s warm) |
| `m4_setpoint.py` | 2.1 s |
| `m4_episodes.py` | 1.7 s |
| `m4_relay.py` | 1.5 s |
| `m4_ring.py` | 1.7 s |

Each script reads only the caches. None reads an rlog, and none loops over individual samples.

**Labels:** **EVIDENCE** = measured on the wire, read from the fork cache, or read from source. **BELIEF** = modelled or inferred. This report scores bands; the operator scores the symptoms. Nothing here is "fixed".

**Units:**
- θ is the 0x14A angle in degrees, + is left.
- θsp = −raw/10.
- err = θsp − θ, in degrees.
- rate is the 0x18F rate in deg/s.
- tap is the 0x1AB field in LSB, = T/8. The motor torque on the wheel is u = −T.
- bar is the 0x18F torque sensor × 1.024. The fork's steeringTorque is the raw counts.

---

## 0. The answer in the operator's words

The data shows **two different ratchets**. Neither one is a ring.

**A. The big-turn ratchet.** This is the one that matches "not strongly and confidently controlled".
- **What happens:** in large turns, mostly at 2–9 m/s plus one at 16–18 m/s, the wheel moves in surges with near-stops, at about 4–7 Hz.
- **How often:** 3.1, 4.7 and 4.2 "ratchet trains" per minute of turning in the 0–5, 5–10 and 10–20 m/s bands. V282 has 0–2.2, and V294 has 0.
  - These are small counts (9 trains on r79).
  - p = 0.012 against V282 pooled; p = 0.11 against r6c alone.
- **The fork's driver override O1 is inside 89 % of these trains.** It works like a relay:
  1. The wheel surges and the torque bar spikes past 600 steeringTorque counts.
  2. O1 snaps the setpoint back toward the wheel, by 3.6° median and 10.8° at p90.
  3. The error collapses from about 4.3° to 1.4°, and the torque collapses with it.
  4. The wheel decelerates. The fork's rate limiter (120 deg/s or the jerk cap) rebuilds the error, and the cycle repeats every 0.14 s (median).
- The same mechanism caps how far the setpoint can lead the wheel. That bears on note (2).

**B. The small-correction stick.** This is "micro-ratcheting" on small, slow corrections.
- **What happens:** the wheel stays stuck for at least 0.2 s while the setpoint drifts at 1.3–1.6 deg/s. Then it catches up.
- **How often:** 4.1 stuck-under-a-moving-setpoint dwells per minute at 0–5 m/s, and 4.1/min at 10–20 m/s. The full 0.25 deg/s dwell rate is 10× V282.
- **Catch-ups:** a catch-up jump of at least 2× the setpoint's own move happens 1.2–1.4 times per minute below 20 m/s. That is 9× V282 pooled (2–15× by band) and similar to V294. It happens 0/min above 20 m/s.
- The jump is 0.8–1.05° median and 1.7–5.8° at p90.
- This is the declared stick-slip across the P dead zone. **But it is not confined to below 8 m/s**, as the design declared.

**The R3\* "3.85 Hz ring" at t = 1089.4 s is not a ring.**
- It is a pulsed, stick-slip unwind. The wheel moves −3.1 deg/s on average and does not reverse: rate ≤ +0.25 deg/s on 96 % of frames.
- The amplitude is ±0.16°.
- The tap stays at 9 LSB or below, which is under Coulomb friction.

**Ruled out as the stutter:**
- **The fork's 20 Hz setpoint staircase.** The setpoint is one (EVIDENCE), but the wheel does not follow it: wheel/setpoint ratio at 20 Hz is 0.005–0.04.
- **Request drops:** 0 in any episode.
- **A lightly damped linear mode:** none is present.

---

## 1. Dwell-then-jump census, re-derived vectorised

`m4_dwell.py` reproduces the kit's own code exactly, so the re-derivation is cross-checked against two methods:
- `v293_symptom_instruments.dwells`: identical per-minute counts on all four routes.
- `nl_sim.dwell_jump`: identical event counts in all 7 bands.

**The three detectors:**
- **(b) symptom:** the 0.1 s mean of |rate| stays below threshold for at least 0.2 s.
- **(a) harness:** the setpoint moved at least 0.1° during the dwell, and the wheel's catch-up within 0.5 s is at least max(2 × the setpoint's move, 0.2°). This needs an angle setpoint, so it runs on r79 only.
- **(a′):** the same as (a), with the reference replaced by the wheel's own 0.5 Hz zero-phase low-pass. This is like-for-like on every route.

**Jump** = the catch-up in degrees. **Ratio** = jump ÷ the reference's move.

| route (build) | band | s | b@0.25 /min | b@0.50 /min | a′ /min | a′ jump p50/p90 ° | a′ ratio p50 | a /min |
|---|---|---|---|---|---|---|---|---|
| **r79 (V298)** | 0-5 | 102 | **4.70** | 12.3 | **1.18** | 1.05/1.65 | 3.2 | 0.59 |
| | 5-10 | 155 | 1.16 | 15.9 | **1.16** | 0.30/18.8† | 5.0 | 1.16 |
| | 10-20 | 309 | **4.47** | 31.9 | **1.36** | 0.80/5.83 | 3.0 | 1.36 |
| | >20 | 102 | 3.53 | 36.5 | 0.00 | – | – | 1.18 |
| r6c (V282) | 0-5/5-10/10-20/>20 | 310/377/676/1764 | 0.58/0.48/0.44/0.24 | 13.0/18.8/24.3/21.9 | 0.00/0.16/0.09/0.03 | 0.75–1.77 | 2.1–2.4 | – |
| r39 (V282) | same | 157/327/286/106 | 0.38/0.00/0.84/0.00 | 6.5/9.0/16.6/9.6 | 0.38/0.55/0.21/0.00 | 0.6–2.5 | 2.5–7.7 | – |
| r71b (V294) | same | 110/226/376/85 | 19.1/8.0/8.3/5.7 | 35/31/39/47 | 1.64/1.33/0.80/0.71 | 1.1–3.0 | 2.4–2.6 | – |

† The 18.8° p90 is one driver-steered event (t 1129.4, O1 active the whole time).

**Pooled (a′) catch-ups:**
- r79: 12 events in 668 s = 1.08/min.
- V282: 8 events in 4001 s = 0.12/min. That is **9× lower.**
- V294: 14 events in 797 s = 1.05/min.

**At the 0.50 deg/s threshold**, r79 is at V282's level below 10 m/s, and 1.3–1.7× V282 above 10 m/s. So the "10×" exists only at 0.25 deg/s. It counts **real stops**.

**What the r79 dwells at 0.25 deg/s are** (`dwell_setpoint_split`, EVIDENCE):

| band | dwells /min with the setpoint moving ≥ 0.1° | dwells /min with the setpoint still | setpoint rate in the moving dwells, p50 |
|---|---|---|---|
| 0-5 | 4.11 | 0.59 | 1.3 deg/s |
| 5-10 | 0.78 | 0.39 | 6.3 deg/s |
| 10-20 | 4.08 | 0.39 | 1.6 deg/s |
| >20 | 1.18 | 2.35 | 0.5 deg/s |

Below 20 m/s, 87–91 % of these dwells are a wheel **stuck under a slowly moving setpoint**. Above 20 m/s they are mostly holds of a still setpoint, which is the position loop doing its job.

**Breakaway error at the end of an (a) dwell:**
- |err| is 0.0–2.9°, median 0.8°.
- 11 of 13 events have err < 0 (binomial p = 0.022). The engaged median err is 0.00.
- Only 3 of 13 events are below 8 m/s. The coincidence with low speed is 0.15 against a base rate of 0.32.

---

## 2. Ratchet in motion: stall-surge trains and the O1 relay

The dwell detectors cannot see the big-turn ratchet. Its stalls last 20–60 ms, under their 100–200 ms minimum, so `m4_episodes.py` adds a rate-only detector that works the same way on every route.

**The detector:**
- "Turning" = the 0.5 s mean |rate| is at least 10 deg/s.
- A **stall** is when the 30 ms in-direction rate falls below 0.25 × the mean, between surges above 0.75 × the mean, each within 0.25 s.
- A **train** is at least 3 stalls spaced 0.08–0.40 s apart.

| route | trains /min of turning (0-5 / 5-10 / 10-20) | share of turning time | train frequency p50 | in-turn 4–8 Hz rate rms, 0-5 / 5-10 (deg/s) | rate concentration q75-90 ‡ |
|---|---|---|---|---|---|
| **r79 V298** | **3.12 / 4.68 / 4.2** (n 3/5/1) | 3.7 / 7.9 / 8.3 % | 5.9 / 4.0 / 3.4 Hz | 4.29 / **7.09** | 0.385 |
| r6c V282 | 1.65 / 2.20 / 0 | 1.4 / 2.4 / 0 % | 4.6 / 6.7 | 5.05 / 4.79 | 0.342 |
| r39 V282 | 0 / 0.86 / 0 | 0 / 1.1 / 0 % | 3.8 | 3.95 / 5.50 | 0.323 |
| r71b V294 | 0 / 0 / 0 | 0 | – | 3.78 / 2.29 | 0.482 |

‡ This is the record's scale-free ratchet measure. On r79 the **setpoint's** own concentration is 0.54–0.84, so the wheel is smoother than its command at the frame level.

**Single-stall counts** (as opposed to trains) are similar across all routes at 0–5 m/s: 28 for r79 against 20–30 /min. At 5–10 m/s r79 runs 2–3.7× the references: 64 against 17–31 /min. So the **periodic train** is the part that discriminates, not the single stall.

### O1 as reconstructed

The O1 path, from `opendbc/car/honda/carcontroller.py` `_update_angle`: while latActive and |steeringTorque| > 600 (off at ≤ 500), the setpoint = θ + 0.06·rate, then the error clip is applied. On release, the rate limiter restarts from θ.

`m4_common.limiter_reconstruct` reproduces the published `carOutput.steeringAngleDeg` on **99.994 % of latActive frames** (residual p99.9 = 1.8e-5°). This is EVIDENCE.
- The pairing is also EVIDENCE: carOutput[i] uses carState[i−1] (98.9 % match on inactive frames) and the carControl before the latest one (78.9 % against 52 % for either other choice).

| | 0-5 | 5-10 | 10-20 | >20 | all |
|---|---|---|---|---|---|
| O1 share of latActive time | **41.5 %** | **24.6 %** | 6.2 % | 0.6 % | 15.0 % |
| O1 onsets /min | 62.5 | **85.1** | 11.9 | 15.4 | 415 episodes |
| share of O1 episodes ≤ 50 ms | 0.68 | 0.92 | 0.84 | 0.96 | 353 / 415 |
| rate/jerk limiter binding | 14.8 % | 11.8 % | 1.3 % | 1.8 % | 5.9 % |
| error clip binding | 0.27 % | 0.24 % | 0 | 0 | 0.1 % |

**Size of the O1 effect:**
- **Onset step:** O1 moves the setpoint **toward the wheel** on 87 % of onsets, by 3.6° (p50) and 10.8° (p90). The error just before onset was 4.2° (p50) and 11.9° (p90).
- **Clusters:** 31 clusters (3 or more O1 episodes with gaps under 0.5 s) cover 109 s. Onset-to-onset is 0.14 s median (p25/p75 0.07/0.17), about 7 Hz.

**The order of events** (`m4_relay.py`): 263 turning onsets, averaged and normalised by turn direction.

| lag (s) | −0.10 | −0.04 | −0.02 | 0 | +0.04 | +0.06 | +0.15 |
|---|---|---|---|---|---|---|---|
| accel (deg/s²) | −89 | +95 | **+128** | +94 | −44 | **−92** | +151 |
| bar | 30 | 122 | 242 | **284** | −212 | −316 | 55 |
| err (°) | 2.5 | 3.9 | **4.3** | 2.0 | 1.4 | 2.1 | 3.4 |
| tap (LSB, − = pushing into the turn) | −16 | −22 | −26 | **−27** | −17 | −14 | −27 |

The sequence reads: error builds, then a surge, then the bar spike, then O1. The error collapses and the wheel decelerates. The next surge comes 0.15 s later.

**Is it a hand or twist?**
- The bar at onset is **5.0× (p50)** what a hands-off inertia + friction fit predicts. The fit is bar = 0.47·α + 0.81·w + 75·sgn w + 60, on engaged frames with |bar| < 450.
- sign(bar) = sign(α) on 74 % of onsets.
- carState steeringPressed is set on only **10 %** of short O1 episodes, because its threshold is 1200 counts for HONDA_ACCORD. Long episodes (over 0.5 s) are 100 % pressed: those are the driver steering.
- BELIEF: a hand resting on the rim adds inertia, and twist alone can trip 600 counts in a surge. There is no hand sensor, so this cannot be resolved from the data.

**The statistical caveat** (EVIDENCE, and it limits the claim):
- 77 % of stalls start within 0.15 s after an O1 frame (in trains: 76 %, median 65 ms).
- But 75 % of all turning frames have an O1 frame in the previous 0.15 s.
- O1 is nearly everywhere in low-speed turning on this route, so **this route cannot separate "O1 causes the stall" from "stalls happen in turns" statistically**. The case for the relay rests on the event-locked order above and on the trace below.

**Trace, t 1186.0–1188.0 s** (fork axis; v 7.3 → 5.2 m/s; O1 pressed only 2 % of the time):
- The planner's desired angle runs from −41° to −185°.
- The applied setpoint rides the 1.2°/frame cap and stays 1–11° ahead of the wheel, until each O1 onset snaps it back to 1–2°.
- O1 onsets: 1186.09, .25, .41, .55, .71, .85, 1187.01, .17, .31, .51, .69, .84. That is **every 0.14–0.20 s**.
- The rate swings between about 0 deg/s and −70 deg/s. It reaches 0 deg/s at 1186.69, and −8 deg/s at 1187.65–67.

---

## 3. The worst 10 episodes

Ranking: stall-surge episodes by cycle count, then the largest (a) dwell-jumps, then R3\*.
- t is logMonoTime.
- "route s" ≈ t − 28.07. This is BELIEF to ±1 s; the segment number is floor(route s / 60).
- In every row: request = 1, STEER_STATUS = 0, 0x14A b4 bits 0–2 = 7.
- **O1, RL, EC, frz, prs** are the share of the episode's frames that are O1, rate-limited, error-clipped, frozen by the EPS freeze predicate, and steeringPressed.
- The freeze predicate is |bar| > 512, or |bar| > 300 opposing. BELIEF: tq4f68 ≈ |bar|.

| # | kind | t (route s, seg) | dur s | v | θ start → end ° | \|rate\| max/min | \|err\| max ° | tap LSB | \|bar\| max | O1 | RL | EC | frz | prs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | train, 11 cycles | 1149.75 (1121.7, s18) | 5.23 | 8.6 | 17 → 25 | 88 / 0 | 5.3 | −126..−47 | 1812 | .24 | .08 | 0 | .46 | .10 |
| 2 | train, 8 | 1079.11 (1051.0, s17) | 1.37 | 2.3 | 7 → 29 | 42 / 0 | 13.6 | −91..−18 | 1103 | .30 | .70 | 0 | .62 | 0 |
| 3 | train, 8 | 475.93 (447.9, s7) | 2.25 | 6.9 | −7 → −69 | 53 / 0 | 10.6 | 15..108 | 1595 | .37 | .63 | 0 | .50 | .03 |
| 4 | train, 7 | 1185.30 (1157.2, s19) | 3.83 | 8.7 | −20 → −176 | 91 / 0 | 14.5 | 42..164 | 1595 | .24 | .61 | 0 | .45 | .02 |
| 5 | train, 6 | 1054.81 (1026.7, s17) | 3.05 | 18.4 | −28 → −60 | 77 / 0 | 7.2 | 52..129 | 2090 | .21 | .42 | 0 | .39 | .03 |
| 6 | train, 6 | 1141.80 (1113.7, s18) | 1.72 | 7.2 | 27 → 24 | 87 / 0 | 6.9 | −114..−55 | 1869 | .52 | .20 | 0 | .64 | .28 |
| 7 | dwell-jump 4.6° | 168.31 (140.2, s2) | 0.62 | 15.6 | 16 → 12 | 41 / 0 | 2.1 | −59..−41 | 933 | .05 | 0 | 0 | .14 | 0 |
| 8 | dwell-jump 2.2° | 447.49 (419.4, s6) | 0.60 | 11.8 | −5 → −8 | 15 / 0 | 3.0 | 40..48 | 428 | 0 | 0 | 0 | .07 | 0 |
| 9 | dwell-jump 1.4° | 1216.40 (1188.3, s19) | 0.47 | 7.9 | −1 → −2 | 16 / 0 | 1.3 | 24..33 | 541 | 0 | 0 | 0 | .10 | 0 |
| 10 | R3\* 3.85 Hz | 1089.41 (1061.3, s17) | 1.05 | 12.0 | 5 → 1 | 8 / 0 | 1.8 | −4..9 | 223 | 0 | 0 | 0 | 0 | 0 |

Rows 1 and 6 have a small net angle change but rates up to 88 deg/s, with |bar| at 1800 or more and pressed at 10–28 %. **The driver may be in the loop on those two; the operator should score them.**

The other train starts, all with O1 inside, are at t 1116.6, 1153.2, 1158.8 and 1188.6 s.

---

## 4. The R3\* 3.85 Hz event, characterised (`m4_ring.py`)

**Band-pass 2.5–5.5 Hz, peak amplitudes in the event span:**

| channel | peak | per-cycle decay a(i+2)/a(i) | ζ (if read as linear) |
|---|---|---|---|
| θ | 0.165° | – | – |
| θsp | 0.077° | – | – |
| err | 0.23° | – | – |
| rate | 3.18 deg/s | 0.92 | 0.013 |
| tap | 1.65 LSB | – | – |
| bar | 80 | – | – |

**Phases relative to rate, at 3.85 Hz:**

| channel | phase | gain |
|---|---|---|
| tap | −75° | 0.49 LSB per deg/s |
| θsp | 139° | 0.014 |
| err | 104° | – |

**What moved:**
- The wheel unwound from 9° to 0° at v = 12.0 m/s, following a setpoint unwinding at −3.6 deg/s.
- The rate was at or below +0.25 deg/s on 96 % of frames (mean −3.1 deg/s), and 21 % of frames were near-stopped (|rate| < 0.75).
- err stayed between −0.8° and −1.8° (mean −1.19°), meaning the wheel lagged the setpoint by about 1.2°.
- The mean tap was +2.1 LSB, about 17 T. That is below the drive-read's Coulomb Fc of 73.5 T at 8–12.5 m/s.
- There was no O1, no limiter binding, no freeze, and no request change.
- **Reading (EVIDENCE):** this is a pulsed **stick-slip** unwind, not a free oscillation. Its decay ratio is not a linear damping ratio.

**Predicted closed-loop modes at 12.1 m/s** (panel-2 exact lifted model `lifted_for` / `Lifted2.exact`, C3B-P: GB-P table, Kp 112, Ki 40, fresh-rate D; BELIEF, modelled). Variants are nominal and the physical frame FAc:

| Kd | 2–6 Hz modes (f, ζ) | worst elsewhere |
|---|---|---|
| **+48 (as built)** | nominal 4.31/0.81 (FAc 3.94/0.83); b_lo 4.42/0.67; tau6 4.59/0.77; light_b 3.75/0.49 | ms_free 0.76/0.34; all ρ < 0.99 |
| 0 | none, except light_b 2.2/**0.065** | ms_free 0.82/0.11 |
| −48 (aiding) | none | modes at 1.2–1.8 Hz; b_lo 1.8/0.035; **ms_free ρ 1.003, light_b ρ 1.05 (unstable)** |

**What this says about the D sign:**
- The event's 3.85 Hz matches the **Kd = +48** loop's natural frequency of 3.9–4.4 Hz.
- No −48 member has a 2–6 Hz mode.
- The tap–rate phase of −75° has a net opposing component (cos = +0.26).
- **Weak evidence for an opposing D**, from one small event with a tap of about 1.6 LSB, near quantisation. This is a single-method caveat.

---

## 5. Mechanisms: EVIDENCE for and against

1. **Low-speed stick-slip across the P dead zone.**
   - *For:*
     - 87–91 % of the 0.25 deg/s dwells below 20 m/s are a stuck wheel under a 1.3–1.6 deg/s setpoint drift.
     - (a′) catch-ups run at 9× V282.
     - The R3\* event is a stick-slip unwind with |err| of about 1.2°.
     - Breakaway |err| is 0–2.9° (median 0.8°). The predicted dead zone Fc/k_P is 1.2–2.4° at 5–22 m/s (BELIEF: drive-read Fc ÷ c_P×80).
     - 23 % of stalls happen with no O1 within 0.15 s, at |err| 1.7° (p50).
   - *Against:* it does **not** live mainly below 8 m/s. Only 3 of 13 (a) events are below 8 m/s, and the stuck-dwell rate is the same 4.1/min at 0–5 and 10–20 m/s.

2. **The fork's setpoint stair-stepping.**
   - *For:* the setpoint is a staircase. 79 % of the desired-angle travel happens in the 2 controls frames after each 20 Hz modelV2 message (45.6 % + 33.3 %).
   - Share of 0xE4 frames with zero increment:

     | setpoint rate | zero-increment frames | a smooth 0.1° ramp would give |
     |---|---|---|
     | 1–5 deg/s | 78.5 % | 56.6 % |
     | 5–20 deg/s | 63.7 % | 0 % |

   - At ≥ 20 deg/s, 35 % of frames sit on the 12-count cap, and at ≥ 60 deg/s 80 % do.
   - *Against:* the wheel does not follow the steps.
     - Phase-locked to modelV2, the 20 Hz component ratio wheel/setpoint is 0.005–0.044 (0.14 in the 0–5 m/s, ≥ 20 deg/s bin), and the wheel-rate depth is 0–6 %.
     - The rate's 20 Hz line in turns is +1.5 dB (0.36 deg/s rms), against V282's +10.5/+10.9 dB (2.7–3.1 deg/s).

3. **The EPS angle's 100 Hz hold inside the 1 kHz P term.** This can only be inferred.
   - *For:* 0x14A one-count flicker (±0.1° and back within 50 ms, setpoint unchanged) runs at 3.0 / 13.7 / 26.3 / 59.8 per minute by band, against 0.2–3.1 on V282 and 1.6–4.6 on V294.
   - *Against:* the amplitude is one 0.1° quantum, and it grows with speed, not with Kp_eff. The angle agrees with ∫rate (gain 0.9986). The hold cannot be isolated from road input on the wire.

4. **The integrator freeze toggling at 300/512.**
   - *For:* freeze toggles appear in 82 % of stall windows against a 43 % base.
   - *Against:* the toggles come from the same surge bar spikes that trip O1 (every O1 onset is above 512), so they are a consequence. They are not enriched at dwell-jumps (0.31 against 0.50). M3 measures the freeze itself.

5. **Request drops, direction-2 fades or A2 skips.**
   - *Against:* 0 of 105 stall windows and 0 of 13 dwell-jumps contain a request change. STEER_STATUS = 0 and b4 = 7 in every episode. The drive-read's A2 was clean on 8 of 8 drops.

6. **A ring.**
   - *For:* R3\* fired once, and it is stick-slip (§4). The drive-read's engaged/disengaged amplitude ratios are the highest of any build in 5–9 Hz (2.53, against V282 0.83–1.68 and V294 1.05) and in 13–17 Hz (2.94, against 1.86–1.88). This is single-method, from the kit instrument.
   - *Against:*
     - No 5–30 Hz line (R4 = []).
     - Ring presence 0 % and F7 = 0.
     - The declared ms_free 0.45–0.9 Hz ring appears only as a "commanded" review event at 0.52 Hz: coherence with the setpoint 0.99, amplitude ratio 0.99, which is the fork's own path.
     - The 5–9 Hz amplitude hands-off is only 0.67–1.08 deg/s, against 3.68 over all engaged frames, so the excess is in hands-on/O1 frames. That is consistent with mechanism 7.

7. **The fork limiter: O1, rate-limit chatter, and the error clip.**
   - *For:* see §2.
     - The error clip binds on only 0.1 % of frames.
     - **O1 makes the setpoint move with the wheel**: 15 % of latActive time, and 41 % at 0–5 m/s.
     - Each onset steps the setpoint 3.6–10.8° toward the wheel.
     - The 7 Hz relay order is established by event-locked averaging.
     - 89 % of ratchet trains contain O1, and the rate limiter is active in 65 % of stall windows against a 42 % base.
     - During O1 the 0.06 s lead feeds rate forward into P: about +c_P·0.6 tap/(deg/s), which is about 0.50 at 5–8 m/s. That is the size of the whole designed D (0.45–0.70), with the **aiding** sign (BELIEF: arithmetic on the drive-read's c_P).
   - *Against:* O1 saturates low-speed turning (75 % base), so the stall-O1 coincidence is not enriched on this route.

8. **A lightly damped closed-loop mode from a weak or aiding D.**
   - *Against:* the only R3\* event is not a free ring. No −48 member predicts 3.85 Hz. The +48 member predicts 3.9–4.4 Hz but heavily damped (ζ 0.49–0.83).
   - *For:* nothing on this route.

---

## 6. Ranked mechanisms, and the one measurement that separates the top two

| rank | mechanism | operator note | strength |
|---|---|---|---|
| 1 | **O1 relay (7) with stick-slip (1) in big turns**: 4–7 Hz ratchet trains | 4 (and 2) | **strong** for the trains; the O1 cause is not statistically separable on r79 |
| 2 | **Small-correction stick-slip across the P dead zone (1)**: stuck under a slow setpoint, then catch-up | 4 | **moderate–strong** |
| 3 | Broadband 5–9 / 13–17 Hz engaged excess (6) | 4 | moderate (5–9 Hz is probably the same as #1) |
| 4 | Freeze toggling (4) | 4 | weak (a consequence of the surge) |
| 5 | Quantum flicker / 100 Hz hold (3) | 4 | weak (0.1°) |
| 6 | Aiding-D light mode (8) | 4 | ruled out for the observed event |
| 7 | 20 Hz setpoint staircase (2) | 4 | ruled out (the wheel does not follow it) |
| 8 | Request drops / A2 (5) | 4 | ruled out |

**The separating measurement, for #1 against #2:** count the stall-surge **train rate** in large low-speed turns where O1 **cannot** fire.
- **Zero-change form** (an inert measurement): one controlled set of large low-speed turns with the hands verifiably off the rim. `m4_common.limiter_reconstruct` already recovers O1 exactly from the cache, so no new telemetry is needed.
- **If O1 still trips on twist alone and the trains persist:** the relay is self-excited.
- **If O1 never trips and the trains persist at 4–6 Hz, with stalls at |err| ≈ 1.2–2.4° (the dead zone):** it is stick-slip in the loop.
- **If the trains fall to V282's ≤ 1.7/min:** it was the relay with a hand on the rim.

The same split could be made by raising ANGLE_OVERRIDE_ON to the car's own steeringPressed threshold of 1200. **That is a fork code constant and a design decision, so it is not proposed here.**

---

## Out of scope, noticed

- **O1 caps authority (note 2).** O1's 600-count threshold is **half** the car's steeringPressed threshold (1200: `honda/values.py` STEER_THRESHOLD default, and HONDA_ACCORD is not overridden). Together with the 1.2°/frame cap, it holds the setpoint lead to about 1–12° while the planner's desired angle leads by up to 50° or more. At t ≈ 1187 s, desired is −146° with θ at −98°. The EPS integrator freezes at the same bar spikes (above 512). This is for M1/M2.
- **err sign asymmetry.** 11 of 13 dwell-jumps end with err < 0 (p = 0.022). This may come from the sar-5 floor: e5 = Ep>>5 gives +1 for +1 count but −2 for −1 count at G ≈ 560. BELIEF, for M3.
- **Pipeline latency.** The EPS executes a setpoint computed from carState[i−1] and the carControl before the latest one, on top of the 20 Hz model cadence. This bears on the O1 0.06 s lead sizing (BELIEF).
- **Large steps with O1 excluded.** 0xE4 increments above 12 counts appear with O1 excluded (5–7 % of frames at ≥ 20 deg/s; maximum 164 counts = 16.4° in one frame). These are probably O1 onset/release frames that the 100 Hz mask misattributes (BELIEF). The O1 onset step is itself a setpoint discontinuity at the EPS.

## Files

**Scripts:** `v298_flight/m4_common.py` (grid and fork-limiter reconstruction), `m4_dwell.py`, `m4_setpoint.py`, `m4_episodes.py`, `m4_relay.py`, `m4_ring.py`.

**Outputs:** `_scratch/out/r79/m4/` holds `m4_*.json` and `m4_*.txt`, plus the cached grids `grid_*.npz`.

**STEER_STATUS** is read from the drive-read's extras cache, `_scratch/angle_loop/drive-read/routes/…_extras.npz`. That is a single source.
