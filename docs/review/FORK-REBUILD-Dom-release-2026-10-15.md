# FORK REBUILD — `Dom-release` = upstream + 5 curated commits, 2026-10-15

Subagent `fork-rebuild` (task 3 + 2b). Spec: `FORK-UPSTREAM-DELTA-2026-10-15.md`. Fork repo
`openpilots/raayyymond-StarPilot/StarPilot`. **Nothing pushed, nothing forced, branch `Dom` untouched** (still
`c6452361e4` = `origin/Dom`, working tree clean). Built in a separate worktree
`openpilots/raayyymond-StarPilot/StarPilot-release` (branch `Dom-release`) so the `Dom` checkout never moved.
No safety-classifier stops. No subagents spawned.

## 1. Commits (`upstream/StarPilot` = `823a5d5674` "Waffles", fetched 2026-10-15)

| # | hash | subject | files | +/− |
|---|---|---|---|---|
| 1 | `79cd6bcf36` | lagd: do not seed a saved lag across a steer-control-type change | 2 | +20 |
| 2 | `18400a6f3f` | honda: Accord variable-ratio rack map for angle mode | 3 | +47/−1 |
| 3 | `5b167ca5d0` | controlsd: do not apply lane-change smoothing to a corner | 2 | +92 |
| 4 | `e69adbd35f` | honda: angle control on the Accord angle-loop EPS (39990-TVA,A16x) — carries the 1b clip fix + 250°/s (section 3b) and the two review fixes (section 3c) | 13 | +365/−4 |
| 5 | `45a1a529c2` | controlsd: no turn-initiation lead under angle control (+ Honda reports `lateralControlMode = angle`) | 3 | +7/−2 |

History: `c0e129b9af` (first commit 4) → `c4ceeca314` (1b folded in) → split into `fc4a2de5b9` + `b818ebc7b0` at the orchestrator's request → review fixes amended into commit 4: `e69adbd35f` + `45a1a529c2` (tree EVIDENCE-identical to the pre-amend fix commit `23bf35f68f`) → review D8 test split amended into commit 4: `e69adbd35f` + `45a1a529c2` (tree EVIDENCE-identical to `3343ad5280`: empty `git diff`). All local, never pushed. The pre-split tip is kept as local branch `Dom-release-pre-split-c4ceeca314`; it predates the held-setpoint test, the final turn-lead comment and the review fixes. Delete it at will.

Commit 1 is a clean cherry-pick of `38cff0247`; it keeps its original message and its original `Claude Opus 5.5`
trailer. Commits 2–4 carry `Co-Authored-By: Claude Fable 5.1`. Git author is the operator's configured identity.

**Diff stat `upstream/StarPilot..Dom-release`: 19 files, +531 / −7** (vs Dom: 44 files, +4,302 / −65). Non-test
code is about 200 lines. `git diff --check` is clean.

## 2. Per-file hunks (cite by grep string)

| file | hunk → purpose |
|---|---|
| `honda/values.py` | `CarControllerParams`: `ANGLE_LIMITS` (400°, `MAX_LATERAL_ACCEL/JERK` 3.589, `MAX_ANGLE_RATE=2.5` = 250°/s), `ANGLE_ERROR_MAX_BP/V` (the clip), `ANGLE_RAW_MAX 4000`, `ANGLE_ARM = 2`, `ANGLE_STEER_ACTUATOR_DELAY = 0.15` · `HondaFlags.EPS_ANGLE_LOOP_FW = 16384` · `is_accord_eps_angle_loop_fw()` · `ACCORD_ANGLE_SR_BP/V`, `ACCORD_ANGLE_SR_LEVEL = 16.84`, `accord_angle_steer_ratio()`, `accord_angle_at_own_ratio()` |
| `honda/interface.py` | fw loop sets `eps_angle_loop_fw`; Accord branch: flag + `steerControlType = angle` + delay. No param |
| `honda/carcontroller.py` | init: `angle_mode`, `VM`, `apply_angle_last` · `_angle_hold_allowed` (panda predicate mirror) · `_update_angle`: `apply_steer_angle_limits_vm` on its own previous output → error clip on the sent value only → raw = round(−10·deg); idle hold = −10·measured when allowed, else 0 · send branch with `angle_arm` · `actuatorsOutput.steeringAngleDeg/torqueOutputCan/lateralControlMode = angle` |
| `honda/hondacan.py` | `create_steering_control(..., angle_arm=None)`: setpoint packed with request off too; `STEER_CONTROL_ARM` set |
| `honda/carstate.py` | angle mode: any `STEER_SENSOR_STATUS_1..3 != 1` → `steerFaultTemporary` |
| `dbc/generator/honda/_bosch_2018.dbc` + 6 `*_generated.dbc` | new signal `STEER_CONTROL_ARM : 19|2@0+` (0xE4 byte 2 bits 3:2) + its `CM_` comment |
| `controlsd.py` | Accord + angle: `sr = accord_angle_steer_ratio(measured − offset)` (before upstream's torque branch) · lane-change turn latch (constant, function, init, use) · `turn_lead_allowed`: `return lateral_control_mode != LateralControlMode.angle` |
| `latcontrol_angle.py` | Accord: re-evaluate the map at the desired angle |
| `lagd.py` | reject a saved lag on a `steerControlType` change |
| tests | `honda/tests/test_honda_accord_angle.py` (new, 34 tests) · `test_lane_change_turn_gate.py` (as Dom) · `test_lagd.py` (+1 test, as Dom) · `test_turn_lead.py` (the `ford, angle → allowed` line replaced by `honda, angle → not allowed` / `honda, inactive → allowed`) |

## 3. Decisions taken

- **DBC signal, not hand-packing (my call).** The generator is pure concatenation and reproduced all 16 committed Honda
  generated DBCs byte-for-byte (LF-normalised) before the edit. EVIDENCE: `gen.py check` reported 0 differing files
  before and after the write. The packer now computes the checksum, so Dom's `set_steering_control_arm()` and its
  manual re-checksum are gone. The signal adds no bytes to torque frames, because the packer starts from zeros.
- **Map gated on angle mode.** Dom applied the SR map to the Accord in torque mode too. On `Dom-release` torque-mode
  Accords keep upstream's `get_honda_accord_steer_ratio_scale` path unchanged, per "torque path byte-identical".
- **SteerRatio is a constant.** `ACCORD_ANGLE_SR_LEVEL = 16.84` reproduces what every angle drive ran (toggle 16.84
  as the level). The `SteerRatio` toggle no longer moves the curve in angle mode.
- **Lane-change gate without its key.** `LaneChangeTurnGate` (default on) is dropped; the gate is unconditional
  inside the existing `lane_change_pace < 10` smoothing block. Reason: the branch is **prebuilt** (`prebuilt` marker,
  committed `common/params_pyx.so`), and any new key needs an on-device `.so` rebuild. Turning the gate off now
  needs a code change.
- **No fault for "angle fw but not angle mode".** It is unreachable now that detection alone selects angle mode.

## 3b. Task-1b changes (orchestrator decision 2026-10-15): clip fix + rate in commit 4, turn-lead gate = commit 5

| change | what | tag / method |
|---|---|---|
| **turn lead off in angle mode** | `turn_lead_allowed` → `lateral_control_mode != LateralControlMode.angle` (brand-agnostic; feature gated, not deleted). The upstream comment is kept, plus: "Measured on the Accord angle-loop EPS 2026-10-15: the fade's engaged_ratio makes the command ~ 2x(lead - measured), feedback on the wheel through the loop lag; the wheel hunted in every sharp turn." | — |
| ⚠ **needed a second line** | `lateralControlMode` comes from `carOutput.actuatorsOutput`, and **only Rivian's car controller writes it**. Honda never did, so it read `inactive` and the one-line gate alone would have left the Accord's lead ON. Honda's angle branch now sets `new_actuators.lateralControlMode = angle` every frame in angle mode (not only when latActive, so the one-frame carOutput lag cannot let the lead through at engagement) | EVIDENCE: `grep lateralControlMode` over `opendbc/car`, `selfdrive` — writers: rivian only; readers: controlsd + the Rivian-only UI tint (gated on `brand == "rivian"`) |
| other angle cars | Tesla, Hyundai CAN-FD, Toyota LTA, Subaru, Ford never set the field, so the gate changes nothing for them. Only the upstream test line `turn_lead_allowed("ford", angle)` flipped | EVIDENCE: same grep |
| **clip no longer re-seeds the limiter** | `apply_angle_last` = the limiter's own output (upstream `apply_steer_angle_limits_vm` shape); the error clip bounds only the sent setpoint | EVIDENCE: tests `test_wheel_motion_does_not_feed_the_limiter_state` (same command, wheel noise σ 15°: limiter state identical every frame) and `test_wheel_moving_under_a_held_setpoint_does_not_move_the_limiter_state` (command held at 20°, wheel 20 ± 15°: state stays 20.0 every frame, sent = clip(20, wheel ± err)) |
| effect vs Dom (both at 250°/s) | 6,401 of 90,000 random frames differ; **every one follows a frame where Dom's clip bound since the last latActive edge** (0 differ otherwise) | EVIDENCE: `fuzz_identity.py`, 8.3 s |
| consequence to know | while the clip binds, the limiter state keeps running toward the command (bounded by the 3.589 m/s² accel limit and 400°); the sent value stays within ±clip of the wheel. When the wheel catches up the send follows the state, not a re-seeded copy of the wheel | BELIEF on the on-car feel; the arithmetic is EVIDENCE (test `test_rate_limit_then_error_clip`) |
| **rate cap 250°/s** | `MAX_ANGLE_RATE=2.5` (deg per 10 ms frame) | the V299 routes ran 250 (config B); upstream Tesla 5°/20 ms = 250°/s and Rivian 2.5°/10 ms = 250°/s; Hyundai CAN-FD 500°/s, Subaru 1°/frame. 250 sits inside upstream practice. At speed the 3.589 m/s³ jerk limit binds first, so the cap mostly acts at low speed. EVIDENCE: `grep MAX_ANGLE_RATE` in upstream `values.py` files |
| **curvature hold below 4.47 m/s** | **not the same class; unchanged.** Its ratchet sources are the raw model action and the plan curvature, by design never the measured value (upstream comment: "never on the floored/measured value, so the hold can't feed itself"). Measured curvature enters only (a) two monotone swept-heading integrators that pick a decay τ / gate re-arming, and (b) the nudge-to-commit latch, which needs `steeringPressed` with driver torque in the blinker direction and only grows the hold. Neither is proportional to (target − measured), so neither forms the lead's sign-reversing loop | EVIDENCE: code read of the hold block (grep `self.curvature` in it); BELIEF: no on-car effect, not measured |

## 3c. Review fixes (`FORK-REVIEW-Dom-release-2026-10-15.md`, orchestrator decision 2026-10-15, in commit 4)

| fix | what | tag / method |
|---|---|---|
| **D1: unread EPS fw** | `interface.py`: Accord, EPS not detected as A16x, and **no `eps` entry in `car_fw`** (and not docs) → `HondaFlags.EPS_FW_UNREAD = 32768`. `carstate.py`: that flag → `steerFaultPermanent`. EPS read as stock or A160 → torque mode, no flag, no fault, as before | EVIDENCE: test `test_eps_fw_unread_faults` (A16C → angle; stock and A160 read → torque, no flag, no fault; no EPS fw → flag + permanent fault). All four cases run the same unfed CarState, so the two read cases are the control: the fault comes from the flag alone |
| ⚠ **D1 side effect** | upstream lists `Ecu.eps` as **non-essential for `HONDA_ACCORD`** in the fw query ("We lose these ECUs without the comma power on these cars"). An Accord whose EPS does not answer, for example without comma power, now gets a permanent steer fault instead of torque-mode steering. The operator's car read its EPS fw on route 79, so it is unaffected. **This commit is not upstreamable as is** | EVIDENCE: `values.py` `non_essential_ecus`; route-79 fw from the delta report |
| **D8: test split** | the held-setpoint test no longer swallows the rate-step check: that check is its own test, `test_each_step_is_bounded_by_the_rate_limit`, and its comment says 2.5 deg/frame (250 deg/s), not 1.2 | EVIDENCE: 34 passed |
| **D4: comment** | `_update_angle` idle hold comment now reads "keep the setpoint at the wheel so engagement starts without a step". Behaviour unchanged | — |

## 4. Dropped, and why

| dropped | why |
|---|---|
| `AccordEpsAngleLoop` switch + `_MISSING` flag/fault | orchestrator: fw-only detection |
| `AccordAngleMaxRate`, `AccordAngleClipScale`, `read_accord_angle_param` | constants; the rate is now 250°/s (config B's dose) |
| 0x1AB torque bar: parser entry, `accord_eps_torque_s10`, `update_accord_eps_torque`, `EPS_TORQUE_*`, torque_bar + mici renderer edits, `AccordAngleBarFromEps` | orchestrator |
| status word: `ANGLE_STATUS_*`, `angle_status`, `card.py` copy, capnp `accordAngleStatus @31` | orchestrator — **see caveat 1** |
| all torque-mode / rate-plant / observer / dither / hysteresis / Ki-schedule code, 22 `Accord*` torque keys, Galaxy + safe-mode entries, capnp `accordObserver*` | unreachable in angle mode |
| LAF ×10 and Kp ceilings, UI sliders, Rebuild Params (doc, panel, Galaxy, mobile), KeepLearnedLatAccelOffset, torqued publish fix | torque-only or key plumbing — **see caveat 3** |
| `test_angle_v299.py`, 610 KB npz, `accord_angle_replay.py`, `accord_torque_mode_replay_r71b.json`, Dom's `test_honda_accord_angle_loop.py`, torque parts of `test_latcontrol.py` | replaced by one test file without binary data |
| the 31 MB `frpc_darwin_*` deletion | upstream tree left as is |

## 5. Verification

| check | result | tag / method |
|---|---|---|
| `honda/tests/test_honda_accord_angle.py` | **34 passed** (0.54 s, on `45a1a529c2`) | EVIDENCE: pytest, Windows shim below |
| all `honda/tests/` (incl. upstream `test_honda.py`, `test_bosch_a_radar.py`) | **244 passed** (0.96 s, on `45a1a529c2`); with `opendbc/dbc` + `opendbc/can/tests`: 293 passed + 604 subtests (on `45a1a529c2`; the D8 amend touched only the test file) | EVIDENCE |
| `turn_lead_allowed` vs the updated upstream test (AST-extracted) | pass | EVIDENCE: `verify_turn_lead.py` |
| `opendbc/dbc` + `opendbc/can/tests` | **50 passed, 604 subtests** | EVIDENCE |
| new `_update_angle` vs Dom `c6452361e` `_update_angle` (AST-extracted) | before the 1b change (both 120°/s): **0 mismatches / 90,000 random frames**; after it (both 250°/s): differences only after clip events (section 3b) | EVIDENCE: `fuzz_identity.py` |
| 0xE4 angle frame, DBC-packed vs Dom hand-packed | **0 byte mismatches / 16,002 frames** (raw −4000…4000, request on/off) | EVIDENCE: `frame_identity.py` |
| torque frame with the new signal vs DBC without it | identical over torque −4096…4096, request, TJA | EVIDENCE: test `test_torque_frame_unchanged_by_the_dbc_signal` |
| SR map vs Dom `get_honda_accord_steer_ratio(·, 16.84)`; desired-angle fixed point vs Dom | max diff 3.6e−15; 1.1e−13 | EVIDENCE: `verify_selfdrive.py` |
| lane-change gate tests (functions AST-extracted from release `controlsd.py`) | 5/5 pass | EVIDENCE (indirect: controlsd itself not imported) |
| `controlsd.py`, `latcontrol_angle.py`, `lagd.py` | py_compile OK | EVIDENCE |
| `test_latcontrol.py`, `test_lagd.py`, `test_lane_change_turn_gate.py`, `test_turn_lead.py` as pytest; `test_car_interfaces.py` | **NOT RUN** — need Linux-only compiled modules (`msgq`, `common.transformations`) and the hypothesis/conftest stack | EVIDENCE of the blocker; the lagd file equals Dom's commit, which was hand-checked then |
| full `CarController.update()` in angle mode | **NOT RUN**; the update-path hunks are Dom's minus the status lines | BELIEF |
| on-device import / drive | not done | — |

Method: Python 3.12 `bin_decompile` env; a `sitecustomize.py` shim (from the V299 fork review) that maps `openpilot` to
the worktree and loads cereal schemas with `car.capnp` from opendbc; `msgq`/`zmq`/`setproctitle` stubbed;
`parameterized`, `hypothesis`, `tqdm`, `crcmod`, `pycryptodome` pip-installed to the scratchpad only (the conda env was
not modified). Scripts and shim: session scratchpad `rebuild/`.

## 5b. Known, not fixed (from the review, LOW, left as they are by orchestrator decision)

| id | item |
|---|---|
| D2 | While the error clip binds, sent = measured ± error_max, so wheel-angle sensor noise passes into the sent setpoint. The stored-state fix does not remove that path (simulation only) |
| D3 | The car controller's own `VehicleModel` uses `CP.steerRatio` 16.33, while the map serves 16.84 at centre down to 12.3 at 380°. The jerk and lateral-accel caps are off by about 3 % at centre and up to 25 % at large angle. The 2.5°/frame cap dominates below about 8 m/s |
| D5 | Scope beyond the Accord: `turn_lead_allowed` keeps an unused `brand` argument; the lane-change turn latch applies to every brand when lane-change pace < 10; lagd drops a saved lag on any steer-control-type change. None touches the Accord angle path |
| wire | 2.4 % of request=1 frames on the flown V299 routes carry raw 0 (no fault noted; the 0x1AB DTC was not checked for those frames). Same rule as Dom |

## 6. Caveats (decision-bearing)

1. **The drive reader loses its F1 gate.** `rlog-tools/studies/angle_loop/drive_read_v299.py` reads
   `starpilotCarState.accordAngleStatus`, which `Dom-release` does not publish. The reader must derive rate/clip
   binding offline from `carControl.actuators.steeringAngleDeg` vs `carOutput.actuatorsOutput.steeringAngleDeg` and
   `carState.steeringAngleDeg` (all still logged) before a `Dom-release` drive is read. BELIEF: derivable.
2. **Unread EPS fw: FIXED in commit 4 (section 3c)** by a permanent fault when the Accord reports no EPS fw at all. It
   still does not cover an EPS that answers with an unexpected string for the angle image; that case stays in torque mode.
3. **No V295 torque-firmware fallback.** The REVERT_to_V295 config needs the ×10 LAF ceiling and `AccordTorqueKi`,
   both dropped. On `Dom-release` the revert floor is an angle-family image (A16A/B/C).
4. **Old toggle configs.** The V298/V299 configs carry keys `Dom-release` lacks (`AccordEpsAngleLoop`,
   `AccordAngle*`, torque keys). Angle mode needs no config now. Do not import them. BELIEF: Galaxy skips unknown keys.
5. **No new param keys, no capnp, no C++.** The diff is `.py` and `.dbc` only, and opendbc's CAN packer/parser here
   is pure Python. So the upstream prebuilt artifacts stay valid and no on-device rebuild is needed. EVIDENCE: diff
   stat; `opendbc/can/` holds only `.py`.
6. **Worktree artefact.** In the worktree, Windows removed `starpilot/system/galaxy/bin/frpc_darwin_*` after checkout
   (BELIEF: Defender quarantine; grep reported "Permission denied" on them first). They show as unstaged deletions
   there. **No commit contains that deletion** (EVIDENCE: per-commit `--stat`). Never `git add -A` in that worktree.

## 7. Where the task-1b constants live (each a one-line edit)

All in `opendbc_repo/opendbc/car/honda/values.py`:

| constant | grep string | value |
|---|---|---|
| max angle rate | `MAX_ANGLE_RATE=2.5` | 2.5 °/frame = 250 °/s |
| jerk bound | `MAX_LATERAL_JERK=MAX_LATERAL_JERK` | 3.589 m/s³, the shared opendbc constant; put a number here to change the Accord only |
| accel bound | `MAX_LATERAL_ACCEL=MAX_LATERAL_ACCEL` | 3.589 m/s² |
| error clip | `ANGLE_ERROR_MAX_V =` | [17.0, 15.5, 19.5, 17.0, 8.5, 4.5] ° at `ANGLE_ERROR_MAX_BP` [3.1, 8.0, 10.0, 11.75, 17.5, 26.9] m/s |
| actuator delay | `ANGLE_STEER_ACTUATOR_DELAY =` | 0.15 s |
| steer ratio level | `ACCORD_ANGLE_SR_LEVEL =` | 16.84 |
| ratio map shape | `ACCORD_ANGLE_SR_V =` | 13 knots, V[0] 16.88 nominal |
| interlock value | `ANGLE_ARM =` | 2 |

## 8. Push and device deploy — for the operator, NOT executed

**Step 1 — push the new branch (PC, fork repo). `Dom` is not touched.**

```bash
cd C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot
git fetch upstream
git log --oneline upstream/StarPilot..Dom-release
#   45a1a529c2 controlsd: no turn-initiation lead under angle control
#   e69adbd35f honda: angle control on the Accord angle-loop EPS (39990-TVA,A16x)
#   5b167ca5d0 controlsd: do not apply lane-change smoothing to a corner
#   18400a6f3f honda: Accord variable-ratio rack map for angle mode
#   79cd6bcf36 lagd: do not seed a saved lag across a steer-control-type change
git push origin Dom-release
```

**Step 2 — put the device on it (car off; `cat /data/params/d/IsOnroad` prints `0`).**

```bash
ssh comma@<device-ip>
cd /data/openpilot
git status --short                      # expect clean; stop and look if not
git fetch origin Dom-release
git checkout -B Dom-release origin/Dom-release
git log -1 --oneline                    # expect 45a1a529c2
sudo reboot
```

No params rebuild and no config import are needed: the branch adds no param keys, no capnp fields and no C++.
Do not import the old V298/V299 toggle configs.

**Step 3 — check the first drive's logs before anything else:**
- `initData` git commit `45a1a529c2`, branch `Dom-release`;
- `carParams.steerControlType = angle`, `carParams.flags & 16384` nonzero, `carParams.flags & 32768` zero, `carParams.steerActuatorDelay = 0.15`;
- `carParams.carFw` EPS fwVersion `39990-TVA,A16C` (or A16A/A16B);
- `carOutput.actuatorsOutput.lateralControlMode = angle` (the turn-lead gate's input);
- 0xE4 byte 2 bits 3:2 = 2 on every frame.

**Step 4 — only once that drive is accepted, make it `Dom` (archive first).**

```bash
cd C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot
git branch Dom-archive-2026-10-15 c6452361e
git push origin Dom-archive-2026-10-15
git push --force-with-lease=Dom:c6452361e origin Dom-release:Dom
# then on the device, if it should follow Dom again:
#   git fetch origin Dom && git checkout -B Dom origin/Dom && sudo reboot
```

**Revert (device):** `git fetch origin Dom && git checkout -B Dom origin/Dom && sudo reboot` returns it to `c6452361e`
(V299 fork) while `Dom` has not been replaced, or to the archive branch after step 4.

BELIEF: the StarPilot updater follows the remote branch it is on, so a device on `Dom-release` stays there until
switched back.
