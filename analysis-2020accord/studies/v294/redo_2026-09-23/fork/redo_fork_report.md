# Independent redo: StarPilot fork side of V294 (Dom `54ff1ea39`)

Subagent `redo-fork`, 2026-09-23. Scope: the fork commit and the two V294 toggle configs. It does not cover how the
V294 plant behaves; that belongs to the physics pass.
Method: every code claim was checked against a `git archive` extract of the relevant commit. The operator's clone was
not modified and no branch was checked out. The fork's real `LatControlTorque` was imported and run on Windows with
three stubs: `setproctitle`, the tici hardware layer and `locationd.helpers.Pose`. Missing pure-Python dependencies went
into a scratch `pylibs/` folder, not the conda environment.
Scripts and outputs are in `scratchpad/redo_fork/`: `decode_all.py`, `leftover.py`, `wiring.py`, `run_ctrl.py`,
`compare.py`, `run_tests.py`, `boot.py`, `decoded_all.json`, `wiring.json`, `fails_fork_*.txt` and `*.npz`.

## Verdict

**The r1 config and the commit are safe to deploy for what they claim, with two conditions.**
EVIDENCE: with r1, the Accord controller at HEAD produces output that is bit-identical to three references:
- the generic torque path for the same car;
- the pre-V293 fork `a357cd2b5` with the same toggles;
- HEAD with empty toggles, which exercises the getattr fallbacks.

This held on two scenarios of 12,000 frames each, covering 4 speeds with engage, override and safety-limited frames.

Conditions:
1. **Import r1 while parked, then start a fresh drive.** The Galaxy restore endpoint does not block these keys while
   onroad. Switching AccordRatePlantFF from true to false while engaged changes the control law in one frame.
   BELIEF on the size: the two laws differ by up to 0.42–0.46 torque at 12–27 m/s in my synthetic scenario.
2. **Run Rebuild Params after pulling `54ff1ea39`.** Without it, the REVERT file cannot restore `AccordJerkLpHz 4.0`
   (details under check 3). r1 does not need the rebuild.

The claim "every torque-mode term reverted to stock by default" is **true for every term in the controller** and
**false for `LaneChangeTurnGate`** (rev 6.2). That toggle defaults ON in the code, r1 does not set it, and it acts on
every car.

## Per-check results

| # | Check | Result |
|---|---|---|
| 1 | Every torque-mode-era change gated, with a stock default | **PASS** for all latcontrol terms, bit-exact. **FAIL, narrow**: `LaneChangeTurnGate` defaults ON and is not reverted. |
| 2 | Wiring from `params_keys.h` through the variables, controller, layout, safe mode and tests | **PASS**. No unread key, no mismatch between fallback and default, no type mismatch. |
| 3 | Decoded values, rev-6 leftovers, REVERT exactness | **PASS** on values. The leftover list is below. The REVERT file is **exact only after Rebuild Params**. |
| 4 | Stock-sync back-fill trap, Honda limits | **PASS**. 0.011 and 14.0 cannot be back-filled under either the old or the new sync logic. |
| 5 | Compile, lint, tests | **FAIL**: `54ff1ea39` breaks 5 of the fork's own Accord tests. Everything else passes or could not run here. |
| 6 | Offline controller run | **PASS**. r1 runs the plain torque path. REVERT runs every rev-6.4 term and is bit-identical to rev-6.4 code. |

## 1. Every torque-mode-era change, `a357cd2b5..54ff1ea39`

The base is `a357cd2b5`, the commit just before `4247cb09e`. Chain: 4247cb09e, 9622aee9f, 8c4051ce6, 66cf4454a,
e8e62f0e1, f4e314da6, 08a5a7064, e44b6cd31, afbe5fb44, b97169c65, d6f7bdd02, 91e902a86, 84766cdc5, 54ff1ea39.
EVIDENCE: the full diff was read. The FAIL criterion, fixed before reading, was any non-stock behaviour that reaches the
controller or controlsd under default toggles.

| Change | Commit | Gate and default at HEAD | Stock by default? |
|---|---|---|---|
| EPS plant G/K tables replaced by V293 values: G [120,95,85,70] became [550,271,246,167]; K [.17,.28,.35,.45,.50] became [.30,1.00,2.30,2.77,3.91] | 9622aee9f, 8c4051ce6, 66cf4454a | Read only inside the AccordRatePlantFF branch, default off | YES. But with plant FF on it is **not** V282's feedforward (defect D6). |
| Hold map; 28 m/s hold knot ×1.2 | e8e62f0e1, f4e314da6 | AccordHoldMap off, inside the plant-FF branch | YES |
| Static-friction hysteresis FF; SteerFriction relay muted while hyst > 0 | e8e62f0e1, f4e314da6 | AccordFrictionHyst 0.0. The function returns 0 when friction is 0, and the relay is only muted when hyst > 0. | YES |
| 100 Hz rate loop; RATE_LOOP_RC changed from 0.03 to 0.01 | e8e62f0e1, e44b6cd31 | AccordRateLoopGain 0.0 inside the plant-FF branch. The filter still runs but is multiplied by 0. | YES |
| Error notch | e8e62f0e1 | AccordErrorNotchQ 0.0 gives an exact pass-through | YES (spy: 0 of 11,600 frames filtered) |
| Reference filter | e8e62f0e1 | AccordRefFilter 0.0 gives a pass-through and re-primes the filter state | YES |
| Speed-scheduled Ki | f4e314da6 | AccordTorqueKiHigh 0.0 gives a flat Ki | YES (Ki = 0.3 on every frame) |
| `_sync_stock_param` treats an explicit 0.0 as a user value | f4e314da6, 08a5a7064 | **UNGATED, all cars**, all 11 synced params | Not a control term. It protects user values. r1 is unaffected. |
| Disturbance observer | e44b6cd31 | AccordDobHz 0.0 inside the plant-FF branch | YES |
| cereal `accordObserverTorque/Frozen` @8/@9 | e44b6cd31 | Logging only; values are 0/false | no behaviour |
| Hold level 1.15/1.45 | afbe5fb44, 84766cdc5 | AccordHoldLevel off, inside the plant-FF branch | YES |
| Jerk low-pass 4.0 Hz on the Accord | afbe5fb44, then gated in 54ff1ea39 | AccordJerkLpHz 1.2 | YES. Alpha 0.070111910197984 is bit-equal to the constructor's value. |
| Friction-hysteresis band schedule | b97169c65 | AccordFrictionHystBand off | YES |
| **Lane-change turn gate** in controlsd | d6f7bdd02 | **LaneChangeTurnGate defaults "1" (stock value "0")**, `get_value(default=True)`. Acts on every car with LaneChanges. | **NO** |
| 14 Hz dither | 91e902a86 | AccordDither 0.0 returns exactly 0.0. AccordDitherGate defaults "1" but has no effect at amplitude 0. | YES (spy: 11,484 calls, 0 non-zero) |
| AccordRatePlantFF default changed from true to false | 54ff1ea39 | param, variables and getattr fallback all false | YES |
| Variable steer-ratio map refit; NOMINAL 16.89 → 16.88, each bin moved ≤0.024 | 4247cb09e | AccordVariableSteerRatio, a pre-V293 toggle defaulting on | Ungated with respect to V294. Not torque mode: it is a steer-ratio measurement from V282 routes. |
| Missing `import math` in a test; macOS frpc binaries removed | 4247cb09e | — | no car behaviour |
| Galaxy layout entries, safe-mode keys, tests | all | — | UI and tests only |

Name-based reader census at HEAD, excluding tests (EVIDENCE, `git grep`):
- Accord params are read by name only in `params_keys.h`, `safe_mode.py` and `starpilot_variables.py`.
- The toggle attributes are consumed only by `latcontrol_torque.py`, the functions in `latcontrol_vehicle_tunes.py`, and
  `controlsd.py` (`keep_learned_lat_accel_offset` and `lane_change_turn_gate`).

## 2. Param wiring, HEAD

EVIDENCE: `wiring.py` parsed the HEAD files and produced `redo_fork/wiring.json`.
- Every float default in `params_keys.h` matches the `get_value` default and the controller's getattr fallback.
- Bools are written by the Galaxy as "1"/"0" (`PYTHON_2_CPP`). They are read back through `get_bool` (== "1") and then
  `bool(getattr(...))`. That round trip is consistent.

| key | r1 | REVERT | params_keys (type/default/stock) | toggle attribute (cast, default, clamp) | latcontrol fallback | layout | safe mode |
|---|---|---|---|---|---|---|---|
| AccordRatePlantFF | false | true | BOOL/0/0 | accord_rate_plant_ff (bool, False) | False | bool | yes |
| AccordTorqueKi | 0.3 | 0.3 | FLOAT/0.30/0.15 | accord_torque_ki (float, 0.30, [0.05,1]) | HONDA_ACCORD_TORQUE_KI=0.30 | [0.05,1] | yes |
| AccordTurnFFTaper | false | false | BOOL/0/0 | accord_turn_ff_taper (False) | False | bool | yes |
| AccordFFRateGain | 0.5 | 0.5 | FLOAT/0.5/0.5 | (0.5, [0,1.5]) | 0.5 | [0,1.5] | yes |
| AccordEpsGainScale / SpringScale | 1.0 / 1.0 | 1.0 / 1.0 | FLOAT/1.0/1.0 | ([0.5,2] / [0,2]) | 1.0 | yes | yes |
| AccordHoldMap | false | true | BOOL/0/0 | (False) | False | bool | yes |
| AccordFrictionHyst | 0.0 | 0.015 | FLOAT/0.0/0.0 | ([0,0.05]) | 0.0 | [0,0.05] | yes |
| AccordRateLoopGain | 0.0 | 0.001 | FLOAT/0.0/0.0 | ([0,0.003]) | 0.0 | [0,0.003] | yes |
| AccordErrorNotchQ | 0.0 | 1.0 | FLOAT/0.0/0.0 | ([0,4]) | 0.0 | [0,4] | yes |
| AccordRefFilter | 0.0 | 0.06 | FLOAT/0.0/0.0 | ([0,0.5]) | 0.0 | [0,0.5] | yes |
| AccordTorqueKiHigh | 0.0 | 0.0 | FLOAT/0.0/0.0 | ([0,6]) | 0.0 | [0,6] | yes |
| AccordDobHz | 0.0 | 0.6 | FLOAT/0.0/0.0 | ([0,3]) | 0.0 | [0,3] | yes |
| AccordHoldLevel | false | true | BOOL/0/0 | (bool, False) | False | bool | yes |
| AccordFrictionHystBand | false | true | BOOL/0/0 | (bool, False) | False | bool | yes |
| AccordDither | 0.0 | 0.0 | FLOAT/0.0/0.0 | ([0,0.02]) | 0.0 | [0,0.02] | yes |
| AccordDitherGate | true | true | BOOL/1/0 | (bool, True) | True | bool | yes |
| AccordJerkLpHz | 1.2 | 4.0 | FLOAT/1.2/1.2 | (1.2, [0.5,8]), guarded by `known()` | LP_FILTER_CUTOFF_HZ=1.2 | [0.5,8] | yes |
| SteerKP | 0.9 | 1.0 | FLOAT/0.0/0.0 | steerKp (clamp [0.05, 0.6×5=3.0]); controlsd writes `pid._k_p` every frame | — | float | yes |
| SteerLatAccel | 14.0 | 14.0 | FLOAT/0.0/0.0 | latAccelFactor (clamp [0.845, 16.89], stock LAF 1.6893) | — | float | yes |
| SteerFriction | 0.011 | 0.0 | FLOAT/0.0/0.0 | friction ([0,1]); a torque-space relay (`get_friction` uses friction×LAF, then /LAF) | — | [0,1] | yes |
| ForceAutoTuneOff / ForceAutoTune / AdvancedLateralTune | T / F / T | T / F / T | BOOL | force_auto_tune_off makes `use_custom_*` true | — | bool | yes |
| KeepLearnedLatAccelOffset | true | false | BOOL/1/0 | (True); read by controlsd | — | bool | yes |
| LaneCentering | true | true | BOOL/0/0 | lane_centering | — | bool | yes |
| SteerDelay / UseAutoSteerDelay / LaneChangeSmoothing / LaneChangeTurnGate | not set | 0.2 / T / 4 / T | FLOAT / BOOL / INT / BOOL(1/0) | — | — | yes | LaneChangeSmoothing is not in safe mode |

**Deployment trap (EVIDENCE).** The fork ships `common/params_pyx.so` prebuilt. Its last commit is `d0585de42`
(2026-09-11), and it contains **none** of the Accord keys, `KeepLearnedLatAccelOffset`, `LaneChangeTurnGate` or
`AccordJerkLpHz`. A `grep -a` count is 0 for each, against 1 for `SteerKP`.
- The device runs its own on-device rebuild. The handoffs show `git pull --ff-only` followed by `rebuild_params` for
  every rev.
- Until the next rebuild, `AccordJerkLpHz` is unknown on the device. The restore skips it, because it is not in
  `_get_toggle_backup_keys()`, and `get_value` falls back to 1.2.
- r1 is immune: every Accord value in r1 equals its `get_value` default, and HEAD with r1 is bit-identical to HEAD with
  empty toggles.

## 3. Decoded configs, leftovers, REVERT

**Codec (EVIDENCE).** `decode_parameters`, `encode_parameters`, `xor_encrypt_decrypt` and `XOR_KEY` were extracted
verbatim from `starpilot/system/the_galaxy/utilities.py` at `54ff1ea39` and executed.
- All 22 wrapper files in `reference/` decode, and each re-encodes **byte-identically** to its `data` field.
- For every file, the readable `.decoded.json` equals the decoded content, including value types.
- The restore endpoint was mirrored (`_get_toggle_backup_keys` plus `_coerce_toggle_restore_value` against HEAD
  `params_keys.h`). All 26 r1 keys and all 30 REVERT keys are accepted, subject to the compiled library as above.

**r1 decoded:** format `starpilot-toggle-backup` v1, 26 settings.
- AccordRatePlantFF false, SteerKP 0.9, AccordTorqueKi 0.3, SteerFriction 0.011, SteerLatAccel 14.0.
- ForceAutoTuneOff true, ForceAutoTune false, AdvancedLateralTune true, KeepLearnedLatAccelOffset true, AccordTurnFFTaper false.
- AccordHoldMap false, AccordFrictionHyst 0.0, AccordRateLoopGain 0.0, AccordErrorNotchQ 0.0, AccordRefFilter 0.0.
- AccordTorqueKiHigh 0.0, AccordDobHz 0.0, AccordHoldLevel false, AccordFrictionHystBand false.
- AccordDither 0.0, AccordDitherGate true, AccordJerkLpHz 1.2.
- AccordFFRateGain 0.5, AccordEpsGainScale 1.0, AccordEpsSpringScale 1.0, LaneCentering true.

Every value matches the stated intent. EVIDENCE: the V282 reference routes' own initData in `WIRE-PARAMS.txt`
(r64 and r65 on `0f98d8c75`, r6c on `57410c3b4`) shows:
- SteerKP 0.9, AccordTorqueKi 0.3, KeepLearnedLatAccelOffset 1, AccordTurnFFTaper 0, ForceAutoTuneOff 1;
- LAF 6.0 and friction 0.01, which r1 deliberately changes to 14.0 and 0.011.

`memory/project-operator-starpilot-toggles-decoded-2026-09-03.md` records the state before the V282 tune (SteerKP 0.6,
ForceAutoTune on). It is stale as a "V282-era" reference. r1 correctly follows the later V282 routes instead.

**REVERT decoded:** the rev-6.4 as-flown ARM-A config (29 keys) plus `AccordJerkLpHz 4.0`. There are no other changes
and every value type is identical.

**Params rev 6.x set that r1 does not set.** These keep the device's rev-6.4 values. The comparison uses the union of
every V293-era config in the kit, 29 keys.

| key | device now (rev 6.4) | V282 reference routes (wire) | pre-V293 backup 09-10 | consequence |
|---|---|---|---|---|
| **UseAutoSteerDelay** | **true** | **0** (r64/r65/r6c) | false | The lateral delay is learned, not pinned at 0.2. This is the operator's own V293 choice (record: rev 3/4 handoff). It is **not** V282-era, and r1's docstring ("Nothing else moves") does not say so. |
| SteerDelay | 0.2 | 0.2 | 0.2 | Has no effect while UseAutoSteerDelay is true |
| LaneChangeSmoothing | 4 | — | 4 | Same as before V293 |
| **LaneChangeTurnGate** | **true** | did not exist | did not exist | The rev-6.2 behaviour stays live, and the code default is also ON |

Other V293-era state that no kit config records (for example SteerRatio: 16.33/16.84 on the V282 routes, 16.88 during
V293) cannot be seen from the kit. BELIEF: read the first V294 route's initData to confirm what flew.

**REVERT exactness.**
- EVIDENCE: HEAD with REVERT is **bit-identical** to the rev-6.4 code `84766cdc5` with the as-flown config, on both scenarios.
- EVIDENCE: without the `AccordJerkLpHz` key reaching the toggle (library not rebuilt), the command differs from rev 6.4
  by max |Δout| 0.39 at 4.5 m/s and 0.06–0.10 at 12–27 m/s (RMS 0.01–0.07).
- The ARM-A file was cross-checked against the wire on only 20 of its 29 keys (`make_ab_config.py` LOGGED). SteerKP,
  SteerFriction, SteerDelay, UseAutoSteerDelay, LaneChangeSmoothing and KeepLearnedLatAccelOffset were not checked.
  BELIEF.

## 4. Back-fill trap and Honda limits

EVIDENCE, code reading:
- `_sync_stock_param` back-fills a param only when it is unset or still tracking a recorded stock value.
  - SteerFriction 0.011 is not the recorded stock value (0.2120497) and is not 0.
  - SteerLatAccel 14.0 is not the recorded stock value (1.6893).
  - Neither can be replaced under the new logic, or under the pre-09-14 logic, which also back-filled any value of 0.
- `_migrate_steer_delay_mode` is one-shot and already flagged on the device (`SteerDelayModeMigrated 1` on the wire).
- Clamps: LAF [0.845, 16.89] admits 14.0 and Kp [0.05, 3.0] admits 0.9.
- Honda: STEER_MAX 4096 on a linear lookup (torqueBP/V [0,4096]). STEER_DELTA_UP/DOWN of 3 per second, times DT,
  gives 0.03 per frame (123 counts). The panda Honda safety checks only that controls are allowed for 0xE4.
- BELIEF: with LAF 14 the feedforward for a 3 m/s² demand is about 0.21 (≈880 counts), far below the rail. Saturation
  or the rate cap can bind only through the low-speed-factor-inflated P term.
  - Synthetic run: max |out| 0.83 at 4.5 m/s and 0.27–0.33 at speed.
  - No frame at ±1.
  - Frames above 0.03 per frame: 1.8 % at 4.5 m/s and ≤0.43 % at speed, mostly at engage and override edges.
- Out of scope, BELIEF: whether the ×6 map plus the trim saturates inside the EPS.

## 5. Compile, lint, tests (HEAD extract)

- `py_compile` OK: latcontrol_torque, latcontrol_vehicle_tunes, starpilot_variables, safe_mode, controlsd. The layout
  test parses as AST and the layout JSON parses.
- `pyflakes` has no findings on the changed files beyond the existing star-import notes (246 at HEAD against 247 at the
  parent; the difference is the now-unused `HONDA_ACCORD_JERK_LP_HZ`).
- `test_device_settings_layout.py`: **25/25 pass**. `test_safe_mode.py`: **13/13 pass**.
- `test_latcontrol.py` has 19 failures at HEAD against 14 at the parent `84766cdc5`. The 14 shared failures are Windows
  environment errors (UnicodeDecodeError on Hyundai, Kia and Tucson paths).
- **5 tests fail only at HEAD.** The parent passes all 25 Accord tests (positive control):

```
test_honda_accord_torque_controller_uses_rate_plant_feedforward   f 0.960 vs expected 0.921±0.01
test_honda_accord_rate_plant_feedforward_keeps_learned_lat_accel_offset   0.0500 vs 0.0417±0.001
test_honda_accord_rate_loop_damps_the_measured_wheel_rate         0.0 vs -0.0096±0.001
test_honda_accord_disturbance_observer_reaches_the_feedforward    abs(0.0) > 0.01 false
test_honda_accord_friction_relay_is_off_under_the_hysteresis_feedforward   -0.4504 vs -0.2384±1e-9
```

- Cause (EVIDENCE): `_build_torque_controller` passes an empty `SimpleNamespace`. These tests relied on the getattr
  fallbacks that `54ff1ea39` changed to off (plant FF, hysteresis, rate loop). The failures are wrong test expectations,
  not a controller defect.
- The commit says "run [pytest] on the comma before deploying". That run will show these 5 failures.
- `test_starpilot_variables.py` and `test_lane_change_turn_gate.py` were **not run**. The error was
  `ModuleNotFoundError: No module named 'msgq'` (native IPC, not available on Windows).

## 6. Offline controller (real `LatControlTorque`, HONDA_ACCORD, controlsd-style Kp/LAF/friction injection)

Spy counts over 11,600 active frames: calls and non-zero results.

| run | plant FF | hysteresis | rate loop | observer | notch filtering | dither non-zero | jerk α | Ki |
|---|---|---|---|---|---|---|---|---|
| HEAD + r1 | 0 | 0 | 0 | 0 | 0 of 11,600 | 0 of 11,484 | 0.0701119 (1.2 Hz) | 0.3 flat |
| HEAD + REVERT | 11,600 | 11,600 | 11,600 | 11,600 non-zero | 11,600 | 0 | 0.2008486 (4.0 Hz) | 0.3 |

The r1 path is also bit-identical to the pre-V293 base and to the generic path (see the verdict). This was confirmed a
second time on a randomised scenario (random-walk demand, roll −0.02, lat_delay 0.25).

## Defects (reported, not fixed)

- **D1:** `54ff1ea39` breaks 5 fork tests. Their expectations assume the old fallbacks and need explicit toggles.
- **D2:** The kit record `studies/v294/fork_revert_patch.py` does **not** reproduce `54ff1ea39` (EVIDENCE: replayed on
  the parent's files, then diffed). params_keys, variables and layout come out identical. The replay misses:
  - the 8 getattr fallback flips in latcontrol_torque;
  - the safe_mode `AccordJerkLpHz` key;
  - the layout-test edits.
- **D3:** No deploy note says that Rebuild Params is needed after this pull. The REVERT file silently loses
  `AccordJerkLpHz 4.0` without it.
- **D4:** `LaneChangeTurnGate` is not reverted: the default is ON, it acts on every car, and r1 does not set it. It also
  lacks the `known()` guard that the Accord keys have. That gap dates from rev 6.2: on a library without the key,
  `get_bool` raises UnknownKeyName.
- **D5:** r1 leaves UseAutoSteerDelay true, but the V282 reference routes flew with 0 and 0.2. This is the operator's
  call. It should be stated rather than implied as "V282-era".
- **D6:** `toggle-config_V282_rate_servo_REVERT.json` is stale. It turns plant FF on, and plant FF now runs the V293
  G/K tables. The hold per degree at 12.5 m/s is 2.3× V282's (0.0085 against 0.0037), and the move term is 0.35×. This
  dates from 9622aee9f and matters only if the car goes back to a V282-class image.
- **D7:** The Galaxy restore allows these keys while onroad. The operational rule is to import while parked.
