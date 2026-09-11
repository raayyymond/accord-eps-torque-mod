# The colleagues' LPF as a DIAGNOSTIC, and the lag-free alternatives in the openpilot pipeline

Date: **2026-09-10**. Read-only analysis of the operator's own fork
`C:\Users\dudei\Desktop\Projects\openpilots\raayyymond-StarPilot\StarPilot`, branch **Dom**,
HEAD `0f98d8c75`. **No edits were made to the fork.** Scripts in
`C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\` (`lpf_math.py`, `recon.py`,
`df_and_chain.py`, `lsb_gain.py`, `notch.py`).

Every decision-bearing claim is marked **[E]** EVIDENCE (with a `file:line` cite and the method) or
**[B]** BELIEF.

> 🛑 **STANDING INSTRUCTION IN CONFLICT.** `memory/feedback/builds/feedback-no-openpilot-side-modifications.md`
> (operator, 2026-07-28) says *"I do not want openpilot side modifications… no notch filters, no low-pass,
> no STEER_DELTA / rate-limit retuning."* This document was commissioned by the orchestrator on 2026-09-10
> off the operator's own new framing ("prevent the ring EXCITATION instead"), so it **evaluates** fork-side
> levers as asked. Whether any of them is actually adopted is the operator's call, not this report's, and
> the 2026-07-28 instruction stands until he lifts it.

---

## 0. Headline, before the detail

1. **The colleagues' filter is not aimed at 20 Hz.** Its time constants span **0.10–0.28 s**, i.e. corner
   frequencies **1.59 → 0.57 Hz**. If 20 Hz were the target, `tau = 0.05` already buys −16 dB there for
   50 ms of lag; they went to 0.28 s and paid **−59° of phase at 1 Hz**. A designer paying that much
   phase in the path-following band is chasing something **well below 20 Hz** — from the magnitude
   profile, roughly **3–10 Hz**. [E for the taus and the response; B for the target band]
2. **The commit that added it is not the one the 09-07 trace names**, and **`f69599fab` "honda wobble" is
   not about command smoothing at all** — it edits the driver-**steering-pressed debounce**. Corrections
   in §1.
3. ⭐ **The verbatim symptom, from the code itself:** *"Extra damping for the tiny near-center commands
   where both modified EPS firmwares still show hunting and escalating sway."*
   (`opendbc_repo/opendbc/car/honda/carcontroller.py:44-45`, added by `c612f7a10` "tüne", 2026-05-01.)
   **"Sway" is a path-level, low-frequency object. Our grinding is a hands-off 20 Hz acoustic ring with
   the wheel nearly still.** They are almost certainly not the same object. [E for the quote; B for the
   non-identity]
4. 🛑 **The brief's premise needs inverting.** The kit's own wire measurement says the command's 20 Hz
   line is **63 % feedback-path and only 9 % open-loop**
   (`memory/accord/mechanism/accord-0xe4-command-is-not-a-staircase-slew-cap-is-the-excitation-grind1-is-a-rung-bell.md`).
   So **reconstructing the model staircase attacks the 9 %; filtering the MEASUREMENT attacks the 63 %.**
   The staircase work is the smaller lever.
5. 🛑 ~~⭐ **The single best lag-free lever is a narrow notch on `measurement`** (`latcontrol_torque.py:237`).
   A Q = 5 notch at 20 Hz costs **−0.5° at 1 Hz and −2.6° at 5 Hz** and **zero command lag and zero slew**,
   against the colleagues' LPF at −42° / −69°. It is testable without touching the ECU.~~
   **RETIRED 2026-09-10 — see APPENDIX B.** The filter-cost arithmetic stands, but the premise does not:
   the excitation enters through the **setpoint/feedforward** path (80–97 % of the command's 13–26 Hz
   content), and after projecting out the camera clock the residual command↔angle coherence at the line
   is **0.022**. There is no echo at the measurement to cut. It would be a confirmation experiment, not a fix.
6. 🛑 **Raising `STEER_DELTA_UP` goes the WRONG way on excitation**, even though it goes the right way on
   authority. Simulated describing function: when the limiter is hard-driven, it *swallows* a small 20 Hz
   rider (|N| = 0.015); raising the limit to 9 restores |N| = 1.000. Numbers in §5.5.

---

## 1. The colleagues' fix, exactly — and three corrections to the 2026-09-07 trace

### 1.1 The commit arc (all `[E]`, `git show` on the fork, read-only)

| commit | date | author | what it actually did |
|---|---|---|---|
| **`345747a04` "more stuff"** | 2026-04-30 | firestar5683 | **ADDED** `get_civic_bosch_modified_torque_lpf_tau`, `get_civic_bosch_modified_steering_pressed`, `self.torque_lpf`, and the call site. Original taus: 0.09 / 0.11 / 0.10 / 0.11 / 0.12 / 0.15. |
| `e57d75a3d` "honda" | 2026-05-01 | firestar5683 | Added `HondaFlags.EPS_MODIFIED = 8192` (`values.py:86`), set it in `interface.py:114-115`, and replaced the `dashcamOnly + testing_ground` gate with `_modified_civic_standard_active()` = `CIVIC_BOSCH and EPS_MODIFIED`. **This is what put the LPF on the road rather than behind a test flag.** |
| `617aa0a5d` "honda I6" | 2026-05-01 | firestar5683 | carcontroller + `latcontrol_pid` + `latcontrol_torque` (not LPF-adding). |
| **`f69599fab` "honda wobble"** | 2026-05-01 | firestar5683 | 🛑 **NOT the LPF.** It rewrites `get_civic_bosch_modified_steering_pressed` — the **driver-override debounce** (trigger times 0.08/0.20/0.70 s, rise rates 1.0/0.75/0.50, decay 6→8/s). |
| **`b77341c80` "honda lpf"** | 2026-05-01 | firestar5683 | **RE-TUNED** the taus **upward** (0.09→0.10, 0.11→0.12, 0.10→0.12, 0.11→0.13, 0.12→0.15, 0.15→0.18) and added a `low_speed` branch and a `sign_change and abs<0.25` branch (0.22/0.18). |
| **`c612f7a10` "tüne"** | 2026-05-01 | firestar5683 | Raised the near-centre taus to **0.28** and added the highway `abs<0.12` branch — **and wrote the symptom comment**. |
| `fc4a53c02` "update" | 2026-05-02 | firestar5683 | Removed the testing-ground `STEER_CAN_MAX` override path; the LPF survived (`git log -S torque_lpf` returns only `345747a04`). |

🛑 **Correction 1 to `STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md` §6:** `b77341c80` did **not** add
`get_civic_bosch_modified_torque_lpf_tau`; `345747a04` (2026-04-30) did. `b77341c80` raised its taus by
~10–25 %. [E — `git log -S get_civic_bosch_modified_torque_lpf_tau` returns exactly one commit, `345747a04`]

🛑 **Correction 2:** `f69599fab` "honda wobble" is **not** "presumably the symptom commit that motivated"
the LPF. Its whole diff is in the steering-pressed debounce. "Wobble" there names a **false-override /
hand-detection** problem, not a command-oscillation problem. [E — full `git show f69599fab`]

🛑 **Correction 3 (matters most for us):** the 09-07 trace lists three stages that "already smooth the
command" and calls `jerk_filter` one of them. **`jerk_filter` is transparent to the setpoint at
12–26 Hz** — see §4.2. It filters a *difference* term that vanishes at HF, leaving the setpoint equal to
the delayed raw curvature.

### 1.2 The tau schedule as it stands at HEAD
`opendbc_repo/opendbc/car/honda/carcontroller.py:27-65` [E]

```
highway (v > 22.35 m/s):   |cmd| < 0.12            -> 0.18 if sign_change else 0.16
                           sign_change & Δ > 0.15  -> 0.10
                           else                    -> 0.12
sign_change & |cmd| < 0.25 -> 0.28 (low_speed, v<13.41 m/s) / 0.22
|cmd| < 0.12               -> 0.28 (low_speed) / 0.20      <- the "hunting and escalating sway" rule
low_speed:  Δ>0.50 -> 0.14 | Δ>0.20 -> 0.16 | Δ>0.05 -> 0.18 | else 0.22
otherwise:  Δ>0.50 -> 0.12 | Δ>0.20 -> 0.13 | Δ>0.05 -> 0.15 | else 0.18
```
Applied at `carcontroller.py:294-298` as `alpha = DT_CTRL/(tau+DT_CTRL); lpf = alpha*cmd + (1-alpha)*lpf`,
i.e. a **one-pole IIR at 100 Hz**, with `torque_lpf` and `prev_torque_cmd` reset to 0 whenever the
filtered steering-pressed flag fires or `latActive` drops (`carcontroller.py:290-302`).

### 1.3 What that filter does, numerically [E — `_scratch/lpf_math.py`, exact discrete response at fs = 100 Hz]

| tau (s) | alpha | fc (Hz) | \|H\| @1 Hz | @5 Hz | @7 Hz | @12 Hz | @16 Hz | @20 Hz | @26 Hz | dB @20 Hz | phase @1 Hz | DC group delay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.10 | 0.0909 | 1.592 | 0.835 | 0.292 | 0.214 | 0.128 | 0.099 | 0.081 | 0.065 | **−21.9** | −31.6° | 100 ms |
| 0.12 | 0.0769 | 1.326 | 0.787 | 0.248 | 0.181 | 0.108 | 0.083 | 0.068 | 0.055 | −23.4 | −36.4° | 120 ms |
| 0.15 | 0.0625 | 1.061 | 0.717 | 0.202 | 0.146 | 0.087 | 0.067 | 0.055 | 0.044 | −25.2 | −42.5° | 150 ms |
| 0.18 | 0.0526 | 0.884 | 0.652 | 0.170 | 0.123 | 0.073 | 0.056 | 0.046 | 0.037 | −26.8 | −47.5° | 180 ms |
| 0.22 | 0.0435 | 0.723 | 0.578 | 0.141 | 0.101 | 0.060 | 0.046 | 0.038 | 0.031 | −28.5 | −52.9° | 220 ms |
| 0.28 | 0.0345 | 0.568 | 0.488 | 0.112 | 0.080 | 0.048 | 0.036 | 0.030 | 0.024 | **−30.5** | **−59.0°** | 280 ms |

**Attenuation across 12–26 Hz: −21.9 dB (tau 0.10) to −30.5 dB (tau 0.28).**
**Price: 100–280 ms of DC group delay and 32°–59° of phase lag at 1 Hz.** The operator's objection
("delays and limits output slew") is quantitatively correct — this is a very expensive way to buy 25 dB
at 20 Hz.

### 1.4 ⭐ Why tau is VARIABLE — and what that reveals

The schedule is a **deliberate authority-preserving compromise**, and its shape names the symptom's
operating point [E for the code, B for the reading]:

| scheduled on | direction | what it protects / implies |
|---|---|---|
| `torque_delta` large → **small** tau | less filtering on fast slew | *"do not blunt real transients"* — they knew the lag cost |
| `v_ego` high → **small** tau | least filtering on the highway | the symptom is **not** a highway problem |
| `v_ego` < 13.4 m/s → **largest** tau (0.28) | most filtering at low speed | **the symptom is a LOW-SPEED problem** |
| `abs(cmd) < 0.12` → **largest** tau | most filtering near centre | **the symptom is a NEAR-CENTRE problem** |
| `sign_change` → larger tau when small | most filtering on zero crossings | **the symptom involves the command REVERSING SIGN about zero** |

Low speed + near centre + sign-reversal + *"hunting and escalating sway"* is the textbook signature of a
**gain/stiction limit cycle about the straight-ahead position** — the wheel overshoots centre, the
controller reverses, it overshoots the other way, and the amplitude grows. A raised near-centre assist
map (which is what "EPS modified" buys) is exactly what turns a stable centre into a hunting one.
**[B, but well grounded: three independent code signals — the speed gate, the magnitude gate, and the
sign-change gate — all point at the same operating point, and the author wrote the word "sway".]**

That is **not** our object. Ours is 20 Hz, hands-off, at **high LKAS demand (idx ≥ 20)**, present at
**every speed bin 0–20 m/s**, with the wheel nearly still (`docs/STATE.md` "THE TWO-OBJECT PICTURE";
`memory/accord/mechanism/accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated.md`).

---

## 2. Is the colleagues' car's situation ours?

| | Civic Bosch Modified | Accord (ours) |
|---|---|---|
| `lateralParams.torqueBP/V` | `[[0,4096],[0,4096]]` (`interface.py:136-137`) | `[[0,4096],[0,4096]]` (`interface.py:148`) — **identical** |
| `STEER_MAX` | 4096 | 4096 — **identical** |
| `STEER_LOOKUP_BP/V` | identity, mirrored (`values.py:47-50`) | identity, mirrored — **identical** |
| `STEER_DELTA_UP/DOWN` | 3 (all Honda, `values.py:39-40`) | 3 — **identical** |
| `HondaFlags.EPS_MODIFIED` | set (`test_honda.py:139`) | **also set** (`test_honda.py:144`, fw `39990-TVA,A150`) |
| gate on the LPF | `CIVIC_BOSCH and EPS_MODIFIED` (`carcontroller.py:253`) | **excluded by the fingerprint half only** |
| lateral controller | torque (`test_honda.py:165`) | torque (operator's `ForceTorqueController = True`) |

[E, all cites above]

🛑 **So the command scale, the rate limiter and the EPS-modified flag are byte-for-byte the same, and the
only thing keeping the LPF off our car is `carFingerprint == CAR.HONDA_CIVIC_BOSCH`.** Enabling it for
the Accord is a one-token change — which is precisely why it is worth being explicit that we should not.

**What `EPS_MODIFIED` means [E]:** `interface.py:109-115` sets the flag purely from the **presence of a
comma in the EPS firmware version string** — it is a *detection* of a modified EPS, not a behaviour. On
the non-Bosch Civic and the CR-V 5G it *also* swaps in raised `torqueBP/torqueV` tables with documented
stock-vs-modified request/output values (`interface.py:124-130`, `:176-181`). On **CIVIC_BOSCH and on the
ACCORD it changes only the (unused, PID-path) `kpV/kiV`** — no table swap. So the two platforms' modified
EPS firmwares are third-party mods of unknown content, related to ours only by category.

**Verdict [B]:** the *platform* is a close structural analogue; the *symptom* is not demonstrably the same
object. A wobble on a different car with a different third-party EPS mod, at low speed and near centre,
is not our 20 Hz high-demand ring. **I found no evidence in the fork — no issue link, no commit body, no
other comment — describing frequency, audibility, or hands-off behaviour for their symptom.** The
`c612f7a10` comment is the only symptom description that exists.

**Anything else in the fork touching the Accord's command smoothing?** [E — `git log` on
`carcontroller.py`, `hondacan.py`, `latcontrol_torque.py`, `controlsd.py`; symptom-word grep over the
whole honda package] **No.** The only Honda command LPF is the Civic one. The only Accord-specific filter
is `accord_angle_des_rate_filter` (feedforward-side, `latcontrol_torque.py:156,581`). The "wobble" hits
elsewhere in the history (`7ea096686` / `b2ded7915` "STOCK LONG I6 wobble fix?" + its revert) are
**longitudinal**.

---

## 3. Corrected picture of the openpilot pipeline (what actually reaches the EPS)

Four things the 09-07 trace did not have, all **[E]**:

1. 🛑 **`measurement` is the STEERING ANGLE, not yaw rate.**
   `latcontrol_torque.py:236-237`:
   `measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg - params.angleOffsetDeg), CS.vEgo, params.roll)`;
   `measurement = measured_curvature * CS.vEgo**2`. Source: `carstate.py:187`
   `ret.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE"]` — CAN **0x14A** (`BO_ 330
   STEERING_SENSORS: 8 EPS` in `honda_civic_hatchback_ex_2017_can_generated.dbc:520-521`), signal scale
   **−0.1 deg/LSB**, at **100 Hz** (the same 0x14A frame the kit's own caves write telemetry into).
   **It is not filtered anywhere before `error`.**
2. 🛑 **The D term is ZERO.** `self.pid = PIDController([INTERP_SPEEDS, KP_INTERP], KI, rate=1/self.dt)`
   (`latcontrol_torque.py:80`) leaves `k_d = 0.` (`opendbc/car/common/pid.py:6`), and no code anywhere
   under `selfdrive/controls/` assigns `_k_d`. `measurement_rate` and its 2.0 Hz filter
   (`latcontrol_torque.py:93,290`) are computed and passed as `error_rate=` but multiplied by zero.
   ⇒ **The measurement reaches the command only through P (and a negligible I).**
3. **`modelV2.action.desiredCurvature` is ALREADY low-passed inside modeld**, with the same one-pole
   form the colleagues used: `smooth_value(desired_curvature, prev_action.desiredCurvature,
   lat_smooth_seconds)` at `modeld.py:346` and `:375`, `LAT_SMOOTH_SECONDS = 0.1` (`modeld.py:65`), run
   at `DT_MDL = 0.05` ⇒ alpha = 0.3935 **at the 20 Hz model rate**. It smooths the *sample sequence*; the
   5-tick hold that follows is untouched. It is a **Param** (`LatSmoothSeconds`, `modeld.py:898`) and the
   controller *compensates* for it by adding it to the lead: `lat_delay = liveDelay.lateralDelay +
   lat_smooth_seconds` (`controlsd.py:806-807`, `:288`).
4. **`delay_frames` does not dither on this car.** `int(np.clip(lat_delay/dt, 1, 100))`
   (`latcontrol_torque.py:276`) would step whole buffer samples if `lat_delay` moved, and `lagd`
   republishes at **4 Hz** (`lagd.py:417-422`). But the operator runs `UseAutoSteerDelay = False`, which
   takes `lagd.py:236-237` `liveDelay.lateralDelay = starpilot_toggles.steerActuatorDelay` = **0.2 s
   constant**, so `lat_delay = 0.3` and `delay_frames = 30`, fixed.
   ⚠ **If he ever turns `UseAutoSteerDelay` on, this becomes a 4 Hz discreteness injector** that steps the
   setpoint by a whole 10 ms buffer sample.

**Ruled out as fixed-cadence injectors [E]:**
- The variable steer ratio (`controlsd.py:481-492`, recomputed every 100 Hz tick from the live angle) —
  `HONDA_ACCORD_STEER_RATIO_V` is **flat at 16.00 from 0 to 60 deg**
  (`latcontrol_vehicle_tunes.py:85-86`), and above 60 deg the local slope is ≤ 0.011 /deg, so a ±0.1 deg
  ring modulates `sr` by ≤ 7e-5 relative. Negligible.
- `torqued` / `liveTorqueParameters` — the kit has already established the controller ran the **defaults**
  1.689 / 0.212 on every modded route
  (`memory/.../accord-backcalc-the-car-needs-friction-0025-and-laf-5-to-10-torqued-cannot-validate-on-the-modded-eps.md`).
  Constant, no cadence.
- `lateralManeuverPlan` — `ignore`d in normal driving (`selfdrived.py:196`), so `controlsd.py:600` takes
  the model action.

---

## 4. What the existing filters actually remove at 20 Hz

[E — `_scratch/df_and_chain.py`, exact discrete responses, `FirstOrderFilter` alpha = dt/(rc+dt),
`common/filter_simple.py:8`]

| filter | site | rc (s) | \|H\| @7 Hz | @12 Hz | @20 Hz | what it is on |
|---|---|---|---|---|---|---|
| `jerk_filter` | `latcontrol_torque.py:90,282` | 0.1326 (1.2 Hz) | 0.164 | 0.098 | 0.062 (−24.2 dB) | `raw_lateral_jerk` |
| `measurement_rate_filter` | `latcontrol_torque.py:93,290` | 0.0796 (2.0 Hz) | 0.262 | 0.159 | 0.100 (−20.0 dB) | **dead — k_d = 0** |
| `accord_angle_des_rate_filter` | `latcontrol_torque.py:156,581` | 0.10 | 0.214 | 0.128 | 0.081 (−21.8 dB) | `d(angle_des)/dt`, FF "move" term only |
| modeld `smooth_value` | `modeld.py:346,375` | tau 0.1 @ 20 Hz | — | — | — | the model's **sample sequence** |

### 4.1 `accord_angle_des_rate_filter` — a remedy, not a knot source [E]
It is a plain one-pole on a derivative, initialised to 0 and primed on engage
(`latcontrol_torque.py:257-262`) precisely so re-engagement does not step. It removes **−21.8 dB at 20 Hz
from the feedforward move term.** It is not a stale-value artefact and it is not a knot source. Its only
cost is 100 ms of lag *on the FF rate term alone*, which is a deliberate plant-matching choice
(`HONDA_ACCORD_FF_RATE_RC = 0.10`, `latcontrol_vehicle_tunes.py:113`).

### 4.2 🛑 `jerk_filter` gives the SETPOINT no protection at 12–26 Hz [E]
`setpoint = expected_lateral_accel + desired_lateral_jerk * lat_delay` (`latcontrol_torque.py:284`), where
`expected = z^-30 · F` and `desired_lateral_jerk = H(z)·(F − z^-30·F)/lat_delay`. So
`setpoint/F = z^-30 + H(z)·(1 − z^-30)`, and since `|H| → 0` at HF the setpoint **tends to the raw
delayed curvature**:

| f | 7 Hz | 12 Hz | 16 Hz | 20 Hz | 26 Hz |
|---|---|---|---|---|---|
| \|setpoint/F\| | 1.080 | 0.878 | 0.912 | **1.000** | 0.943 |

**At 20 Hz the transfer is exactly 1.000.** The jerk filter cannot be counted as a smoothing stage for
the setpoint. It only shapes the *lead*.

---

## 5. ⭐ The lag-free alternatives, examined and scored

### 5.1 `clip_curvature` — how often does it bind, and what does it leave behind?

`drive_helpers.py:25-51`, called `controlsd.py:803`. `max_curvature_rate = MAX_LATERAL_JERK(5.0) *
jerk_factor / v_ego**2`, clamped per `DT_CTRL`. **Stated in the units that make it speed-independent:**

> **the cap is 0.050 m/s² of lateral acceleration per 100 Hz tick — 0.250 m/s² per model frame.** [E]

Two different discontinuities come out of it, and the brief's question needs them separated:

- **NOT binding → the ZOH step survives intact.** `new_curvature = new_desired_curvature` exactly, i.e. a
  **zeroth-order** discontinuity every 50 ms, spectral envelope ~1/f. This is the dominant 12–26 Hz
  injector.
- **Binding → a ramp at the cap, with a slope break** when it catches up or when the next model frame
  arrives: a **first-order** discontinuity, envelope ~1/f². Milder.

⇒ **Binding *reduces* 12–26 Hz energy; it is not itself the injector.** [E — simulation]

| reconstruction | 12–26 Hz band rms (m/s², arb. input) | ratio vs ZOH | added command lag |
|---|---|---|---|
| ZOH (today, non-binding) | 1.06e-2 … 1.66e-2 | **1.000** | 0 |
| `clip_curvature` slew-limited (today, binding) | 5.9e-3 … 6.5e-3 | **0.39 – 0.56** | 0 |
| **linear interpolation** between model frames | 4.8e-4 … 4.9e-3 | **0.045 – 0.29** | **+50 ms** |
| **linear extrapolation** from the last two frames | 2.5e-3 … 1.9e-2 | **0.24 – 1.14** | **0** |
| **model's own trajectory** (ideal limit) | ~0 | **~1e-9** | **0, or lag-NEGATIVE** |

[E — `_scratch/recon.py`; four input cases: a smooth 0.4 + 1.1 Hz path demand, and the same plus
frame-to-frame model innovation at sd = 0.01 / 0.03 / 0.10 m/s². **Synthetic input — the real binding
rate and innovation size are the sister agent `modelrate`'s measurement, not mine.** My synthetic bind
rate lands at 12–16 %.]

**Direct answers to the brief's questions:**
- **Slope-discontinuity size at each knot:** when binding, up to the full cap, **0.050 m/s² per tick**,
  which at the operator's `latAccelFactor = 1.6893` is **121.2 raw 0xE4 counts/tick**.
  ⚠ **Note the coincidence:** openpilot's own `rate_limit` is `3 × 0.01 × 4096 = 122.88 counts/tick`.
  **The ISO jerk cap and the Honda rate limit are the same slew to within 1.4 %.** [E for both numbers;
  **B** that this is why the kit's measured "top-1 % step = the cap" is hard to attribute to one of them.]
- **Would a slope-continuous reconstruction remove the knots at zero added lag?** **Partly and
  conditionally.** Linear *interpolation* removes 71–95 % of the band energy but costs exactly one model
  frame (**+50 ms**) — that is real lag and it is the thing the operator is trying to avoid. Linear
  *extrapolation* costs zero lag but is a discrete differentiator: it helps (×0.24) when the model output
  is clean and **hurts (×1.14) when the frame-to-frame innovation is large**. Only the **model's own
  published trajectory** is both slope-continuous and lag-free.
- **Does openpilot already publish future curvature?** **Yes.** `modelV2.action` is a scalar
  (`cereal/log.capnp`, `struct Action { desiredCurvature; desiredAcceleration; shouldStop; }`), but
  **`modelV2.orientationRate` is a full `XYZTData` trajectory with its own `t` axis**, and the
  longitudinal planner already converts it to curvature live:
  `longitudinal_planner.py:682` `curvatures = np.interp(T_IDXS_MPC, ModelConstants.T_IDXS,
  model_msg.orientationRate.z) / np.clip(v, 0.3, 100.0)`. `controlsd` also already reaches into the plan
  (`limit_curvature_to_plan`, `controlsd.py:608`). [E]
  ⇒ **A reconstruction that interpolates along the model's own trajectory between action publishes is
  slope-continuous, needs no new message, and — if sampled at *now* rather than at the frame's own
  timestamp — is lag-NEGATIVE by up to one model frame (50 ms).**
  🛑 **Honest caveat:** `orientationRate.z/v` is the **plan**, a different object from the **action head**
  that `action.desiredCurvature` comes from. Substituting it outright changes what the controller is
  tracking. The minimal correct form keeps `action.desiredCurvature` as the per-frame **anchor** and uses
  the plan only for the **intra-frame shape**. That preserves the action head's decision. [B]

### 5.2 ⭐ The measurement side — where the 63 % lives

`latcontrol_torque.py:236-237,296`. Channel **0x14A `STEER_ANGLE`**, **100 Hz**, **0.1 deg/LSB**,
**unfiltered**, entering only through **P**.

**Aliasing:** a 20 Hz line sampled at 100 Hz is at 0.2 of Nyquist — **there is no aliasing**. [E] The
residual sampling concern is the **beat** between the car's 100 Hz 0x14A cadence and controlsd's own
100 Hz `Ratekeeper` (`controlsd.py:947`), which occasionally repeats or drops a sample. That is a
broadband, sub-Hz-rate click, **not** a 20 Hz line. [B]

🛑 **What matters instead is the QUANTISER.** One LSB = 0.1 deg. Propagating one LSB through
`VM.calc_curvature` (Accord specs, `values.py:188`; `sR = 16.00` on-centre) × `v²` × the **P** gain
(`k_p = 0.6`, pinned every frame by `controlsd.py:449-450`, plus the `low_speed_factor` term
`latcontrol_torque.py:294,298`) ÷ `latAccelFactor 1.6893` × `STEER_MAX 4096`:

🛑 **THE TABLE BELOW IS SUPERSEDED — 2026-09-10. Both of its parameters were taken from module
constants, and both are wrong on the wire. Use APPENDIX B's table instead.** It is kept, struck, so the
error is visible rather than silently rewritten.

| v (m/s) | 5 | 8 | 10 | 12 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|
| ~~**raw 0xE4 counts per 0.1 deg LSB**~~ SUPERSEDED | ~~13.2~~ | ~~14.5~~ | ~~15.9~~ | ~~17.4~~ | ~~20.6~~ | ~~28.4~~ | ~~39.0~~ | ~~52.8~~ |
| ~~wheel-angle ring implied by 30 counts (deg)~~ SUPERSEDED | ~~0.227~~ | ~~0.207~~ | ~~0.189~~ | ~~0.172~~ | ~~0.146~~ | ~~0.106~~ | ~~0.077~~ | ~~0.057~~ |

[SUPERSEDED — `_scratch/lsb_gain.py`, formulas from `opendbc/car/vehicle_model.py`, but with
`latAccelFactor = 1.6893` and `k_p = 0.6` read from carParams / the module constant rather than measured.
Corrected values, with both parameters measured on the wire and dated, are in **APPENDIX B**.]

⭐ **The record's 20 Hz command amplitude is 15–40 raw counts (`docs/STATE.md` "THE TWO-OBJECT PICTURE").
That is ONE-TO-THREE quantiser LSBs of steering angle.** The echo is a **quantiser-scale dither**, not a
faithful reading of the ring. **[B — the gain chain is EVIDENCE, the inference that the ring lives at
1–2 LSB follows from combining it with the kit's measured amplitude, and should be checked against the
actual 0x14A `STEER_ANGLE` sample sequence in a grinding window.]**

**Why this is the best lever:** the kit measured the command's 20 Hz line at **63 % feedback / 9 %
open-loop**, and grind #1 as a **rung bell with ζ ≈ 0.026 and positive damping**, so cutting excitation
shrinks it and the 8–13 % direct share is a **floor** of the benefit
(`memory/.../accord-0xe4-command-is-not-a-staircase-slew-cap-is-the-excitation-grind1-is-a-rung-bell.md`).
Filtering here costs **no command lag and no slew** — it is inside the *feedback* path, not the *command*
path, so the model's output is never delayed or clipped.

**Cost, honestly:** a measurement filter **is** inside the openpilot outer loop, so it does spend outer-loop
phase. A **notch** spends almost none away from its centre [E — `_scratch/notch.py`, biquad at fs = 100]:

| | 1 Hz | 3 Hz | 5 Hz | 7 Hz | 12 Hz | 20 Hz |
|---|---|---|---|---|---|---|
| notch 20 Hz **Q = 3**: \|H\| / phase | 1.000 / −0.83° | 0.999 / −2.53° | 0.997 / −4.36° | 0.994 / −6.46° | 0.968 / −14.5° | **0.000** |
| notch 20 Hz **Q = 5**: \|H\| / phase | 1.000 / −0.50° | 1.000 / −1.52° | 0.999 / −2.62° | 0.998 / −3.89° | 0.988 / −8.81° | **0.000** |
| colleagues' LPF tau = 0.15 on the **command** | 0.717 / **−42.5°** | 0.324 / −65.8° | 0.202 / **−69.5°** | 0.146 / −69.2° | 0.087 / −63.7° | 0.055 |

🛑 **A Q = 5 notch on the measurement is ~85× cheaper in 1 Hz phase than the LPF and costs nothing on the
command path at all.** ⚠ Two residuals: (a) it interacts with the 7 Hz strong-turn ring only at −3.9°,
which is fine, but (b) **if the ring relocates the way V289's firmware notch relocated it (20 Hz → 15–17 Hz),
a fixed 20 Hz notch goes blind.** A wider Q = 2 notch (−9.6° at 7 Hz, 0.749 at 16 Hz) hedges that at a
real phase cost. The V289 lesson applies to this placement too.

### 5.3 `jerk_filter` and `accord_angle_des_rate_filter` — remedy or artefact?
Answered in §4: `accord_angle_des_rate_filter` is a genuine −21.8 dB remedy on the FF move term and is
**not** a knot source; `jerk_filter` is a remedy **for the lead term only** and is **transparent to the
setpoint at 12–26 Hz**, so it should stop being counted as command smoothing.

### 5.4 Anything else injecting discreteness at a fixed cadence?
Only three, and two are conditional [E, §3]: the **20 Hz model ZOH** (the real one); **`delay_frames`
stepping at 4 Hz** *if* `UseAutoSteerDelay` is ever enabled; and the **0x14A 0.1 deg quantiser**, which is
not a cadence but is the amplitude floor of the whole feedback echo.

### 5.5 🛑 `rate_limit(±3/frame)` analysed as a nonlinearity — and the answer is uncomfortable

`carcontroller.py:306`; `rate_limit` is a pure `np.clip` on the delta (`opendbc/car/__init__.py:95-96`);
`R = 3.0 /s` normalised = **0.03/frame = 122.88 raw counts/frame**; `STEER_MAX = 4096`.

**Single-tone describing function** [E — `_scratch/df_and_chain.py`, first-harmonic extraction from a
byte-faithful simulation of the actual `clip` loop, 60 cycles, fs = 100]:

| f | A\* = R/2πf (counts) | A/A\* = 1 | 2 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| 1 Hz | 1956 | 1.000 / 0° | 0.637 / **−37.9°** | 0.255 / **−70.5°** | 0.127 / −79.2° | 0.064 / −82.8° |
| 3 Hz | 652 | 1.000 / 0° | 0.637 / −36.7° | 0.255 / −68.3° | 0.128 / −75.6° | 0.064 / −79.1° |
| 7 Hz | 279 | 1.000 / 0° | 0.640 / −34.3° | 0.257 / −60.8° | 0.129 / −68.4° | 0.064 / −71.6° |
| 20 Hz | 98 | 1.000 / 0° | 0.658 / −18.0° | 0.263 / −54.0° | 0.132 / −54.0° | 0.066 / −54.0° |

So: **up to −83° of phase lag, approaching the classic −90° asymptote, once drive exceeds ~2× the
saturating amplitude.** In the 1–3 Hz band that is a textbook PIO/limit-cycle mechanism — and it is a
plausible mechanism for the colleagues' *"hunting and escalating sway"* [B].

**Two-tone: a small 20 Hz rider (30 raw counts) on top of a large slow drive** [E, same script]:

| slow drive (counts) @ 2 Hz | 200 | 600 | 1200 | 2000 | 3000 |
|---|---|---|---|---|---|
| bind duty | 0 % | 0 % | 61.9 % | 99.8 % | 96.0 % |
| \|N\| seen by the 20 Hz rider | 1.000 | 1.000 | **0.401** | **0.015** | **0.007** |
| phase at 20 Hz | 0° | 0° | −4.3° | +39.6° | +56.8° |

🛑 **When the limiter binds, it does not phase-lag the 20 Hz rider — it SWALLOWS it.** A hard-driven rate
limiter outputs a triangle at the driving frequency and the small rider is simply gone.

**Therefore, raising `STEER_DELTA_UP`:**

| `STEER_DELTA_UP` | counts/frame | bind duty (2000 ct @ 2 Hz) | \|N\| at 20 Hz |
|---|---|---|---|
| **3.0 (today)** | 122.9 | 99.8 % | **0.015** |
| 4.5 | 184.3 | 67.9 % | 0.229 |
| 6.0 | 245.8 | 20.0 % | 0.747 |
| 9.0 | 368.6 | 0 % | **1.000** |

⇒ **Raising the limit reduces the limit-cycle / PIO tendency in the 1–3 Hz band (it removes up to 83° of
lag there) but ADMITS MORE 20 Hz command energy — up to 67× more.** Against our actual target these two
effects point opposite ways. **This is the opposite of what the brief anticipated, and it is measured, not
argued.** [E]

**Safety, stated honestly:** 🛑 **Nothing outside openpilot constrains this.** `opendbc/safety/modes/honda.h:274-282`
is the only 0xE4 check and it is `if (!controls_allowed) { if (data[0]|data[1]) tx = false; }` — **no
magnitude limit, no rate limit.** [E, read directly; corroborates
`memory/accord/signals/accord-honda-steer-slew-is-12288-not-300.md`.] So `STEER_DELTA_UP = 3` is pure
openpilot policy, and raising it means openpilot can slam the wheel harder with **no independent backstop
except the EPS firmware's own governor** — and this kit's own record is that raising authority is where
the undriveable builds came from. **I do not recommend raising it as an excitation lever. If it is ever
raised, it should be raised for authority, deliberately, with its own drive.**

---

## 6. The scorecard

`Δ(12–26 Hz)` is the fraction of the band energy **remaining** (lower is better). "Share attacked" is
against the kit's measured 63 % feedback / 9 % open-loop split of the command's 20 Hz line.

| # | lever | site | share attacked | Δ(12–26 Hz) | added **command** lag | authority / slew cost | impl. risk | no flash? |
|---|---|---|---|---|---|---|---|---|
| ~~**1**~~ | 🛑 **RETIRED 2026-09-10 (APPENDIX B)** — ~~20 Hz notch on `measurement`, Q 3–5~~ | `latcontrol_torque.py:237` | ~~63 %~~ → **~0 %; no echo there to cut** | ~0 at 20 Hz | 0 ms | none | — | ✅ |
| **2** | Trajectory-shaped reconstruction: anchor on `action.desiredCurvature`, shape from `orientationRate.z` | `controlsd.py:600` | 9 % | **~0** | **0, or −50 ms (LEAD)** | none; increases responsiveness | **medium** — plan/action semantics differ (§5.1 caveat) | **✅** |
| **3** | Widen the notch to Q 2, or track the line | as #1 | 63 % + relocation hedge | ~0 at 20 Hz, 0.75 at 16 Hz | 0 ms | −9.6° at 7 Hz — real | low | **✅** |
| **4** | Linear interpolation between model frames | `controlsd.py:600` | 9 % | **0.045–0.29** | **+50 ms** | one model frame of delay | low | **✅** |
| **5** | Linear extrapolation from the last two frames | `controlsd.py:600` | 9 % | 0.24 **…1.14** | 0 ms | none | **medium** — amplifies model innovation; can make it worse | **✅** |
| **6** | 1-LSB hysteresis deadband on `steeringAngleDeg` | `latcontrol_torque.py:236` | 63 % | large | 0 ms | none linear | 🛑 **high** — a deadband is itself a limit-cycle generator; the colleagues' symptom may BE one | **✅** |
| **7** | Raise `STEER_DELTA_UP` 3 → 4.5/6 | `values.py:39` | — | **worse (×15–50)** | 0 ms | **+authority** | 🛑 **high** — no panda backstop at all | ✅ |
| **8** | Raise `LatSmoothSeconds` (the colleagues' lever, already a Param) | `modeld.py:65,898` | both | good | **+100 ms per 0.1 s**, partly lead-compensated | **the operator's stated objection** | low | ✅ |
| **9** | Port the Civic LPF to the Accord (`carcontroller.py:253`) | one token | both | 0.03–0.13 | **+100…280 ms** | 🛑 −32…−59° at 1 Hz | trivial to do | ✅ |

**Recommended order: 1, then 2. 8 and 9 are what the operator asked to avoid, and the numbers back him.
7 is not an excitation lever and should not be sold as one.**

---

## 7. What I could not determine

1. **The colleagues' symptom's frequency, audibility, or hands-off character.** The only description in
   the entire fork is the eight-word comment at `carcontroller.py:44-45`. No issue link, no commit body,
   no test name. My 3–10 Hz inference is **[B]** from the tau magnitudes alone.
2. **What their third-party Civic Bosch EPS mod actually changes.** `EPS_MODIFIED` is only a fingerprint
   detection (`interface.py:109-115`); unlike the non-Bosch Civic and the CR-V there is no documented
   request/output table for it. I cannot say whether their modified map resembles ours.
3. **The real `clip_curvature` bind rate and the real model-frame innovation size.** My §5.1 table is
   synthetic. **The sister agent `modelrate` owns the wire measurement**; my ratios should be re-run on
   his measured innovation distribution before any of them is quoted as a prediction.
4. **Whether the ring in the measured angle really sits at 1–2 LSB.** The gain chain is EVIDENCE; the
   inference is BELIEF. **The check is cheap:** histogram the first difference of `0x14A STEER_ANGLE`
   inside a grinding window and see whether it is dominated by ±1 and 0 counts.
5. **Whether a measurement-side notch relocates the ring the way V289's firmware notch did.** V289
   removed the 20 Hz object entirely and a pre-existing 15–17 Hz pole took its margin
   (`docs/STATE.md`). A fork-side notch sits in a *different* loop (openpilot's 100 Hz outer loop, not the
   EPS's 1 kHz rate loop), so the V289 result does **not** transfer directly — but it is the obvious
   failure mode and should be the pre-registered revert signature.

### Runtime state that would change these answers
- **`UseAutoSteerDelay`** — currently False, giving a fixed `delay_frames = 30`. If turned on, add a 4 Hz
  whole-sample setpoint step to the injector list (§3.4).
- **`LatSmoothSeconds`** — if the operator has ever moved it off 0.1, the model staircase's step size and
  `lat_delay` both change.
- **`ForceAutoTune`** (True) with **torqued never validating on the modded EPS** — the whole §5.2 gain
  table assumes `latAccelFactor = 1.6893`. A live-learned LAF of 5–10 (which the back-calc memory says the
  car actually wants) would scale the counts-per-LSB down by 3–6×.
- **`SteerKP`** — pinned at 0.6 and overwriting the Kp table every frame (`controlsd.py:449-450`). The
  §5.2 table is computed at 0.6; at the platform table's low-speed values (11.5 at 5 m/s) the per-LSB gain
  is ~3× higher.
- **`AccordVariableSteerRatio` / `SteerRatio` level** — moves `sr` in the measurement path
  (`controlsd.py:481-492`); a level of 14.3 instead of 16.0 raises every §5.2 number by 12 %.

---

# APPENDIX A — the 1–2 LSB question, taken to the wire (2026-09-10)

Run at the orchestrator's request, against the rlogs, on **five routes across four builds**:
**r39 (V282), r5e_v288 (V288r2), r62_v289 + r63_v289 (V289), r35 (V281r3)**. Band **18–22 Hz** on
V281r3/V282/V288 and **13–18 Hz** on V289 (the 18–22 Hz gate is blind to V289's relocated line).
Windows: the census recipe (2 s / 0.5 s step, lateral-engaged, `bar` line prominence ≥ 8 **and**
`bar` band amplitude ≥ 40 raw), **2,127 present windows** against speed- and demand-**matched**
baselines. Scripts `rlog-tools/studies/grind/angle_lsb_echo_2026_09_10.py` and
`rlog-tools/studies/grind/angle_lsb_echo_xspec_2026_09_10.py`; full output in
`rlog-tools/studies/grind/_scratch/angle_lsb_echo_*.txt`.

## A0. Verdict in one paragraph

**The sub-LSB claim is CONFIRMED, and by a wider margin than §5.2 guessed. The claim that this
quantiser ACCOUNTS FOR the command's ring line is NOT established, and the simple version of it is
falsified.** And a decision-bearing claim of my own in §5.5 is **WRONG at the real operating point**;
it is corrected in A5.

## A1. The angle ring is 0.17–0.28 LSB — a quarter of one quantiser step [EVIDENCE]

Measured twice: on the quantised 0x14A angle, and independently via **0x18F `STEER_ANGLE_RATE`**,
whose LSB (0.125 deg/s; fitted 7.80–7.96 counts per deg/s against the kit's `V.CPD = 8.0`)
corresponds to **0.00099 deg of ring amplitude at 20 Hz — it resolves this band ~100x finer than the
angle channel does.**

| route | build | n | angle amp (deg) [95% CI] | in LSB | rate amp (deg/s) | -> rate-derived amp (deg) | **in LSB** | rate/angle |
|---|---|---|---|---|---|---|---|---|
| r39 | V282 | 364 | 0.0334 [0.0316, 0.0350] | 0.33 | 2.829 | **0.0229** | **0.23** | 0.69 |
| r5e_v288 | V288r2 | 198 | 0.0334 [0.0303, 0.0355] | 0.33 | 2.773 | **0.0221** | **0.22** | 0.66 |
| r62_v289 | V289 | 562 | 0.0247 [0.0234, 0.0262] | 0.25 | 1.482 | **0.0175** | **0.17** | 0.71 |
| r63_v289 | V289 | 710 | 0.0266 [0.0253, 0.0283] | 0.27 | 1.548 | **0.0187** | **0.19** | 0.70 |
| r35 | V281r3 | 293 | 0.0387 [0.0360, 0.0419] | 0.39 | 3.577 | **0.0283** | **0.28** | 0.73 |

The angle channel's own quantisation-noise floor in a 4 Hz band is **0.115 LSB** (uniform step
0.1 deg, white over 0–50 Hz). The angle channel reads **1.4x high** on every route (rate/angle
0.66–0.73) — exactly the inflation expected when the signal sits ~2x above the quantiser floor.

⇒ **The wheel's ring is between one-sixth and one-quarter of one LSB on every build, at every speed.**
openpilot's 20 Hz angle input is therefore a 1-LSB bang-bang, and **~40 % of the ring-band content the
controller actually sees in that channel is quantisation noise, not motion.** §5.2 guessed
"1–3 LSB"; the wire says **0.17–0.28 LSB** — the effect is *stronger* than claimed, not weaker.

## A2. The LSB step histogram, full distribution [EVIDENCE]

`diff(0x14A STEER_ANGLE)` in raw LSBs, grinding vs speed+demand-matched baseline (0–4 unmatched of
2,127 present windows):

| route | arm | n samples | 0 | 1 | 2 | 3 | 4 | 5 | >=6 | mean abs(d) |
|---|---|---|---|---|---|---|---|---|---|---|
| r39 (V282) | **GRIND** | 72,072 | 28.8 % | 25.9 % | 14.4 % | 9.5 % | 6.1 % | 4.0 % | 11.4 % | 2.32 |
| | BASE | 72,071 | 38.3 % | 22.1 % | 9.9 % | 6.8 % | 4.4 % | 3.1 % | 15.4 % | 2.64 |
| r5e_v288 (V288r2) | **GRIND** | 39,204 | 27.1 % | 24.1 % | 14.3 % | 9.4 % | 6.5 % | 4.4 % | 14.2 % | 2.61 |
| | BASE | 39,204 | 39.6 % | 22.0 % | 7.9 % | 4.8 % | 4.0 % | 2.8 % | 18.8 % | 2.94 |
| r62_v289 (V289) | **GRIND** | 111,276 | 61.1 % | 17.7 % | 5.3 % | 3.4 % | 2.8 % | 2.2 % | 7.5 % | 1.28 |
| | BASE | 110,680 | 66.2 % | 14.5 % | 4.0 % | 2.8 % | 2.6 % | 2.0 % | 8.0 % | 1.26 |
| r63_v289 (V289) | **GRIND** | 140,579 | 62.5 % | 18.6 % | 5.4 % | 3.4 % | 2.4 % | 1.6 % | 6.2 % | 1.22 |
| | BASE | 139,788 | 64.1 % | 15.5 % | 4.0 % | 2.8 % | 2.5 % | 2.2 % | 8.9 % | 1.50 |
| r35 (V281r3) | **GRIND** | 58,016 | 31.8 % | 25.0 % | 13.9 % | 9.3 % | 7.3 % | 4.9 % | 7.8 % | 1.99 |
| | BASE | 58,015 | 44.3 % | 20.3 % | 8.0 % | 5.9 % | 4.6 % | 3.5 % | 13.4 % | 2.08 |

**The mode alone would have misled, which is why the whole distribution is here.** It is *not*
"dominated by 0 and ±1" in the simple sense — but grinding shifts mass **out of 0 and out of >=6 into
1–5 LSB** on every route, and the mean step is *lower* in grinding on 4 of 5 routes. That is the
signature of a wheel that is nearly still but flickering: more frequent small transitions, fewer large
slews. It matches the operator's own description (hands-off, wheel nearly still) and it is what a
sub-LSB ring riding a quantiser looks like.

## A3. It is a real ring DITHERING the quantiser, not quantiser hash [EVIDENCE]

The orchestrator's discriminator, run as specified:

| route | build | n | angle-line prominence | delta f0 vs `bar` | spectral flatness (1 = white) | residual amp (LSB) | **coherence(angle, 0x18F rate) at the line** |
|---|---|---|---|---|---|---|---|
| r39 | V282 | 364 | **10.8** | −0.03 Hz | **0.490** | 0.334 | **0.860 [0.840, 0.877]** |
| | baseline | 364 | 6.3 | +0.28 | 0.560 | 0.208 | 0.553 [0.515, 0.600] |
| r5e_v288 | V288r2 | 198 | 9.4 | +0.01 | 0.499 | 0.335 | **0.877 [0.855, 0.891]** |
| | baseline | 198 | 6.0 | +0.02 | 0.552 | 0.206 | 0.684 [0.643, 0.732] |
| r62_v289 | V289 | 562 | 8.1 | +0.26 | 0.486 | 0.244 | **0.782 [0.763, 0.811]** |
| | baseline | 559 | 6.0 | +1.16 | 0.557 | 0.173 | 0.478 [0.426, 0.526] |
| r63_v289 | V289 | 710 | 8.8 | +0.12 | 0.472 | 0.265 | **0.831 [0.812, 0.845]** |
| | baseline | 706 | 6.9 | +0.81 | 0.526 | 0.196 | 0.645 [0.598, 0.682] |
| r35 | V281r3 | 293 | **14.6** | −0.03 | **0.458** | 0.387 | **0.903 [0.885, 0.916]** |
| | baseline | 293 | 6.0 | −0.90 | 0.590 | 0.189 | 0.617 [0.570, 0.667] |

Three things agree: the angle's own line sits at the **same frequency as the `bar` line** (delta f0
−0.03 to +0.26 Hz in grinding, vs −0.90 to +1.16 Hz in baseline where there is no line to find); the
band is **not white** (flatness 0.46–0.50 grinding vs 0.53–0.59 baseline); and the quantised angle is
**0.78–0.90 coherent with the independent rate channel** at the line, against 0.48–0.68 in matched
baseline.

⇒ 🛑 **This is the limit-cycle side of the orchestrator's dichotomy, not the dither side. The
quantiser is being DRIVEN by a real ring; it is not manufacturing one.** The practical consequence is
unchanged and is the point: the ring is sub-LSB, so what crosses into the controller is a real ring
*plus* ~40 % added quantisation noise, in a band where the EPS lane cannot be commanded anyway.

## A4. 🛑 CLOSING THE LOOP FAILS — the echo does NOT account for the command's ring line

Prediction: `abs(cmd)_ring = abs(angle)_ring [deg] x counts_per_deg(v)`, with `counts_per_deg` = 132
(5 m/s) -> 528 (30 m/s) from the fork chain (P is the only path; `k_d = 0`).

| route | build | n | pred ct | meas ct | **ratio [95 % CI]** | via rate-derived angle |
|---|---|---|---|---|---|---|
| r39 | V282 | 364 | 5.2 | 25.7 | **0.21 [0.19, 0.22]** | 0.14 [0.13, 0.15] |
| r5e_v288 | V288r2 | 198 | 4.7 | 40.7 | **0.13 [0.11, 0.14]** | 0.08 [0.08, 0.09] |
| r62_v289 | V289 | 562 | 5.3 | 7.3 | **0.68 [0.58, 0.78]** | 0.45 [0.40, 0.51] |
| r63_v289 | V289 | 710 | 5.9 | 5.6 | **1.04 [0.94, 1.08]** | 0.65 [0.58, 0.71] |
| r35 | V281r3 | 293 | 6.2 | 30.4 | **0.22 [0.20, 0.24]** | 0.15 [0.14, 0.18] |
| **POOLED** | | **2,127** | | | **0.37 [0.35, 0.41]** | **0.27 [0.25, 0.29]** |

**P re-transmitting the measured angle accounts for about a quarter to a third of the command's
ring-band amplitude, not for all of it.** Within-route the ratio rises with speed (0.17 -> 0.36 on
r39; 0.23 -> 1.90 on r63_v289), which is what a v^2-scaled gain against a roughly speed-flat residual
looks like.

**The floor-immune version does not rescue it, and it says why.** `GI.band` on the command measures
the line *plus* the broadband floor of a signal that changes on 92 % of frames, so I re-ran it as a
cross-spectrum, `abs(H) = abs(S_ac)/S_aa` in counts per degree, which the incoherent floor cancels out
of:

| route | build | abs(H) measured | abs(H) predicted | ratio | **gamma^2** | phase |
|---|---|---|---|---|---|---|
| r39 | V282 | 650.2 | 143.4 | **4.54** | **0.376** | +9° |
| r5e_v288 | V288r2 | 632.6 | 133.8 | **4.73** | **0.259** | +65° |
| r62_v289 | V289 | 99.0 | 185.4 | **0.53** | **0.052** | −42° |
| r63_v289 | V289 | 75.1 | 209.7 | **0.36** | **0.055** | −54° |
| r35 | V281r3 | 611.5 | 152.3 | **4.02** | **0.380** | +17° |

🛑 **This estimate is not usable as a forward gain, and I can demonstrate that rather than assert it.**
(a) The ratio is **x4.5 on the base builds and x0.4 on V289 — opposite directions**, which no scaling
error produces. (b) Making x4.5 a real forward gain would need `latAccelFactor ~ 0.373`, far below
torqued's own cap floor of 1.182 — **inadmissible**. (c) On the base builds `abs(H)` collapses to the
plain amplitude ratio of the two channels: 0.0334 deg / 25.7 ct gives **769 ct/deg against a measured
650** (r35: 786 vs 612). That is the estimator reading the **reverse** direction — command -> motor ->
wheel -> angle — which is physically the loud one. The angle and the command are two nodes of one
closed loop, and a single-input transfer estimate cannot separate the directions at gamma^2 = 0.05–0.38.

⇒ **Item 4's verdict is NEGATIVE and honest: the quantiser hypothesis is confirmed as a description of
what openpilot SEES, and is NOT established as the explanation of what openpilot SENDS.** The
remaining 63–73 % of the command's ring-band content is unattributed; the candidates are the
setpoint/feedforward side (the 20 Hz staircase and the Accord rate-plant FF, both of which carry the
band and neither of which is the measurement) and the broadband floor.

🛑 **Correction to §0.4, §5.2 and the §6 scorecard.** I wrote that a measurement notch "attacks the
63 % share". That mis-mapped the kit's decomposition: the record's *"open-loop share of T's 20 Hz: 9 %,
feedback path 63 %"* splits the **motor torque** into what the COMMAND drives (9 %) and what the
**EPS's own internal rate feedback** drives (63 %). openpilot's angle echo lives entirely inside the
9 %. **Both lever #1 and lever #2 attack the same ~9 % open-loop share** (with the rung-bell argument
putting an 8–13 % floor on the benefit, since the loop amplifies what it is fed). They differ only in
*which component* of the command's ring band they remove — the echo vs the staircase — and A4 says the
echo is at most a third of it. **This lowers the expected size of lever #1; it does not change the
ordering, because lever #1 is still the only zero-lag, zero-slew option and the cheapest to test.**

## A5. 🛑 CORRECTION — §5.5's `STEER_DELTA_UP` conclusion is WRONG at the measured operating point

Measured rate-limiter bind duty, four strata, at the 122.88 counts/frame cap:

| route | build | max abs(d) | p99 | p99.9 | mean abs(d) | all % | engaged % | **GRIND %** | pre-0.5 s % | enrichment |
|---|---|---|---|---|---|---|---|---|---|---|
| r39 | V282 | 330 | 122 | 123 | 18.8 | 0.72 | 0.77 | **1.68** | 2.21 | x2.17 |
| r5e_v288 | V288r2 | 2465 | 123 | 123 | 20.3 | 1.34 | 1.80 | **4.29** | 4.68 | x2.38 |
| r62_v289 | V289 | 1091 | 123 | 123 | 19.0 | 1.22 | 1.86 | **2.46** | 2.91 | x1.32 |
| r63_v289 | V289 | 1396 | 123 | 123 | 18.7 | 1.45 | 1.74 | **2.16** | 2.21 | x1.24 |
| r35 | V281r3 | 2497 | 122 | 123 | 16.3 | 0.43 | 0.50 | **1.45** | 1.84 | x2.92 |

Share of engaged frames at or above each threshold (counts/frame):

| route | >=40 | >=60 | >=80 | >=100 | >=110 | >=120 | >=122 | >=123 |
|---|---|---|---|---|---|---|---|---|
| r39 | 12.63 % | 7.41 % | 4.95 % | 3.33 % | 2.77 % | 2.20 % | 1.93 % | 0.77 % |
| r5e_v288 | 15.01 % | 10.63 % | 8.15 % | 6.44 % | 5.67 % | 4.87 % | 4.51 % | 1.80 % |
| r62_v289 | 13.34 % | 9.60 % | 7.54 % | 6.15 % | 5.53 % | 4.84 % | 4.42 % | 1.86 % |
| r63_v289 | 13.22 % | 9.87 % | 7.87 % | 6.39 % | 5.69 % | 4.92 % | 4.46 % | 1.74 % |
| r35 | 9.86 % | 5.56 % | 3.59 % | 2.41 % | 1.95 % | 1.53 % | 1.35 % | 0.50 % |

**The limiter binds on 1.4–4.3 % of grinding frames, not 13–21 %.** (The >=40-counts column reads
9.9–15.0 %, which is plausibly where the brief's figure comes from — but >=40 is a third of the cap
and is not binding.) The two-tone describing function re-parameterised by duty:

| bind duty | 0.0 % | 2.16 % (**measured**) | 5 % | 10 % | 13 % | 21 % | 40 % | 80 % | 99 % |
|---|---|---|---|---|---|---|---|---|---|
| abs(N) @20 Hz | 1.000 | **1.000** | 0.996 | 0.935 | 0.929 | 0.825 | 0.582 | 0.190 | 0.010 |
| phase | 0° | **0°** | −0.3° | −3.4° | −3.6° | −4.6° | −4.3° | −6.3° | +40° |

⇒ 🛑 **At the real duty the rate limiter is TRANSPARENT (abs(N) = 1.000, 0°). §5.5's claim that raising
`STEER_DELTA_UP` "admits up to 67x more 20 Hz energy" rested on my synthetic 99.8 %-duty sweep and is
FALSE at the operating point this car actually runs at.** Raising the limit would change the 20 Hz
content by **essentially nothing**, because the limiter is not binding during grinding to begin with.
It would buy authority and remove what little 1–3 Hz describing-function lag remains, at no 20 Hz cost.
**Scorecard row #7 should read "no effect on excitation either way" rather than "worse (x15–50)".**

The safety statement is unchanged and still binding: panda enforces no Honda steer limit at all
(`opendbc/safety/modes/honda.h:274-282`), so this is an authority decision with no independent
backstop, and it should be taken on its own merits with its own drive — not smuggled in as an
excitation lever. The direct empirical check needs no model at all: the ring line **is** present in the
post-limiter 0xE4 stream at 5.6–40.7 raw counts, so the limiter is demonstrably passing it.

## A6. What this changes, and what it does not

| §5.2 / §5.5 claim | status after the wire |
|---|---|
| `measurement` is the 0.1 deg/LSB 0x14A angle, unfiltered, P-only (`k_d = 0`) | **EVIDENCE, unchanged** (code) |
| the ring is ~1–3 LSB | **REVISED — it is 0.17–0.28 LSB**, measured on an independent channel |
| ~40 % of the angle's ring-band content is quantisation noise | **EVIDENCE, new** |
| the ring-band angle content is a real line, not dither | **EVIDENCE, new** (coherence 0.78–0.90 vs the rate) |
| the echo accounts for the command's ring line | **NOT ESTABLISHED; the simple form is falsified** (0.27–0.37) |
| a measurement notch attacks "63 %" | **WRONG — it attacks the ~9 % open-loop share** (A4) |
| raising `STEER_DELTA_UP` admits 15–67x more 20 Hz | **WRONG at the measured 2 % duty — no effect** (A5) |

**Ranking unchanged, expected size reduced.** Lever #1 (a 20 Hz notch on `measurement`) is still the
only zero-command-lag, zero-slew option and still the cheapest to test, and A1/A3 give it a clean
rationale it did not have before: the channel it filters carries a sub-LSB signal with ~40 %
quantisation noise, in a band where the EPS lane cannot be commanded anyway, so almost nothing real is
lost. But A4 says it can only be removing part of a ~9 % share, so **it should be pitched as a cheap
experiment, not as a fix.**

## A7. Residuals, and what would close them

1. **The missing 63–73 % of the command's ring band is unattributed.** The clean next measurement is
   the sister agent `modelrate`'s: the model staircase's own contribution. My A4 ratio and his
   innovation measurement are the two halves of the same accounting.
2. **The reverse-causality confound is structural, not fixable by better estimation** from these two
   channels alone. Separating forward from reverse needs an *exogenous* input — which is exactly what
   an inert openpilot-side notch would provide, since toggling it changes the forward path and nothing
   else. That makes lever #1 a measurement as much as a candidate fix.
3. **`counts_per_deg` still assumes LAF = 1.6893 and `k_p = 0.6`.** A4(b) rules out LAF as the
   explanation of the x4.5 (it would need 0.373, below the 1.182 floor), but a live-learned LAF would
   scale A4's ratios.
4. **The fitted counts-per-deg/s (7.80–7.96) sits ~2 % below `V.CPD = 8.0`**, consistent with
   errors-in-variables attenuation from regressing on the quantised angle's first difference. It biases
   A1's rate-derived amplitudes *high* by ~2 % — i.e. the true ring is, if anything, slightly smaller
   than 0.17–0.28 LSB.
5. **All five routes are the operator's own car with his own toggles.** Nothing here is cross-validated
   against a different vehicle or a stock EPS.

---

# APPENDIX B — two corrections, 2026-09-10 close-out

Both were found by later measurements from other agents on this session's team. Neither is a rewrite:
the superseded numbers are struck in place above, so the error stays visible.

## B1. 🛑 The one-LSB gain table used two parameters that are wrong on the wire

§5.2's table (and, through it, Appendix A's `counts_per_deg` and its A4 ratios) took
**`latAccelFactor = 1.6893`** from carParams and **`k_p = 0.6`** from the `latcontrol_torque.py:28`
module constant. Both were **measured live** instead, from `−(p + i + d + f) / output` being a hard
constant (p5 == p95):

| route | build | **live `latAccelFactor`** | **live `k_p`** | vs what §5.2 assumed |
|---|---|---|---|---|
| r39 | V282 | **2.1100** | **0.8000** | LAF ×1.25, k_p ×1.33 |
| r35 | V281r3 | **2.1100** | **0.6000** | LAF ×1.25, k_p unchanged |
| r5e_v288 | V288r2 | **6.0000** | **0.9000** | LAF ×3.55, k_p ×1.50 |
| r62_v289 / r63_v289 | V289 | **6.0000** | **0.9000** | LAF ×3.55, k_p ×1.50 |

Neither is torqued's filtered 2.46–2.50 either. `slewburst` flagged the LAF independently before it was
stopped, and the corrected value agrees with the measured echo share — which is why it matters rather
than being a rounding quibble.

### Corrected table — raw 0xE4 counts per ONE 0.1° LSB of `STEER_ANGLE`

Same chain as before (`curvature_factor(v) × rad(1°)/sR × v² × (k_p + LSF(v)) / LAF × STEER_MAX`), only
the two parameters change. `_scratch/lsb_gain_corrected.py`.

| v (m/s) | 5 | 8 | 10 | 12 | 15 | 20 | 25 | 30 |
|---|---|---|---|---|---|---|---|---|
| ~~SUPERSEDED — k_p 0.6, LAF 1.6893 (carParams)~~ | ~~13.23~~ | ~~14.49~~ | ~~15.91~~ | ~~17.42~~ | ~~20.61~~ | ~~28.41~~ | ~~39.00~~ | ~~52.80~~ |
| **r39 (V282) — k_p 0.8, LAF 2.1100** | **10.97** | 12.56 | 14.24 | 16.10 | **19.87** | 28.73 | 40.57 | **55.74** |
| **r35 (V281r3) — k_p 0.6, LAF 2.1100** | **10.59** | 11.60 | 12.74 | 13.95 | **16.50** | 22.75 | 31.22 | **42.28** |
| **r5e / r62 / r63 (V288r2, V289) — k_p 0.9, LAF 6.0000** | **3.92** | 4.58 | 5.27 | 6.04 | **7.58** | 11.16 | 15.91 | **21.97** |

Counts per **degree** are ten times these: 109.7 → 557.4 (r39), 105.9 → 422.8 (r35), 39.2 → 219.7
(V288/V289).

**On the three V288/V289 routes the gain is smaller by ×0.30–0.42 — the "13.2 / 20.6 / 52.8 counts per
0.1°" at 5 / 15 / 30 m/s become 3.9 / 7.6 / 22.0.** On r39 and r35 the change is modest (×0.80–1.06),
because the k_p rise partly offsets the LAF rise.

### Knock-on to Appendix A

**A1–A3 are unaffected** — they measure the angle and the rate channels directly and use neither
parameter. The ring is still **0.17–0.28 LSB**, still 1.4× over-read by the quantised channel, still a
real line (coherence 0.78–0.90 against the independent rate channel), not white dither.

**A4 is affected, and it moves further against my own hypothesis.** Multiply A4's published
predicted/measured ratios by ×0.94 (r39), ×0.80 (r35), ×0.36 (r5e/r62/r63):

| route | A4 as published | **corrected** |
|---|---|---|
| r39 (V282) | 0.21 | **≈ 0.20** |
| r5e_v288 | 0.13 | **≈ 0.05** |
| r62_v289 | 0.68 | **≈ 0.24** |
| r63_v289 | 1.04 | **≈ 0.37** |
| r35 (V281r3) | 0.22 | **≈ 0.18** |

A4's verdict — *the echo does not account for the command's ring line* — is unchanged and **strengthened**.

## B2. 🛑 Recommendation #1 (the measurement-side notch) is RETIRED

It was my top-ranked lag-free candidate and it is now withdrawn. The filter arithmetic that justified
its *cost* still stands (a Q = 5 notch at 20 Hz costs −0.5° at 1 Hz and −2.6° at 5 Hz, zero command lag,
zero slew). What fails is the *premise* that there is anything at the measurement worth cutting:

1. **The excitation enters on the setpoint/feedforward side.** An exact algebraic decomposition of
   openpilot's output (residual 3.9e-9) puts the command's 13–26 Hz content at **80–97 %
   setpoint-derived and only 2.4–14.6 % fed-back measurement.**
2. **The echo is falsified as a coherent link, not merely sized down.** After projecting the camera
   clock out of both signals, residual command↔angle coherence at f0 is **0.022** (down from 0.388),
   against a matched quadrature control that *rises* to 0.598. A P-path echo carrying the ring would
   make the angle's dominant free content reappear in the command at ≥144° of lag. It does not.
3. **The outer loop cannot sustain anything anyway**: |L| = 0.026–0.165 at the ring, assumption-free
   upper bound 0.096–0.189, ≤ 0.38 at the most adverse friction the fork allows — a describing-function
   bound computed *from the quantised angle at the true operating amplitude*, so it prices the quantiser
   in rather than linearising around it.
4. ⭐ **The physical reason, which is the part worth keeping:** the driver-torque bar is **34 %
   camera-locked while the steering angle is only 2 %**. A 20 Hz torque comb barely moves the column's
   inertia — and **openpilot measures the angle, not the torque.** The feedback path sees almost none of it.

⇒ **A measurement-side notch would be a confirmation experiment at best, not a fix.** Recorded here in
full rather than deleted, so a future session does not re-derive it: it was good analysis that a later
measurement overtook.

## B3. Frame for anything downstream of this document

The session's verdict is **(C) excited resonance** — the grinding is a lightly-damped mode rung by
ordinary broadband excitation, engagement-gated (×33–72 rarer with lateral off at matched or higher
load, 17 routes), with the camera comb worth only **3–8 % of ring amplitude if perfectly deleted.**
**No fork-side excitation fix is recommended.** Rows 2–5 of the §6 scorecard were sized against a 9 %
open-loop share that is itself only 3–8 % reachable; treat the whole table as an account of what the
pipeline does, not as a menu of fixes.

**What stands from this document, unchanged:**
- The colleagues' LPF is **~1 Hz, not 20 Hz** (τ 0.10–0.28 s, corner 1.59 → 0.57 Hz, 100–280 ms group
  delay, −32° to −59° at 1 Hz), aimed at a low-speed near-centre *"hunting and escalating sway"* — the
  only symptom description in the whole fork — and almost certainly a different object from our
  hands-off 20 Hz ring (§1).
- The **three commit-attribution corrections** to the 2026-09-07 trace, including that `f69599fab`
  "honda wobble" is the driver-override debounce and has nothing to do with the filter (§1.1).
- **`measurement` is the steering angle, not yaw rate**, and **`k_d = 0`**, so the outer controller is a
  pure gain on the angle (§3).
- **`jerk_filter` is transparent at 20 Hz** (|setpoint/F| = 1.000) and should stop being counted as
  command smoothing (§4.2).
- **The ring at the wheel is sub-LSB** (A1) and is a real line dithering the quantiser, not quantiser
  hash (A3).
- **Raising `STEER_DELTA_UP` is an authority lever, not an excitation lever**, and panda enforces no
  Honda steer limit at all (§5.5, A5).
