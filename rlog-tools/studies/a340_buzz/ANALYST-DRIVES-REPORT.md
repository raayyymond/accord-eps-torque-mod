# A340 buzz — drive analysis (subagent report, 2026-11-17)

Offline log analysis only. Nothing was sent to any car. Symptom in the user's words: *"a slight buzz on
return to center movements between 11 and 1, even without starpilot engaged"*.

## Data
| set | route | firmware | segments | moving s | engaged-moving s |
|---|---|---|---|---|---|
| MODDED | 27da1a2b0cde4a09 / 00000055--a39019e01a | V300-A340 REV 3 (fw string `39990-TVA,A34C` in every seg) | **all 23** (17 newly downloaded) | 1107 | 819 |
| STOCK, same car | 27da1a2b0cde4a09 / 0000005d--ff985a4e01 | stock A340 | 7 | 362 | 137 |
| A160 V300 | 75604b0a432fdc89 / ad, ae, af, b0, b1, b2, b3, b4, b8, b9 (all segs) | `39990-TVA,A16C`; V300 per memory for ad..b4 (EVIDENCE: memory note), b8/b9 V300 = BELIEF (chronology + brief) | ~170 | — | — |

Cache: `rlog-tools/_scratch/cache/{a340_user55, a340_user5d, a160_b8_all, a160_b9_all, a160_v300_<route>}/seg*.npz` + `_features.npz`.

Decodes re-checked from data (EVIDENCE, 3 routes): 0x18F b0-1 = `carState.steeringTorque` (slope 0.995–1.000, r ≥ 0.998);
0x18F b2-3 = −8 × 0x14A rate (slope −7.999, r 0.9999) — a finer-resolution copy of the same rate, same frame, so it
cannot de-alias; engaged 0xE4 cmd = −9.79 × wheel angle (r −0.986, n 82 863) → the −10·angle setpoint encoding;
`req` agrees with `latActive` in ≥ 99.9 % of samples in every segment.

**Buzz metric BZ(t)** = rms over 0.32 s (32 samples, centred) of the 0x14A wheel rate high-passed at 10 Hz (4th-order
Butterworth, zero-phase), deg/s. "Buzz" = BZ > 4 deg/s.

## 1. Census, all 23 segments (scripts `a340_buzz_census2.py`, files `census_*.txt`)
Moving (> 2 m/s): BZ > 4 for **72.7 %** of time modded vs **1.8 %** stock same car, **0.5 %** A160 V300 (b8, b9).

| condition (moving) | MODDED s | MODDED %>4 / BZ p50 | STOCK A340 %>4 / p50 | A160 V300 pooled %>4 / p50 |
|---|---|---|---|---|
| manual, return-to-centre, \|ang\|<30, \|tq\|<800 | 9.1 | **94 % / 11.9** | 2.8 % / 1.0 (10.6 s) | 1.0 % / 0.95 (80 s) |
| manual, return-to-centre, \|ang\|≥30 | 20.7 | 38 % / 2.2 | 2.0 % / 1.6 | 0.8 % / 1.2 (150 s) |
| manual, turning away (any) | 31.9 | 29 % / 2.3 | 3.4 % / 1.5 | 2.6 % / 1.3 (226 s) |
| manual, wheel still, \|ang\|<10, \|tq\|<800, v>8 | 109 | **48 % / 3.3** | 0.1 % / 0.46 | 0.3 % / 0.49 (44.5 s) |
| engaged, same still cell | 543 | **89 % / 8.9** | 0.6 % / 0.81 (82 s) | 0.0–0.4 % / 0.46–0.63 per route |

(EVIDENCE, sample-level counts; n in seconds of 100 Hz data.)

## 2. When it buzzes (modded route)
- **Firm driver torque suppresses it.** Engaged, wheel still: \|tq\|<80: 79 %, 80–300: 88 %, 300–800: 83 %, **≥800: 13 %**.
  Engaged `steeringPressed`: **6.7 %** (21.6 s) vs not pressed 88 % (797 s). Manual still: ≥800: 7 % vs 36–40 % below. (EVIDENCE)
- **Manual buzz with the wheel STILL and light torque: YES.** Manual, still, \|ang\|<3: 39 % (\|tq\|<80, 19 s), 35 % (80–300, 82 s),
  43 % (300–800, 43 s), 18 % (≥800, 16 s). At \|ang\| ≥ 10 still-manual it is ~0 % — but those cells are almost all ≥ 800 torque
  (holding against self-aligning), so angle and grip are confounded there. (EVIDENCE)
- **Manual turning AWAY: yes, less.** \|ang\|<10: 54 % (9.6 s); 10–30: 42 %; 30–60: 24 %; >60: 10 %. (EVIDENCE)
- **Engaged with the driver pressing: rarely** (6.7 %, above). (EVIDENCE)
- **Speed.** Duty (still, \|ang\|<10, \|tq\|<800) by speed — engaged: 2–6 m/s 56 %, 6–10 45 %, 10–14 93 %, 14–18 100 %,
  18–22 99 %, 22–26 84 %, 26–30 78 %; manual: 2–6 13 %, 6–10 18 %, 10–14 53 %. Standstill/≤2 m/s ≈ 0 %. The rise is between
  ~8 and ~12 m/s, not at 16 m/s. (EVIDENCE; whether this matches the DampAxis speed schedule is for the firmware tracer.)
- **LKAS command (engaged).** Duty is flat in \|cmd\| (86 % at <50, 85–90 % up to 600); amplitude rises with \|cmd\|/\|ang\|
  (BZ p50 9 → 22 deg/s at \|cmd\| 600–1500). (EVIDENCE)
- **Hysteresis / trigger** (`hysteresis.txt`, still \|ang\|<10 \|tq\|<800 v>8): P(buzz \| buzz 1 s earlier) = 0.88 manual / 0.98
  engaged; P(buzz \| quiet 1 s earlier) = 0.15 / 0.19. If quiet and the wheel did not move > 3 deg/s in that second:
  P = 0.04 (manual, 48 s); if it moved 3–8 deg/s: 0.61 (9 s); > 8 deg/s: 0.95. (EVIDENCE) → once kicked, it sustains until
  grip/torque rises; un-kicked, light hands stay quiet.

### Hypothesis test
- **"Needs the LKAS angle loop engaged": REJECTED as a necessity.** 31 manual episodes, 85 s, req = 0 and cmd = 0 throughout
  (EVIDENCE). Caveat (BELIEF): with −10·angle encoding, cmd = 0 means a 0° setpoint, so this rests on the firmware gating the loop
  off at req = 0. Supporting EVIDENCE that it is gated: manual still-hold torque vs angle at 8–14 m/s is 117 units/deg modded vs
  115 stock (12–15 s each; crude) — no extra centring torque toward 0°.
- **But engagement roughly doubles the duty at matched grip and angle**: \|ang\|<3, still, 80–300 torque: engaged 87 % vs manual
  35 % (EVIDENCE). The engaged loop is a strong *promoter* (it keeps kicking), not a prerequisite.
- **"Buzz whenever the driver is not gripping firmly": partially supported, and partly broken.** Firm torque reliably suppresses
  it (above). Against: in manual with light hands near centre the wheel is quiet ~60 % of the time — light grip is necessary, not
  sufficient; a kick (≥ 3 deg/s wheel motion) is also needed (P 0.04 → 0.61). Also note the grip proxy is torsion-bar torque, not
  hand impedance; a high-torque operating point also changes the assist slope, so "hand impedance damps it" vs "operating point
  stabilises it" is NOT separated by these logs (BELIEF either way).

## 3. Onset / offset anatomy (`anatomy_55.txt`, `growth_55.txt`, `onoff_55.txt`)
Episodes examined in raw 100 Hz: seg 7 t 422.4 (user's "seg 7 ~25 s" is inside the 27.6 s engaged episode 422.4–450.0),
seg 7 451.3 (engaged, large angle), seg 12 732.0 (user steering, firm), seg 16 979.3, seg 18 1114.3, seg 22 1345.7
(manual, still, light hands), seg 0 17.0, seg 1 73.3, seg 22 1338.9 (manual return-to-centre). Route time t ≈ seg×60 + segment time.
- **Onset**: triggered by a small wheel motion (engaged p50 \|rate\| 1.3 deg/s at onset; manual p50 2.9, pre-max 5.1, often
  as the driver releases: \|tq\| before p50 1208). Growth ×1.2, ×1.9, ×2.8 per 6-sample cycle, reaching full amplitude in about
  3 cycles (~0.2 s), then flat (66 episodes; EVIDENCE). Not a slow build-up.
- **Amplitude**: near-centre per-cycle pk-pk p10/p50/p90 = 23/30/34 deg/s (engaged) and 16–28 (manual still) — nearly constant
  → amplitude-limited (saturation-like). Larger at large \|ang\|/\|cmd\| (pk-pk ~51). (EVIDENCE)
- **Waveform**: folded mean cycles are sinusoidal, e.g. [14.7, 8.0, −6.1, −13.8, −9.2, 6.4] (6-sample), [12.3, 7.0, −1.6, −8.1,
  −11.0, −7.6, 0.4, 9.0] (8-sample). Not square, not triangle. (EVIDENCE)
- **As-sampled frequency**: p10/p50/p90 = 12.7 / 16.3 / 22.1 Hz (n 1208 windows). \|ang\|<5: 16.1 Hz engaged, 14.8 manual; \|ang\|>20:
  ~29 Hz. It tracks amplitude (r +0.93), \|cmd\| (+0.61), \|ang\| (+0.57); not speed (−0.28; p50 14–17 Hz in every speed bin). (EVIDENCE)
- **Offset**: manual — 16/31 end with torque rising > 1.5× (driver grips/turns), 5 with a fast wheel move; engaged — 8/35 with torque
  rise, 23/35 with no listed change. (EVIDENCE)
- **Aliasing.** logMonoTime jitter is batching, not sampling (dt 0 ms in 2.6 %, ~19.6 ms in 2.1 %, mean exactly 10.000 ms) — the
  non-uniform-timestamp de-alias is **not valid** (EVIDENCE). Substitute test (`a340_buzz_alias2.py`, calibrated by `a340_buzz_aliassim.py`):
  the >10 Hz part of Δangle/Δt vs interval-mean rate. A true 12–30 Hz motion of one shaft gives corr **+0.8 to +0.98** in the
  simulation (with or without a 5 ms rate lag, both amplitudes). Measured in buzz: **−0.35 (BZ 5–10, n 733), −0.36 (10–15, n 384),
  −0.47 (≥15, n 91)**, tight IQRs; quiet windows +0.06; real 1.5–4 Hz steering: angle/∫rate ratio 1.09, corr +1.00 (EVIDENCE).
  ⇒ The data **reject** "angle and rate measure the same rigid element and it moves at the as-sampled 12–30 Hz" (EVIDENCE).
  Two readings remain (BELIEF, not separable from logs): **(a)** a > 50 Hz line folded into 12–30 Hz (≈ 70–88 Hz if angle and rate are
  sampled together; ≈ 112–130 Hz if rate is skewed ~5 ms); **(b)** a true 12–30 Hz two-mass mode in which the angle-measured and
  rate-measured elements move in anti-phase (requires the two fields to come from different elements across a compliance).
  Which sensor/instant each 0x14A field comes from is a firmware question — that is what decides it.

## 4. Motor / torque side (`motor.txt`)
- **0x18F torque**: during buzz, coherence with the rate line p50 0.66 (quiet 0.19); \|tq/rate\| 2.1 units per deg/s; phase
  −150° (IQR −164…−112); tq >10 Hz rms 33 vs 14 quiet (EVIDENCE, n 567 / 166 windows). So the torsion bar *does* carry it, at
  ~±27 units for ±13 deg/s — small. In fast free return-to-centre (seg 1 t 73.3, 280 deg/s) it is large: rate ±40, tq ±200,
  anti-phase. Physical units of `tq` are not established here (BELIEF ~1 mNm/unit), so no stiffness inference is drawn.
- **0x1AB** (50 Hz): b0 bit7 always 1; the 10-bit field ((b0&3)<<8 | b1) correlates with \|steering rate\| (r +0.79 modded,
  +0.84 stock, +0.80 A160), not with \|cmd\| (+0.04) or signed torque (−0.08). p50 1, p99 28–129. It is **not a motor-torque
  readout on these logs** (EVIDENCE for the correlations; its meaning = BELIEF). During engaged buzz its mean rises 0.32 → 1.57
  and sample-to-sample \|diff\| 0.16 → 0.67 — a weak imprint, at 50 Hz, unusable for phase.

## 5. Controls
- (a) **Stock, same car**: quiet everywhere: BZ > 4 1.8 % moving; stock LKAS engaged 2.2 % at 8–16 m/s; manual return-to-centre
  \|ang\|<30 2.8 % (10.6 s). Same signals, same car ⇒ the buzz is the modified firmware, not the sensor or the car (EVIDENCE).
- (b) **A160 V300, manual return-to-centre** (10 routes pooled): \|ang\|<30 light/medium torque **1.0 %** (80 s), ≥30 0.8 % (150 s),
  manual still near centre v>8 0.3 % (44.5 s); engaged duty 0.0–0.4 % on every route (EVIDENCE). A160 is quiet in the exact
  condition where A340 buzzes 94 %.
- (c) **Plant comparison: inconclusive.** Light-hands free return-to-centre exists only at 2–8 m/s: A340 modded |rate| ≈ 1.22·|ang| + 30
  (2.2 s), A160 0.86·|ang| + 24 (5.4 s); stock A340 has < 1 s. Still-hold slope at 2–8 m/s: A340 stock 99 units/deg, A160 46
  (10 s each) — A340 maybe stiffer at low speed, but n is too small and assist maps differ. BELIEF at most.

## 6. Summary
| metric (still wheel, \|ang\|<10, \|tq\|<800, v>8) | MODDED A340 | STOCK A340 | A160 V300 (10 routes) |
|---|---|---|---|
| **SCORE engaged** = median BZ, deg/s | **8.91** (543 s) | 0.81 (82 s) | 0.46–0.63 |
| DUTY engaged (% BZ>4) | 88.9 % | 0.6 % | 0.0–0.4 % |
| SCORE manual | **3.30** (109 s) | 0.46 (83 s) | 0.49–0.64 (b0 38 s, others < 3 s) |
| DUTY manual | 48.1 % | 0.1 % | 0.0–0.2 % |
| manual return-to-centre \|ang\|<30 \|tq\|<800, % BZ>4 | 94 % (9.1 s) | 2.8 % | 1.0 % |

Scorer: `a340_buzz_census2.py <cache>` then `a340_buzz_score.py <cache>` (seconds). Pass band for a future build: SCORE engaged
< 1.0 and DUTY < 2 % (stock and A160 sit there); report manual separately because its n depends on how the user drives.

**What the data support**: a self-sustained, amplitude-limited oscillation that is (i) present only with the modified firmware on
the A340 car, (ii) independent of the LKAS request (manual episodes with req = 0), (iii) promoted by engagement, (iv) needs a kick
(wheel motion ≥ 3 deg/s) to start from quiet and then persists, (v) suppressed by firm driver torque / pressing, (vi) prevalent
above ~8–10 m/s. That matches "an unstable feedback lane outside the angle loop (DampAxis is the obvious candidate) that the angle
loop aggravates" — but **the cause is NOT proven**: no log here isolates DampAxis from the 6× map or the ported loop constants, and
"hand impedance damps it" vs "high-torque operating point stabilises it" are not separated. The true frequency is unresolved
(either ≥ 50 Hz folded, or a two-mass anti-phase mode); a firmware answer on which element and instant 0x14A angle/rate sample would
settle it.

**Windows for before/after** (route t ≈ seg×60 + segment time; reproduce the *condition* on a fix drive):
1. seg 7, t 422.4–450 (seg-time ~2–30 s, includes the user's "seg 7 ~25 s"): engaged, straight, 16 m/s, hands light — SCORE cell.
2. seg 16, t 979.3–989 and seg 18, t 1114.3–1121: manual, wheel still near centre, 10–12 m/s, \|tq\| 100–400.
3. seg 1, t 73.3 and seg 22, t 1338.9: manual return-to-centre from −178° / −111° with hands released, 6–8 m/s.
4. seg 12, t 732.0 (user's "seg 12 ~13 s"): user steering at −107°, 4.4 m/s, firm torque — short (0.4 s), period-4 regime.
5. seg 22, t 1345.7–1356: manual, 10 m/s, 10 s near-centre episode drifting to 69°.

Scripts (all in `rlog-tools/_scratch/`, cache-only, seconds): `a340_buzz_extract_par.py`, `a340_buzz_lib.py`, `a340_buzz_census2.py`,
`a340_buzz_episodes.py`, `a340_buzz_anatomy.py`, `a340_buzz_xtab.py`, `a340_buzz_onoff.py`, `a340_buzz_growth.py`,
`a340_buzz_alias.py`, `a340_buzz_alias2.py`, `a340_buzz_aliassim.py`, `a340_buzz_motor.py`, `a340_buzz_plant.py`, `a340_buzz_score.py`.
