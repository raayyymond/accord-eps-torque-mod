# DRIVE CARD — V296 (C3-rev2-P, the firmware angle loop), first flight — 2026-10-01

**One page. The operator drives; the reader scores bands; the operator scores symptoms.** Nothing here licenses the word
"fixed". Design: `docs/specs/design/DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md` (§5 stop bands, §6 hazards, §7 the
instrument). Reader: `rlog-tools/studies/angle_loop/angle_loop_drive_read.py`. Controls:
`rlog-tools/studies/angle_loop/angle_loop_controls.py` (outputs `_scratch/angle_loop/drive-read/controls/`).
**No flash and no CAN send happens from this card.** The flash needs the operator to name the file and the bus.

## 1. Before the drive: prerequisites (every one is checked on the wire afterward, section 0 of the read)

| # | must be true | how the read checks it |
|---|---|---|
| P1 | The EPS runs the V296 image: F181 `39990-TVA,A16A` | `carParams.carFw` EPS string (attribution line) |
| P2 | **Camera LKAS OFF** (the car's own LKAS button off) — the ruling on the camera hazard is open: procedure (this) or the interlock variant | bus-2 0xE4 census: any frame with request = 1 → "PREREQUISITE VIOLATED" |
| P3 | Fork in angle mode: `AccordEpsAngleLoop` = true; the fork sends `raw = round(−10·θ_des)` (SPEC C1), the measured angle while inactive (C3), 0 when not allowed (C4), clip ±4000 (C2) | initData param; inactive frames with raw = the 0x14A field ≈ 1.0 (a torque fork reads ≈ 0); max \|raw\| |
| P4 | **No fork angle integral** (or τ_o ≥ 6 s, per the operator's open ruling), and none below 8 m/s | config read only — not observable on the wire; check the toggle file by hand |
| P5 | `UseAutoSteerDelay` on for this drive (SPEC §5.7) | initData param |
| P6 | Revert files to hand, re-headered to list A16A (V295 `.rwd` `…-REHEADERED-FOR-REVERT-FROM-V296…` in `accord-firmwares/flashing-2020accord/rwd/`, V294 the same) **and** the fork toggles back: `AccordEpsAngleLoop` false + `toggle-config_V295_r2.json` | — |

## 2. The drive: one short symptomatic drive, **≥ 8 m/s (18 mph) first**

1. Engage on a straight at **≥ 22 m/s (49+ mph)**, hands off, **15–30 s**. Then **10–12.5 m/s (22–28 mph)**, the gain dip,
   15–30 s. Only if both were quiet: **5–8 m/s (11–18 mph)**, 15–30 s.
2. At 10–15 m/s, two **light holds**, 3 s each, a resting hand only (lighter than "pressing"; the read wants 300–500 on
   the 0x18F word): one **inward** (2–4° toward straight), one **outward** (2–4° further into a curve). Then let go.
3. One gentle constant curve held hands-off for ≥ 2 s, and one ordinary disengage with hands on the wheel.

**STOP AND DISENGAGE AT ONCE** on any of: grinding or a buzz; the wheel oscillating or hunting (any back-and-forth you did
not command); a lurch or snap when you let go after a hold; the wheel pulling toward straight or away from the lane; a
jerk; any steering warning. The read does not need more than that episode — stopping is the correct outcome, not a
lost drive. **Revert** = the re-headered V295 `.rwd` (P6) and the fork toggles back.

## 3. What each read decides (thresholds pre-registered; tap in 0x1AB field LSB = T/8)

| read | LIVE / pass | what a FAIL means |
|---|---|---|
| **The angle loop** (structural regression: tap = a·P_raw + b·P_meas + c·I + d·D, the firmware's own component signals rebuilt from the wire) | c_meas/c_raw = −b/a ∈ **[−1.25, −0.80]** | > 0 → **INVERTED, R1: revert** · \|c_meas\| < 0.2 \|c_raw\| or the V295 replay explains the tap (R² ≥ 0.9) → **NOT LIVE: wrong image** |
| The speed schedule | c_P within **±30 %** of the GB-P prediction in every band; c_P(10–12.5)/c_P(5–8) ∈ **[0.25, 0.60]** (predicted 0.42–0.44); c_P(>22)/c_P(5–8) ∈ **[1.05, 1.80]** (1.37–1.39) | c_P ≈ 0.14 everywhere or the SKIP replay wins → **NOT LIVE: cave skipped** |
| Ki 40 (F1 fix) | c_I/c_P ∈ **[1.9, 3.6] /s** (predicted 2.79) | ≈ 3.9 or the C3 (Ki 56) replay wins → "the Ki-40 fix did not ship" |
| Re-sized D | c_D ∈ **[0.45, 0.70]** tap/(deg/s) (predicted 0.566) | ≈ 0.40 → "the D was not re-sized"; **< 0 → INVERTED (pol), R1: revert** |
| A2 | every request drop: \|tap\| < **20** within **0.15 s** | the PID runs through the 2 s ramp-down |
| Opposing-hand freeze (N1) | light hold: the I component moves ≤ **200 T**; release overshoot ≤ §4 value + 2° (inward 9.2°, outward 9.2° below 12.5 m/s / 4.8° above) | the I ramps or the release lurches → the freeze is not live: revert |
| **Stop bands** | R2 \|tap\| ≥ 300 hands-off > 0.3 s · R3* a 0.25–5.5 Hz ring, ≥ 4 cycles ζ < 0.25 or growing, **amplified ≥ 1.25× over the setpoint** · R4 a new 5–30 Hz line (≥ 4 dB, absent < 2 dB on r6c/r39/r3a/r71b, ≥ 1.5× their amplitude) · R5 ring presence > 0.5 % or F7 > 0 · R6 \|θ − θ_sp\| > 10° hands-off > 0.5 s above 8 m/s · R7 tap pushing to 0° > 0.2 s after a drop · R8 STEER_STATUS ≠ 0 or 0x14A b4 bits 0–2 ≠ 7 | **any one → REVERT** |
| The goal (≥ 60 s per band to call FAILED) | tracking 0.95–1.05, turn-hold ≥ 0.90 in every band ≥ 8 m/s; dwell-then-jump and dwells/min vs V282 (r6c, r39); 18–22 Hz engaged/disengaged vs V294 r71b (V295's rlog is not on disk) | under 60 s: reported, not a goal verdict |
| Friction (next step only) | Coulomb Fc and breakaway per band, T counts | not a verdict — sizes friction compensation |

## 4. The sentence a null licenses (written before the drive)

*"If the regression reads −b/a in [−1.25, −0.80] and the C3-rev2-P replay explains the tap at R² ≥ 0.9, the angle loop
is live and is the designed one. If c_I/c_P reads ≈ 3.9 (or the Ki-56 replay wins), the Ki-40 fix did not ship. If c_D
reads ≈ 0.40, the D was not re-sized. If an outward 3 s light hold ramps the I by more than 200 T or lurches on release,
the opposing-hand freeze is not live. If a curve hold at a2+ rings at 0.45–0.9 Hz with the wheel moving more than the
setpoint asks, that is the declared ms_free margin (M-F1). Revert on any of these. A drive that shows none of them
licenses only: 'the instrument saw no failure in the bands it covered' — never 'fixed'."*

## 5. What the controls established (EVIDENCE; synthetic = the common time harness, 4 plant members, 6 × 32 s bands)

| control | structural −b/a | c_I/c_P | c_D | replay R² (own / C3-rev2-P) | verdict |
|---|---|---|---|---|---|
| **V296 = C3-rev2-P** | −0.997…−0.999 | 2.77–2.78 | 0.548–0.554 | 1.000 | **LIVE** (all clauses pass, 4/4 members) |
| V295 lane, angle setpoints | −0.21…−0.46 (a = 0.11–0.12) | — | — | V295 0.999 / C3B-P ≤ −72 | NOT LIVE wrong image (4/4) |
| cave skipped (G = 256) | +0.6…+1.5 (a 0.12–0.16) | — | — | SKIP 1.000 / ≤ −2.2 | NOT LIVE cave skipped (4/4) |
| C3 (Ki 56, G-P48) | −0.96…−0.97 | 3.61–3.72 | 0.48–0.50 | C3-P56 1.000 / 0.93 | live, image C3-P56 (4/4) |
| Kd 34 | −0.997…−0.998 | 2.77–2.79 | **0.382–0.391** | 1.000 / 0.999 (replay cannot separate D) | live, NOT designed: re-sized D (4/4) |
| D sign inverted | −0.99…−1.00 | 2.79–2.83 | **−0.56** | — | INVERTED (3/4), RAILED → revert (1/4) |
| angle sign inverted | (railed) | — | — | all < 0 | RAILED → revert (4/4); R2, R3*, R6 fire |

- **The design's literal regression form fails its own c_D clause on the correct build** (c_D 0.34–0.42 vs 0.566,
  c_I/c_P 3.2–3.5 vs 2.79) — closed-loop collinearity of e and ω plus the frozen-I misspecification — so the
  structural form decides and the literal one is printed beside it. The ratio clause reads −0.97…−1.01 either way.
- Real route r71b (V294), the whole pipeline: **NOT LIVE (wrong image)**; the V295 lane replay explains its tap at
  R² 0.997, every angle-loop image at R² < −18; carFw `A160`; inactive raw ≠ the 0x14A field (torque fork, 0.000);
  **camera bus-2 0xE4 carried 3,238 request frames — the camera LKAS was ON on that drive** (P2 is checkable).
- A2: V296 quiet in ≤ 0.03 s on 8/8 drops; the lane without A2 stays loud 0.39–9.9 s on 3/4 drops per member.
  **R7 has no demonstrated positive control** (the sign-hold gate and the wheel reaching 0° cap a push toward centre
  at ≤ 0.1 s even without A2; impulse 2.8–3.8 LSB·s at 6.5 m/s only); A2 carries that decision.
- R3*: silent on V296 (both members, plus a commanded 0.42 Hz weave); fires on D-inverted, angle-inverted, Ki × 10
  (amplification 3–300×); Ki × 4 is marginal (1.20–1.32×: fires on one member of two). Without a setpoint (V282/V294
  routes) it fires on 2 of 4 historical drives (r6c 3.3 Hz at 1.6 m/s creep; r39 0.41 Hz, 3–4°) — those are REVIEW
  items on the angle loop only if the setpoint carries them. The real-road margin is **BELIEF**.
- R4 on a real background (r71b + a planted sinusoid, vs r6c/r39/r3a): a new rate line is flagged from 1 deg/s at
  11–14 Hz, 2 deg/s at 8.8/17/26 Hz; bar lines from 20–40 counts at 17–26 Hz, not at 8.8–14 Hz up to 40. No V282 route
  flags a line against the other two.
- Goal metrics: on the r71b real paths the reader reproduces the common scorer's tracking slope to ±0.001 and turn-hold
  to ±0.008; **dwell-then-jump on the wire counts half the harness's events** (7 vs 15) — compare drives with drives,
  never with harness counts. Friction: Coulomb recovered to ±3 % below 8 m/s, 15–50 % low above; the bc member's ×2
  recovered (×1.95–2.2); breakaway p50 within ±30 % except at n ≤ 2.
