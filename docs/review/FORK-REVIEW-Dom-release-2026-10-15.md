# Independent adversarial review: `Dom-release` (HEAD c4ceeca314) vs `upstream/StarPilot` (823a5d5674), 2026-10-15

Reviewer: general-purpose subagent. Read-only on git. Nothing sent, flashed or committed.
Scripts (all under 10 s, in the session scratchpad): `rv_sim.py` `rv_pack.py` `rv_fw.py` `rv_map.py` `rv_sens*.py` `rv_raw0.py`.

Method note: the fork's `cereal` aborts on import on this Windows host (fatal error at `cereal/__init__.py:9`), so `opendbc` cannot be imported.
I loaded the real `lateral.py`, `vehicle_model.py`, `can/packer.py`, `can/dbc.py`, and the real function source from `values.py` and `hondacan.py` by file, with the cereal-dependent imports stubbed.

## Verdict per item

| # | Item | Verdict |
|---|---|---|
| 1 | Limiter semantics, call order, state, simulation | PASS (observation D2) |
| 2 | DBC ARM signal, packed frame, checksum, torque-mode identity | PASS |
| 3 | Firmware-family detection and the fw query | PASS_WITH_DEFECTS (D1) |
| 4 | Sensor-status fault | PASS (D6 minor) |
| 5 | Idle hold vs panda predicate | PASS (premise in the brief not supported, D4) |
| 6 | `turn_lead_allowed` and `lateralControlMode` | PASS_WITH_DEFECTS (D5 scope) |
| 7 | Variable-ratio map and own-ratio fixed point | PASS (D3 observation) |
| 8 | Tests | NOT RUN on this host (D7); coverage gaps listed |

## Item 1: limiter (EVIDENCE: read `lateral.py`, executed it)
- Signature is `(apply_angle, apply_angle_last, v_ego_raw, steering_angle, lat_active, limits, VM)`. The Honda call passes `(CC.actuators.steeringAngleDeg, angle_last, vEgoRaw, steering_angle, latActive, p, self.VM)`. Positions are correct. `p` supplies `ANGLE_LIMITS` and `STEER_STEP` (class attributes, `STEER_STEP = 1`, so 0.01 s).
- Order inside the function: `v = max(v, 1)`; jerk-limited delta, then `min()` with `MAX_ANGLE_RATE` (2.5 deg/frame); `rate_limit` around `apply_angle_last`; lateral-accel clip; **if not lat_active the result is the measured angle** (this seeds the limiter); final clip to `STEER_ANGLE_MAX` 400.
- `_update_angle` stores the function's own output in `apply_angle_last`. The error clip acts on a local copy only. Confirmed by reading. The first frame seeds from the measured angle.
- Simulation: the real `apply_steer_angle_limits_vm`, an Accord vehicle model, a 90 deg step and a 2 s ramp. Plant is a first-order lag of 0.25 s with a 3 deg Coulomb stick and a setpoint quantised to 0.1 deg.

| speed | command | release reversals | Dom (clip stored) reversals |
|---|---|---|---|
| 3 and 10 m/s | step or ramp, clean sensor | 0 | 0 (identical trajectories) |
| 3 m/s | step, 0.25 deg sensor noise, 6 deg stick | 20 (10 backward steps) | 20 |
| 3 m/s | ramp, noise | 12 | 12 |
| 10 m/s | step, noise | 10 | 12 |
| 10 m/s | ramp, noise | 0 | 0 |

- With a clean sensor the sent setpoint never reverses while the command is monotone, in both variants.
- With sensor noise the reversals come from the error clip itself (sent = measured +/- error_max while the clip binds). Both variants share that path.
- EVIDENCE for the simulation. BELIEF that the real wheel behaves like this plant.
- Not storing the clipped value gives no benefit while the clip binds. It gives a small one (10 vs 12) after release.
- The jerk cap bites above about 8 m/s: max step 1.02 deg/frame at 10 m/s, 2.5 at 3 m/s.

## Item 2: DBC and frame (EVIDENCE: executed the repo's pure-Python packer on the real DBC, plus a hand-packed Dom frame)
- `STEER_CONTROL_ARM : 19|2@0+` in message 228 (`STEERING_CONTROL`). That message is **5 bytes, not 8**, matching the panda TX table entry `{0xE4, 0, 5}`.
- Big-endian bits 19 and 18 are byte 2 bits 3:2. No overlap with DRIVER_OVERRIDE (17), REQUEST (23) or CONTROL_STATE (26..24). Parsed signal: msb 19, lsb 18, size 2.
- The Accord's pt DBC is `honda_civic_hatchback_ex_2017_can_generated` (see HONDA_ACCORD in `values.py`), and it carries the signal.
- 9 raw values x request 0 and 1 gives 18 frames. In every one `(b2 >> 2) & 3 == 2`, and every frame is byte-identical to Dom's hand-packed frame (0 differences). Example raw=-1234 req=1: `fb 2e 88 00 1b`.
- Checksum recomputed independently (Honda nibble sum, last byte high nibble only) matches every frame. It covers the ARM bits because the packer signs after all values are set. The counter steps 0,1,2,3,0,1.
- Torque-mode frames (no `angle_arm`): 4684 combinations of torque (-4096..4096 step 7), request and tja are byte-identical to upstream's DBC output.
- On the real wire (routes 9c, 9d, 79; bus 1 TX, src 129): ARM = 2 on every frame read. The camera's own frames (src 128 and 2) carry ARM 0.

## Item 3: fw detection (EVIDENCE: executed the function source, read the query config, read carFw from rlogs)
- 18 cases. A160 False. A16A, A16B, A16C, A16Z True. `A16B` plus NUL padding True. A bytearray True. Stock `39990-TVA-A160` False. `TVA-A16B` with a dash False. Lowercase `A16b` False. Short, long, embedded NUL, empty, `A170`, `A26B`, non-ASCII and leading NUL all False.
- The Honda eps query is `StdQueries.UDS_VERSION_REQUEST`, read-by-identifier 0xF181 (`APPLICATION_SOFTWARE_IDENTIFICATION`), bus 1. `fw.ecu == "eps"` is the same pre-existing comparison the `eps_modified` line uses just above, so it is the right form.
- Real cars, from carParams in rlogs: `39990-TVA,A16B` plus two NULs on routes 9c and 9d (V299), `A16A` on route 79 (V298), `A160` on route a6. The second eps entry `\x11L-130520-...` is the logging-only alternate query and does not match.
- Image note: the V298 and V299 plain images hold `39990-TVA,A16x` at 0x13100 and a second `39990-TVA,A160` at 0x14137 (V300 holds `TVA-A160` with a dash there). The wire shows the query returns the first. EVIDENCE: wire.
- `CarParamsCache` is `CLEAR_ON_MANAGER_START`, so a reboot after flashing re-queries.
- D1: nothing guards "angle firmware present, not detected".

## Item 4: sensor status (EVIDENCE: DBC and decoded rlogs)
- The Accord's DBC has `STEER_SENSOR_STATUS_1..3` in `STEERING_SENSORS` (0x14A, 8 bytes) at bits 34, 33, 32, which is byte 4 bits 2:0.
- Decoded byte 4 & 7 on 0x14A (bus 1) reads **7 (all three bits 1) on every frame**. Segments read: 9c seg 0, 2, 3, 7, 14; 9d seg 6, 13 (V299); 79 seg 0, 1 (V298); the route 71 cache (torque V294). That is about 70 000 frames, no exceptions, including drive start. The fault will not fire permanently.
- The assignment sits after the stock steer-status block and is not overwritten later.
- Before the first 0x14A frame `cp.vl` reads 0, so there is one transient `steerFaultTemporary` at start (alert level).

## Item 5: idle hold vs panda `honda.h` (EVIDENCE: read the C)
- The panda blocks 0xE4 when `!(aol_allowed || controls_allowed)` and `data[0] | data[1] != 0`. `aol_allowed = (acc_main_on || lkas_on) && ALWAYS_ON_LATERAL`. `controls_allowed` drops when ACC main goes off or the PCM leaves cruise.
- The fork sends nonzero (idle hold or setpoint) only when `cruiseState.available && (enabled || aol)`, else raw 0. Raw 0 always passes the predicate.
- I found no case where the fork sends a nonzero field the panda blocks, apart from the few-millisecond lag between the PCM message and `CC.enabled`. That class exists in torque mode too.
- `alternativeExperience` is read at call time from the same CP object that card.py trims, so it matches what the panda was given.
- D4, premise not supported: the brief says the firmware treats raw 0 with request on as a fault sentinel. Design doc `DESIGN-ANGLE-LOOP-C2-rev2-A` row H-fork-0 says raw 0 with request 1 is a valid command to 0 deg. The sentinel is `0x7FFF` after the 510 ms timeout, and request other than 1 skips the PID.
- Wire: on flown V299 routes 2.4 % of request=1 frames carry raw 0 (143 of 5973, 107 of 4919, 157 of 5974; runs up to 39 frames). Same rule as Dom, no fault noted. I did not check the 0x1AB DTC for those frames.
- BELIEF on the firmware reading. EVIDENCE on the frequency.

## Item 6: lateral mode (EVIDENCE: grep of every `*.py`, `*.capnp`, `*.cc`, `*.h`)
- The field exists: `car.capnp` `Actuators.lateralControlMode @9`. card.py publishes the whole `last_actuators_output` as `carOutput.actuatorsOutput`.
- Readers: `controlsd.py` (turn lead, using the previous cycle's carOutput) and `rivian_lateral_mode.py` (UI, gated on brand rivian). Only Rivian and now Honda write `angle`. Honda torque mode leaves it at the default, unchanged.
- D5: `turn_lead_allowed(brand, mode)` is now brand-agnostic and the `brand` argument is unused. Its test changed from `ford` to `honda`.

## Item 7: variable-ratio map (EVIDENCE: executed the real functions)
- The contraction factor at the fixed point is the map's elasticity theta*m'/m. Worst absolute value is 0.442, left of the 303 deg knot. Others are 0.31 or less. A positive 0.29 band sits at 227 to 236 deg. All are below 1, which matches the docstring's 0.44.
- Sweep of 25 measured-ratio values x 2801 desired angles (+-700 deg) plus edge values, 10 passes: worst residual against the converged fixed point is 0.0085 deg (at -379.5 deg, all 10 passes used), under the 0.01 deg tolerance.
- At 0 deg the map gives 16.84 and the result is 0.0. Above 380 the ratio is flat at about 12.3 and the fixed point is reached in one pass. The setpoint is monotone in the desired angle (min step 0.05). A desired 380 gives 295.4. A desired 700 gives 510, which the 400 deg limiter then clips.
- controlsd: the angle branch sits before the `accord_ratio_is_explicit` branch, so the `SteerRatio` toggle and `lp.steerRatio` cannot override it. `update_params` appears once in controlsd. EVIDENCE: grep.
- D3: the carcontroller's own `VehicleModel` still uses `CP.steerRatio` 16.33, while the served ratio is 16.84 at centre and falls to 12.3 at 380 deg. The jerk and lateral-accel caps use 16.33.

## Item 8: tests
- Not run. `pytest` lacks xdist for the repo's `-n` addopts. With `-o addopts=""` the import dies in `cereal/__init__.py` on this host. WSL Ubuntu-24.04 exists but has no pytest or capnp. I re-ran the logic of the relevant cases by file extraction (items 1, 2, 3, 7).
- The honda test file covers: fw detection, selection, frame arm and checksum, rate limit then clip, wheel motion not feeding the limiter, first-frame seed, idle hold, raw clip.
- Not covered:
  - map contraction, 0 deg and above 380 deg;
  - the DBC bit position against a hand-computed byte;
  - the carstate sensor fault, with no test and no wire check;
  - panda predicate parity;
  - `lateralControlMode` reaching carOutput;
  - the controlsd ratio override beating `SteerRatio`;
  - the detection-failure path;
  - the real F181 string including NUL padding.

## Defects, ranked

1. **D1 (Medium) No guard for an undetected angle firmware.** Dom had `EPS_ANGLE_LOOP_FW_MISSING` and a permanent fault. The release has neither. If the EPS fwVersion is not read as `A16x` (query failure, a letter outside A..Z, eps missing), the car runs torque mode into the angle EPS. That lane ignores torque frames, so openpilot engages with no steering and no alert. EVIDENCE: code diff. BELIEF on the on-car consequence, taken from Dom's comment. Fix idea: refuse to engage, or raise a fault, when an eps string contains `TVA,A16`.
2. **D2 (Low) The error clip passes sensor noise into the setpoint.** While the clip binds, sent = measured +/- error_max in both variants, so the stored-state change does not remove that path. Simulation only.
3. **D3 (Low) Cap geometry uses 16.33 while the map serves 16.84 down to 12.3.** The caps are off by 3 % at centre and up to 25 % at large angle. The 2.5 deg/frame rate cap dominates below about 8 m/s.
4. **D4 (Low, documentation) The code comment says the firmware treats a 0 setpoint as a fault sentinel.** The design docs and the wire do not support it. The code is harmless: the idle hold is nonzero only when the panda allows it.
5. **D5 (Low, scope) Changes that reach other cars.** `turn_lead_allowed` has an unused `brand`. The lane-change turn latch (1.5 m/s^2) applies to every brand whenever lane-change pace is under 10. `lagd` drops a saved lag on any steer-control-type change. None touches the Accord angle path.
6. **D6 (Info) One transient sensor fault before the first 0x14A frame.**
7. **D7 (Info) Tests could not be executed on this host.**

I found nothing that should block flashing the Accord path on this evidence. D1 is the one worth fixing before a release build that others will drive.

## Addendum: re-check at HEAD b818ebc7b0 (5 commits)
- EVIDENCE: `git diff 696ea28c22 Dom-release` (the tip I reviewed) changes only the honda test file (+11 lines). The carcontroller, values, hondacan, carstate, interface, DBC, controlsd and latcontrol_angle code I reviewed is byte-identical to the new HEAD, so every verdict above stands.
- New test `test_wheel_moving_under_a_held_setpoint...` was inserted in the middle of the previous test. The rate-limit-step check that belonged to `test_wheel_motion_does_not_feed_the_limiter_state` is now an orphan tail of the new test, and its comment still says 1.2 deg/frame while the limit is 2.5. It still runs and passes by reading, but it is mislabelled. Severity: info (D8).
- controlsd diff vs the pre-split tip: comment text only.
