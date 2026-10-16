# Drive read — the first V299 routes (2026-10-15) — TASK 1a

Subagent `routes-review`. Analysis only: nothing flashed, nothing sent, fork not edited, no firmware proposed.

## 0. Routes and attribution — from the wire

The browser fetch was blocked because the Chrome extension was not connected. The operator placed both routes by hand.
Both routes are complete, with segments contiguous from 0 and sizes between 7.5 and 15.4 MB.

| route | segs | EPS carFw | image | fork commit (initData) | steerControlType | AccordAngleMaxRate / ClipScale / BarFromEps | SteerRatio | lat-engaged |
|---|---|---|---|---|---|---|---|---|
| `0000009c--7f2f4d267c` | 15 (0–14) | `39990-TVA,A16B` | **V299** | Dom `c6452361e` | angle | **250.0** / 1.0 / 1 | 16.84 | 541.6 s, 8 episodes |
| `0000009d--371ec93849` | 14 (0–13) | `39990-TVA,A16B` | **V299** | Dom `c6452361e` | angle | **250.0** / 1.0 / 1 | 16.84 | 566.9 s, 8 episodes |
| `00000079--a1f5d2a272` (comparator) | 21 | `39990-TVA,A16A` | V298 | Dom `2712e1336` | angle | — (pre-V299 fork) | 16.84 | 670.7 s, 8 episodes |

EVIDENCE: carFw, initData params, and the rule-identity replay. The V299 rule beats V298's on 15/15 and 14/15
30-s hands-off windows, with pooled ΔR² of +1.87 and +1.99. The positive control is route 79, where V298 wins
18/18. **Both routes flew config B's rate cap of 250 deg/s, not config A's 120.** The drive card and the reader
assume config A.

## 1. Drive-2 verdict (reader), per route

| criterion | r9c | r9d | note |
|---|---|---|---|
| LIVE angle loop | LIVE (ratio −1.006, c_D 0.671, c_I/c_P 2.75) | LIVE (−1.013, 0.588, 2.83) | EVIDENCE |
| F1 | FAIL | FAIL | **The FAIL is an artefact.** The rule clause passes and the status word is on 100 % of frames. The only failing clause counts setpoint steps above 1.2°/frame (239 on r9c, 115 on r9d). That literal is config A's 120 deg/s. These routes ran 250 deg/s, which allows 2.5°/frame, and the largest step was exactly 2.50. EVIDENCE |
| F2 ring / grind | PASS (presence 0.12 %, 18–22 Hz 0.99) | PASS (0.13 %, 0.72) | V282 3.4–3.9 |
| F3 / F5 release | PASS (n 1) | PASS (n 4 / 3) | thin |
| F4a/b/c turn-ins | NOT TESTABLE | NOT TESTABLE | no hands-off turn-in in class |
| F6 stutter | **FAIL** (trains 6.64 /min at 5–10 m/s; 300/512 enrichment 3.53×) | PASS (trains 0; 1.54×) | split |
| F6b, F7, F8, F9 | PASS | PASS | F8 bar check: 0.000 % mismatch, no stale frames |
| F10, cap read | NOT TESTABLE | NOT TESTABLE | no qualifying hold |
| X3 | the reader prints "N/A config A" | same | **Wrong.** The cap-250 dose flew. |
| camera 0xE4 commanding | PREREQUISITE VIOLATED (1230 req frames) | same (2052) | as on r79 |

### Stutter readouts vs V282 (per minute of turning; r6c / r39 = V282)

| readout | band | r79 V298 | r9c V299 | r9d V299 | V282 |
|---|---|---|---|---|---|
| stall-surges | 0–5 / 5–10 / 10–20 | 28.1 / 63.6 / 37.8 | 45.4 / 49.8 / – | 49.2 / 29.5 / 52.2 | 29.6/20.2 · 22.0/17.1 · 0/3.3 |
| ratchet trains | 0–5 / 5–10 / 10–20 | 3.1 / 4.7 / 4.2 | 4.1 / 6.6 / – | 0 / 0 / 2.6 | ≤ 2.2 |
| dwells | 0–5 / 5–10 / 10–20 / >20 | 4.7 / 1.2 / 4.5 / 3.5 | 15.0 / 2.0 / 8.7 / 1.7 | 6.8 / 0 / 5.9 / 7.7 | 0.24–0.84 |
| 300\|512 enrichment, 0–20 m/s | | 3.58× | 3.53× | 1.54× | 0.93–1.08× |
| 1.6–3 Hz hard-turn wheel-rate rms (deg/s) | all | 8.48 | **21.7** | **13.0** | 3.45–4.02 |

### Tracking gain per band (hands-off runs ≥ 15 s)

| band | r79 | r9c | r9d |
|---|---|---|---|
| 8–15 m/s | 0.989 | — | **0.566 FAIL** (67 s) |
| 15–22 | 0.976 | 0.976 | 0.997 (49 s) |
| >22 | 0.895 (filter edge) | 0.975 | 0.976 |

The r9d 8–15 m/s FAIL is unexplained. **BELIEF:** it is the 12–13 m/s stretch around 224–235 s, where the driver
held the wheel against the loop with bar ≈ 1700–2750 and steeringPressed 57 % of the time.

## 2. The complaint: the wheel jumps back and forth instead of landing at a hard-turn angle

**Verdict: FORK-SOURCED.** The setpoint itself moves back and forth, and the wheel follows it. Two fork
mechanisms feed the measured wheel angle back into the setpoint. The firmware tracks the setpoint at about unity
gain in the 1–5 Hz band and does not hunt on its own in these episodes.

### 2.0 The pre-registered rule, applied per episode (`high_angle_hunt.py`, 0.4–4 Hz band)

The rule was written before any V299 route was read:
- **FORK** when R² ≥ 0.5 and setpoint rms ≥ 0.7 × wheel rms.
- **FIRMWARE** when setpoint rms < 0.4 × wheel rms.
- **MIXED** otherwise.

No episode is ≥ 80 % hands-off by |bar| < 300, so the rule is applied to every episode. The hand is marked
from the bar.

| route / t | v | wheel rms | sp rms | sp/wheel | R² | rule | hand? |
|---|---|---|---|---|---|---|---|
| 9c 331.6 | 6.9 | 4.50 | 5.83 | 1.30 | 0.80 | FORK | partly (press 0.75) |
| 9c 702.7 | 6.2 | 5.15 | 5.37 | 1.04 | 0.90 | FORK | no: bar = inertial reaction, R² 0.88 |
| 9c 746.2 | 3.9 | 8.78 | 8.99 | 1.02 | 0.85 | FORK | partly |
| 9c 780.9 | 3.8 | 4.73 | 4.00 | 0.85 | 0.42 | MIXED | partly |
| 9d 138.3 | 9.0 | 4.32 | 3.23 | 0.75 | 0.74 | FORK | no |
| 9d 224.6 | 12.7 | 2.53 | 0.16 | 0.06 | 0.03 | FIRMWARE by rule | **yes**: bar mean 1726, freeze 69 % |
| 9d 227.8 | 12.6 | 1.96 | 0.93 | 0.47 | 0.39 | MIXED | light |
| 9d 231.7 | 13.1 | 1.57 | 0.57 | 0.36 | 0.01 | FIRMWARE by rule | **yes**: bar 2751, freeze 100 % |
| 9d 569.0 | 6.0 | 4.91 | 4.61 | 0.94 | 0.90 | FORK | no |
| 9d 758.9 | 5.8 | 7.87 | 6.26 | 0.80 | 0.62 | FORK | partly |
| 9d 775.0 | 3.2 | 3.44 | 5.20 | 1.51 | 0.29 | MIXED | yes (press 1.0) |
| **tally** | | | | | | **FORK 6 · MIXED 3 · FIRMWARE 2** | Both FIRMWARE rows are the driver holding the wheel against the loop at 12–13 m/s. |

**Route 79 (V298) comparison.** 17 of 19 episodes have R² 0.86–1.00 with sp/wheel ≈ 1. Those are also
fork-sourced, but by a different mechanism: the V298 fork's override snapped the setpoint to the wheel, so the
setpoint reversed 1–18 times per second. V299 removed that override. The new fork sources are the turn lead and the
error clip, below.

**Error-clip candidate: clip-bind duty from the fork's own status bit 16.** Per episode it is 0.02–0.53. The clip
binds most at 3–6 m/s, at 0.44 and 0.53 in 9d at 759 s and 775 s, with 0.4–1.2 onsets per second. At route level
it binds on 0.83 % (9c) and 3.19 % (9d) of latActive frames. Where it binds, the setpoint moves more than the
pre-limiter angle (9d 138 s: 1.82 vs 0.65; 9d 759 s: 1.94 vs 1.55). So it is a **secondary** fork source. The
turn lead is the primary source in the 9c blinker turns.

### 2.1 Where the 1–5 Hz motion is born

Every row below is a high-angle episode: lateral-engaged, |θ| ≥ 60°, at least 1 s long. Each column is the 1–5 Hz
band rms in degrees of wheel angle. Curvatures are scaled by their own regression on the carControl angle.

| route / t (s) | v m/s | blinker | model action | desiredCurvature | carControl angle (pre-limiter) | 0xE4 setpoint | wheel | fork clip / rate bits | press |
|---|---|---|---|---|---|---|---|---|---|
| 9c 331.6 | 6.9 | L | 0.64 | **2.57** | 2.51 | 1.30 | 1.16 | 0.28 / 0.28 | 0.75 |
| 9c 702.7 | 6.2 | R | 1.53 | **4.87** | 4.89 | 3.49 | 2.95 | 0.07 / 0.25 | 0.06 |
| 9c 746.2 | 3.9 | R | 1.34 | **5.14** | 5.22 | 2.02 | 2.42 | 0.16 / 0.21 | 0.59 |
| 9c 780.9 | 3.8 | R | 1.13 | 2.35 | 2.31 | 2.15 | 2.00 | 0.03 / 0.08 | 0.56 |
| 9d 138.3 | 9.0 | – | 0.58 | 0.60 | 0.65 | **1.82** | 1.71 | 0.02 / 0.20 | 0.02 |
| 9d 224.6 | 12.7 | – | 0.21 | 0.29 | 0.29 | 0.12 | **1.29** | 0 / 0.93 | 0.57 (hand) |
| 9d 231.7 | 13.1 | – | 0.55 | 0.56 | 0.53 | 0.44 | 0.65 | 0 / 0.66 | hand (bar 2751) |
| 9d 569.0 | 6.0 | – | 1.17 | 1.23 | 1.24 | 1.18 | 1.30 | 0.19 / 0.28 | 0.00 |
| 9d 758.9 | 5.8 | R | 1.50 | 1.56 | 1.55 | **1.94** | 1.71 | 0.44 / 0.48 | 0.71 |
| 9d 775.0 | 3.2 | R | 5.18 | **9.81** | 9.53 | 2.36 | 1.29 | 0.53 / 0.55 | 1.00 |

EVIDENCE: wire plus fork cache, `high_angle_chain.py`, and the fork's own status bits. Reading the table:

1. **In blinker turns at 3–7 m/s, the fork's controlsd adds 2–4 times the model's motion.** Compare the
   desiredCurvature column with the model column in the 9c rows and in 9d at 775 s.
2. **Where the setpoint exceeds the pre-limiter angle, the fork's error clip adds motion.** See 9d at 138 s and
   759 s. The clip rebuilds the setpoint from the *measured* wheel every frame (±ANGLE_ERROR_MAX(v)).
3. **The wheel follows the setpoint.** On every hands-off-ish row, wheel rms is within a factor of 0.8–1.2 of
   setpoint rms. The firmware neither amplifies nor adds a resonance in 1–5 Hz.
4. **The 12–13 m/s rows on 9d are the driver's hand, not hunting.** The bar is persistent and one-sided, with a
   mean of 1726 and 2751. It does not fit the wheel's inertial reaction (R² 0.00–0.02). The firmware freeze held
   69–100 % of the time.

### 2.2 The mechanism in controlsd: the turn-initiation lead closes a loop on the wheel

Source: fork Dom `c6452361e`, `selfdrive/controls/controlsd.py`, the "Turn-initiation lead (see TURN_LEAD_*)" block.
It is active with a blinker on, lane change off, and 3 ≤ vEgo < 7 m/s:

```
engaged_ratio = abs(self.curvature) / abs(lead_curvature)      # self.curvature = MEASURED, from steeringAngleDeg
engage_w      = clip((1 - engaged_ratio) / (1 - 0.5), 0, 1)
lead_curvature *= speed_w * engage_w                            # in 0.5 < ratio < 1:  lead = 2 (L - kappa_meas)
if lead*dir > max(new*dir, 0): new_desired_curvature = lead_curvature
```

In the linear zone the commanded curvature falls by 2 for each unit the wheel gains. The EPS angle loop then
follows with roughly unity gain and a 50–180 ms lag. That is a feedback loop with gain magnitude 2 around a lag,
which predicts a sustained back-and-forth.

| test | 9c 331.6 | 9c 702.7 | method / tag |
|---|---|---|---|
| frames in engage_w's linear zone | 52 % | 56 % | replay from logged plan, vEgo, blinker and measured curvature; EVIDENCE |
| sign of rate-limited desiredCurvature steps predicted, WITH the lead | **100 %** (53 steps) | **97.7 %** (131) | one-step replay through clip_curvature; EVIDENCE |
| same, model only | 81 % | 71 % | EVIDENCE |
| corr(fork-added curvature, measured curvature), 1–5 Hz | −0.55 (390 ms lag), slope −0.87 | **−0.82 (20 ms), slope −1.48** | code predicts −2 where the lead binds; EVIDENCE |
| the 0x18F bar during the episode | — | bar ≈ 0.61 × θ̈, R² 0.88 | **it is the wheel's inertial reaction, not a hand**; EVIDENCE (`high_angle_probe.py`) |

**Not replayed:** below 4.47 m/s the curvature HOLD block takes over (rows 9c 746 and 780, 9d 775), and the
step-sign test there is 0.20 on 9d at 775 s. That block also captures the measured wheel ("nudge-to-commit"
latches `self.curvature`). **BELIEF:** it is the same class of wheel-referenced setpoint, but it is unverified.

**BELIEF, not simulated:** that the lead loop is *unstable*, rather than merely lightly damped, with the 250 deg/s
cap and the EPS lag. A closed-loop sim of the lead, jerk clip, 250 deg/s limiter and the V299 inner loop would
settle it.

### 2.3 Firmware-side observations: reports, not the cause

- **The V299 1229 freeze toggles on reaction spikes at high angle.** In 9c at 704–707 s the duty was 0.11 with
  2.3 toggles per second, while the bar was the wheel's inertia (R² 0.88). steeringPressed flickered with it, at
  0.06–0.61. The reader's F6b counts **0** hands-off onsets because its hands-off filter (|bar| < 300) labels these
  frames as hands-on. **The instrument cannot see a reaction-driven freeze relay at high angle.** EVIDENCE.
- **Small-correction stick is unchanged or worse.** Dwells per minute are 6.8–15 at 0–5 m/s against V282's
  0.4–0.6. V299 declared this as not addressed. EVIDENCE.
- **Firmware residual.** The wheel minus the fitted setpoint is 1.7–3.6° rms in the high-angle episodes. That
  residual includes the hand and the lag. A separate firmware hunt is not resolved by this data.

### 2.4 Answer to the brief's question

**Task 1b should tune the FORK, not the firmware PID cells.** The fork levers, as observations rather than
proposals:
- the turn lead's measured-curvature engagement fade, `TURN_LEAD_ENGAGED_FRAC` and the `engage_w` form;
- the curvature-hold capture below 4.47 m/s;
- the error clip, which re-references the setpoint to the measured wheel;
- `AccordAngleMaxRate` 250, which passes more of the lead's motion than 120 would.

The firmware's high-angle tracking is close to unity in 1–5 Hz.

## 3. Things that contradict the V299 design expectations

1. **The cap-250 dose flew in place of config A on both routes**, so the drive-2 card's config-A clauses misfire:
   F1's snap clause and X3. EVIDENCE.
2. **F6 fails on r9c.** The design predicted no stall-surges in the sim; r9c reads 45–50 per minute with a 3.53×
   enrichment. **BELIEF:** the enrichment counts reaction-driven bar crossings, given the 2.2 finding.
3. **The 1.6–3 Hz hard-turn wheel-rate is 13–22 deg/s against V298's 8.5 and V282's 3.5–4.0.** That is
   consistent with the fork lead and limiter loop at the higher rate cap. BELIEF on the attribution.
4. **The hands-off definition (|bar| < 300) excludes almost every high-angle episode.** Only 0.0–0.1 s per route
   at |θ| ≥ 60° counts as hands-off. So none of the reader's hands-off turn-in, cap or F10 clauses can see sharp
   turns. EVIDENCE.

## 4. Commands (each ≤ 10 s on a cached route; first extraction ≈ 65 s once per route)

```
export ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
python rlog-tools/studies/angle_loop/angle_loop_drive_read.py 75604b0a432fdc89_0000009c--7f2f4d267c   # 5-6 s cached
python rlog-tools/studies/angle_loop/angle_loop_drive_read.py 75604b0a432fdc89_0000009d--371ec93849
python rlog-tools/studies/angle_loop/high_angle_hunt.py <9c> <9d> <79> --plot analysis-2020accord/figures/v299_latest --json _scratch/out/hah_latest.json   # 8 s, 3 routes
python rlog-tools/studies/angle_loop/high_angle_chain.py <route> t0:t1 ...     # model -> desired -> carControl -> 0xE4 -> wheel
python rlog-tools/studies/angle_loop/turn_lead_replay.py <route> t0:t1 ...     # c6452361 turn-lead replay
python rlog-tools/studies/angle_loop/high_angle_probe.py <route> t0:t1 ...     # bar vs inertial reaction, freeze toggling
```

Figures: `analysis-2020accord/figures/v299_latest/highangle_0000009c_7f2f4d267c.png`, `…0000009d_371ec93849.png`,
`…00000079_a1f5d2a272.png`. They show wheel, setpoint, fork pre-limiter angle, tap and bar per episode.
Reader outputs: `_scratch/angle_loop/drive-read/read_r9c_7f2f4d_al.{json,txt}`, `read_r9d_371ec9_al.*`.
