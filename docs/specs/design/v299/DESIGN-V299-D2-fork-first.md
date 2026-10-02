# DESIGN V299, designer D2: FORK-FIRST (2026-10-02)

**Status: DESIGN ONLY.** Nothing was sent, flashed or built. The fork, the firmware, the golden model, STATE and the
lineage were not touched. Ghidra was not opened: D2 changes **no firmware byte**, and the three cave immediates named in
§8 (grafts) were located by a Python byte-pattern scan of the V298 image. Their decodes are BELIEF until Ghidra confirms them.
**Author:** designer D2, a SUBAGENT of the judge-panel orchestrator.
**Labels:** EVIDENCE = measured on route 79 / read from the V298 image (sha256 `177abf04…`) / read from fork source at
Dom `2712e1336`, method given. BELIEF = modelled (the r71b plant family, M3's twist fit) or inferred.
**Bands are scored here; the operator scores the symptoms.**

**Scripts** live in `analysis-2020accord/studies/angle_loop/v299_design/D2-fork-first/`. Outputs go to `_scratch/v299_D2/`. Wall times were measured:

| script | what | wall |
|---|---|---|
| `x1ab_extract.py` | 0x1AB bytes 0-2 from the 21 r79 rlogs (16 procs); Honda checksum and counter | **2.7 s** |
| `cf_fork_r79.py` | O1-gate counterfactual; limiter re-run on the hard windows; bar | **1.6 s** |
| `gate2_fork.py` | inner loop PM/GM/\|S\| (V298 bytes); the O1, clip and lead loops (common freq scorer, unchanged) | **2.9 s** |
| `sim_fork_loop.py` | closed loop: V298 lane (common `CandLane`) × r71b plant × fork model; 4 scenarios, 4 procs | **6.3-6.8 s** |
| `d2_common.py` | image reads (GB-P, Kp, Kd, Ki, ICL, ramps, all asserted), G walk, s(v), VM, twist model | — |

---

## 0. One-page answer

**D2 changes no firmware.** V298 stays on the car as flown (sha `177abf04…`). Every lever is in the fork's angle
interface. Each new term defaults to V298's behaviour, so the code commit alone replays byte-identical 0xE4 frames, and
each term is gated by `AccordEpsAngleLoop` and exposed as a param. Consequences:

- GATE 1 is vacuous: no new RAM.
- The bricking class is absent.
- The next drive is a fork update plus a toggle-config restore, with no flash.

| operator note | mechanism (r79 + refutations) | D2 lever | measured on r79 | D2 predicts |
|---|---|---|---|---|
| 2 lacking authority / rate | **O1 relay**: 600/500 raw trips on the reaction twist, snaps the setpoint to the wheel, then re-slews at the cap (73 % of cap binding) | **G4 gate**: \|tq\| > 1200 instantly (Honda's steeringPressed), or > 600 held 80 ms; O1 lead 0.06 → 0; **0.4 s takeover ramp** after a release or engage | 415 O1 eps, 347 of them without press (13.8 s); 415 releases | **79 eps, 30 without press (1.6 s); 79 releases; 116 of 116 hand episodes caught, never later than steeringPressed + 10 ms** (EVIDENCE, counterfactual) |
| 2 | rate cap 120 deg/s; **then the error clip** (P-cap 36/40/26/17 % of rail at 3.1/8/10/11.75 m/s) | cap → 300 deg/s (binds only below about 6 m/s; the VM jerk limit is unchanged above that); clip ×1.6 at ≤ 11.75 m/s → P-cap **61/63/43/25 %**; highway clip unchanged | hard-frame tap p99 135, peak 183 LSB (59 % of rail) | hands-off 90° turn (sim): t90 **0.93-1.11 → 0.54-0.65 s**, ω_in 111-124 → 168-185 deg/s, tap peak 124-150 → 155-179 LSB (BELIEF) |
| 1 caveat, 4 small-correction stick | the designed loop lag (Tin group delay 51-573 ms by speed, model, which matches M6's measured 260-440 ms) plus friction | **setpoint lead**. (a) SteerDelay 0.35 → 0.45 (toggle only). (b) speed-scheduled plan lead 0.05-0.35 s, sampled from the model trajectory (this also interpolates the 20 Hz staircase) | \|sp\| < 5° slope 0.64-0.82 at 12-25 m/s; 0.1 Hz lag 1188 ms | sim lane change, lag at 17.5 / 26.9 m/s: **515 / 275 → 415 / 175 (a) → 135 / 135 ms (b)**. Drift at 15 m/s, err rms **0.78 → 0.65 (a) → 0.32° (b)**. Dwells 1 → 0 (BELIEF) |
| 3 indicator | bar = (a_des − roll) / 0.3247; a_act cancels | **bar = signed 0x1AB lane torque / 2461** (`carState.steeringTorqueEps`) | pinned 59.7 %; \|corr\| 0.135 | pinned **0.00 %**; it *is* the delivered lane torque. 0x1AB checksum valid on **100 %**, counter on 99.997 % of 61 113 frames (EVIDENCE) |
| 4 ratchet (big turns) | freeze toggling at \|bar\| 300/512 (strong, firmware) + O1 relay (association) | G4 and takeover remove 88 % of the twist O1 time; **the freeze cannot be reached from the fork** (declared, §7; graft in §8) | 80.7 vs 30.3 surges/min near vs away from a crossing (5-10 m/s) | relay share ↓; **freeze ratchet unchanged** (BELIEF: it may rise, because faster slews twist harder) |

**On the "6×":**
- The rail stays 2461 T, which is 6× stock and byte-identical since V282.
- D2 lets the fork use more of that rail: the P-cap below 12 m/s rises 1.5-1.7×, and the setpoint rate rises 2.5× below 6 m/s.
- On r79's recorded errors, the open-loop P demand would rise from p90 66 to 191 LSB (EVIDENCE arithmetic, with the wheel *not* re-simulated).
- **The honest risk is the reaction twist.**
  - In the sim, with M3's twist model, faster slews raise the twist word above 1200. O1 then yields by design, and the t90 gain shrinks to about 0 (A: 1.08-1.14 s vs V298 1.01-1.13 s).
  - The twist model is BELIEF (R² 0.31). The drive decides which case holds; §6 pre-registers that.

**Pick:** fly **(a)** first. It has the fewest code lines, and most of it is params plus one toggle (`SteerDelay`).
Keep (b) as the follow-up when the drive shows the linear-lag class dominates at 12-25 m/s.

---

## 1. Mechanisms addressed: the number each must move

| # | mechanism | what moves it | measured (r79) | predicted | status of prediction |
|---|---|---|---|---|---|
| M1 | O1 trips on the hands-off twist (C5) | G4 gate | no-press O1: 347 eps / 13.8 s; 31 per lat-minute | **30 eps / 1.6 s; 2.7 per lat-minute** | EVIDENCE (r79 counterfactual, recorded \|tq\|) |
| M2 | re-slew after an O1 release: 73 % of cap frames (REFUTE-data #7) | fewer releases (415 → 79); takeover ramp (rate *and* clip 0 → full over 0.4 s) | cap-bound frames within 0.3 s of a release: 83.6 % | 58.6 % (G4 + takeover, open loop) | EVIDENCE (counterfactual) |
| M3 | O1 lead +0.06·ω is anti-damping (M4: +0.5 tap/(deg/s)) | lead 0 | positive-feedback GM of the O1 loop: **10.7 dB** (Trt 60 ms) / 18.6 (30 ms) | **15.7 / 24.1 dB** | BELIEF (common freq model, §3.2) |
| M4 | fork rate cap 120 deg/s (17 % of all hard time; 50 % hands-off) | cap 300 deg/s; it binds only below ~6 m/s (VM jerk: 387 / 271 / 155 deg/s at 5 / 6 / 8 m/s) | hands-off hard \|rate\| p99 110-140, max 191 | sim 90° turn ω_in 168-185, ω_out 213-221 deg/s | BELIEF (sim) |
| M5 | error clip, the next binder (C3) | ×1.6 at the ≤ 11.75 m/s knots | P-cap 877 / 994 / 648 / 416 T | **1497 / 1540 / 1064 / 612 T** (61 / 63 / 43 / 25 %) | EVIDENCE (image G walk × M1 tap/S) |
| M6 | linear lag of the designed loop (C8) | lead (a) +0.10 s / (b) τ(v) | M6: 260-440 ms; model Tin group delay at 0.1-0.25 Hz: 51/79/115/248/368/501/573/345/215 ms at 3.1…26.9 m/s | residual lag ≈ 0.15 s (the model's own assumption) in (b) | model ≈ measurement: EVIDENCE that the lag is the designed loop's (two methods agree within 60-80 ms at 12-26.9 m/s) |
| M7 | D drag on slews (REFUTE-inference §2c) | a lead of τ ≈ Kd/s(v) = 0.07-0.09 s at ≤ 8 m/s is the (a) lead | wheel 5-8° behind a 120 deg/s setpoint | sim A vs A-nolead: t90 0.63 → 0.54 s (3 m/s) | BELIEF |
| M8 | bar measures nothing about the wheel (C12) | parse 0x1AB | 59.7 % pinned | 0 % pinned; p50 / p99 / max 0.05 / 0.35 / 0.59 of rail on r79 | EVIDENCE (r79 replay of the formula) |
| M9 | 20 Hz model staircase | (b) samples the plan trajectory between model frames | ruled out as a symptom (wheel/setpoint at 20 Hz 0.005-0.044) | only matters so (b)'s lead does not differentiate a staircase | EVIDENCE (M4) |

**Not addressed** (needs firmware, §7/§8): the bar-keyed freeze ratchet (80.7 vs 30.3 /min), the A3 cap (82 LSB I
at ≤ 6 m/s), the freeze discarding 26-37 % of the integral, and D at 0.55-0.88× design.

---

## 2. Two implementations

### 2.0 Firmware: none, for both (a) and (b)

| item | (a) | (b) |
|---|---|---|
| code bytes | **0** | **0** |
| cal cells | **0** | **0** |
| cave | none (V298's 260 B cave at 0xC4C00 unchanged) | none |
| new RAM words (GATE 1) | **0** (vacuous) | **0** |
| image | V298 `_v298_…A16A_plain_image.bin`, sha256 `177abf04…` (flown r79) | same |

The fork already reads V298's F181 `39990-TVA,A16A` interlock. Every term below is unreachable unless angle mode is
active (`interface.py`: A16A *and* `AccordEpsAngleLoop`).

### 2.1 Implementation (a): toggle config + the minimum code

**Toggle-only lever:**

| param (existing) | V298 drive 1 | (a) | effect |
|---|---|---|---|
| `UseAutoSteerDelay` | true (liveDelay never estimated, so 0.35) | **false** | use the custom delay |
| `SteerDelay` | — (0.35 effective) | **0.45** | `lagd.py`: `liveDelay.lateralDelay = toggle.steerActuatorDelay`. `modeld.py` samples the plan at `lat_delay + …`. **The plan leads 0.10 s more.** Feed-forward only. |

**Code:** one commit, all in angle mode, all params read at `CarController.__init__` (via `self.param_store`, like
the switch). The defaults reproduce V298, so an I1-style replay of r71b/r79 frames must stay byte-identical with the
defaults.

| # | file / function | change, in words | toggle-config expressible after the commit? | param (default = V298 → (a) value) |
|---|---|---|---|---|
| a1 | `honda/values.py` `CarControllerParams` + `carcontroller.py __init__` | `ANGLE_LIMITS.MAX_ANGLE_RATE` comes from a param, in deg/s ÷ 100. Clamp to [60, 450]. The VM jerk and accel limits stay as they are. | yes | `AccordAngleMaxRate` 120 → **300** |
| a2 | `carcontroller.py _update_angle` | error-clip table: the knots ≤ 11.75 m/s are scaled by the param; 17.5 and 26.9 m/s are unchanged. Clamp the scale to [1, 2]. | yes | `AccordAngleClipScale` 1.0 → **1.6** (V: 27.2/24.8/31.2/27.2/8.5/4.5°) |
| a3 | `_update_angle` (override state) | **G4 gate**. ON if \|tq\| > `OvrHard`, or \|tq\| > 600 for ≥ `OvrDebounce`·100 consecutive frames. OFF at \|tq\| ≤ 500. With debounce 0 and hard 600 it is V298 exactly. One int counter. | yes | `AccordAngleOvrHard` 600 → **1200**, `AccordAngleOvrDebounce` 0 → **0.08** |
| a4 | `_update_angle` (O1 setpoint) | `θ + rate·OvrLead` | yes | `AccordAngleOvrLead` 0.06 → **0.0** |
| a5 | `_update_angle` (release / engage) | On the O1 release edge **and** the latActive rising edge: start the limiter from the wheel (as today), start a timer `since = 0`, and for `since < T` scale **both** `max_angle_delta` and `error_max` by `since/T`. | yes | `AccordAngleTakeover` 0 → **0.4** |
| a6 | `honda/carstate.py` + `get_can_parsers` + UI `torque_bar.py` | parse 0x1AB `STEER_MOTOR_TORQUE` with **freq 0** (`ignore_alive`, so it never affects `can_valid`). The parser keeps checksum and counter checks; a bad frame does not update. In angle mode only, set `ret.steeringTorqueEps = −8·s10(MOTOR_TORQUE)` (s10: bit 9 = sign, bits 0-8 = \|T\|/8). UI: when angle mode and the param is on, bar = clip(`steeringTorqueEps`/2461, −1, 1), with the + sign meaning left like the current angle branch. **Unit test:** in a steady left hold the new bar sits on the same side as the current formula's. EVIDENCE for the tap sign: r79 left holds 5-60° have tap < 0 on **100 %** of 2332 frames, right holds > 0 on 100 % of 2026. | yes | `AccordAngleBarEps` false → **true** |
| a7 | `carcontroller.py update` (the instrument) | in angle mode, `new_actuators.torque` (0 on 100 % of r79 frames, so free) := status code = O1 (1) + 2·takeover-active + 4·rate/jerk-bound + 16·error-clip-bound + 32·debounce-pending + 64·O1 entered via the hard path | — (always on in angle mode) | — |

**Reference Python for (a)'s `_update_angle`** (the fork's own language; float, not integer):

```python
def _update_angle(self, CC, CS):                           # (a); defaults reproduce 2712e1336 exactly
    p, P = self.params, self.ap                             # self.ap: the AccordAngle* params read at __init__
    th, rate, tq = CS.out.steeringAngleDeg, CS.out.steeringRateDeg, abs(CS.out.steeringTorque)
    was = self.angle_override
    if CC.latActive:
        self.n600 = self.n600 + 1 if tq > 600 else 0                      # a3 debounce counter
        if tq > P.ovr_hard or self.n600 >= round(P.ovr_debounce * 100):
            self.angle_override = True; self.via_hard = tq > P.ovr_hard
        elif tq <= p.ANGLE_OVERRIDE_OFF:                                  # 500, unchanged
            self.angle_override = False
    else:
        self.angle_override, self.n600 = False, 0
    released = was and not self.angle_override
    engaged_edge = CC.latActive and not self.lat_last
    if self.apply_angle_last is None or released or engaged_edge:          # V298 seeds from the wheel; a5 adds the timer
        self.apply_angle_last, self.since = th, 0.0
    k = min(1.0, self.since / P.takeover) if P.takeover > 0 else 1.0       # a5
    lim = replace_rate(p, P.max_rate * 0.01 * k)                          # a1 (MAX_ANGLE_RATE scaled)
    a = apply_steer_angle_limits_vm(CC.actuators.steeringAngleDeg, self.apply_angle_last, CS.out.vEgoRaw, th,
                                    CC.latActive, lim, self.VM)
    if CC.latActive:
        if self.angle_override:
            a = th + rate * P.ovr_lead                                     # a4 (0.0)
        emax = np.interp(CS.out.vEgoRaw, p.ANGLE_ERROR_MAX_BP, P.err_v) * k  # a2 table, a5 ramp
        a = clip(clip(a, th - emax, th + emax), -400, 400)
    self.apply_angle_last, self.since, self.lat_last = a, self.since + 0.01, CC.latActive
    ...                                                                   # raw packing unchanged
```

### 2.2 Implementation (b): the fuller code path = (a) + four terms

| # | file / function | change | param (default → (b)) |
|---|---|---|---|
| b1 | `_update_angle` | **second-order limiter**: the rate toward the target is capped by the braking curve sign(d)·√(2·A·\|d\|) and the per-frame rate change by A. One float state, `prev_rate`, reset to 0 on engage, release and disengage. | `AccordAngleMaxAccel` 0 (off) → **1500** deg/s² |
| b2 | `latcontrol_angle.py update` (Accord branch) | **speed-scheduled plan lead + interpolation.** From `model_data`, κ_traj(t) = orientationRate.z / velocity.x on `T_IDXS`. With Δt = time since that modelV2 frame (clipped to [0, 0.05] s), add Δκ = κ_traj(t_d + Δt + τ(v)) − κ_traj(t_d) to the desired curvature before the VM / ratio map, where t_d = lat_delay. Bound \|Δangle\| ≤ 4° and ≤ the angle of Δa_lat 0.6 m/s². Write the lead in degrees to `angleState.output` (0 on r79: a free field). | `AccordAngleLeadSched` false → **true**; `SteerDelay` back to auto (0.35) |
| b3 | b2's table | τ(v) = (0.05, 0.10, 0.15, 0.25, 0.32, 0.35, 0.22, 0.10) s at (3.1, 8, 10, 11.75, 14, 17.5, 22, 26.9) m/s ≈ Tin group delay + 0.04 − 0.15 (§3.3), floored at 0.05 below 8 m/s for the stick | hard-coded table, scaled by `AccordAngleLeadGain` 1.0 |
| b4 | `_update_angle` | confirmed-hand off-hold: an O1 episode with ≥ 100 ms above 1200 or ≥ 300 ms of O1 releases only after 200 ms at ≤ 500 | `AccordAngleOvrHold` 0 → **0** (shipped off: §4 shows it lengthens O1 into turns, 11 % → 35 % of hard no-press time) |

The (b) status code also sets 8 = acceleration-bound.

### 2.3 The wire instrument for every new state word, already on disk before the dose

Every new fork state lands in a field the kit's fork extractor **already** caches (`r79_extract_fork.py` keys `co_tq`,
`ang_output`, `cs_tqeps`, all 0 on r79). So the instrument exists now, and the dose adds only the values:

| state | field | decode |
|---|---|---|
| O1, takeover, rate/jerk/accel/clip bound, debounce pending, via-hard | `carOutput.actuatorsOutput.torque` (`co_tq`) | int bit field (a7) |
| (b) lead, in degrees | `controlsState…angleState.output` (`ang_output`) | float |
| delivered lane torque | `carState.steeringTorqueEps` (`cs_tqeps`) | T, + = left; must equal −8·(0x1AB tap) on every frame. **This is the bar's own control.** |
| SteerDelay in force | `liveDelay.lateralDelay` (`ld_lat`) | must read 0.45 for (a) |

The firmware side carries no new state words, and its existing taps are unchanged (0x1AB tap, 0x14A b4 = 7).

---

## 3. GATE 2 and the time criteria

### 3.1 The inner loop: V298 bytes, unchanged by D2 (`gate2_fork.py` §1; common freq scorer `panel2/score_freq.py` imported unchanged; GB-P read from the image)

PM° / GM dB / max\|S\| at θ = 0. Tier-A bar 45°, tier-B (combined) bar 30°, GM ≥ 6 dB.

| v m/s | nominal | J_hi | b_lo | tau6 | mode20 | b_lo·J_hi (B) | b_q (B) |
|---|---|---|---|---|---|---|---|
| 3.1 | 83.7 / 23.2 / 1.24 | 66.5 / 28.2 / 1.20 | 69.7 / 21.5 / 1.34 | 81.1 / 18.1 / 1.30 | 83.7 / 24.7 / 1.24 | 56.2 / 26.9 / 1.31 | 83.7 / 23.2 / 1.24 |
| 8.0 | 85.9 / 23.0 / 1.25 | 70.0 / 27.4 / 1.26 | 67.7 / 21.1 / 1.38 | 82.8 / 17.8 / 1.32 | 85.8 / 24.9 / 1.25 | **54.5** / 26.0 / **1.41** | 85.9 / 23.0 / 1.25 |
| 11.75 | 92.3 / 27.8 / 1.10 | 99.4 / 30.1 / 1.11 | 114.2 / 24.5 / 1.18 | 91.8 / 22.7 / 1.13 | 92.3 / 28.3 / 1.10 | 104.8 / 28.4 / 1.17 | 92.3 / 27.8 / 1.10 |
| 17.5 | 95.5 / 33.3 / 1.04 | 97.5 / 33.7 / 1.06 | 106.6 / 28.7 / 1.09 | 95.1 / 28.2 / 1.06 | 95.5 / 33.9 / 1.04 | 108.5 / 30.4 / 1.11 | 115.3 / 23.6 / 1.21 |
| 26.9 | 79.9 / 35.0 / 1.04 | 77.7 / 35.2 / 1.05 | 95.1 / 29.6 / 1.09 | 79.0 / 29.7 / 1.05 | 79.9 / 35.8 / 1.04 | 89.9 / 30.6 / 1.12 | 94.9 / 23.1 / 1.26 |

Over 9 speeds × 7 members: min PM 54.5° (tier B), min GM 17.8 dB, max \|S\| 1.41, so every bar passes.
- **This is a reproduction of V298, not a new gate.** The curve-hold operating-point gate and the F3 op-skip are V298's own (C3-rev2 §2), carried unchanged.

### 3.2 The fork loops D2 touches (`gate2_fork.py` §2)

Each fork loop closes around Tin = θ/θ_sp:
- the 100 Hz ZOH;
- a round trip Trt of 30 ms (refuters' best lag) or 60 ms (V298's declared value);
- the members above.

The loops are positive feedback, so margins are taken about +1 (`pm_gm(−L_o)`).

| loop | condition | L (O1 lead) | positive-feedback margin, worst over 9 speeds × 7 members | verdict |
|---|---|---|---|---|
| O1 (I frozen → PD; fade 1.0 = twist or light hand) | Trt 60 ms | **0.06 (V298)** | no \|L_o\| = 1 crossing; GM **10.7 dB**; peak \|L_o\| 0.958 at 1.9 Hz (b_lo·J_hi, 8 m/s) | stable, least margin |
| | | 0.03 | GM 14.9 dB | |
| | | **0 (D2)** | GM **15.7 dB** | +5.0 dB |
| | Trt 30 ms | 0.06 / 0.03 / **0** | GM 18.6 / 23.3 / **24.1 dB** | |
| O1, fade 0.297 (firm hand) | Trt 30-60 ms | 0.06 / 0 | GM 22.2-29.7 / 26.8-35.3 dB | |
| ERROR CLIP while binding (PID, L = 0) | Trt 30 / 60 ms | — | **PM 20.8 / 22.4° at 0.15 Hz** (J_hi, 11.75 m/s); GM 23.8 / 15.4 dB; \|L_o\| peaks at 1.30 (0.8 Hz) and every crossing keeps PM > 0 | stable but slow-mode-light. **Present in V298 already.** A clip-bound episode lasts < 1 s, which is shorter than one 0.15 Hz period (6.7 s). BELIEF: it cannot ring up. Declared (§7). |
| LEAD in the path loop (scorer's E2-K0 outer model: τ_o 1 s, 60 ms; the lead as a prediction e^{+sΔ}) | nominal, 9 speeds | Δ 0 / 0.1 / 0.2 / 0.3 s | min PM **59.3 / 64.3 / 69.4 / 74.5°**; min GM 16 / 37 / 64 / 43 dB | the lead **raises** the path-loop PM (BELIEF model of the planner) |

The lead (a: SteerDelay; b: plan sampling) is a function of the planner's output only, and no measured quantity enters it. **It creates no new loop in the EPS.**

### 3.3 Why a lead: the inner closed loop's own lag (`gate2_fork.py` §3, nominal)

| v m/s | 3.1 | 5 | 8 | 10 | 11.75 | 14 | 17.5 | 22 | 26.9 |
|---|---|---|---|---|---|---|---|---|---|
| Tin group delay at 0.1 Hz (ms) | 51 | 79 | 115 | 248 | 368 | 501 | 573 | 345 | 215 |
| at 0.25 Hz (ms) | 81 | 101 | 124 | 278 | 419 | 464 | 481 | 345 | 245 |
| M6 measured, 0.2 Hz (ms) | — | — | — | — | 399 (12-18) | — | 322 (18-25) | — | 293 (> 25) |
| \|Tin\| at 0.5 Hz | 1.23 | 1.13 | 1.03 | 0.86 | 0.66 | 0.55 | 0.50 | 0.72 | 0.91 |

- **EVIDENCE that the linear lag is the designed loop's:** the model is within 60-80 ms of M6's measurement in all three measured bands.
- **The plan already assumes 0.15 s** (full 0.35 = 0.15 + 0.2 s software).
- Every millisecond beyond that is unmodelled lag that the fork can lead away: about 0 below 8 m/s and 0.1-0.4 s at 10-22 m/s.
- (a)'s single +0.10 s under-leads at 10-22 m/s and over-leads at ≤ 5 m/s by ≤ 0.16 s. (b)'s table follows the measured loop.

### 3.4 Time criteria: the fork in the loop (`sim_fork_loop.py`)

Setup:
- the common scorer's byte-exact `CandLane` with V298's bytes (C3B-P, Ki 40, A3 + sgn 300, fresh D 48, ramps 328/66);
- the r71b family plant (Karnopp, 10 kHz);
- frame vgr;
- the fork model at 100 Hz, reading the wheel 30 ms old.

Twist word:
- *none*: the ideal sensor;
- *twist*: M3's fit, −0.69α − 0.69ω − 163·tanh(ω/2) − 61, plus 8 Hz noise of sd 132 gp, which is the r79 refit residual. The same noise realisation is used in every column.

Rows are member *nominal*. F_hi agrees within 6 % on every *none* metric.

**Hands-off 90° turn** (plan 0→90° at 320 deg/s = the planner's p99, hold, return):

| cfg | v | t90 in / out (s) | ω peak in / out (deg/s) | tap peak (LSB, rail 307.6) | 1.6-3 Hz ω rms | twist: t90 in / O1 eps / word peak |
|---|---|---|---|---|---|---|
| V298 | 3 | 0.93 / 0.85 | 124 / 140 | 124 | 7.8 | 1.01 / 4 / 942 |
| **A** | 3 | **0.54 / 0.47** | **185 / 221** | 156 | 10.7 | 1.08 / 4 / 1350 |
| A, no lead | 3 | 0.63 / 0.57 | 185 / 221 | 156 | 10.8 | 1.16 / 4 / 1436 |
| A, current clip | 3 | 0.79 / 0.68 | 124 / 156 | 124 | 9.5 | 1.21 / 1 / 993 |
| **B** | 3 | 0.63 / 0.56 | 187 / 221 | 155 | 9.9 | 1.02 / 1 / 1081 |
| V298 | 5 | 1.06 / 0.80 | 114 / 134 | 147 | 8.2 | 1.13 / 1 / 938 |
| **A** | 5 | **0.62 / 0.43** | 173 / 221 | 176 | 11.7 | 1.14 / 4 / 1310 |
| **B** | 5 | 0.68 / 0.50 | 175 / 215 | 174 | 10.7 | 1.18 / 4 / 1497 |

Overshoot ≤ 0.4° in every row. The unwind undershoot of 6-8° is V298's own and unchanged.

**Hands-off lane change** (1.45 m/s² sine, 4 s):

| cfg | 17.5 m/s: lag / peak err / gain | 26.9 m/s: lag / peak err / gain |
|---|---|---|
| V298 | 515 ms / 11.8° / 0.82 | 275 ms / 3.39° / 1.05 |
| A | 415 / 10.4 / 0.82 | 175 / 2.21 / 1.05 |
| **B** | **135 / 6.4 / 0.82** | **135 / 1.76 / 1.04** |

The gain of 0.82 at 17.5 m/s is the loop's stiffness against the plant spring. It is the same in all configs, because the lead does not change it.

**Slow drift** (1.5 deg/s for 2.5 s; the small-correction stick):

| cfg | 8 m/s: dwells ≥ 0.2 s / err rms / lag at end | 15 m/s: dwells / err rms / lag at end |
|---|---|---|
| V298 | 1 / 0.25° / 0.23° | 1 / 0.78° / 0.90° |
| A | 0 / 0.11 / 0.10 | 0 / 0.65 / 0.75 |
| **B** | 0 / **0.08 / 0.03** | 0 / **0.32 / 0.47** |

The sim's plant Coulomb friction is 8-15 T at speed against the measured 73-94 T, so the car's stick is worse than simulated (BELIEF).

**Hand holds the wheel 40° off the plan, then releases** (5 m/s):

| cfg | lane tap while held | O1 eps during the hold | after release: t90 / ω peak / α peak | tap peak |
|---|---|---|---|---|
| V298 | 92 LSB | 7 | 0.42 s / 106 deg/s / 626 deg/s² | 130 |
| A | 99 | 4 | 0.29 / 142 / 1210 | 159 |
| B | 99 | 4 | 0.30 / 136 / 1208 | 153 |
| A + plain 200 ms off-hold | 75 | 3 | 0.41 / 132 / 784 | 152 |

No overshoot in any row (≤ 0.8° short).
- Before the clip ramp (a5) was added, A's α peak was 1729: the takeover ramp on the clip halves the release kick.
- A **plain** off-hold softens the hand relay, but it breaks hands-off unwinds under twist (90° turn: unwind undershoot −15° to −50°, O1 on for 1.0-1.6 s). That is why b4 ships off and confirmed-hand only.

**The kit's goal grid** (`panel2/score_time.py`, `outer='ff'`) cannot see fork terms, because its fork is a feed-forward 100 Hz ZOH. The firmware lane is V298's unchanged, so its rows are C3B-P's published ones (`c3/rev2B/rbf_score_time_tables.md`: 0 goal time fails at ≥ 8 m/s). D2 adds nothing to that grid and removes nothing from it.

---

## 4. Route-79 counterfactuals (`cf_fork_r79.py`; EVIDENCE for the recorded inputs, open loop for the wheel)

**O1 gates** on the recorded \|carState torque\| at i−1:
- 116 steeringPressed episodes (75.8 s);
- the current gate's no-press episodes last p50 / p90 / max 40 / 50 / 400 ms and peak at p50 / p90 / max 822 / 1086 / 1385.

| gate | eps | s | no-press eps / s | hand eps caught | yield vs press onset p50 / max (ms) | O1 share of hard no-press time |
|---|---|---|---|---|---|---|
| G0 V298 600/500 | 415 | 100.8 | 347 / 13.8 | 116/116 | −500 / −10 | 23.0 % |
| G1 Honda 1200/900 | 78 | 79.7 | 22 / 0.4 | 116/116 | −50 / **+10** | 4.8 % |
| G3 deb 60 ms \| 1200 | 88 | 86.6 | 39 / 2.1 | 116/116 | −205 / +10 | 11.7 % |
| **G4 deb 80 ms \| 1200 (D2)** | **79** | 85.9 | **30 / 1.6** | **116/116** | −175 / **+10** | 11.0 % |
| G5 deb 80 ms \| 1500 | 50 | 84.6 | 12 / 1.1 | **91/116** ✗ | −430 / +50 | 10.1 % |
| G7 α-compensated (refit) | 284 | 92.0 | 220 / 5.7 | 116/116 | −450 / +10 | 14.7 % |
| G8 deb 80 ms \| deb 30 ms 1200 | 45 | 84.4 | 11 / 1.1 | **85/116** ✗ | −480 / +30 | 10.1 % |
| G10 G4 + confirmed-hand hold | 56 | 106.7 | 17 / 0.7 | 116/116 | −500 / +10 | **35.3 %** ✗ |

**Why G4 and not a debounced 1200 (G8):**
- 59 of the 116 steeringPressed episodes last ≤ 30 ms (0.99 s in all). They peak at p50 1303, while \|rate\| is only p50 38 deg/s, so they are not fast-motion twist.
- The brief requires instant yield to a real hand. G4 yields no later than Honda's own steeringPressed, to the frame. The "+10 ms" is the i−1 carState pairing.
- G7, the α-compensated gate, is worse than plain debouncing. The 100 Hz carState-rate α is too noisy (residual sd 132 gp; refit gp60 = −0.60α + 0.45ω − 158·tanh(ω/2) − 46).

**Limiter re-run on the 55 hard windows** (122 s):
- Validation: the baseline re-run equals the published `co_ang` on **99.992 %** of window frames.
- Every row is on hard ∧ no-press frames.
- The wheel is the RECORDED one, so err and P are the demand the new setpoint would put on V298's stiffness, not a closed-loop prediction.

| config | O1 / rate-jerk / clip-bound | \|sp − θ\| p50 / p90 | P tap p50 / p90 / max (LSB) | P+D drive p90 / max | 1.6-3 Hz setpoint-rate rms |
|---|---|---|---|---|---|
| C0 V298 | 23.6 / 41.4 / 0.2 % | 2.8 / 9.5° | 19 / **66** / 115 | 49 / 128 | 14.1 deg/s |
| C2 G4 + takeover | 10.3 / 39.4 / 13.9 % | 3.0 / 16.3 | 20 / 115 / 119 | 131 / 196 | 22.0 |
| **C4 = (a)** (+ cap 300, clip ×1.6) | 10.3 / 26.6 / 20.1 % | 2.9 / 27.1 | 19 / **191** / 192 | 168 / 242 | 34.5 |
| C5 = (b) limiter (+ accel 1500) | 10.3 / 70.3 / 16.1 % | 2.6 / 27.0 | 18 / 191 / 192 | 168 / 242 | 35.4 |
| *recorded tap, same frames* | | | *74 / 118 / 183 (\|tap\|, P + I + D)* | | |

The setpoint's 1.6-3 Hz content rises 2.4× open loop.
- In the closed-loop sim it rises 1.3-1.5× hands-off and 2.2-2.5× with twist (§3.4 table).
- **The goal's "hard-turn 1.6-3 Hz wheel rate ≤ V282" will get worse** (declared, §7).
- A faster commanded slew *is* 1.6-3 Hz content (a 0.3 s slew sits around 1.7 Hz). That criterion cannot tell authority from stutter. The stutter scores in §6 are the ratchet-train and stall-surge counts.

**Bar on r79:**
- lane torque / 2461: pinned 0.00 % (current 59.7 %); \|bar\| p50 / p99 / max 0.05 / 0.35 / 0.59.
- 0x1AB src 1: 61 113 frames, Honda checksum **100.000 %**, counter step 1 on **99.997 %** (2 misses, at segment joins), OUTPUT_DISABLED 0 %, CONFIG_VALID 100 %.
- **C12 is closed:** the V298 cave's 0x1AB is a valid Honda frame (EVIDENCE, `x1ab_extract.py`).

---

## 5. Hazards and fail-safe paths (every new state word)

| state / event | init and reset | engage (latActive ↑) | disengage / request drop | 0xE4 timeout sentinel (firmware 510 ms) | real hand | twist |
|---|---|---|---|---|---|---|
| `n600` debounce counter | 0 at `__init__`; 0 whenever \|tq\| ≤ 600 or not latActive | 0 | 0; O1 false | firmware path unchanged; the fork's state is irrelevant there (request handling is Honda's A2/B2 + op-skip) | ≤ 80 ms to O1 at 600-1200; **instant above 1200** | short spikes do not trip |
| `angle_override` (O1) | false | false | false (as V298) | — | true; setpoint = wheel, lead 0 | trips only above 1200 or after 80 ms |
| `since` takeover timer | 0 at engage and at each O1 release | 0: the limiter starts at the wheel; rate and clip ramp over 0.4 s | irrelevant (not latActive, so the setpoint is the measured angle and request 0, as V298) | — | — | — |
| `prev_rate` (b) | 0 | 0 | 0 | — | 0 at release | — |
| lead term (b) / SteerDelay (a) | 0 when not active (`latcontrol_angle` !active, so desired = measured) | ramps in through the takeover clip | 0 | — | O1 overrides it (setpoint = wheel) | — |
| `steeringTorqueEps` | 0 until the first valid 0x1AB | — | keeps updating (display only) | — | — | — |

**Release to the driver.** The firmware is unchanged:
- the hand fade (×0.30 at \|bar\| 2289);
- the hard freeze at > 512;
- the request-drop ramp (0.5 s).

These give **instant physical yield** at any hand torque, independent of the fork. D2 changes only when the *setpoint* follows the hand:
- at 1200 it does so instantly, as before;
- at 600-1200 it does so after 80 ms.

The extra lane torque a gentle hand can meet in those 80 ms is bounded by s(v) × (hand rate × 0.08 s), for example 52 T/deg × 8° = 416 T (17 % of rail) at a 100 deg/s hand at 3 m/s. It is also capped by the clip, and the I is frozen above 512. BELIEF arithmetic.

**New hazards, and why they are bounded:**
- **Cap 300.**
  - Active below about 6 m/s only. A model glitch can slew the setpoint 2.5× faster.
  - The setpoint stays bounded by the VM accel limit, the clip (61 % of rail P), and the rail.
  - Sim wheel peak: 221 deg/s.
- **Clip ×1.6 at ≤ 11.75 m/s.**
  - The P-cap rises to 1497-1540 T.
  - The sim's peak lane torque is 155-179 LSB (≤ 58 % of rail). The rail itself is unchanged.
- **Release kick.** α peak 626-1270 → 1210 deg/s² in the sim. It is bounded by the takeover ramp on rate *and* clip, with no overshoot.
- **Lead.**
  - It is feed-forward and raises the path-loop PM (§3.2).
  - Over-lead at ≤ 5 m/s in (a) is ≤ 0.16 s, which could mean an early turn-in (BELIEF, small).
  - (b) bounds the lead at 4° or the angle of 0.6 m/s².
- **Twist at faster slews** (BELIEF model) can cross 1200. O1 then yields, which is the safe direction but costs authority. The instrument bit "64 = via hard path" separates this on the wire (§6).
- **The bar parse cannot disengage openpilot.** It uses freq 0, so `ignore_alive`. A bad frame only fails to update.

---

## 6. Pre-registered criteria for ONE short drive

**Exposure (about 3 minutes, one route):**
- (i) 3 hands-off 90° intersection turns at 3-8 m/s, in AOL, with the hands visibly off;
- (ii) 2 hands-off lane changes and one long curve at 18-27 m/s;
- (iii) one deliberate grab-and-hold at 5 m/s, then release;
- (iv) 30 s of straight at 12-20 m/s.

Before driving, check:
- `ld_lat` = 0.45 (a);
- `co_tq` status bits are non-zero somewhere;
- `cs_tqeps` = −8·tap on 100 % of frames.

### DO NOT FLY AGAIN if any of these occur (safety)

| # | condition | baseline (r79) |
|---|---|---|
| F1 | lane tap > 200 LSB on any frame with steeringPressed (the lane fighting a hand at 65 % of rail) | pressed-frame tap p99 93, max 164 |
| F2 | within 0.5 s of an O1 release, \|ω\| > 250 deg/s, or the wheel overshoots the plan by > 5° | sim A: 142 deg/s, 0° |
| F3 | ring presence > 0.5 %, F7 > 0, or a new 5-30 Hz line | 0 / 0 / none |
| F4 | `cs_tqeps` ≠ −8·tap on > 0.1 % of frames, or any `can_valid` drop in angle mode | — |
| F5 | operator: any lurch on engage or release, or any moment the wheel would not yield to his hand | — |

### FALSIFIED (revert the lever; not a safety stop)

| # | condition | baseline (r79) | prediction |
|---|---|---|---|
| X1 | no-press O1 episodes > 6 per latActive minute → the G4 gate failed | 31 | 2.7 |
| X2 | hands-off 90° turns: t90 not below 0.85 s **and** the clip/rate bits bound < 10 % of the turn → the binder is not the fork | — | sim 0.54-0.65 s |
| X3 | > 50 % of hands-off hard turn-ins carry an O1 via the 1200 path (bit 64) → **the twist is the binder**; D2's authority claim is falsified for the fork class; graft §8 | 22 no-press trips via 1200 on r79 | — |
| X4 | \|sp\| < 5° tracking slope at 12-25 m/s not above r79's 0.64-0.82, or the lag-compensated best lag not reduced by ≥ 80 ms ((a)) / ≥ 200 ms ((b)) | — | — |
| X5 | ratchet trains per minute of turning above r79 (3.1 / 4.7 / 4.2 at 0-5 / 5-10 / 10-20 m/s), or near-crossing stall surges up > 25 % → the faster slews fed the freeze ratchet | — | — |

**The sentence a null licenses:**
- "If the clip and rate bits (4/16) bind on < 10 % of hands-off hard frames while t90 stays ≥ 0.85 s, then neither the fork's limits nor its O1 were the binder. The remaining binders are firmware: the twist-keyed freeze and fade, A3, and D. D2's class is exhausted for note 2."
- The instrument named in that sentence (`co_tq` bits) is on the wire in this build.

---

## 7. Declared misses

1. **The freeze ratchet (note 4, the strongest measured mechanism) is untouched.**
   - The 300/512 thresholds are cave immediates.
   - Faster slews twist harder (BELIEF): with M3's model the word rises from 942 to 1350 at A's rates, so the freeze may fire more.
2. **The twist can cross Honda's 1200.** In the sim this erases the turn-in gain. That would cap the fork class's authority gain below 6 m/s (X3 tests it).
3. **The goal criterion "hard-turn 1.6-3 Hz wheel rate ≤ V282" gets worse** (sim ×1.3-1.5 hands-off, ×2.2-2.5 with twist). It already failed on r79 (8.48 vs 3.45-4.02). D2 argues the criterion conflates slew with stutter. That is a ruling for the operator.
4. **Highway authority is untested.** The 17.5 and 26.9 m/s clip knots (P-cap 16-18 %) and the VM jerk limit (20-38 deg/s) are unchanged, because r79 has 6 s of hard frames above 12.5 m/s.
5. **The A3 cap** (I ≤ 82 LSB at ≤ 6 m/s) and the effective Ki of 0.34-0.42× below 8 m/s are untouched. The sim's peak tap (≤ 58 % of rail) never reaches the rail.
6. **D at 0.55-0.88× design** is untouched. The (a) lead offsets D drag on setpoint ramps (BELIEF).
7. **The clip-bound fork loop** has a 0.15 Hz positive-feedback crossing with PM 20.8°. It is V298's own, present today, and clip episodes last < 1 s (BELIEF that it cannot ring up).
8. **The hands-on relay at the 500/600 hysteresis** with a resting, resisting hand remains (sim: 4 O1 episodes per 1.8 s hold, down from 7). The plain off-hold that fixes it breaks twist cases, so it is not shipped.
9. **The sim's friction is below the car's** (8-15 vs 73-94 T at speed), so the drift and stick benefits are optimistic.
10. **(a)'s global +0.10 s over-leads at ≤ 5 m/s.** The model's conditioning on lat_delay is learned, and its effect beyond a time shift is BELIEF.

---

## 8. What D2 would graft from the other angles

| graft | bytes (V298 image, Python pattern scan; decode BELIEF until Ghidra confirms) | why |
|---|---|---|
| **G-a: freeze thresholds to the twist** (firmware angle) | hard freeze `movea 0x200,r0,r13` at **0xC4C62** (`20 6e 00 02`). Opposing freeze `movea 0x12C,r0,r13` at **0xC4C6A** (`20 6e 2c 01`). Raising them to about 1200 / 700 is a 2-byte in-cave immediate edit each, with no new instruction. | The measured ratchet mechanism (80.7 vs 30.3 /min). It is the one lever the fork cannot reach. Size it against the hands-off word p90 607-681 and r79's twist peaks (max 1385). Needs GATE 2 (Ki 40, more integral at the operating points), N1 re-check, and the adversarial pass. |
| **G-b: A3 low-speed cap** | `movea 0x1000` (4096) at **0xC4CA2** (`20 6e 00 10`) | lifts the 27 %-of-rail I ceiling below 6 m/s, so the P + I steady ceiling rises above 62-65 % |
| **G-c: twist compensation in the EPS** | a cave term: word − Ĵ·α̂ from the 1 kHz motor rate, before the 300/512 tests | the fork's 100 Hz α is too noisy (G7 failed). The EPS has gp-0x6abe at 1 kHz. This would fix both the freeze and the O1 trips. |
| **G-d: friction feed-forward after the integrator** | cave | the fork cannot add torque. Any setpoint offset is integrated into an angle offset (§1, M7 caveat). |
| from a judge or refuter | the hands-on 4-8 Hz near-O1 modulation needs a hands-off-only reference recompute | needed to score X5 fairly |

**If the drive returns X3 (twist binds), the next build is D2 (a) plus G-a and G-c.** That is the smallest firmware edit that attacks both of the strongest measured mechanisms. **If it returns X2 with the bits idle,** the next build is G-a plus G-b.
