> NOTE (orchestrator, 2026-10-02): the reviewed commit 66780911 was AMENDED to **c6452361e43812c7a7931c76dd4e036bbe5a1835** (message trailer only: Co-Authored-By corrected to Claude Fable 5.1; the tree is byte-identical, `git diff 66780911 c6452361` is empty).

# REVIEW: V299 fork commit, identity and tests lens

- **Commit:** `66780911279bc5343406a042b173674feb3b1a81` on Dom. Its parent is `2712e1336`. It is local and not pushed (`origin/Dom` = `2712e1336`).
- **Reviewer:** subagent, READ-ONLY on the fork. Nothing was edited and nothing was committed.
- **Date:** 2026-10-02.
- **Verdict:** **PASS_WITH_DEFECTS.** All defects are low or info. None bears on what goes on the wire.

**What a FAIL would have looked like, written before running anything:**
- Any frame where the new `_update_angle` raw differs from the 2712e1336 code with the override set to `inf`.
- Any torque-path CAN send that differs with the switch off.
- A config that differs from V298 drive-1 in anything but the three new keys.
- A commit file outside the brief.
- A failing test.

## 1. Commit scope (EVIDENCE: `git show --name-only`, `git status --porcelain`)
- The commit touches exactly 15 fork files. All 15 are in the brief's list:
  - cereal/custom.capnp
  - params_keys.h
  - honda carcontroller / carstate / interface / values
  - the two test files and the npz fixture
  - card.py
  - torque_bar.py and mici model_renderer.py
  - device_settings_layout.json
  - safe_mode.py
  - the layout test
- Shared files hold only Accord hunks:
  - params_keys.h: the 3 new keys, plus the AccordEpsAngleLoop comment.
  - layout JSON: the AccordEpsAngleLoop text and the 3 new entries.
  - safe_mode: the 3 keys.
- The working tree is clean after the commit, and there is no stash. I cannot prove what the tree held before the commit. Nothing outside the brief is inside the commit.
- Committed blobs are LF (checked with Python on `git cat-file`). The CRLF seen in `git archive` comes from `core.autocrlf=true` on export, not from the blobs.

## 2. Tests re-run (EVIDENCE)
- **Interpreter:** bin_decompile `python` 3.12.13. I wrote my own sys.path shim, `scratchpad/rv_idt/boot.py`, which does three things:
  - maps `openpilot` to the fork root;
  - stubs `openpilot.system.hardware` and `locationd.helpers`;
  - loads cereal from a fresh mirror of `HEAD:cereal` with `car.capnp` materialised.
- **Command:** `pytest -p no:cacheprovider --noconftest`. Results:

| suite | result |
|---|---|
| test_angle_v299.py + test_honda_accord_angle_loop.py | **109 passed** (60 + 49) in 15 s |
| honda tests dir + galaxy test_device_settings_layout.py | **344 passed** |
| starpilot/common/tests/test_safe_mode*.py | **14 passed** (344 + 14 = the commit's 358) |
| selfdrive test_latcontrol, opendbc test_lateral_limits / test_vehicle_model | **NOT REPRODUCED.** The environment lacks `parameterized`, `tqdm`, `zmq`, `crcmod`, and the fork's `.venv` has no pytest. The commit changes neither `lateral.py` nor `selfdrive/controls`. The commit's 205+2 / 573 figures stand as the implementer's claim. |

## 3. Independent identity replay (EVIDENCE)
Script: `scratchpad/rv_idt/worker.py` + `compare.py`, about 12 s per tree, run in parallel.
- It runs the REAL modules from `git archive` of each commit (`old` = 2712e1336, `new` = 66780911). It does not use the test file's vendored class.
- For the old tree, the controller instance gets `ANGLE_OVERRIDE_ON = OFF = inf`.

| stimulus | frames | raw identical | setpoint bit-identical |
|---|---|---|---|
| fork fixture `accord_angle_r79_v299.npz` (lim_*) | 66,775 | **66,775 / 66,775** | yes |
| kit cache `r79_fork.npz`, every carState row with nearest-earlier carControl (whole route, latActive on/off) | 121,383 | **121,383 / 121,383** | yes |
| synthetic, seed 299: random latActive toggling (196 rising edges), hand torque N(0,1500), random desired/angle/speed 0-35 m/s | 40,000 | **40,000 / 40,000** | yes |

**Full `CarController.update()` on the recorded r71b windows.** Every CAN send was compared, not only 0xE4 (1,922 sends per config):
- **Switch off** (A16A, A16B, A160) and A160 with the switch on: identical to old, and 0xE4 equals the 20d24ab79 golden. With the switch off this also holds under non-default params (MaxRate 250, ClipScale 1.6, BarFromEps on). **The torque path is byte-identical.**
- **A16A with the switch on (angle mode):** all sends identical to old with `inf`. Non-default params differ, by design.
- **A16B with the switch on:** new = angle mode. Its sha equals new A16A's. Old = the FW_MISSING torque path. This is by design: the family detection.

**The vendored `V298AngleController`** in test_angle_v299.py is AST-identical to 2712e1336 `CarController._update_angle` and `_angle_hold_allowed`, after substituting `p.ANGLE_OVERRIDE_*` -> `self.on/off/lead` (EVIDENCE: `ast.unparse` compare).

**The (e) claims, re-derived with the old real module at 600/500/0.06** (`flown2.py`, 3 s):
- As-flown matches the recorded field on every latActive frame except [24872, 30533, 40759], the three artefacts the test documents.
- O1 occupies 10,075 latActive frames, with 415 releases.
- New vs flown outside O1: **3,245 / 56,692 = 5.72 %.** That is 381 differing runs, each starting exactly at an O1 release, with no orphan run.
- New vs recorded outside O1 and those windows: 3. These are the same pairing artefacts.

**The fixture rebuilds** byte-identically from the kit cache. I ran `build_v299_fork_fixture.py` with OUT redirected to scratch: every array is equal, and the file is 609,778 B (< 1 MB).

## 4. Configs (EVIDENCE)
I wrote my own decoder from the fork's `utilities.py` codec (XOR key + base64 + JSON, read at HEAD).
- The V298 base sha is `3e6c7b64...` and it holds 29 keys.
- **A** (`d1aeab7e...`), **B** (`ced2a4e2...`) and **REVERT** (`4633091a...`) each hold 32 keys, `settingsCount` 32, and each `.decoded.json` equals its encoded file.
- Every key is declared in params_keys.h at the commit.
- Each config's delta from V298 drive-1 is exactly the three new keys:
  - **A:** BarFromEps true, MaxRate 120.0, ClipScale 1.0.
  - **B:** BarFromEps true, MaxRate 250.0, ClipScale 1.0. That is A + one dose.
  - **REVERT:** BarFromEps false, 120.0, 1.0.
- The README's six sha256 values match the files on disk.

## 5. Spot checks beyond the tests
- **`accord_eps_bar`**, exercised with a real capnp `car.CarParams` reader (`uibar.py`, UI deps stubbed):
  - angle/honda/flag with steeringTorqueEps -1200 -> +0.4876. That is 1200/2461, the sign the brief specifies.
  - torque mode, a missing flag or the param off -> None.
  - The result clips at +-1.
  - The param is read once per `started_frame`.
- **The 0x1AB staleness clock** is `max(last_nonempty_nanos, _last_update_nanos)`. These are real CANParser attributes (parser.py, `update`), so the bar cannot be held forever by a missing attribute.
- **No reader** of `ANGLE_LIMITS` or `ANGLE_ERROR_MAX*` exists outside the Honda carcontroller (`git grep` over selfdrive, starpilot, honda and safety). The per-instance override is therefore private.
- **card.py:** FPCS is a fresh `StarPilotCarState.new_message()` per frame (honda carstate), so a zero status is never latched. `self.CI.CC` always exists, possibly as None, and `getattr(None, ..., 0)` = 0.

## Defects
| # | severity | what | where | fix |
|---|---|---|---|---|
| D1 | low | Commit trailer reads `Co-Authored-By: Claude Opus 5.5`. The brief asked for `Claude Fable 5.1` verbatim. | commit 66780911 message | Operator's call. Rewording changes the hash that README.md and write_v299_config.py (`V299_COMMIT`) pin, so leave it and note it, or reword and update both. |
| D2 | low | The test_latcontrol / lateral_limits / vehicle_model pass counts in the commit message cannot be reproduced from any recorded interpreter. bin_decompile lacks the deps, and the fork `.venv` lacks pytest. | commit message; kit handoff | Record the exact interpreter and shim used, e.g. in the V299 handoff. The changed code is not in those modules. |
| D3 | low | The card.py publication is tested only by a source-string check (`test_card_publishes_the_controller_status`). No runtime test calls `Car.state_publish`. | test_angle_v299.py, TestAngleStatus | Optional: a runtime test with a stub PubMaster, or accept. The field is telemetry, not control. |
| D4 | low | No committed unit test covers `torque_bar.accord_eps_bar` or the mici feed. The sign and gating were verified here only. | selfdrive/ui/onroad/starpilot/torque_bar.py | Add a small test using a capnp CarParams reader. |
| D5 | info | The fixture holds only 8 latActive rising edges, the limiter-restart path. Identity is proven by construction and by my 196-edge synthetic replay, but not in the committed tests. | test_angle_v299.py (a) | Optional: add a synthetic toggling stimulus to the identity test. |
| D6 | info | Status bit 4 flags only the rate/jerk step. Bit 16 flags the error clip. Neither the lateral-accel max-angle clamp (`get_max_angle_vm`) nor the +-400 deg clip sets a bit, so an accel-clamped setpoint reads as unbound. This matches the spec as written. | carcontroller.py `_update_angle` | Document it, or add a bit if drive 2 needs to see it. |
| D7 | info | `build_v299_fork_fixture.py` writes straight into the fork tree with no overwrite guard. Re-running it rewrites a committed file. The output is reproducible, so the content is the same. | kit v299_design/fork/build_v299_fork_fixture.py | Open with an "x"-mode or hash-check guard. |

## Scripts (scratchpad, all < 30 s)
- `C:/Users/dudei/AppData/Local/Temp/claude/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/aa635277-343b-4774-be4a-fa2982d3b91e/scratchpad/rv_idt/`: `boot.py`, `run_tests.py`, `worker.py`, `compare.py`, `flown2.py`, `rebuild_fixture.py`, `uibar.py`.
- The old and new trees are in `old/` and `new/`, from `git archive`.
