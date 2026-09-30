# V294 flight attribution: route `75604b0a432fdc89_00000071--a7b8ba5d9d` (kit tag `r71b_v294`)

Subagent "extract", 2026-09-30. Analysis only: nothing was sent, flashed, committed or pushed, and no fork or firmware artifact was touched.
Every number below was produced by `analysis-2020accord/studies/v295/flight/r71b_attribution.py`, and its full output is in
`r71b_attribution_out.txt` next to this file. Claims are marked EVIDENCE (with the method) or BELIEF.

> 🛑 **The dongle counter is reused.** Counter `00000071` names three routes on disk: `--f2c9d073a3` (V293 rev 2, 2026-09-13),
> `--ac50da2a6a`, and this one, `--a7b8ba5d9d`. Everything here is keyed on the full `counter--hash`, and the kit tag is
> **`r71b_v294`**. Never use plain `r71`.

## Bottom line

**The wire says this route is V294, and the acceleration trim is live, with the right sign and at about the designed gain.**
- **The FF is V293's.** |427 tap| against the image surface gives R² 0.9868 on all engaged frames (resid 22 counts) and
  R² 0.998 (resid 5.8) on low-acceleration frames. V282 cells fail (R² −1.02).
- **The trim reads LIVE on the pre-registered instrument.** E3 median is +0.197 T counts per deg/s², and all 6 windows are above
  +0.10. The pooled value is +0.210 (95 % block CI [+0.208, +0.212]), against a modelled +0.211 for a live V294 on this route's
  own excitation. The V293 null routes read +0.003 and +0.000 through the same code.
- **The fork ran exactly the r1 config.** All 26 keys match in both initData and the runtime toggles, on `Dom 20d24ab79`, not dirty.
  The 100 Hz reads are Kp 0.9000, Ki 0.3000, LAF 14.0000 and friction 0.011. The generic torque controller ran, with the
  variable-ratio steer map at level 16.84.
- **No EPS fault of any kind.**

Symptoms are the operator's to score. Nothing here says anything about how the car felt.

## FAIL / surprise criteria (written before computing; copied from the script header)
- **F1: attribution FAILS** if the FF-identity R² with V293 cells is below 0.90, or if sign(tap) = +sign(cmd) holds on less than
  99 % of frames. If V282 cells reach R² ≥ 0.95, the image is V282-class. **Result: PASS.** R² is 0.9868. The sign holds on
  0.9992 of 17,659 frames with |cmd| > 200 and T ≠ 0. V282 gives −1.02.
- **F2:**
  - NOT LIVE if the E3 median has |β| < 0.04; LIVE if β > +0.10; INVERTED if β < −0.10. Anything between is inconclusive.
  - The port must reproduce rp7b on r75 (null |E3| < 0.04, synthetic > +0.15), or the r71b reading is void.
  - **Result: port reproduced, and the trim is LIVE.**
- **F3: fork mismatch.** List every r1 key that flew differently from the file. Flag Kp off SteerKP by more than 1 %, or LAF off
  SteerLatAccel by more than 2 %. **Result: 0 differences; Kp and LAF match exactly.**
- **F4: faults.** Any STEER_STATUS ≠ 0, steerFault flag, steer-unavailable event, or OUTPUT_DISABLED while engaged.
  **Result: none.**

## 0. The cache and the loader (other agents: start here)

**Extractor:** `analysis-2020accord/studies/v295/extract_r71b.py`.
- It makes one pass over all 17 segments, one worker per segment, and takes about 10 s.
- It is deterministic: a rebuild reproduced every output sha256.
- It decodes with the **fork's own cereal** (`Dom 20d24ab79` = the commit that flew; copied to `_scratch/cereal_fork_native/`
  with opendbc's `car.capnp`). `starpilotLateralState` and `customReserved9` therefore decode under their real names.
- **Positive control:** segment 0 decoded through the kit's patched schema (`v293_flight_read.fork_log_schema`) gives
  identical 0x18F counts, carState angle, torqueState.p and lateralState.ff arrays. EVIDENCE.

**Files it writes**, all gitignored and regenerable:

| path | sha256 (first 16) | contents |
|---|---|---|
| `_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz` | f735dd2c8e55ee60 | raw CAN per (address, bus): `x<ADDR>_b<BUS>_{t,dat,dlen}` for 0xE4 (buses 0/1/2/128/129/193), 0x18F, 0x14A, 0x1AB, 0x158, 0x1D0, 0x309, 0x33D; `send_x0E4_b1_*` from sendcan |
| `…/svc.npz` | 3ab6d904bdba9e63 | every service stream at its native rate (112 arrays) |
| `…/meta.json` | 0db115a8882ae3f9 | initData (git, **all 706 params**), carParams, GPS/clock anchors, onroadEvents census and changes, runtime toggles (first dict + changes), alerts, Testing Ground, segment spans |
| `analysis-2020accord/_scratch/cache/v280/r71b_v294{.npz,_b4.npz,_marks.json,_params.json}` | 366a4c2d… / 0caa6385… / 12e96320… / 32443f5a… | the kit's v280-format cache, decoded exactly as `v293_flight_read.extract` decodes. `creep20_loop_id.load('r71b_v294')` and `v293_flight_read.load_route('r71b_v294', …)` work unchanged |
| `rlog-tools/studies/grind/_scratch/cs_r71b_v294.npz` | 964c30ec3e9b5457 | the flight read's control-path cache (`build_cs_cache` format) |
| `rlog-tools/_scratch/cache/<route>/CACHE-POINTER.json` | – | pointer file |

**Loader:** `analysis-2020accord/studies/v295/lib/r71b_cache.py`.
- `load()` returns a dict of native-rate arrays, plus `meta` and `can_raw`.
- `grid100(D)` puts every stream on the 0x18F frame axis with previous-value (ZOH) sampling. It also provides
  `eng` (= 0xE4 req & SCA) and `eng_ctl` (= latActive).
- `kit_grid()` returns the kit's dejittered grid.
- `wheel_rate_dps()` and `wheel_accel_dps2()` give wheel rate and acceleration.
- `v294_cells()` reads the image cells, hash-checks the image, and decodes `e_shift` and `fb_op` from the code halfwords.
- `python r71b_cache.py --selftest` re-runs every positive control. Current result: **PASS**.

**Array names returned by `load()` (136):**
- **CAN (decoded):**
  - 0xE4, 100 Hz: `e4_t e4_cmd e4_req e4_b2 e4_b3`
  - 0x18F, 100 Hz: `s18_t s18_tq_raw s18_rate_raw x_fw s18_sca s18_status s18_cfg s18_b4`
  - 0x14A, 100 Hz: `s14_t s14_angle s14_rate s14_b4`
  - 0x1AB tap, 50 Hz: `tap_t tap_T tap_b0 tap_b2`
  - 0x158, 100 Hz: `v158_t v158`
  - `t0`
- **carState (100 Hz):** `cs_{t,angle,rate,torque,torque_eps,pressed,vego,aego,vego_raw,yaw,standstill,fault_tmp,fault_perm,blink_l,blink_r,cruise_en,angle_off}`
- **controlsState / torqueState (100 Hz):** `ctl_{t,which,active,error,error_rate,p,i,d,f,output,saturated,la_act,la_des,jerk_des,version,curv,des_curv}`
- **carControl (100 Hz):** `cc_{t,enabled,lat_active,torque,angle,curv,torque_can}`
- **carOutput (100 Hz):** `co_{t,torque,torque_can,angle,curv}`
- **selfdriveState (100 Hz):** `sd_{t,enabled,active,state,engageable}`
- **starpilotLateralState (100 Hz):** `spl_{t,active,fric_thr,fric_scale,ff,fric_jerk,fric_jerk_dz,lsf,unwind,dob,dob_frozen}`
- **modelV2 (20 Hz):** `mdl_{t,des_curv,frame}`
- **drivingModelData (20 Hz):** `dmd_{t,des_curv}`
- **liveParameters (20 Hz):** `lpar_{t,sr,roll,off,off_avg,stiff,valid,sr_valid,sensor_valid,sr_std}`
- **livePose (20 Hz):** `pose_{t,wz,wx,wy,ay,ax,roll,pitch,ok}`
- **liveTorqueParameters (4 Hz):** `ltp_{t,laf,off,fric,laf_raw,off_raw,fric_raw,valid,use,pts,cal}`
- **liveDelay (4 Hz):** `ldel_{t,delay,est,est_std,blocks,status,cal}`
- **pandaStates (10 Hz):** `panda_{t,allowed,rx_inv,tx_blk,safety,nfaults,rxchk_inv,ign}`

**Units and signs, each positive-controlled against carState on this route (EVIDENCE, by regression over the whole route):**

| signal | relation measured | meaning |
|---|---|---|
| `s14_angle` = i16be(b0..1) × −0.1 | = carState.steeringAngleDeg (slope 1.0000) | deg, + = left |
| `s14_rate` = i16be(b2..3) × −1 | = carState.steeringRateDeg (slope 1.0002) | deg/s, 1 deg/s resolution. The firmware writes (−x)>>3 here |
| `s18_rate_raw` (the kit's `wire`, the v280 `rate` column) | = **−7.997 ×** steeringRateDeg | 🛑 NEGATIVE of the wheel rate. `x_fw` = −raw = 8 × rate in counts, so `wheel_rate_dps` = x_fw/8 at 0.125 deg/s resolution |
| `s18_tq_raw` | carState.steeringTorque = −1.0006 × raw | the kit's `bar` = raw × 1.024 |
| `e4_cmd` (bus 129 = panda TX-echo) | = carOutput.torqueOutputCan (slope 0.9998, r 0.99996); ≈ −4093 × carOutput.actuatorsOutput.torque | + = steer RIGHT (openpilot torque + = left) |
| `tap_T` = sign bit 9, (fld & 511) × 8 | sign(T) = **+sign(cmd)** on 0.9992 of 17,659 frames (\|cmd\| > 200, T ≠ 0) | delivered lane torque gp-0x6b38 |

Additional field checks:
- **0x14A byte 4:** bits 0–2 are 7 on every frame (stock Honda). Duty of bits 3–7: 0.444, 0.305, 0.033, 0.247, 0.378.
- **Not populated on this car:** carState.yawRate and steeringTorqueEps are 0 on every frame. Use `pose_wz` for yaw rate.
- **0x158 speed:** v158 = 0.976 × vEgo. Speed bands use vEgo.
- **0x18F carries no angle.** The brief's "0x18F STEER_ANGLE" is on 0x14A.
- **Two grids, different lengths:** `kit_grid()` fills 171 dropped frames (102,039 frames against 101,868 native). Align the two
  grids by time, never by index.

## A. Exposure (EVIDENCE: wire; wall clock from the GPS anchor)
- **Time:** 2026-09-30 03:10:06 → 03:27:07 UTC, i.e. **2026-09-29 20:10 → 20:27 PDT** (the UTC−7 offset is BELIEF).
  initData.wallTimeNanos reads 2026-07-28 because the device clock was not synced at boot; ignore it.
- **Size:** 1020.4 s over 17 segments (0–16), contiguous, with 3–8 ms inter-segment gaps.
- **Laterally engaged** (0xE4 STEER_REQUEST & 0x18F SCA): **800.7 s (78.6 %)**. carControl.latActive gives 800.8 s, and the two
  overlap on 800.7 s.
- **6 episodes:** longest 306 s, median 110 s. Max speed 30.6 m/s; engaged speed p50 10.9 and p90 20.4 m/s.
- ⚠ **Almost entirely lateral-only.** selfdriveState.enabled (openpilot longitudinal) was on for only 14.4 s: buttonEnable at
  695 s, cancelled at 709.6 s. The rest ran on always-on lateral with the driver on the pedals. panda controlsAllowed was on
  1.4 % of the time, which is consistent with this.
- **steeringPressed share of engaged frames: 0.066.** Hands-off engaged: **747.7 s** (not pressed), or 709.0 s by the kit's
  \|bar\| < 400.

| band m/s | engaged s | pressed share | hands-off s | \|bar\|<400 s |
|---|---|---|---|---|
| 0–5 | 109.7 | 0.187 | 89.1 | 81.2 |
| 5–10 | 228.5 | 0.088 | 208.4 | 191.2 |
| 10–15 | 225.4 | 0.041 | 216.0 | 207.4 |
| 15–22 | 162.9 | 0.012 | 160.8 | 157.4 |
| 22+ | 74.3 | 0.013 | 73.3 | 71.8 |

## B. Fork: what flew (EVIDENCE: initData, the runtime toggle object, and the control path's own arithmetic)

**Build and config**
- **initData:** gitCommit **`20d24ab7906883a9cdccfd945a4f54b6e109288b`**, branch **Dom**, **dirty False**, remote
  raayyymond/StarPilot, commit date 2026-09-29 17:37 −0700, device `mici`. The commit is the same in all 17 segments.
  - It is the redo-fork "fix the rev-6.4 tests + LaneChangeTurnGate known()" commit, one after `54ff1ea39`. The operator
    committed and deployed it.
- **Config:** all 26 keys of `toggle-config_V294_accel-trim_r1.decoded.json` **MATCH** in both initData.params and the runtime
  toggles (`starpilotPlan.starpilotToggles`, 537 keys, 0 changes during the route). **Zero differences.**
- **Other lateral params present:**
  - Steer ratio: `SteerRatio 16.84` (stock 16.33), `AccordVariableSteerRatio 1`.
  - Delay: `SteerDelay 0.2` (stock 0.30), with `UseAutoSteerDelay 1`.
  - Controller: `ForceTorqueController 1`, `NNFF 0`, `NNFFLite 0`, `LateralTune 1`, `AdvancedLateralTune 1`.
  - Lane handling: `AlwaysOnLateral 1`, `LaneCentering 1`, `LaneChangeTurnGate 1`, `LaneChangeSmoothing 4`.
  - Other: `SteerOffset 0.0`, and a `LiveDelay` param (72-byte blob).
  - The stock values the fork would back-fill are `SteerKPStock 0.6`, `SteerLatAccelStock 1.689`, `SteerFrictionStock 0.212`.
    None of them was used.

**"Default lateral logic with custom tuning values", exactly**

The generic `LatControlTorque` ran: torqueState on **79,744 / 79,744** active frames. Every Accord torque-mode term was off, in
params and at runtime:
- AccordRatePlantFF, HoldMap, HoldLevel and FrictionHystBand were false.
- FrictionHyst, RateLoopGain, ErrorNotchQ, RefFilter, TorqueKiHigh, DobHz and Dither were 0.
- `accordObserverTorque` was identically 0.

The custom values that flew:

| quantity | flown value | read from the wire (method) |
|---|---|---|
| Kp | SteerKP 0.9 | **0.90000** (torqueState.p/error, 77,312 frames, p1 = p99) |
| Ki | AccordTorqueKi 0.3 | **0.3000** (Δi/(0.01·error), 67,668 unfrozen frames, IQR [0.3000, 0.3000]) |
| Kd | 0 | max \|d\| = 0 |
| LAF | SteerLatAccel 14.0 (custom; the live learner's 2.22 is NOT used) | **14.0000** ((p+i+d+f)/−output, 58,321 unsaturated frames) |
| friction | SteerFriction 0.011 (torque units) | the relay term in `f` has a plateau of 0.157 m/s² (p95) = **0.0112 torque**. opendbc `get_friction` scales friction by LAF: 0.011 × 14 = 0.154 m/s² = **45 CAN counts** of relay, with threshold 0.30 m/s² |
| latAccelOffset | KeepLearnedLatAccelOffset 1, useParams 1 | the learner's filtered offset (p50 −0.151 m/s²) is subtracted. `f` regressed on it gives slope −1.003 |
| steer ratio | the variable-ratio map at level 16.84/16.88 | **the map ran.** Across angle bins 15° → 400° at 3–10 m/s, q·SR_map varies 2.98 % and q·16.84 varies 23.07 %. SR goes from 16.84 on centre to 14.17 at 200–400°. liveParameters.steerRatio (16.84) is ignored for this platform |
| lateral delay | UseAutoSteerDelay | liveDelay.lateralDelay **0.326 s constant** (status "estimated" all route). lat_delay = 0.326 + LAT_SMOOTH 0.1 = 0.426 s (code-read, BELIEF) |
| jerk LPF | AccordJerkLpHz 1.2 | runtime toggle 1.2 (the generic path) |

Other reads:
- **starpilotLateralState.ff equals torqueState.f on 100 % of active frames.** lowSpeedFactor p50 0.888, unwind share 0.015,
  frictionThreshold 0.30.
- **carParams:** HONDA_ACCORD, lateralTuning torque (LAF 1.689, friction 0.212, both replaced by the custom toggles),
  steerActuatorDelay 0.1, torqueBP/V [0, 4096].

## C. Firmware: is this route V294? **YES**

**Cells and the two images**
- **V294 image cells, read from the image** (sha256 `3143616d…`):
  - code halfwords: `e_shift` 2 (0x29D76 `shl 2`), `fb_op` diff (0x28FA4 `subr`)
  - fb-lag pole 1011 (2.033 Hz), b 567, fb clamp 1024
  - Kp 960 on every knot, Kd 0, Ki 0
  - out lag 992/507, gain 5346, P/sum/T clamps 15360/15360/3072
- **Map, fade and setpoint-taper cells are identical to V293's.** EVIDENCE: byte read.

**C1. The FF identity.** Method: `v293_flight_read.identity_block` computes |427 tap| against surface(idx) × fade with zero
free parameters, over 40,037 laterally engaged tap frames at best lag −30 ms.

| cells / fade axis | R² | resid (counts) |
|---|---|---|
| V293 / bar | **+0.9868** | 22.4 |
| V293 / speed | +0.504 | 137 |
| V293 / const | +0.642 | 117 |
| V282 / bar (negative control) | **−1.024** | 277 |

The same identity split by wheel acceleration (\|d/dt LPF_2.03(rate)\|):

| frames | n | R² | resid (counts) |
|---|---|---|---|
| all engaged | 40,037 | 0.9868 | 22.4 |
| \|acc\| < 50 deg/s² | 33,256 | 0.9977 | 6.9 |
| \|acc\| < 20 | 27,954 | **0.9981** | **5.8** |
| \|acc\| < 10 | 23,247 | 0.9982 | 5.4 |

The residual grows with wheel acceleration. That is the trim's signature: V293 is flat there.

**A second implementation, the golden model:**
- `lkas_rate_pid_surface` on a Calibration built from the V294 image cells equals the golden model on the V293 image cells at
  **241/241** demand indices.
- It matches `v293_lib.surface` to within 4 counts. The difference is the closed-form lag against the integer march, and it is
  below the tap's 8-count LSB.
- On taper-254 frames with \|acc\| < 20 it gives R² 0.9984, resid 5.3.

**Sign:** sign(T) = +sign(cmd) on 0.9992 of frames. The identity table's own column reads 0.94–0.95 because it includes
cmd ≈ 0 and T = 0 frames.

⚠ **The FF identity alone cannot tell V293 from V294.** The FF is bit-identical by design. The trim instrument below is the
discriminator.

**C2. The pre-registered trim-live instrument** (HANDOFF-2026-09-23 item 2)

The implementation is a port of `redo_2026-09-23/physics/rp7b_dynamic_pred.py` with every constant read from the V294 image:
- **Predictor:** the byte-exact 1 kHz integer march on the route's own command (ZOH), with the tap sampling instant and tap sign
  scanned.
- **Regressor:** `Rm = lp1(−d/dt lp1(wire/8, 2.03 Hz), 5.05 Hz)` in deg/s².
- **Estimator E3:** residual ~ 1 + Rm + FF + dFF/dt, on 20 s hands-off windows (\|bar\| < 400).

*Port controls (it must reproduce rp7b_out.txt):*

| route | null E3 median | synthetic-live E3 median | rp7b's values |
|---|---|---|---|
| r75_v293r4 | +0.003 | +0.207 | +0.005 / +0.208 |
| r70_v293 | +0.000 | +0.191 | −0.000 / +0.191 |

**Port reproduced.** EVIDENCE.

*Sign calibration on this route:*
- The polarity leg (the HP correlation between the FF-predicted torque and the wheel's acceleration) gives
  x_tapconv = **+1 × wire**, the same as every V293 route. Its peak correlation is +0.18, against 0.33–0.57 on V293.
- BELIEF: the correlation is weaker because a live damping trim reduces the wheel's acceleration response.
- With s_x = +1, **β > 0 means negative feedback, the design sign.**

*Results on r71b:*

| read | value |
|---|---|
| **E3, 6 windows** (the pre-registered form) | **median +0.197**, 5–95 % [+0.138, +0.211]; **6/6 > +0.10**; 0/6 below 0.04 |
| E3 on the MODELLED trim alone (what a live V294 reads on this route's excitation) | median +0.191 [+0.160, +0.211] |
| E3 on the real tap + a second synthetic trim | +0.387 (additive, as expected) |
| **POOLED E3, 709 s hands-off engaged, 10 s block bootstrap (86 blocks, 1000 resamples)** | **β = +0.210, 95 % CI [+0.208, +0.212]** (model: +0.211 [+0.210, +0.212]) |
| **SCALE** (residual regressed on the modelled trim + FF nuisance) | **0.964, 95 % CI [0.943, 0.975]** (1 = live at the design gain, 0 = not live, < 0 = inverted) |
| **SIGN CONTROL** on frames where the modelled trim is ≥ 24 counts (1,639 frames, 33 s) | rms(tap − null march) **63.3** counts; rms(tap − live march) **7.5**; rms(tap − march with the operand INVERTED) **125.6**. EVIDENCE of the right sign |
| all hands-off engaged frames | rms null 15.0 → live 5.4 counts |

*By speed band* (pooled E3, block-bootstrap CI):

| band m/s | β | 95 % CI | hands-off s | modelled β |
|---|---|---|---|---|
| 0–5 | +0.212 | [+0.206, +0.216] | 81 | +0.212 |
| 5–10 | +0.211 | [+0.209, +0.213] | 191 | +0.211 |
| 10–15 | +0.206 | [+0.201, +0.210] | 208 | +0.210 |
| 15–22 | +0.201 | [+0.191, +0.204] | 157 | +0.213 |
| 22+ | +0.197 | [+0.183, +0.221] | 72 | +0.203 |

*Per window* (route time, mean speed, E3 real / model):
- 151 s, 7.7 m/s: +0.196 / +0.210
- 297 s, 10.5 m/s: +0.187 / +0.158
- 373 s, 12.4 m/s: +0.198 / +0.168
- 491 s, 21.0 m/s: +0.201 / +0.212
- 723 s, 15.3 m/s: +0.122 / +0.174
- 822 s, 13.3 m/s: +0.215 / +0.208

**Verdict, from the wire:**
- **This route ran the V294 image, or a byte-equivalent one.**
- The FF identity is V293-class, and V282 cells fail it.
- The acceleration trim is **LIVE, with the design sign**, at **0.96× the gain** the byte-exact march predicts from the 100 Hz
  wire rate.
- The small shortfall is BELIEF: the ECU's operand is the 1 kHz resolver-derived x, and ours is the 100 Hz 0x18F field
  up-sampled. It is not decision-bearing.
- The pre-registered sentence that fires is **"β > +0.10 = LIVE (expected +0.21)"**.

## D. Faults, events, limits (EVIDENCE: wire and logs)

**No fault of any kind.**
- **0x18F STEER_STATUS** is 0 on all 101,868 frames, and CONFIG_INDEX is 0.
- **carState** steerFaultTemporary and steerFaultPermanent are both 0 frames.
- **0x1AB OUTPUT_DISABLED** is never set.
- **onroadEvents** has no steerUnavailable, steerTempUnavailable or canError. Counts: steerOverride 230 msgs, gasPressedOverride
  710, pedalPressed 302, laneChange 79, brakeHold 150, cruiseMismatch 14, buttonEnable 1, buttonCancel 2 (userDisable at
  709.6 s), commIssue 1, selfdrivedLagging 7 (at start-up), wrongGear/reverseGear (parking).
- **Alerts:** 5 lane changes, brakeHold, one gas override during the 14 s long-engagement, and reverse at 1001 s.
- **panda:** safetyTxBlocked is 19 at t = 10.7 s, which is pre-engagement and equals the 19 missing 0xE4 echoes (100,517 sent,
  100,498 echoed). It is 1–2 during the 706–709 s gas override. safetyRxInvalid is 0 and faults are 0.
- **EME:** no EME indicator exists on the wire in this build (BELIEF: none is in the record's instruments). The tap never
  exceeded 1464 counts, which is 60 % of the 2461 rail, and never touched the rail.

**Command and wheel limits**
- **0xE4 command:** max +4096, min −2130. **|cmd| ≥ 4096 on 0.23 % of engaged frames (181 frames, 1.81 s).**
  - **Every one of those frames is driver-pressed**, at v p50 1.6 m/s with |bar| p50 2838: low-speed manoeuvres with the driver
    overriding.
  - At those frames the tap reads |T| p50 504 and max 744. The driver-torque fade and the setpoint taper cut it.
  - Hands-off, the command never reached the limit.
- **Slew:** 0.25 % of latActive frames asked for |Δtorque| > 0.03/frame, the Honda STEER_DELTA cap of 123 counts. carOutput's
  |Δ| max is exactly 0.0300/frame. 0.42 % of engaged 0xE4 frames step by 120 counts or more.
- **Wheel:** max |steeringRateDeg| **373 deg/s** (engaged 373, p99 engaged 177). Max |angle| 394°, engaged 374°.
- **427 tap:** max |T| **1464** counts. It was nonzero while not engaged on only 20 frames (max 160), which are ZOH edges at
  engage/disengage.

## Surprises and notes (reports, not actions)
1. **The flown fork commit is `20d24ab79`**, not the `54ff1ea39` named in the 09-20/09-23 handoffs. It is the redo-fork test-fix
   commit, now committed and deployed, and it is not dirty.
2. **The route was 98 % lateral-only.** Always-on lateral was active and openpilot longitudinal ran for only 14.4 s.
   "Engaged" here always means lateral.
3. **The SteerFriction relay is live on the generic path.** Its amplitude is SteerFriction × LAF = 0.154 m/s², which is
   0.011 torque or 45 CAN counts, with a 0.30 m/s² threshold. It is 19× smaller than route 73's accidental 0.212, but it is a
   relay (friction/threshold acts as a loop gain on the error), so it is worth keeping in view in any closed-loop model of
   this setup. BELIEF on its effect.
4. **liveDelay stayed at 0.326 s for the whole route** (status "estimated", 50 blocks). lat_delay is 0.426 s including the
   0.1 s smoothing (code-read).
5. **The polarity-leg correlation is lower than on V293** (+0.18 against 0.33–0.57), and the best tap sampling offset is 0 ms
   against −4 ms. Both are consistent with a live damping trim (BELIEF). The sign rests on the inverted-operand control, not on
   this correlation.
6. **The steer-ratio shape test leaves a residual rise with angle.** q·SR_map goes 0.337 → 0.347 (+3 %) from 15° to 200°+.
   Possible causes: the map under-corrects slightly at large angle, or the unmodelled understeer/roll terms. BELIEF; not
   resolved here.
7. **v293_lib's closed-form surface and the golden model's integer march differ by up to 4 counts at some indices.** Both
   predict the tap to R² ≥ 0.998 on low-acceleration frames. The golden model is exact V293 = V294 at 241/241.

## Open issues
- The pre-registered E3 form uses 20 s hands-off windows and yields only 6 on this route. The pooled 709 s estimate agrees with
  it, and I carried both.
- The 3.6 % trim-gain shortfall (scale 0.964) is unexplained beyond the 100 Hz / 1 kHz belief above.
- EME has no wire indicator, so "no EME event" is bounded only by STEER_STATUS 0 and the tap staying at or below 60 % of the rail.
- The 0x14A cave bits 3–7 are cached raw and are not interpreted for V294 here.

## Files
- `analysis-2020accord/studies/v295/extract_r71b.py` — the extractor
- `analysis-2020accord/studies/v295/lib/r71b_cache.py` — the loader and self-test
- `analysis-2020accord/studies/v295/flight/r71b_attribution.py` — this attribution
- `analysis-2020accord/studies/v295/flight/r71b_attribution_out.txt` and `.json` — its output
- `analysis-2020accord/studies/v295/flight/census_seg.py` — the single-segment census used to pick the buses
- Caches: see section 0.
