# HANDOFF 2026-09-15 — V293 rev 4 FLEW (route 75): the loop's ceiling, and REV 5 = a disturbance observer

**Firmware unchanged: V293 stays in the car. Nothing flashed, nothing sent on CAN.** Fork `Dom 08a5a706 → e44b6cd31`,
config `toggle-config_V293_torque_mode_r4 → _r5`. Deployed to the device and rebooted at 00:38.
Page: https://claude.ai/artifact/8Bc1Xqt9qeFhsDLbayqK2H

## 0. The wrong-route incident (read this first if you fetch a route)

The fetch subagent (no browser tools in its context) never reached connect; the orchestrator fetched
`75604b0a432fdc89_00000075--9bbcb3f7da` from connect — an **August 2026 route** (branch StarPilot, commit `9e3ab90`,
SteerKP 0.6) that shares the counter `00000075` with the real drive because the dongle counter reset on 2026-09-13.
Everything derived from it (extract caches, flight read, a full rev-5 read) was deleted. The real rev-4 drive is
**`75604b0a432fdc89_00000075--6c8687d5bd`** (2026-09-14 22:43–22:57, 15 segments, 195.5 MB) plus the 57-s lead-in
`00000074--2bf17ca67d`, both taken by `scp` from the device's `/data/media/0/realdata`. **Rule: decide "newest" from
the device's realdata or connect's date, never from the counter; attribute from `initData` before analysing anything.**

## 1. What route 75 said (EVIDENCE — the wire; `v293r3_read.py r75_v293r4 r72_v293r3 r73_v293r3`, `v293r5_read.py`, `_scratch/hardturn_spec.py`)

Attribution: `GitCommit 08a5a706 / Dom`, Kp 0.8500 and LAF 14.0000 on every active frame, `AccordTorqueKiHigh 2.5`,
`UseAutoSteerDelay 1` (liveDelay 0.280 s). 872 s wall, 803 s laterally engaged, 758 s hands-off; speeds 2.8–28 m/s.
Operator: *"still a little loose; still jerky on hard turns; not as smooth, confident and well-controlled as the 1 kHz
inner loop; the command has to overshoot to get over friction."*

| hands-off, planner desire vs actual | 1–8 | 8–15 | 15–22 | >22 m/s |
|---|---|---|---|---|
| tracking gain, rev 3 (r72) → rev 4 (r75) | 0.96 → 0.98 | 0.98 → 0.97 | **0.80 → 0.98** | **0.74 → 0.97** |
| lag planner→actual, s | 0.00 → 0.29 | 0.11 → 0.13 | 0.46 → 0.31 | 0.52 → 0.45 |
| rms error / rms signal, rev 4 | 0.19 | 0.26 | 0.21 | 0.30 |
| error energy <0.3 Hz / 0.3–1 Hz, rev 4 | 49 / 34 % | 66 / 23 % | 62 / 18 % | 69 / 17 % |
| integrator share of the torque, rev 4 | 0.32 | 0.29 | 0.29 | 0.33 |
| turn hold actual/planner at >1.5 m/s² | 0.94 | 0.93 | 0.97 | – |

- **Rev 4 did its job** (the Ki schedule fixed the high-speed gain) **and the residual is exactly the integrator-paced
  catch-up the operator calls loose**: half to two thirds of the error energy below 0.3 Hz.
- **The hard-turn jerk is the lightly damped 2–2.7 Hz closed-loop wheel mode.** v<10 hard turns (25 s): 24 rate bursts
  >80 deg/s, 0.12 s long, spaced 0.53 s; torque command +6.9 dB at 1.95 Hz; wheel-rate energy 59 % in 0.3–1 Hz, 19 % in
  1.6–3 Hz. v 10–20 (9 s): des→act |H| **2.28 at 2 Hz, coherence 0.99**, 47 % of the rate energy in 1.6–3 Hz, peak 2.73 Hz
  +13 dB. Route 72 shows the same burst spacing (0.56 s). **Zero stiction dwells** by the route-70 definition on either drive.
- **Plant damping by speed:** the time-domain fit u(t−Td) = hold(θ) + bθ' + Jθ'' + F sign θ' gives **b 0.0005–0.0009
  torque/(deg/s) below 15 m/s on both drives**, 0.0004/0.0038 at 15–22 (r75/r72 disagree), ~0.0043 above 22 (2–4 stretches,
  R² 0.73–0.86); F 0.009–0.014 (the 0.015 hysteresis is right); J 8e-5 confirmed. The joint-IO transfer at 15–30 m/s leans
  lightly damped below 0.6 Hz and has no coherence above (planner instrument). **The 09-13 ident's b (0.0018–0.0049) is
  BELIEF below 20 m/s.**
- Command-proportional friction (N4): cU·|u| ≤ 0.001 torque at the median |u| — the firmware friction-comp lane is not a
  visible factor. Roll median +1.7–1.8° on every route; removing it cuts 7–23 % of the low-frequency residual (device
  levelling or camber, BELIEF).
- 2 Hz mode on straights (S3): rate 1.6–3 Hz +1.7..+5.6 dB, the 3–5.5 Hz rate-loop hump +0.9..+4.0 dB — the rate loop's
  own crossover through the delay (see §2).

## 2. Why a 100 Hz loop cannot linearise friction here (EVIDENCE — linear model `v293r5_loopshape.py`)

Not the rate: the ~60 ms round trip plus filters. A P loop through it has static stiffness 1 + Kp_t/k = **1.7** (≈3 at the
most Kp the margins allow), so 1/1.7 of any hold-level error / crown / missed friction stays in the angle until the
integrator arrives at its own 0.2–0.5 Hz corner. A rate damper has phase −(ω·Td + atan ω·RC): with RC 0.03 it stops
damping at ≈2.8 Hz and pumps 3–5 Hz (the hump above); RC 0.01 moves the boundary to ≈3.3 Hz. The 1 kHz EPS loop damped
to tens of Hz; that cannot be recovered from outside the EPS.

## 3. Rev 5 — the disturbance observer (fork `e44b6cd31`, BELIEF = simulation; every number from `v293r5_design*.py`)

`HondaAccordDisturbanceObserver` (`latcontrol_vehicle_tunes.py`): every frame
w = hold(θ) + b(v)·θ' + J·θ'' − u_left(t − 0.06) from the measured angle/rate (+left frame) and the controller's own
output six frames back; two first-order poles at `AccordDobHz`; clip ±0.3; fade 3→6 m/s; held (not reset) while
`steer_limited_by_safety or steeringPressed`; reset on engage; the estimate is ADDED to the torque feedforward
(`inner_torque += -w_left`). Its loop closes only through model mismatch (|Q|·|P/P_m − 1| < 1), not the plant's phase.

**Design decisions and why (each one a sweep):**
- **Model b = the fork's 1/G(v) (0.0018–0.0049), not the drive's 0.0006.** Residual = (b_m − b)·rate + F sign + w, so the
  observer injects damping Δb·Re Q(f): positive below f_Q, negative above. Model b HIGH: installs damping below the corner
  (T2 overshoot 0.51 → 0.20) and costs a little at the 2 Hz mode. Model b LOW (0.0006) in the identified world strips the
  plant's damping: T2 overshoot +0.37..+0.49, hold error 0.48–0.84 m/s² — worse than rev 4. Wrong-high is the safe side.
- **Corner 0.6 Hz, not 0.8**: 0.8 rang (T3 4.0°) with delays ×1.5 in the lightly damped world and cost +40..+150 % 1.6–3 Hz
  energy with Kp 1.2. 0.6 keeps most of the tracking gain.
- **Kp 1.0** (not 1.2): 1.2 buys little more and costs mode energy. **Ki 0.3 flat, `AccordTorqueKiHigh 0`**: the observer
  does the schedule's job 3–5× faster without reference-path lag; 0.3 stays as the backstop for freeze/clip.
- **Kv 1e-3, RC 0.01**: −15..−20 % simulated hard-turn 1.6–3 Hz energy vs 6e-4/0.03; noise 1e-3 × 0.125 deg/s LSB = 1e-4 torque.
- **Notch unchanged** (Q1 at √(k/J)): moving it ×1.35 to the closed-loop mode is unstable at 26 m/s (T3 834°).

**Shipping candidate, speed-averaged 6–26 m/s (`V293-REV5-DESIGN-SHIP-2026-09-15.txt`, ALT-A = rev 5):**

| world | T1 |e|@1 s | T2 overshoot | T3 max ring ° | T8 hold error | T8 1.6–3 Hz rate rms |
|---|---|---|---|---|---|
| lightly damped: rev 4 → rev 5 | 0.074 → 0.029 | +0.51 → +0.20 | 1.84 → 0.92 | 0.219 → 0.086 | 3.20 → 3.48 (+9 %) |
| lightly damped, hold ×1.5 | 0.062 → 0.033 | +0.12 → +0.05 | 1.82 → 1.79 | 0.163 → 0.203 (worse at 19–26) | 3.04 → 3.16 |
| identified | 0.073 → 0.049 | +0.20 → +0.12 | 0.96 → 1.35 | 0.329 → 0.159 | 1.06 → 1.10 |
| identified, delays ×1.5 | 0.075 → 0.050 | +0.23 → +0.17 | 1.00 → 1.53 | 0.378 → 0.181 | 1.17 → 1.25 |
| lightly damped, delays ×1.5 | 0.065 → 0.020 | +0.59 → +0.30 | 2.18 → 0.73 | 0.266 → 0.108 | 4.06 → 4.96 (+22 %) |
| lightly damped, J ×1.5 | 0.071 → 0.029 | +0.65 → +0.34 | 2.15 → 0.96 | 0.250 → 0.125 | 2.72 → 3.10 (+14 %) |

**Rejected, with numbers:** the model-PREDICTED rate damper (`il_pred_td` in the simlib — propagate the measured state
60 ms through the model, close the rate loop on the prediction): **divergent** at 26 m/s in the lightly damped world with
the identified-b model (T3 179–462°), divergent with delays ×1.5 (T8 rate rms 41 deg/s), biased during stiction; no gain
even with a matched model. Dead until b(v) is identified per speed. Dither: not proposed (7–10 Hz sits on the V281 7 Hz
ripple and passes the base-assist path hands-off).

**Fork verification:** the observer class extracted from the patched file passes a standalone cross-check
(`_scratch/observer_xcheck.py`: converges to an injected +0.04 with the right sign, controller-frame addition −0.04,
viscous-mismatch formula exact, freeze/fade/off/6-frame delay correct). Tests on the comma: **254 passed, 2 failed =
the pre-existing Bolt/Palisade failures.** Patch script: scratchpad `patch_fork_rev5_dob.py` (exact-count anchors; dry-run
on a copy first). Fork files: `latcontrol_vehicle_tunes.py` (constants, class, RC), `latcontrol_torque.py` (init, reset,
add, step, publish), `params_keys.h` (`AccordDobHz` FLOAT 0.6), `starpilot_variables.py`, `safe_mode.py`,
`device_settings_layout.json`, `cereal/custom.capnp` (`accordObserverTorque @8`, `accordObserverFrozen @9`), two test files.

**Wire instrument:** `starpilotLateralState.accordObserverTorque` (torque frame, the term added this frame) and
`accordObserverFrozen`. Kit: `v293_flight_read.py` decodes both (patched schema, cache keys `sp_dob`/`sp_dobfrozen`, an
OBSERVER line in section 0); `v293r5_observer_read.py` is the pre-registered read.

## 4. Deployed (EVIDENCE — read back from the device, 10.0.0.168 after the move indoors)

`git pull --ff-only` to `e44b6cd31`; `rebuild_params` 221 s (`AccordDobHz` missing before, none after); the 22 keys of
`toggle-config_V293_torque_mode_r5.decoded.json` written with `put_bool`/`put_float` and read back; rebooted 00:37:51;
after the boot: `AccordDobHz 0.6`, `SteerKP 1.0`, `AccordTorqueKi 0.3`, `AccordTorqueKiHigh 0.0`, `AccordRateLoopGain 0.001`,
`GitCommit e44b6cd31…`, the schema loads with the new fields, the observer imports, `HONDA_ACCORD_RATE_LOOP_RC 0.01`.

## 5. The SteerFriction canary (OPEN)

Route 74 (22:20) logged `SteerFriction 0.0`; route 75 (22:43) logged `0.2120497` (stock) — both after the rev-4 fix.
Facts: the live file's mtime was `2026-07-28 08:05:30`, and **boot-time writes on this device carry a July-28 08:04–08:05
timestamp because the clock is not yet set** (GitCommit, IsOnroad, the params cache all show it) — so the file WAS
rewritten ~30 s into a boot. `Params.put` is mkstemp+rename (mtimes are real). The Galaxy restore writes floats as `str`
("0.0", never empty). A Sonnet trace of every writer (`_sync_stock_param` — only both-keys-unset back-fills; troubleshoot
reset / FLM apply / profile load all move sibling keys too; no CLEAR_ON flags; the boot cache sync `params_defaults_cache_sync`
only fills a None) found no mechanism whose blast radius matches. **Experiment tonight: 0.0 written before the offroad
reboot survived it** (mtime 00:37:34 unchanged after boot) → the remaining suspect needs ignition-on/onroad
(`starpilot_variables.update()` with CarParams). Functionally moot (the relay is off under `AccordFrictionHyst`); the
flight read flags a MISMATCH. **Check it in the r5 drive's initData first**, and if it flips again, `stat` the file and
grep the swaglog of THAT boot for `SteerFriction`.

## 6. Pre-registered read (in `v293r5_observer_read.py`'s docstring; baseline on r75 written)

O1 on the wire: |dob| median >0.002, frozen <30 %. O2 loose: planner-error rms 0.05–0.3 / 0.3–1 Hz falls ≥30 % vs r75
(8–15: 0.048/0.040 · 15–22: 0.064/0.056 · >22: 0.067/0.030), integrator share 0.25–0.29 → <0.15. O3 confident: des→act |H|
0.85–1.15 at 0.5 Hz, 0.7–1.3 at 1 Hz. O4 jerky: hard-turn 1.6–3 Hz share ≤ 29 % (r75 19 %), reversals ≤ 1.5× r75's 77/min
(this estimator). O5: sign(dob)=sign(u) >60 %, p90 <0.15, 0.2–1 Hz share <40 %. Revert (`_r5_REVERT_to_r4`): any felt
oscillation, one-sided pull at rest, |dob| pinned at 0.3 >2 s, des→act resonance >1.5 at 0.5–1.5 Hz. If O2/O3 pass and O4
fails → `AccordDobHz 0.4` / `SteerKP 0.85` by config.

## 7. Files

Kit: `rlog-tools/studies/grind/` — `v293r5_loopshape.py`, `v293r5_design.py`, `v293r5_design_lowspeed.py`,
`v293r5_design_pred.py`, `v293r5_design_dobb.py`, `v293r5_design_jerk.py`, `v293r5_design_ship.py` (+ their
`V293-REV5-*-2026-09-15.txt`), `v293r5_read.py` (+ `V293-REV5-READ-r75-r72-r73-2026-09-15.txt`), `v293r5_observer_read.py`
(+ baseline txt), `v293r5_pagedata.py`, `v293r5_page_build.py`, `v293r2_simlib.py` (DOB + predictor options),
`v293_flight_read.py` (observer fields, r5 commit gate), `_scratch/hardturn_spec.py`, `_scratch/observer_xcheck.py`.
`tools/make_galaxy_toggle_config.py` (TORQUE_MODE_R5 + revert); `analysis-2020accord/reference/toggle-config_V293_torque_mode_r5*.json`;
`docs/artifacts/V293-REV5-PAGE-2026-09-15.html`. Rlogs: `analysis-2020accord/rlogs/…00000075--6c8687d5bd--{0..14}`, `…00000074--2bf17ca67d--{0,1}`.

## 8. Standing rules re-learned

Attribute before analysing (the counter collision cost a full read). The device's boot-time mtimes are the unsynced clock.
Every new term gets its own graph (Q, Re Q, the damping budget, the traces, the LERPs are on the page). Agents stopped
before close-out: `fetch-rlogs-1`, `friction-writer-hunt` (roll-call probe empty).
