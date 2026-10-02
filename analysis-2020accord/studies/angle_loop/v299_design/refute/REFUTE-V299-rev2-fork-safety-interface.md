# RE-REFUTE V299 rev 2: fork / safety / interface lens (pre-registration, written BEFORE any check)

## What a FAIL looks like (written first, 2026-10-02)
FAIL ("do not build") if ANY of the following holds:
- R0: a defect D1–D14 from `REFUTE-V299-fork-safety-interface.md` is only re-worded, not resolved: rev 2's fix, applied to fork
  Dom `2712e1336` as written, does not remove the failure the defect named.
- P1: a reachable state in which a real hand at or above Honda's `steeringPressed` level does NOT get the firmware freeze or fade
  acting, or in which the lane torque keeps rising against that hand. With no fork override, this now rests entirely on the
  firmware. Also: the removal of the override leaves a fork state that holds a stale setpoint across a hand release, or across a
  latActive edge, in a way that can drive the wheel past the clip.
- P2: an unbounded setpoint or a fork exception path: a param read, the T <= 0 guard, a NaN, a decode of 0x1AB that raises, or
  a `cp.vl_raw` lookup that does not exist in this parser.
- P3: a fork change that cannot work as written on Dom `2712e1336`: a wrong API (`vl_raw`, `message_states[0x1AB]`,
  `ts_nanos`), a capnp slot that is already taken, a parser change that still drops canValid, a prefix rule that rejects
  A16A/A16B or accepts A160, or a toggle config that cannot express config A.
- P4: a mici / UI consumer of a field the fork now writes (`steeringTorqueEps`, `accordAngleStatus`, the bar,
  `_torque_filter`) that shows a false or inverted indication, or a learner, alert or persisted param that reads one of them
  as physical.
- P5: a rwd re-header plan that, as written, leaves a revert unflashable, or that accepts a target the car does not report.
PASS_WITH_DEFECTS if every surviving defect has a bounded fix that does not change the loop. PASS only if nothing survives.
Where I am uncertain, I default to refuted.

---

# RESULT: verdict **PASS_WITH_DEFECTS**. No P1/P2 state found. Two MED defects (a revert criterion and the differential test) and one false EVIDENCE claim must be fixed in the build round.

Author: RE-REFUTER (fork-safety-interface) subagent, 2026-10-02. Target: `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md`.

**What I worked from:**
- Fork Dom `2712e1336`, with HEAD verified by `git rev-parse`; nothing was edited.
- V298 image `177abf04`, read with Python.
- r79 caches (`_scratch/cache/v280/r79_fork.npz`, `r79_a1f5d2_al.npz`) and r79 segment-0 rlog bytes.

**Classifier interruptions:** 0.
**Process note:** one inline command stalled on a stdin heredoc and was stopped (TaskStop) after the 120 s tool timeout. It computed nothing, and every script below runs in under 1 s.

**Pre-registered criteria, as they stand:**
- **P1:** no hit. At or above Honda's level the freeze immediate is `cd 04` = 1229 at 0xC4C64. The V298 bytes there read `20 6e 00 02`, i.e. 512, re-read. Raw 1229 → wire 1200 and raw 1230 → wire 1201, by `(raw*125)>>7`, so the freeze edge is exactly `steeringPressed` (EVIDENCE).
  - The limiter cannot hold a stale setpoint across a latActive edge. `lateral.py apply_steer_angle_limits_vm` returns the wheel angle when `lat_active` is false (EVIDENCE).
  - During a hold, the stored setpoint is re-clipped to wheel ± `error_max` every frame (EVIDENCE: `_update_angle`).
- **P2:** no hit.
  - The takeover ramp was removed, so its T <= 0 division is gone.
  - Param reads are guarded (F11).
  - The 0x1AB decode reads `vl_raw`, which exists and is a plain dict that never auto-adds a message (EVIDENCE: `opendbc/can/parser.py`).
- **P3:** two near misses, both fail-safe: the F9 length rule against padded fwVersions (N3), and the existing test file (N4).
- **P4:** no false UI indication found (§2 row 6).
- **P5:** one gap, the V294 revert (N5).
- **R0:** the colleague's D1–D14 are all resolved or moot. D3 and D4 are resolved in effect, but each leaves a residue: escalation 1, and N2.

## 1. The colleague's defects, one by one

| id | rev 2's resolution | verified | status |
|---|---|---|---|
| D1 | bits → `starpilotCarState.accordAngleStatus @31`; the mici cue is fed from the bar | **`@31` is free** (`cereal/custom.capnp StarPilotCarState` ends at `pulseAndGlide @30`; that is the only definition of the struct, and opendbc's carstate imports `from cereal import custom`). `starpilot_card.update` returns the same builder, so card can set the field. The field is logged: r79 holds 121,383 `starpilotCarState` frames. The mici `ModelRenderer._render` cue is fed from the bar. The param-off path stays `-actuatorsOutput.torque`, which on r79 is **0 on all 121,383 frames** (EVIDENCE), so it really is "0 as today". `actuatorsOutput.torque` is untouched. | **RESOLVED** |
| D2 | V299 lists A16A + A16B; the V298 and V295 reverts are re-headered with A16B and read back | The plan mirrors `build_v298_tva.py header_add_a16a` / `parse_x31` readback. **However, V298's build also re-headered the V294 revert, and rev 2 drops it** (N5). | RESOLVED (N5 LOW) |
| D3 | S2 rows 550–2500 words, F7b, a ~25 m/s co-steer item | All three exist (§3.5, §7, §6 item 3). **The exposure itself grew and is now operator escalation 1** (§2 row 7). | RESOLVED as specified; underlying exposure escalated |
| D4 | `ignore_counter`; checksum verified in carstate; bar 0 after 100 ms | `MessageState.ignore_counter` exists and gates `update_counter` (EVIDENCE). With `nan`, `ignore_alive` is set. So 0x1AB cannot touch `can_valid`. **But the rationale is false:** the DBC *does* declare a CHECKSUM (N2). | RESOLVED in effect (N2) |
| D5 | takeover removed (ruling i) | F4/F5 are gone from the change table, so no T and no division | MOOT (resolved by removal) |
| D6 | the exact band is stated; the change is a later dose | `ANGLE_ERROR_MAX_BP/V` (values.py) give 13.67° at 14 m/s for s = 1.0 | RESOLVED |
| D7 | family + letter; card says pull Dom before flashing | New fork + A16B: the existing `carstate.py` fault block raises a permanent fault with the switch OFF and runs angle mode with it ON (EVIDENCE). An old fork cannot be fixed by code, so the card order is the only cover. **Padding caveat:** N3. | RESOLVED (N3) |
| D8 | F11 guarded reads | try/except, isfinite, clamp; the UI param read falls back to false | RESOLVED |
| D9 | clamps [60, 250] and [1.0, 1.6] | as specified | RESOLVED |
| D10 | the three keys go in `SAFE_MODE_MANAGED_KEYS` | the list currently holds every other `Accord*` key | RESOLVED |
| D11 | takeover removed | — | MOOT |
| D12 | the deletion's only gate is a reflash | Now also needs a **fork code rollback**, because REVERT = V298 + Dom `2712e1336` (rev 2 §10.7 says so) | RESOLVED as declared |
| D13 | G4 removed | — | MOOT |
| D14 | raw 1229 ↔ wire 1200 | Arithmetic re-done (above) | RESOLVED |

## 2. Rev 2 itself, checked against the source

| # | claim | method | result |
|---|---|---|---|
| 1 | "0x1AB has COUNTER but no CHECKSUM" (§2.1, labelled EVIDENCE) | Read `honda_accord_2017_can_ext_generated.dbc` (the pt DBC per `values.py radar_dbc_dict`) **and** the generator source `dbc/generator/honda/_honda_common.dbc` | **FALSE. Both files declare `SG_ CHECKSUM : 19|4@0+` on `BO_ 427`.** `can/dbc.py get_checksum_state` attaches `honda_checksum` to any signal named CHECKSUM in a `honda_*` DBC. So the parser **does** check the checksum, and a bad frame is dropped without updating `vl_raw`. Rev 2's carstate re-check is therefore dead code: it re-tests frames the parser already passed, so bit 8 can only ever mean "stale". The colleague's "keep the checksum" was right; rev 2's "the fork refuter… has no parser checksum to keep" is wrong (N2). |
| 2 | F12(a): "identical raw on every frame **outside** V298's O1 episodes"; (b) ≥ 99.99 % | `rr2_f12_differential.py` (0.82 s). A recursive replay of V298's `_update_angle` reproduces the published `co_ang` raw on **100.000 %** of 66,767 latActive frames. The same replay without the override (rev 2 F3) is compared to it. | **FALSE.** **3,245 frames outside O1 (5.72 %) differ**, and (b)-style agreement is **94.27 %**. **Cause (EVIDENCE, code):** V298 restarts the limiter from the wheel on each O1 release; rev 2 continues from its clipped last output. Every one of r79's 415 releases is followed by a divergence window: p50 6, p90 13, max 167 frames. The test as specified cannot pass, so it will be weakened ad hoc or will block the build. Rev 2's header sentence "the override removal changes only frames inside V298's O1 episodes" is false for the same reason (N1). |
| 3 | F3 "after a hand release, \|θ − θsp\| > 8° within 1.5 s at ≥ 8 m/s → revert"; predicted 8.0° at the bar | Same script, open loop on r79's hands. With no override the setpoint stays clipped away from the wheel through the hold, so the gap at the release frame **is** F3's quantity at t = 0. | At V298's 415 release frames, rev 2's \|θsp − θ\| is p50 9.3°, p90 16.7°, max 17.0° (V298: p50 1.2°, max 2.8°). **Of 155 releases at ≥ 8 m/s, 38 have a gap > 8° at the release frame itself; V298 has 0.** The clip at 8–11.75 m/s is 15.5–19.5°, so the gap can exceed F3's bar by construction. F3 was written for a fork whose setpoint follows the hand; under ruling (i) it measures the hold gap, not a lurch. It can fire with no wheel motion at all. This is BELIEF for the closed loop: under V299 the lane would pull the wheel during the hold and shrink the gap (N6). |
| 4 | F9 `is_angle_fw(v) = v.startswith(FAMILY) and len(v) == 14 and 65 <= v[13] <= 90` | Raw scan of r79 seg 0 (0.07 s) | The car reports **`b'39990-TVA,A16A\x00\x00'` (16 bytes)**, and A160 appears only in the earlier, cached CarParams. Today's `interface.py` strips at the call site (`fw.fwVersion.rstrip(b"\x00") == …`). Rev 2's predicate, applied to the raw fwVersion, gives len 16 → false → `EPS_ANGLE_LOOP_FW_MISSING` → permanent fault with the switch ON. That fails safe but loses the drive. F12(c) tests only bare 14-byte strings, so it cannot catch this (N3). Once stripped: A16A/A16B true, A160 ('0' = 48) false, A150 false. No stock `,A16<letter>` exists in `fingerprints.py` (BELIEF that Honda never ships one). |
| 5 | F3 deletes `angle_override` / `ANGLE_OVERRIDE_*` | grep of the fork | **`opendbc/car/honda/tests/test_honda_accord_angle_loop.py`** asserts O1 behaviour and the state census `assigned == {"angle_override", "apply_angle_last"}`, and imports `HONDA_ACCORD_EPS_ANGLE_LOOP_FW`. Rev 2's F12 adds a new test file but never says this one must be rewritten. CI catches it, so the risk is mechanical (N4). |
| 6 | mici consumers of every field written | Full-tree grep of `steeringTorqueEps`; read `mici/onroad/model_renderer.py`, `mici/onroad/hud_renderer.py`, `onroad/starpilot/torque_bar.py` | `steeringTorqueEps` has **no consumer outside car ports** (Toyota/Chrysler/etc. read their own), so it is safe. **The mici HUD imports the SAME `TorqueBar`** (`hud_renderer.py`), so F7 lands on the bar the operator sees. F7 and F7m feed one value to both widgets, as upstream torque mode does with `-actuatorsOutput.torque`. Orientation: sign(tap) agrees with today's drawn angle-mode bar on 85.4 % of 31,987 frames (re-ran `rev_bar_sign.py`, 0.04 s). The cue turns orange at > 60 % of rail: a true reading, not a status bit. The helper has no latActive gate, but the tap is lane-only: \|tap\| p99 = 0 when not latActive, including 3,804 frames with a hand > 1200 wire (EVIDENCE, 0.05 s). |
| 7 | the override yield in every state (ruling i) | code + r79 | At or above `steeringPressed`: the firmware freeze and fade act (P1 clean). **Moderate band (600 < \|wire\| ≤ 1200, not pressed), measured on r79 (`rr2_moderate_band_r79.py`, 0.35 s):** 22.1 s of 662 s latActive, in 538 runs (only 4 longer than 0.3 s). On **67 %** of those frames the rev 2 setpoint sits more than 1° on the side opposite the hand, \|err\| p50 13.9°, p90 17.0°, i.e. at the clip. Driver-torque sign is confirmed + = left (86.2 % agreement with wheel rate when not engaged). So escalation 1 is not hypothetical: this operator's hands enter the band about 50 times a minute. Most entries are short, which is why F7b's 0.3 s clause is met by only 2 opposing runs open loop. BELIEF: closed loop, more resistance may lengthen the holds. |
| 8 | F1 per-instance `dataclasses.replace` | `lateral.py` | `AngleSteeringLimits` is a `@dataclass`, so this works. The default 1.2 deg/frame equals V298's `MAX_ANGLE_RATE`. |
| 9 | config A is expressible as a toggle config | `the_galaxy.py _build_default_params` (from `_params_raw.all_keys()`), `_get_toggle_backup_keys`, `_coerce_toggle_restore_value` | **Yes.** The three keys reach the allow-list via params_keys.h alone. The BOOL coercion accepts `true`, and the FLOAT path rejects non-finite values. MaxRate 120 and ClipScale 1.0 equal their defaults, so config A's only live entry is `AccordAngleBarFromEps true`. **REVERT is not a toggle config:** it needs the `2712e1336` fork, as declared. |
| 10 | rwd re-header plan | `build_v298_tva.py` | Sound and mirrors V298: payload `encs` equality, '/' readback, original untouched. V294 is omitted (N5). |
| 11 | drive-read instrument for `accordAngleStatus` | `v298_flight/r79_extract_fork.py build_schema` | The extractor copies the fork's **live working tree** cereal, restamped by content hash, so it follows whatever commit is checked out. The kit's own `rlog-tools/cereal/custom.capnp` reuses the **same struct id `0xf35cc4560bbf6ec2` for `LongitudinalPlanSP`**, so any decoder on the kit schema reads this message as garbage. The extractor is also hard-wired to r79 and does not extract the new field. If the field is not added, F1's "accordAngleStatus absent" fires falsely (N7, INFO). |

## 3. New defects (ranked)

| id | what | where | sev | fix |
|---|---|---|---|---|
| **N1** | F12(a)/(b) expect V298-identical 0xE4 outside O1. On r79 they differ on 5.72 % of those frames ((b) 94.27 %), because V298 restarts the limiter from the wheel at each release and rev 2 does not. The page's sentence "changes only frames inside V298's O1 episodes" is false. | rev 2 §2 header, F12(a)(b) | **MED** | Make the differential a true identity: run the vendored `2712e1336` `_update_angle` with `ANGLE_OVERRIDE_ON = OFF = inf` (O1 never fires, so no release restarts) and require **identical raw on 100 % of frames**. Keep (b) only on frames outside O1 **and** outside the post-release convergence window (until the two agree). Fix the header sentence. |
| **N6** | F3's \|θ − θsp\| > 8° measures the no-override hold gap, which is up to the clip (15.5–19.5° at 8–11.75 m/s). Open loop on r79, 38 of 155 releases at ≥ 8 m/s start above 8° (V298: 0). That is a pre-registered **revert** criterion that can fire with no wheel motion, giving a false revert or a criterion everyone learns to ignore. | rev 2 §7 F3, §3.5 | **MED** | Under ruling (i), redefine F3 on wheel motion: wheel excursion **past** θsp after release (overshoot), or peak \|θ̇\| / wheel travel within 1.5 s beyond the pre-release gap. Re-predict it from the S2 hands rows. Keep the "operator reports a lurch" clause. |
| **N2** | §2.1 claims (EVIDENCE) that the 0x1AB DBC has no CHECKSUM and that the colleague was wrong. Both the generated pt DBC and its generator source declare `CHECKSUM 19|4`, so the parser verifies `honda_checksum` and drops bad frames. The carstate raw re-check is dead code, so bit 8's "bad" meaning cannot fire. | rev 2 §2.1, F6, F8 bit 8 | LOW-MED (record; no safety effect) | Correct §2.1: parser checksum active (`get_checksum_state` honda_*), counter ignored. Drop the carstate re-check, or keep it labelled as redundant. Bit 8 = stale only. |
| **N3** | F9's `len(v) == 14` fails on the padded fwVersion the car actually sends (`…A16A\x00\x00`, 16 B). If applied without the existing call-site `rstrip`, angle FW is never detected, giving a permanent fault with the switch ON. That fails safe but loses the drive. F12(c) tests only bare strings. | rev 2 F9, F12(c); `interface.py _get_params` | LOW | Strip inside `is_angle_fw` (`v = v.rstrip(b"\x00")`). Add the r79 literal `b'39990-TVA,A16A\x00\x00'` and `b'39990-TVA,A16B\x00\x00'` (true), and `b'39990-TVA,A160\x00\x00'` (false), to F12(c). |
| **N4** | The existing `tests/test_honda_accord_angle_loop.py` asserts O1, the lead, and the state census `{"angle_override","apply_angle_last"}`, and it imports `HONDA_ACCORD_EPS_ANGLE_LOOP_FW`. Rev 2 does not mention it. | fork tests | LOW | Add it to F12: delete the O1 tests, change the census to `{"apply_angle_last"}`, and repoint the FW import to the family helper (its padded fixture is the right shape). |
| **N5** | The V294 revert rwd (re-headered for A16A by V298's build) is not re-headered for A16B, so after V299 it cannot be flashed. | rev 2 §11.2 | LOW | Add V294 to §11.2 (same `header_add`), or declare V294 retired as a revert target. |
| **N7** | The drive-read extractor does not yet extract `accordAngleStatus`. It copies the schema from the fork's live tree, while the kit's schema collides on the struct id. | `v298_flight/r79_extract_fork.py`, rev 2 §6 item 2 | INFO | Before the drive read: pin `FORK_COMMIT` to the V299 commit and check it out (or copy the schema from `git show`), add the field, and assert it is present on ≥ 99 % of frames before scoring F1. |
| N8 | Staleness is clocked against 0x18F's timestamp. If 0x18F itself stops, the bar freezes at its last value (canValid then drops for 0x18F, so lateral ends). | F6 | INFO | Clock against `cp.last_nonempty_nanos`, or zero the bar when `not CS.canValid`. |

## 4. Not a defect of this lens, but decision-bearing (relayed, verified)

Escalation 1 (the moderate band) is real driving, not an edge case (§2 row 7, EVIDENCE for exposure, BELIEF for the closed-loop torque).

The ruling's stated consequence ("<= ~20 % of the rail at low speed" with a firm hand) holds only for a firm hand, as rev 2 itself says. In 550–1500 words, rev 2's own sim gives 37–60 % of rail opposing and F7b firing. On r79 the operator's hand was in that band 22 s per 11 min, with the setpoint at the clip on the opposite side 67 % of that time.

## 5. What would flip this to PASS
- Fix N1 and N6: both are wording and test changes; neither touches the loop.
- Correct N2 on the page.
- Apply N3–N5 mechanically in the build round.
- The operator decides escalation 1.

## A. Scripts (all under 1 s; `v299_design/refute/`)

| script | wall | result |
|---|---|---|
| `rr2_f12_differential.py` | 0.82 s | V298 replay == published raw 100.000 %; outside-O1 mismatch 5.72 %; release gap p50 9.3° / max 17.0°; F3 38/155 at ≥ 8 m/s |
| `rr2_moderate_band_r79.py` | 0.35 s | band 22.1 s / 538 runs; opposing at the clip 67 %, p50 13.9° |
| `rev_bar_sign.py` (re-run) | 0.04 s | sign(tap) vs today's bar 0.854 |
| inline: r79 seg-0 rlog raw scan | 0.07 s | EPS fwVersion `39990-TVA,A16A\x00\x00` |
| inline: V298 image 0xC4C62, 0x1310D | < 0.1 s | `20 6e 00 02` (512); `0x41` 'A' |
| inline: tap when not latActive; co_tq; driver-torque sign | < 0.1 s each | p99 0; co_tq all 0; + = left 0.862 |
