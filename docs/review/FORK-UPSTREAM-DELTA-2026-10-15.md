# FORK vs UPSTREAM DELTA — StarPilot `Dom` vs `firestar5683/StarPilot`, 2026-10-15

Subagent `fork-upstream` (read-only on git: `git fetch` only; no checkout/rebase/merge/commit/push).
Fork: `openpilots/raayyymond-StarPilot/StarPilot`, branch `Dom`, HEAD `c6452361e4`, working tree clean.
Method for every count below: `git rev-list`, `git log --numstat`, `git diff --stat`, `git merge-tree --write-tree`
(git 2.39), run after `git fetch upstream` + `git fetch origin` on 2026-10-15. All EVIDENCE unless tagged BELIEF.

## 1. What Dom tracks, and the upstream update

| item | value | tag |
|---|---|---|
| upstream default branch | **`StarPilot`** (`git remote show upstream` → `HEAD branch: StarPilot`) | EVIDENCE |
| upstream `Dom` branch | exists and is **identical** to `upstream/StarPilot` (both `823a5d5674`, 2026-10-15 "Waffles") | EVIDENCE |
| `origin/Dom` | `c6452361e4` = local Dom → **V299 fork commit IS pushed** (the fork-config README's "Not pushed" is stale) | EVIDENCE |
| Dom's upstream config | `branch.Dom.remote = origin` (no upstream tracking); local `StarPilot` = `50fb062853` (2026-07-10), stale | EVIDENCE |
| merge-base Dom ↔ upstream/StarPilot | `50a8d1abdb` 2026-09-13 "Prevent rejected SLC limit auto-application" | EVIDENCE |
| Dom ahead / behind | **34 ahead / 171 behind**; Dom is linear (0 merges); its oldest commits carry Sept-03 author dates, so Dom was last rebased onto upstream at the 09-13 merge-base | EVIDENCE |
| upstream since merge-base | 171 commits (1 merge, PR #194 Honda City fw), 551 files, +36,765 / −5,566; authors firestar5683 110, firestarsdog 27, AngusBell97 16, others 18 | EVIDENCE |
| areas | UI 16 % (big text/polish, mici, model renderer), panda prebuilt binaries 17 % (`panda/board/obj/*` rebuilt twice), opendbc car ports 14 % (Hyundai, Toyota, Subaru AVH, Tesla legacy/preap, Ford, GM, Volvo, VW), `starpilot/` + Galaxy 26 %, `selfdrive/controls` 6 % (new `steering_saturation.py`, SLC rewrite, G70/GV70 tunes, latcontrol_torque +85/−?, vehicle_tunes +401), safety: ford/hyundai/subaru/tesla/toyota/volvo .h changed, **`honda.h` UNCHANGED** | EVIDENCE |
| Honda in the update | `honda/values.py` 1 line (City docs), `fingerprints.py` +6 (City 2025 fw). Nothing Accord, nothing in `carcontroller/carstate/interface/hondacan`. Upstream controls contain exactly 1 new line mentioning Accord | EVIDENCE |
| opendbc / panda layout | **vendored, not submodules**: no `.gitmodules`, no gitlink (mode 160000) entries; `opendbc_repo/` and `panda/` are plain trees. The Accord car edits sit in this repo directly | EVIDENCE |

## 2. Every Dom commit not in upstream (34), grouped

`+/−` = numstat totals. "Superseded" = dead or irrelevant once `steerControlType = angle` (LatControlTorque is not instantiated in angle mode, so every torque-path term is unreachable).

### (i) Accord angle interface — 4 commits
| commit | date | files | +/− | content | superseded? |
|---|---|---|---|---|---|
| `51c199f28` | 10-01 | 15 | +752/−6 | V298 angle interface: fw detect, angle branch, 0xE4 arm, limits, params, tests | — (is the interface; V299 revises) |
| `38cff0247` | 10-01 | 2 | +20 | lagd: don't seed a saved lag across a steerControlType change (generic) | keep |
| `2712e1336` | 10-01 | 6 | +89/−17 | review fixes: MISSING fault, panda-mirroring hold predicate, limiter seeded from wheel | — |
| `c6452361e` | 10-02 | 15 | +782/−90 | V299: override removed, 0x1AB torque bar, A16 family detect, AccordAngle* params, status word, mici cue, 505-line test + 610 KB npz | — |

### (ii) Accord torque-mode / rate-plant / V293–V294 / SR map — 23 commits
| commit | date | files | +/− | content | superseded? |
|---|---|---|---|---|---|
| `5706c1d32` | 09-03 | 3 | +32/−15 | variable-SR rack curve | **no** — angle mode uses the SR map |
| `5b9e49836` | 09-04 | 1 | +2/−2 | SR map ≥48° knots | no (SR map) |
| `47d28addd` | 09-04 | 1 | +1/−1 | turn-FF taper 0.10→0.30 | yes |
| `2727c1d4a` | 09-05 | 2 | +38/−6 | SteerRatio toggle sets the map level | no (SR map) |
| `6dd9a5529` | 09-07 | 9 | +234/−7 | rate-plant FF, KeepLearnedLatAccelOffset, Galaxy patch switches | yes |
| `6c455eb70` | 09-07 | 7 | +55/−10 | EPS gain/spring scales | yes |
| `26c7f386b` | 09-07 | 11 | +554/−50 | latAccelOffset in rate-plant path + safe-mode + rebuild-params hardening + torqued publish fix | mostly yes (see iii) |
| `305732c85` | 09-10 | 2 | +88/−28 | SR map reshaped (82 routes) | no (SR map) |
| `4247cb09e` | 09-13 | 4 | +12/−5 | SR refit (83 routes) **+ deletes `frpc_darwin_*` binaries** (31 MB) | SR part no; deletion is unrelated |
| `9622aee9f` `8c4051ce6` `66cf4454a` | 09-13 | 2/1/2 | +49/−23 | V293 plant tables | yes |
| `e8e62f0e1` `f4e314da6` `08a5a7064` | 09-13/14 | 8/9/3 | +539/−24 | V293 rev 3/4 (hold map, hysteresis, rate loop, notch, Ki schedule, stock-sync fix) | yes |
| `e44b6cd31` | 09-15 | 9 | +177/−2 | rev 5 disturbance observer + capnp `accordObserver*` | yes |
| `afbe5fb44` `b97169c65` `91e902a86` `84766cdc5` | 09-16 | 8/8/8/2 | +494/−23 | rev 6–6.4 (constants, band, dither, hold level) | yes |
| `d6f7bdd02` | 09-16 | 6 | +107 | rev 6.2 LaneChangeTurnGate (controlsd, generic) | no — car-agnostic, still acts in angle mode (it gates the curvature clamp in controlsd) |
| `54ff1ea39` `20d24ab79` | 09-20/29 | 6/2 | +100/−45 | V294 revert-to-stock defaults + test fixes | yes |

### (iii) Other the operator carries — 7 commits (+ parts of `26c7f386b`, `4247cb09e`)
| commit | content | needed in angle mode? |
|---|---|---|
| `6259d00a5` | `LAT_ACCEL_FACTOR_MAX_MULT` 1.5→10 | no (torque only) — **but the V295 torque-fw revert config (`SteerLatAccel 14.0`) needs it**: upstream clamps SteerLatAccel to 1.5× stock (`starpilot_variables.py` `max=latAccelFactor * 1.5`) |
| `ad472b15d` `08e657689` | UI/Galaxy slider ceiling follows the above | no |
| `8228eda2c` | SteerKP clamp 0.05–5× | no (upstream 0.5–1.5× of 0.6 already admits 0.9) |
| `4f74a7e3e` `b8d9c6a9e` `a357cd2b5` (+ `26c7f386b` part) | Rebuild Params action (doc, software panel, Galaxy, mobile) | only because new param keys exist; **unneeded if the elegant set adds no keys** (BELIEF: Galaxy skips keys absent from the built params library — per the fork-config README deploy notes) |
| `26c7f386b` part | `torqued.py` always publishes the learner's own filter state | torque only; a genuine generic fix, upstreamable separately |

## 3. Current Accord-specific diff (Dom vs merge-base): 44 files, +4,302 / −65

### (a) The angle interface itself (non-test: 7 files +269/−7 in opendbc honda + latcontrol_angle + lagd; plus UI/cereal/params)
| file | hunk → purpose |
|---|---|
| `honda/values.py` | `ANGLE_LIMITS` (400°, VM accel/jerk 3.589, MAX_ANGLE_RATE 1.2°/frame) → limiter config · `ANGLE_ERROR_MAX_BP/V` → error clip (the fork's only bound; panda bounds nothing) · `ANGLE_RAW_MAX 4000` → pack guard · `ANGLE_*_PARAM` → operator params · `ANGLE_STATUS_*` → status bits · `EPS_TORQUE_LSB/RAIL/STALE_NS` → 0x1AB bar · `ANGLE_ARM = 2` → camera interlock · `HondaFlags.EPS_ANGLE_LOOP_FW / _MISSING` · `is_accord_eps_angle_loop_fw()` (`39990-TVA,A16` + one capital, NULs stripped) · `HONDA_ACCORD_ANGLE_STEER_ACTUATOR_DELAY 0.15` |
| `honda/interface.py` | `accord_eps_angle_loop_enabled()` reads `AccordEpsAngleLoop` · fw loop sets `eps_angle_loop_fw` · Accord branch: flag + `steerControlType = angle` + delay iff fw AND switch; `_MISSING` flag if switch without fw |
| `honda/carcontroller.py` | `read_accord_angle_param()` · init: VM, per-instance limits from params · `_angle_hold_allowed()` mirrors panda `controls_allowed || aol_allowed` · `_update_angle()`: `apply_steer_angle_limits_vm` + error clip + status bits + raw = round(−10·deg), hold = −10·measured when allowed, else 0 · send branch with `angle_arm` · `actuatorsOutput.steeringAngleDeg/torqueOutputCan` |
| `honda/hondacan.py` | `create_steering_control(..., angle_arm)` packs the field with request off · `set_steering_control_arm()` writes byte-2 bits 3:2 + re-checksums (no DBC signal) |
| `honda/carstate.py` | angle mode: `STEER_SENSOR_STATUS_1..3 != 1` → `steerFaultTemporary` · angle fw + torque mode → `steerFaultPermanent` · `_MISSING` → permanent · `accord_eps_torque_s10()` + `update_accord_eps_torque()` → `steeringTorqueEps` from 0x1AB · parser adds 0x1AB (nan, checksum/counter ignored) |
| `latcontrol_angle.py` | Accord: re-evaluate the SR map at the DESIRED angle (`get_honda_accord_angle_at_own_ratio`) |
| `controlsd.py` (SR part) | `sr = get_honda_accord_steer_ratio(measured angle, level)` replacing upstream's flat `get_honda_accord_steer_ratio_scale` |
| `latcontrol_vehicle_tunes.py` (SR part) | the rack map + level + fixed-point helper |
| `lagd.py` | reject a saved lag on steerControlType change |
| `card.py` + `custom.capnp @31` | publish `accordAngleStatus` |
| `params_keys.h` | `AccordEpsAngleLoop`, `AccordAngleMaxRate`, `AccordAngleClipScale`, `AccordAngleBarFromEps` |
| `torque_bar.py` + `mici/model_renderer.py` | bar draws −steeringTorqueEps/2461 when `AccordAngleBarFromEps` |
| `device_settings_layout.json`, `safe_mode.py` | Galaxy entries / safe-mode stock values for the new keys |

### (b) Leftover torque-mode code (unreachable in angle mode)
`latcontrol_torque.py` +173 (rate-plant FF, hysteresis, rate loop, observer, dither, Ki schedule) · `latcontrol_vehicle_tunes.py` ~+500 of +564 (plant tables, hold map, bands, dither, observer) · `controlsd.py` LAF-offset keep · `torqued.py` · capnp `accordObserverTorque @8/@9` · 22 `Accord*` torque keys in `params_keys.h` (+ Galaxy layout ~300 lines, safe_mode) · LAF/Kp ceilings · Rebuild Params (~470 lines across 7 files).

### (c) Tests / data / docs
`test_angle_v299.py` 505 + `accord_angle_r79_v299.npz` (609,778 B binary) · `test_honda_accord_angle_loop.py` 436 · `accord_angle_replay.py` 77 · `accord_torque_mode_replay_r71b.json` (torque leftover) · `test_latcontrol.py` +657 (mostly torque mode; +88 angle) · `test_lane_change_turn_gate.py` 54 · `test_lagd.py` 17 · rebuild/safe-mode/variables/Galaxy tests ~370 · `docs/how-to/rebuild-params-on-device.md` 87.

### How other angle cars do it (EVIDENCE: `git grep` on upstream/StarPilot `opendbc_repo/opendbc/car`)
| pattern | cars | shape |
|---|---|---|
| detect → flag → `steerControlType = angle` + `safetyParam` flag | Hyundai CAN-FD (`HyundaiFlags.CANFD_ANGLE_STEERING`), Toyota (`ANGLE_CONTROL_CAR` → `ToyotaSafetyFlags.LTA`, `steerActuatorDelay 0.18`, `steerLimitTimer 0.8`), Subaru, Tesla | interface-only switch; **no params**; the panda gets a safety flag so it bounds the angle |
| limiter v2 (`apply_steer_angle_limits_vm` + `AngleSteeringLimits(MAX_LATERAL_ACCEL, MAX_LATERAL_JERK, MAX_ANGLE_RATE)` in `values.CarControllerParams`) | Tesla, Hyundai, Subaru | carcontroller: `self.apply_angle_last = apply_steer_angle_limits_vm(actuators.steeringAngleDeg, self.apply_angle_last, CS.out.vEgoRaw, CS.out.steeringAngleDeg, CC.latActive, CarControllerParams, self.VM)`; `new_actuators.steeringAngleDeg = apply_angle_last` |
| limiter v1 (`apply_std_steer_angle_limits`, rate tables) | Ford (curvature), Nissan, PSA, Toyota LTA, Volvo, Subaru | same carcontroller shape |
| lateral controller | all angle cars use stock `LatControlAngle`; per-car hooks there are rare (Subaru Ascent only) | — |

Dom's carcontroller already follows the v2 shape; its extras are the error clip, the hold-when-idle packing and the arm field — all Honda-angle-firmware specific.

### The ELEGANT, upstream-shaped Accord angle implementation (spec)
Smallest set that (1) detects `39990-TVA,A16?`, (2) uses the standard angle path, (3) carries Accord tuning:

| # | file | edit | keep reason |
|---|---|---|---|
| 1 | `honda/values.py` | `HondaFlags.EPS_ANGLE_LOOP_FW`; `is_accord_eps_angle_loop_fw()`; in `CarControllerParams`: `ANGLE_LIMITS` (constants, rate 1.2°/frame), `ANGLE_ERROR_MAX_BP/V`, `ANGLE_RAW_MAX`, `ANGLE_ARM = 2` | detection + limits |
| 2 | `honda/interface.py` | fw loop → flag; `if flag: steerControlType = angle; steerActuatorDelay = 0.15` (Toyota/Hyundai shape, no param) | switch |
| 3 | `honda/hondacan.py` | pack STEER_TORQUE as the angle with request off; arm bits 3:2 = 2 every frame. **Cleaner:** add a `STEER_CONTROL_ARM` signal (byte 2 bits 3:2) to the Honda DBC and pass it in `values` → `set_steering_control_arm()` and its manual re-checksum disappear (BELIEF: needs the DBC generator re-run; verify the generated file's signal) | **safety: camera interlock** |
| 4 | `honda/carcontroller.py` | `angle_mode` branch: `apply_steer_angle_limits_vm` → error clip → raw = round(−10·deg); idle: hold = −10·measured when panda-allowed, else 0 | **safety:** error clip is the only bound; idle hold — the firmware's 0xE4 fault sentinel rails P for 2 s on a 0 setpoint (kit memory 2026-09-30, "fork must send −10·angle when idle") |
| 5 | `honda/carstate.py` | angle mode: sensor status ≠ 1 → `steerFaultTemporary`; angle fw without angle mode → `steerFaultPermanent` | **safety:** false absolute angle |
| 6 | SR map: `latcontrol_vehicle_tunes.py` map + `controlsd.py` hook (replaces upstream's flat scale) + `latcontrol_angle.py` desired-angle re-eval | Accord tuning; in angle mode SR scales the setpoint 1:1 |
| 7 | `lagd.py` | 3-line guard (generic; separate commit, upstreamable) | correctness |
| 8 | one test file | fw detect (A16A/B yes; A160, A1x0 no; NUL pad), pack + arm + checksum, limiter seed, hold predicate, faults; no binary route data | — |

**Dropped by the spec:** `AccordEpsAngleLoop` switch and the `_MISSING` flag/fault · `AccordAngleMaxRate`/`ClipScale` params and `read_accord_angle_param` · `AccordAngleBarFromEps`, 0x1AB parser/decoder, torque-bar and mici-renderer edits · status word (`card.py`, capnp `@31`, `ANGLE_STATUS_*`) — **see caveat** · every torque-mode term, key, Galaxy entry, safe-mode value, capnp `accordObserver*` · `AccordVariableSteerRatio` key (apply the map unconditionally on the Accord) · LAF/Kp ceilings · Rebuild Params · KeepLearnedLatAccelOffset · `accord_torque_mode_replay_r71b.json`, `test_angle_v299.py` + 610 KB npz, `accord_angle_replay.py`.

**Caveats on the drops (decision-bearing):**
- **Status word is the drive-2 instrument.** `rlog-tools/studies/angle_loop/drive_read_v299.py` gates F1 on `starpilotCarState.accordAngleStatus` (≥ 99 % of latActive frames) and pins the fork schema (EVIDENCE: grep). Drop it only after the reader derives rate/clip binding offline from `carControl.actuators.steeringAngleDeg` vs `carOutput.actuatorsOutput.steeringAngleDeg` and `carState.steeringAngleDeg` (BELIEF: derivable; both are logged). Until then it is a 4-line instrument commit.
- **Dropping the switch changes one failure mode.** Today: switch on + EPS fw unread → permanent fault (alerted). Fw-only detection: EPS fw unread on the angle firmware → torque mode → the lane ignores the frames → **no steering, no alert** (BELIEF, from the interface.py comment). Keeping the `carstate` permanent fault for "angle fw flagged but not angle mode" does not cover the unread case. Operator's call; the switch costs one param key and one Rebuild Params.
- **V295 torque-firmware fallback.** The `REVERT_to_V295_r2` config needs `SteerLatAccel 14.0` (needs the 10× LAF ceiling) and `AccordTorqueKi 0.3` (upstream hard-codes 0.15). If V295 stays a revert target, carry a 2-item "torque fallback" commit; otherwise the revert floor is V298 on the angle set.
- **Panda safety:** Honda `honda.h` "STEER: safety check" only requires `data[0] | data[1] == 0` while not `controls_allowed || aol_allowed`; it bounds no angle (EVIDENCE: Dom == upstream for `honda.h`; read). So **no panda change is needed and none is in Dom.** An upstream reviewer would ask for a `HondaSafetyFlags.ANGLE_STEERING` with `steer_angle_cmd_checks_vm` — out of the minimal set (new safety code + rebuilt panda binaries, which this fork commits under `panda/board/obj/`).

## 4. Rebase vs merge — recommendation: REBUILD (= `rebase -i` with 30 of 34 dropped), not merge

| option | result | conflicts (merge-tree) |
|---|---|---|
| `git merge upstream/StarPilot` | keeps all 4,300 lines incl. ~3,000 dead torque-mode lines; history 34 + merge | **4 files**: `latcontrol_angle.py` (import vs upstream's `steering_saturation` move — trivial), `latcontrol_torque.py` (Accord torque block vs Kia Carnival friction — torque-mode leftover), `starpilot_variables.py` (LAF/Kp ceilings vs Sonata migration), Galaxy `SystemTools.js` (Rebuild Params vs reboot-scope refactor) |
| `git rebase upstream/StarPilot` (all 34) | same code, linear; 3 of 4 conflicts sit in commits that would be deleted anyway, replayed per commit | ≥ 4, likely more per-commit (BELIEF: not dry-run; git 2.39 lacks `merge-tree --merge-base`) |
| **rebuild from upstream (recommended)** | Dom = upstream + 3–5 readable commits, ~300 non-test lines | the angle set touches upstream-changed files only at `latcontrol_angle.py` (1 trivial), `honda/values.py` (City docs line, far away — clean), `controlsd.py` / `card.py` (merge-tree clean) |

Reasons: 30 of 34 commits are superseded or unrelated; the 4 angle commits depend on earlier ones (SR map, params layout, safe_mode), so a cherry-pick would drag them in; `rebase -i` would replay conflict-prone torque-mode commits only to delete them. Proposed sequence (**NOT executed**):

```bash
cd StarPilot
git fetch upstream origin
git branch Dom-archive-2026-10-15 c6452361e          # keep the full history
git push origin Dom-archive-2026-10-15
git switch -c Dom-next upstream/StarPilot
git cherry-pick 38cff0247                              # 1. lagd guard (lagd untouched upstream)
# 2. "honda: Accord variable-ratio rack map" -- hand-port from c6452361e:
#    get_honda_accord_steer_ratio + map constants + get_honda_accord_angle_at_own_ratio (vehicle_tunes),
#    controlsd sr hook (replace get_honda_accord_steer_ratio_scale), latcontrol_angle re-eval (on top of the
#    steering_saturation import). No AccordVariableSteerRatio key.
# 3. "honda: angle control on the Accord angle-loop EPS (39990-TVA,A16x)" -- start from
#    git show c6452361e:opendbc_repo/opendbc/car/honda/{values,interface,carcontroller,hondacan,carstate}.py
#    and delete the dropped items listed in section 3; one test file.
# 4. (optional, instrument) "Accord: publish the angle limiter status" -- card.py + capnp @31.
# 5. (optional, torque fallback) LAF ceiling 10x + AccordTorqueKi.
pytest opendbc_repo/opendbc/car/honda/tests selfdrive/controls/tests/test_latcontrol.py selfdrive/locationd/test/test_lagd.py
git push origin Dom-next
# only after a drive on Dom-next: git push --force-with-lease=Dom:c6452361e origin Dom-next:Dom
```
Squashed: `51c199f28`+`2712e1336`+`c6452361e` → commit 3 (minus drops); SR commits `5706c1d32`, `5b9e49836`, `2727c1d4a`, `305732c85`, SR part of `4247cb09e` → commit 2. Dropped: all other (ii) and (iii). `d6f7bdd02` LaneChangeTurnGate is car-agnostic and still acts in angle mode — keep it as its own commit only if the operator wants it (it was a rev-6.2 fix for a corner on route 76). The force-push rewrites the branch the device pulls (BELIEF: the StarPilot updater resets to the remote branch, so the device follows; verify on the device before deleting the archive).

## 5. Device-facing facts

| fact | value | tag |
|---|---|---|
| last measured device commit | route 79 (`00000079--a1f5d2a272`, V298, 2026-10-02) ran **Dom `2712e1336`** | EVIDENCE (initData attribution, `HANDOFF-2026-10-02-v298-flown-v299-built.md`) |
| does the device run HEAD `c6452361e` now? | **unknown** — it is pushed, but no V299 drive-2 rlog is in the kit (latest Accord rlogs = route 79) | EVIDENCE for the absence; the device state is unmeasured |
| SteerRatio | **16.84** in every angle config (V298, V299-A, V299-B, both REVERTs), = route 71b's initData value; `AccordVariableSteerRatio` absent from configs → default **true**, so 16.84 is the map LEVEL (map nominal 16.88, platform 16.33) | EVIDENCE (decoded configs) |
| other angle-config values | `AccordEpsAngleLoop` true, `UseAutoSteerDelay` true, `LaneCentering` true; V299-A adds `AccordAngleBarFromEps` true, `AccordAngleMaxRate` 120, `AccordAngleClipScale` 1.0; V299-B = MaxRate 250 (later dose). Torque-era keys carried inert: SteerKP 0.9, AccordTorqueKi 0.3, SteerFriction 0.011, SteerLatAccel 14.0, all torque terms off | EVIDENCE |
| consequence for the elegant set | it must reproduce SteerRatio 16.84 as the map level via the existing upstream `SteerRatio` toggle (upstream admits 0.5–1.5× of 16.33 → 16.84 OK), and rate 120°/s / clip ×1.0 become constants. V299-B's 250°/s dose would need a code change (or keep `AccordAngleMaxRate`) | EVIDENCE (upstream `starpilot_variables.py` SteerRatio clamp) / BELIEF on the operator's dosing plan |

No safety-classifier stops occurred. No subagents spawned.
