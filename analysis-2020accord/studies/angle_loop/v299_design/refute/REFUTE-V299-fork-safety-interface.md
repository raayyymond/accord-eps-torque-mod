# REFUTE V299 — fork / safety / interface lens (pre-registration, written BEFORE any check)

## What a FAIL looks like (written first, 2026-10-02)
FAIL ("do not build") if ANY of:
- P1 a reachable state (engaged, AOL, blinker, request drop, takeover ramp, mis-deploy) in which a real hand at or above the
  Honda stock steeringPressed level (STEER_THRESHOLD, 0x18F STEER_TORQUE_SENSOR) does NOT make the fork setpoint yield AND/OR the
  firmware fade/freeze act, or the lane torque keeps rising against that hand;
- P2 a reachable state in which the sent setpoint can run away (move without bound or against the wheel) — e.g. a param parse
  failure, a clamp that is not applied, a timer that does not reset, a ramp that starts from a stale value;
- P3 a fork change that, as written, cannot work on Dom 2712e1336 (wrong function, missing plumbing, parser that faults,
  a CAN message that drops canValid / makes the panda block 0xE4);
- P4 the firmware hand threshold and the fork threshold are not in the same unit (claim "1229 = 1200 raw x 1.024" wrong-way);
- P5 a new value written into a field another consumer reads as physical (actuatorsOutput.torque, steeringTorqueEps) that
  corrupts a learner / alert / persisted param;
- P6 a feature deleted rather than gated with no measured replacement.
PASS_WITH_DEFECTS if every defect has a bounded fix that does not change the loop; PASS only if nothing above survives.
Default to refuted where uncertain.

---

# RESULT — verdict **FAIL as written** (do not build the fork commit until D1 and D4 are fixed); no override or runaway state found

Author: REFUTER (fork-safety-interface) subagent, 2026-10-02. Target: `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-2026-10-02.md`.
Fork read at Dom `2712e1336` (HEAD verified with `git rev-parse`; nothing edited). Ghidra read-only (dry-run listing on
`ADVIG_V298_177abf04.bin`). Python = `bin_decompile`. Classifier interruptions: 0.

**Which pre-registered criteria fired:**
- **P5: FIRED (EVIDENCE).** F8 writes a status bit-field (1..119) into `carOutput.actuatorsOutput.torque`. The operator's device is a
  **comma four (`"deviceType": "mici"`, found by a raw scan of route 79 segment 0's initData)**. In the fork, `selfdrive/ui/mici/onroad/model_renderer.py`
  `ModelRenderer._render` feeds `-actuatorsOutput.torque` into `_torque_filter` **unconditionally**, and `_get_ll_color` turns an ego
  lane line **orange ("high torque") when |torque| > 0.6**. Every bit that is set drives that value to −1…−119, so the right-hand ego lane
  line turns orange whenever O1, takeover, rate/jerk-bound, clip-bound or debounce is set. That is a false indicator, on exactly the
  axis of note 3. Rate/jerk-bound alone would have been set on **≈ 9.4 % of route 79's latActive frames (62 s)**. This share is BELIEF:
  my approximation of the VM jerk limit leaves out the slip term (script §A).
- **P6: FIRED AS WORDED (BELIEF-level replacement).** The firmware deletes the opposing-hand freeze instead of gating it. The
  replacement (the asymmetric bound) is supported by simulation only, so it is not measured. The only "gate" left is a reflash to
  V298, and that reflash needs D2.
- **P4: clean (EVIDENCE).** The firmware hand threshold and the fork threshold are in the same unit (row 1).
- **P1, P2: no hit.** No state was found in which a hand at or above Honda's level fails to override, and no unbounded setpoint was found
  (§2, §3). P3: D4 (the counter check can drop canValid) and D5 (a division by zero at the default value, as the change is literally
  specified) come close, but neither stops the change from working on r79's traffic.

All of the fixes are small and none touches the loop. So this result means "do not build AS WRITTEN". It does not mean "do not pursue".

## 1. What I checked, and the result

| # | claim in the synthesis | method | result |
|---|---|---|---|
| 1 | firmware freeze `1229` ≡ Honda's steeringPressed (wire > 1200) | Ghidra dry-run 0x7FE84–0x7FECF: `gp-0x4f68` is written ONLY at 0x7FECA (`st.h r14`), as **\|gp-0x4f60\| saturated to 0xFFFF** (behind a gp-0x448c shadow-copy check). Python LE scan of the V298 image for 4-byte gp-relative forms on −0x4f68: 37 loads, **1 store**. Memory note `accord-wire-torque-is-raw-times-1024`: wire = −((raw·125)>>7) | **EVIDENCE: the thresholds line up.** raw > 1229 ⇔ raw ≥ 1230 ⇔ wire ≥ 1201 ⇔ `steeringPressed` (`abs(STEER_TORQUE_SENSOR) > STEER_THRESHOLD.get(HONDA_ACCORD, 1200)` in `carstate.py CarState.update`). The page's wording "1229 = 1200 **raw** × 1.024" has raw and wire swapped: it is 1200 **wire** ↔ 1229 raw. The number itself is right. §2 has the same slip ("G4 fires … > 1200 raw"; it is wire). |
| 2 | the override yields to a real hand in every state | read `carcontroller.py CarController._update_angle` and `_angle_hold_allowed`, `lateral.py apply_steer_angle_limits_vm`, `hondacan.py create_steering_control`, and panda `safety/modes/honda.h honda_tx_hook` | **No state fails to yield at or above Honda's level** (§2 table). There is new, untested exposure in the raw 513–1229 band (D3). |
| 3 | parsing 0x1AB is safe for canValid | read `opendbc/can/parser.py` (`_add_message`, `MessageState.parse` / `update_counter`, `CANParser.can_valid`); re-ran `D1-firmware-minimal/d1_427_check.py` (5.9 s) | Listing the message with `nan` only sets `ignore_alive`. **The COUNTER is still checked**: once `counter_fail` reaches `MAX_BAD_COUNTER` (5), `can_valid` drops for the WHOLE pt parser, so canValid drops and lateral disengages. Route 79: 61,113 frames on bus 1 (= `CanBus.pt` for HONDA_ACCORD, per `hondacan.py CanBus`), 49.9 Hz, checksum 100.000 %, counter step 99.997 %, CONFIG_VALID 100 %. The trip rate is low, but it is a new disengage path created by a display-only signal (D4). A checksum failure only drops that frame (the value goes stale). Because of `ignore_alive`, **a dead 0x1AB freezes the bar at its last value** (D4). |
| 4 | the bar's sign matches today's direction | re-ran `judges/jg_bar_sign_check.py` (0.04 s), plus my own hold check (0.05 s): sign(tap) equals sign(cs_ang, + = left) on **0.0 %** of 3,170 hands-off hold frames | **EVIDENCE: tap + = right.** So `steeringTorqueEps = −8·s10` is + = left (the carState convention), and the bar +s10/307.6 agrees with today's drawing on 0.854 of frames. F6/F7 as specified have the right sign. A full-tree grep finds no consumer of `carState.steeringTorqueEps` outside the car ports, so populating it is safe. |
| 5 | the F8 bit-field in `actuatorsOutput.torque` sits in a "free" field | full-tree grep of `actuatorsOutput` | Consumers: `selfdrive/ui/mici/onroad/model_renderer.py` (**live on this device → D1**); `torque_bar.py TorqueBar._update_state` (torque branch only, not reached in angle mode); `selfdrive/locationd/torqued.py TorqueEstimator.handle_log` (points with \|steer\| ≥ 1 fall outside `STEER_BUCKET_BOUNDS` ±0.5 and are dropped, `use_params` is false in angle mode, and the cache key includes `lateralTuning.which()`, so **safe, EVIDENCE**); `controlsd.py` (`steer_limited_by_safety` reads torque only in the non-angle branch, so safe); `the_galaxy/flm_workspace.py` (torqueState only, so safe); offline tools. |
| 6 | toggle configs can express A and B | read `the_galaxy.py` `_get_toggle_backup_keys`, `_build_default_params`, `_coerce_toggle_restore_value`; `fork-config/write_v298_config.py` | **They can.** The allow-list is every PERSISTENT key in `params_keys.h` that has a default, so F10 is enough, and FLOAT restore rejects non-finite values. Gaps: `starpilot/common/safe_mode.py SAFE_MODE_MANAGED_KEYS` lists every other `Accord*` key but not the seven new ones (D10). The params are read only in `CarController.__init__`, so B needs an openpilot restart; the drive card already says so, and that makes initData consistent and the drive attributable. |
| 7 | features are gated, not deleted | page §1, §2, §9 | Fork: all seven terms are param-gated, with defaults = V298 (OK). Firmware: the opposing-hand freeze is **deleted**, and its job is handed to the asymmetric bound on simulation evidence only (P6, D12). |
| 8 | a mis-deploy fails safe | read `interface.py CarInterface._get_params` (`eps_angle_loop_fw` exact-string match, `accord_eps_angle_loop_enabled`), the fault block in `carstate.py`, and `create_steering_control` (torque frames carry arm 0) | New fork on A16A: safe (as the page says). Old fork on A16B **with the switch ON**: permanent fault (page correct). Old fork on A16B **with the switch OFF**: not detected, so the fork runs torque mode and sends arm 0, and the V299 camera gate zeroes the lane. **openpilot shows engaged, the EPS does nothing, and no fault is raised** (D7). |
| 9 | panda path | `honda.h honda_tx_hook` "STEER: safety check" | The panda bounds nothing on 0xE4 except "bytes 0-1 must be zero while !(aol_allowed ∥ controls_allowed)". V299 changes neither that predicate nor the hold frame, so this path is unchanged. **Every authority bound in config B is fork-only** (rate 250, clip ×1.6). The rail (2461 T) and the firmware fade are the only backstops outside the fork; page §5 states this. |
| 10 | revert path | `builds/v108_plus/build_v298_tva.py` docstring and `header_add_a16a` | V298 needed its own rwd '/' header, and the V295/V294 revert rwds had to be re-headered to list A16A. **V299 changes F181 to A16B, and the page never mentions re-headering.** Without it the operator cannot flash back to V298 (the page's REVERT) or to V295 (D2). |
| 11 | lag budget | `_update_angle` and page §2/§3 | Moderate hand (wire 600–1200): setpoint yield moves from about 10–20 ms (V298: 600 instant, 0.06 s lead) to **at least 80 ms plus the i−1 pairing**. In that band there is no firmware freeze (< 1229 raw) and no fade (< 1216 raw) either (D3). Hard hand (> 1200): yields in the same frame as `steeringPressed`; lead 0 adds the declared +17 % drag force (M5). |

## 2. Override yield, state by state (the binding rule)

| state | hand ≥ 1201 wire (Honda pressed) | hand 601–1200 wire | hand 501–600 wire | evidence |
|---|---|---|---|---|
| engaged / AOL, latActive | fork O1 in the same frame (sp := wheel, lead 0); firmware I frozen within 1 tick; fade ×0.85 → ×0.30 (record 0xE54FC, unchanged) | fork O1 after 8 frames (80 ms); **firmware: no freeze, no fade**; I winds within its bound (toward centre ≤ B; outward up to 16\|θ\|+B, with the 4096 cap only at ≤ 12.5 m/s) | O1 **never** fires (G4 needs > 600 for 80 ms); firmware unfrozen; the system pushes P (≤ clip) + I against the hand until the hand rises past 600 or 1200 | code; page §1.2 |
| blinker with lateral paused (LaneCenteringPauseOnSignal / speed gate) | latActive false ⇒ request 0 ⇒ A2/B2 skip the PID, Honda's epilogue zeroes I, 0.5 s ramp-out; fork sends the hold frame | same | same | `_update_angle` (`angle_override = False` when not latActive); page §5 |
| lane change (blinker, latActive) | a nudge > 1200 triggers O1 at once (the same level as `steeringPressed` for laneChange) | O1 after 80 ms | no O1 | code |
| request drop | as the blinker row | as the blinker row | as the blinker row | bytes unchanged |
| takeover ramp (F5, 0.4 s after engage / release) | O1 re-entry overrides the ramp (sp := wheel) | the ramp's clip starts at 0 ⇒ sp = wheel, P ≈ 0 for the first frames | same | page §2 F5 |
| fork dead (card crash) | last 0xE4 value held 510 ms → sentinel → decay (V298 H-tmo); the fade still acts | same | same | C3-rev2 §H-tmo |

**Verdict on the rule.** The driver can ALWAYS override at Honda's own threshold (EVIDENCE: rows 1–2, the fade/freeze bytes are
unchanged, and the G4 hard path is the same test as `steeringPressed`).

What V299 newly creates is a **moderate-hand band (wire 501–1200 ≈ raw 513–1229)**. In that band the firmware does not yield, and the
fork does not yield for at least 80 ms (and never below wire 600). V298 yielded at 512 raw in the firmware and at 600 wire in the fork.
The design's sims test this band only at **400 words (LH)** and **1500 words (OV)**, with nothing in between. F7 is keyed on
`steeringPressed`, so it cannot see this band (D3).

## 3. Setpoint runaway search

| candidate | result |
|---|---|
| param parse (`Params.get_float`) | A non-numeric value falls back to the default (safe), and Galaxy restore rejects non-finite floats. **However:** a key missing from a params library that was not rebuilt raises `UnknownKeyName`. The switch read in `interface.py` guards against that; the spec does not say the seven new reads do. Also `np.clip` passes NaN through, so "clamped [60, 450]" is not NaN-proof. A NaN that reaches `math.floor(-10·apply_angle + 0.5)` raises inside `card`; 0xE4 then stops, giving a 510 ms hold and a decay (D8). |
| F5 timer `since/T` with **T = 0 (the V298 default)** | As literally specified, this divides by zero on the first release or engage edge under the REVERT config, raising an exception in `card` (D5). It needs `scale = 1 if T <= 0 else min(1, since/T)`. |
| G4 counter | resets on ≤ 600 or !latActive; OFF at ≤ 500. No stuck-ON or stuck-OFF state found. |
| F1/F2 clamps | They allow up to 450 deg/s and clip ×2 (P cap ≈ 52 × 34° ⇒ ~72 % of rail at 3.1 m/s, BELIEF from the stiffness list in `values.py`). That is **beyond the envelope the page evaluated (250, ×1.6)**, and a config typo would be accepted silently (D9). |
| clip scale "≤ 11.75 m/s knots only" | `np.interp` carries the ×1.6 into **11.75–17.5 m/s**: at 14 m/s the clip is 19.9° vs V298's 13.7° (×1.45). The page says the 17.5/26.9 m/s knots are "unchanged", which is true only at the knots themselves (D6). |
| plan glitch | Bounded by the rate limit (2.5°/frame up to about 6 m/s, the jerk limit above) and by the clip. Worst-case lane torque ≤ rail; driver yield as in §2. No runaway. |

## 4. Defects (ranked)

| id | what | where | sev | fix |
|---|---|---|---|---|
| **D1** | F8's bit-field in `actuatorsOutput.torque` turns the **mici** ego lane line orange ("high torque") whenever any bit is set: ≈ 9 % of engaged frames from rate/jerk-bound alone (BELIEF). It is a false indicator on note 3's axis; the device is mici (EVIDENCE). | page §2 F8; fork `selfdrive/ui/mici/onroad/model_renderer.py ModelRenderer._render` / `_get_ll_color` | **HIGH (pre-reg P5)** | Do not use `actuatorsOutput.torque`. Put the bits in a field nothing renders (a StarPilot custom-state field, or cloudlog). **Also**, in angle mode, feed the mici cue from the F7 bar value (or 0). Re-grep every `actuatorsOutput` consumer in the build round. |
| **D2** | F181 goes A16A → A16B with no rwd re-header plan. V299's rwd must list A16A (what the car reports now) and A16B, and the V298 / V295 revert rwds must be re-headered to list **A16B**. Otherwise the page's REVERT cannot be flashed. | page §1.1 0x1310D; §7 "revert" | **MED** | Add this to the build round exactly as `build_v298_tva.py header_add_a16a` did, and verify each revert rwd's '/' header by readback before the drive. |
| **D3** | New un-yielded moderate-hand band (wire 501–1200). There is no firmware freeze or fade there, and fork O1 fires only after 80 ms (never below 600). Config B raises the P reachable in that band to 61–63 % of rail at ≤ 8 m/s. Above 12.5 m/s the outward I bound has no cap: (\|θ\|<<6)+B ≈ 3170 S ≈ 500 T ≈ 21 % of rail at a 3° wheel (BELIEF, using the page's 0.16 T/S). The band is **unsimulated** (LH at 400 and OV at 1500 words only) and **unexercised** (the drive card's co-steer items are at 5/15 m/s, none at highway). **No FAIL criterion can see it**, because F7 keys on steeringPressed. | page §2 G4, §3.2 LH/OV, §6 card, §7 F3/F7 | **MED** | Run S2 LH/OV at hands of 550 / 800 / 1150 words, both directions, at 5/15/25 m/s. Add F7b: "\|wire\| > 600 for > 0.3 s while the tap is ≥ 40 % of rail and opposing". Either add a highway (≥ 22 m/s) light co-steer-and-release item to Part A, or declare highway N1 untested on the page. |
| **D4** | 0x1AB in the pt parser keeps the COUNTER check, so 5 net bad counters drop `canValid` for the whole pt bus and lateral disengages, for a display-only signal. With `ignore_alive`, a dead 0x1AB also freezes the bar at its last value. | page §2 F6; `opendbc/can/parser.py MessageState.update_counter`, `CANParser.can_valid` | **MED** | Set `pt_parser.message_states[0x1AB].ignore_counter = True`, as is already done for 0x201. Keep the checksum check (bad frames are simply dropped). Zero the bar when `ts_nanos["STEER_MOTOR_TORQUE"]` is older than 100 ms. With that, the F8 criterion "any canValid drop" cannot be caused by this parser. |
| D5 | F5 `since/T` with the default T = 0 divides by zero, as specified | page §2 F5 | LOW-MED | Guard T ≤ 0 ⇒ scale 1. Add a unit test that the defaults replay r79's 0xE4 byte-identically (the page's own claim). |
| D6 | the clip ×1.6 carries into 11.75–17.5 m/s through `np.interp` (×1.45 at 14 m/s); the page says only ≤ 11.75 changes | page §2 F2 | LOW | Scale the knot values and state the interpolated band, or add a 12.5 m/s knot at V298's interpolated value. |
| D7 | old fork + switch OFF + A16B ⇒ silent torque mode: the camera gate zeroes the lane, and the car shows "engaged" with no steering and no fault | page §5 mis-deploy row; `interface.py` exact-string match | LOW-MED | Match the family `b"39990-TVA,A16"` for the FW_MISSING / permanent-fault logic instead of a tuple of exact strings, and order the drive card "pull Dom" BEFORE "flash V299". |
| D8 | the seven param reads: no `UnknownKeyName` guard is specified, and NaN passes `np.clip` | page §2 F1–F5, F10 | LOW | Read once in `__init__` with try/except UnknownKeyName falling back to the V298 default, plus a `math.isfinite` check. |
| D9 | the F1/F2 clamp ceilings (450 deg/s, ×2) exceed the evaluated envelope (250, ×1.6) | page §2 F1/F2 | LOW | Clamp to [60, 250] and [1, 1.6] until a higher dose is scored. |
| D10 | `SAFE_MODE_MANAGED_KEYS` (fork `starpilot/common/safe_mode.py`) lists every Accord* key except the seven new ones | page §2 F10 | LOW | Add them. This is moot while Safe Mode also clears AccordEpsAngleLoop, but it keeps the list honest. |
| D11 | Each false hard-path O1 (X3) now costs a 0.4 s takeover ramp (rate AND clip from 0), which is a self-inflicted stall-surge on a hands-off turn-in. X3 counts via-hard trips, but no criterion counts surges AFTER them. | page §2 F5, §7 X3, M6 | LOW-MED | Add "stall-surges within 0.5 s after a via-hard O1 release" to the drive read. Consider T = 0.2 s, or no clip ramp after via-hard releases shorter than 50 ms. |
| D12 | the opposing-hand freeze is deleted in firmware rather than gated; its replacement rests on simulation (BELIEF) | page §1.1 edit 2, §9 | LOW (P6 as worded) | Acceptable under "is it still necessary?", but say on the page that the only gate is a reflash to V298, which needs D2. |
| D13 | "116/116 steeringPressed episodes caught" follows by construction (G4 hard = 1200 = `STEER_THRESHOLD`), so it is a vacuous check | page §2, §4 | INFO | Label it as such. The informative number is the 600–1200 band (D3). |
| D14 | wording: "1229 = 1200 raw × 1.024" and "> 1200 raw" have wire and raw swapped | page §0 #1, §2 | INFO | Write "raw 1229 ↔ wire 1200 (wire = raw·125>>7)". |

## 5. What would flip this to PASS_WITH_DEFECTS
Fix D1 as specified (no bit-field in `actuatorsOutput.torque`; the mici cue fed from the bar, or zeroed in angle mode) and apply D4's
`ignore_counter`. D2, D3 and D5 must then be closed before flashing: D2 and D5 are mechanical, and D3 needs one sim row and one criterion.
D12 (P6) stands as a declared deletion whose replacement is checked on-car by F3/F5.

## A. Scripts run (all < 30 s)
| script | wall | result |
|---|---|---|
| `D1-firmware-minimal/d1_427_check.py` (re-run) | 5.9 s | as in §1 row 3 |
| `judges/jg_bar_sign_check.py` (re-run) | 0.04 s | 0.854 / +0.822 |
| inline: tap sign vs cs_ang / cs_tq on the r79 caches | 0.05 s | tap + = right (0.0 % agreement with + = left angle, n 3,170) |
| inline: Python LE scan of the V298 image for gp-relative ld/st of −0x4f68 / −0x4f60 | < 1 s | 1 writer of −0x4f68 (0x7FECA) |
| inline: raw scan of r79 segment 0's rlog for `deviceType` | 0.01 s | `"mici"` |
| inline: rate/jerk-bound frame share (VM jerk limit without the slip term) | 0.04 s | 9.4 % of 66,768 latActive frames (BELIEF) |
