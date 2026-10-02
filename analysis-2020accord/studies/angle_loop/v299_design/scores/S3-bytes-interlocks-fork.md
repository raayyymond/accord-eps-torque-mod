# S3: bytes, interlocks and fork scorer for the V299 judge panel (2026-10-02)

**Role.** S3 is the common scorer for bytes, interlocks and the fork, written by a SUBAGENT of the judge-panel orchestrator.

**Status.**
- Read-only. No image was written, and nothing was flashed or sent.
- The fork, the golden model, STATE, the lineage and git were not touched.
- Ghidra was used read-only (`disassemble_bytes dry_run`, `get_xrefs_to`).
- One automated safety-classifier interruption occurred mid-session. The work continued afterwards.

**Labels.** EVIDENCE means one of: image bytes, a Python scan, a Ghidra decode, the route-79 caches, or fork source at Dom `2712e1336` (read-only). BELIEF means anything inferred.

**Scripts** are in `scores/S3-bytes-interlocks-fork/`. Each writes its outputs to a `.txt` beside it.

| script | what | wall |
|---|---|---|
| `s3_bytes.py` | Checks every cited cell against the V298 image (sha `177abf04…`). Applies each candidate in memory. Recomputes CRCs with `zlib.crc32`, the `build_v298_tva` method; the control is V298's own 3 trailers, which reproduce. Then counts diffs. | **0.7 s** |
| `s3_gate1.py` | GATE-1 static census of gp-0x6a32 (D4b) and gp-0x6c44 (D5a). Uses V289's `gp_accesses` rules, vectorised over every even offset, plus scans for literals, movhi pairs and gp-base materialisations. | **0.1 s** |
| `s3_bar_sign.py` | Which bar formula keeps today's bar sign (route 79), and whether the fork fields D2 reuses are free | **0.1 s** |

---

## 0. Verdict table (one row per candidate)

**Units.**
- fw B = bytes that differ from V298, before the CRC trailer (+4 per CRC block); computed by `s3_bytes`.
- Cave = bytes in the cave at 0xC4C00.
- The fork diff size is an estimate (BELIEF) from each design's own list of edits, measured against the current files.

| candidate | fw B (pre / with CRC) | new caves | cave B | new RAM | fork diff (lines, est.) | toggle-config after code? | instrument on the wire | S3 verdict |
|---|---|---|---|---|---|---|---|---|
| **D1c** | 152 / 156 (153 / 157 with A16B) | 0 (V298's cave relinked) | 260 → 252 | 0 | ~12 (bar only) | no: bar keyed to the existing switch | rule-identity replay vs 0x1AB tap (18/18 windows on r79) + the bar | **PASS WITH DEFECTS** (bump to A16B; parser counter coupling) |
| D1a | 4 / 8 | 0 | 260 | 0 | ~12 | no | same | **NOT FOR FLIGHT** (designer's own N1 FAIL; bytes correct) |
| D1-a2 G0-1400 | 4 / 8 | 0 | 260 | 0 | 0 | — | P slope at ≤ 3.1 m/s | bytes PASS (separate dose) |
| **D2a** | 0 / 0 | 0 | 0 | 0 | ~60–70 | yes (params; `SteerDelay` is toggle-only) | `co_tq` bits, `cs_tqeps`, `ld_lat` (all free on r79, EVIDENCE) | **PASS WITH DEFECTS** (bar sign inverted; "never affects can_valid" is false; misses the freeze) |
| D2b | 0 / 0 | 0 | 0 | 0 | ~100–120 | yes | + `ang_output` (free) | PASS WITH DEFECTS (as D2a, larger diff) |
| **D3a** | 9 / 13 | 0 | 260 | 0 | ~50–60 | yes, once the params exist (K5 is code) | P-slope regression, rule replay, lead = −raw/10 − co_ang | **PASS WITH DEFECTS** (weakest override at Honda's level; A16B not coupled to K2; no bar) |
| D3b | 13 / 21 (2 CRC blocks) | 0 | 260 | 0 | ~55–65 | yes | as D3a | **DO NOT FLY**: soft-EME band 5120–~5900 not cleared (designer concurs) |
| **D4b** | 218 / 222 | 0 (V298's cave grown, relinked) | 260 → 312 | **1** (gp-0x6a32) | ~12–15 | **no** (code constants) | 0x14A b4.7 = sign(h) repoint + rule replay | **PASS WITH DEFECTS** (most firmware; no instant hard O1 path; not toggle-gated) |
| D4a | 14 / 18 (designer wrote 19) | 0 | 260 | 0 | ~12–15 | no | P slope at 10–20 m/s | PASS WITH DEFECTS (does not move the freeze) |
| D4b+GBS13 | ≈ 231 / 235 (BELIEF; not built) | 0 | 312 | 1 | ~12–15 | no | as D4b | as D4b |
| **D5b** | 5 / 9 | 0 | 260 | 0 | ~55–65 | yes (+ REVERT config) | rule replay (R² 0.927 vs 0.128) + limiter reconstruct | **PASS WITH DEFECTS + one PENDING DISQUALIFIER** (N1 outward hold; bar sign inverted) |
| D5a | ≈ 110 (BELIEF, not assembled) | 0 | 260 → ≈ 330 | 1 (gp-0x6c44) | ~45 | yes | washout replay (R² 0.926 vs 0.419) | NOT RECOMMENDED (GATE 1 owed; GATE 2 margin +0.4°) |

**Ranking on the operator's priority** (fewest firmware edits, fewest caves, smallest caves), firmware-moving candidates only:

D5b (5 B) < D3a (9 B) < D4a (14 B) < D1c (152 B, cave −8 B) < D4b (218 B, cave +52 B, +1 RAM) < D5a (≈ 110 B, cave +70 B, +1 RAM).

- **No candidate adds a new cave.** D1c, D4b and D5a rewrite and relink V298's own cave.
- D1a, D1-a2, D3a, D3b, D4a and D5b are immediate or cal edits inside V298's cave. They need no relink.

---

## 1. (a) Cited cells vs the V298 image (EVIDENCE: `s3_bytes`, Python LE)

**Every address the designers cite holds the bytes they claim.** All 21 checks are OK.

| addr | V298 bytes | cited by | meaning |
|---|---|---|---|
| 0xC4C62 | `20 6e 00 02` | D1, D2, D3, D5 | `movea 0x200,r0,r13`; the imm16 is at 0xC4C64 (D3 and D5 cite the imm16, D1 and D2 the instruction; these are consistent) |
| 0xC4C6A | `20 6e 2c 01` | D1, D2, D3, D5 | `movea 0x12c,r0,r13`; imm16 at 0xC4C6C |
| 0xC4C5E | `e4 47 99 b0` | D1 | `ld.hu -0x4f68[gp],r8`, unsigned \|hand word\| |
| 0xC4C1C | `29 06 da 4c 0c 00` | D1 | `mov 0xC4CDA,r9`, the table pointer. D1c's hex holds `…d2 4c…` = 0xC4CD2 (relinked; EVIDENCE) |
| 0xC4CDA | `ca 02 9a 04 11 04` | D1, D3 | GB-P row 0: X 714, G 1178, S 1041 |
| 0xC4CE4…0xC4CF6 | `88e7 / f802 / 0ff8 / 3002 / 2206 / 2c04 / 4608` | D4 | S1, G2, S2, G3, S3, G4, S4: all as stated |
| 0xC4CA2 | `20 6e 00 10` | D2 graft G-b | A3 cap `movea 4096`. The pattern also occurs at 0x31C74, which is Honda code and not targeted |
| 0x29D72 | `64 87 ce 95` | D4 N0 | `st.h r16,-0x6a32[gp]` (V288 rev 2 hooked this same site and flew) |
| 0xC4B92 | `24 37 b4 94` | D4 T7 | `ld.h -0x6b4c[gp],r6`, the 0x14A b4.7 rung |
| 0x1310D | `41` | D3, D4, D5 | `39990-TVA,A16A`; the 'A' of A16A |
| 0xC4FFC | `f3 d8 7c 6b` | D4, D5 | main-block trailer = `zlib.crc32([0x13000,0xC4FFC))` (control reproduces) |
| 0xC61BC / 0xC61BE / 0xC61B4 | `003c` / `003c` / `000c` | D3 | PCL 15360 / SCL 15360 / OCL 3072 |
| 0xC6CD0 | `e2 14` | D3 | fwd 5346 |

**Stock `code.bin`** (D3's "6×" claim, EVIDENCE): OCL 512, SCL/PCL 15360, and the 0xC6CD0 cell reads 0xFFFF. **D3's "the 6× is the rail, not a gain" is confirmed from bytes.**

**Ghidra cross-check** (dry-run on `ADVIG_V298_177abf04.bin`, `0xC4C5A`):
```
be 0xC4CC8 (CAM)
ld.hu -0x4f68,gp,r8
movea 0x200,r0,r13 ; cmp r13,r8 ; bh 0xC4CC2
movea 0x12c,r0,r13 ; cmp r13,r8 ; bnh 0xC4C7A
ld.h -0x4f60,gp,r9 ; xor r16,r9 ; blt 0xC4CC2
ld.h -0x6a00 …
```
- D5's claim that FZ2 becomes **dead** at 1229 is correct by this structure. `bh` not taken means r8 ≤ 1229, so `bnh` with the same 1229 is always taken.
- D3's opposing threshold of 800 stays **live** for 800 < r8 ≤ 1229.

**Pattern uniqueness.** `20 6e 2c 01` occurs once (0xC4C6A). `20 6e 00 02` occurs at 0xC4C62 and at 0x6271E (Honda code). A builder must patch by **address**, never by pattern replace.

**Free run.** 0xC4D04..0xC4FF0 is 748 B, all 0xFF (EVIDENCE). D4b's cave ends at 0xC4D38 and D5a's at ≈ 0xC4D4A, so both fit. 0xC4FF0 starts the CRC node; `build_v298_tva.CAVE_FREE_END` agrees.

**Table slopes re-derived** (S = (G1 − G0)·4096/(X1 − X0)). These are arithmetic controls on the designers' numbers.

| table | cell | computed | design value |
|---|---|---|---|
| V298 | S0 | 1041.2 | 1041 |
| D3a | S0 | 185.0 | 185 |
| D1-a2 | S0 | 235.8 | 236 |
| D4a | S1 | −4238.2 | −4238 |
| D4a | S2 | −2642.6 | −2643 |
| D4a | S3 | 2040.3 | 2040 |
| D4a | S4 | 1512.8 | 1513 |

All the S values are inside the s16 range.

**Caves the designers shipped as hex** (EVIDENCE).

| cave | sha256 prefix | matches the design page? | bytes differing from V298's cave region | first diff |
|---|---|---|---|---|
| D1c | `80dd2052edc0…` | yes | **152**, as claimed | 0xC4C1E, the table pointer, as claimed |
| D4b | `59b90cbdf004…` | yes | 211 | — |
| D3a (immediates applied) | `83b9799b` | yes | — | — |

- D4b's total of 218 = 211 cave bytes + 4 for N0 + 2 for T7 + 1 for V1. With the CRC trailer that is **222**, as claimed.

**Accounting nits** (not defects):
- D4a is 14 B, not 15. At 0xC4CEE (`30 02` → `d8 02`) the high byte does not change, so the total with the CRC trailer is 18, not 19.
- D1a counts 4 bytes without its trailer; the CRC trailer makes it 8.

---

## 2. (b) GATE 1: the two new RAM words (EVIDENCE: `s3_gate1`)

**The scanner's positive controls** (Python):

| cell | accessors found |
|---|---|
| gp-0x6abe | 23 |
| gp-0x6dd0 | 6 |
| gp-0x6cf8 | 4 |
| gp-0x4f68 | 45 |

**Ghidra cannot serve as the second method here.** `get_xrefs_to` returns **0** for gp-0x6abe (0xFEDF1542) on `code.bin`, so its xref set does not see gp-relative accesses. Its nulls for the two words below therefore carry **no information**. GATE 1 rests on the Python census plus targeted Ghidra decodes.

| check | gp-0x6a32 (D4b, halfword, 0xFEDF15CE) | gp-0x6c44 (D5a, word, 0xFEDF13BC) |
|---|---|---|
| direct gp-relative accessors (every width, ext6, ld.bu parity, bit-ops) | **2, both `st.h`**: 0x29D72 (live, nopped by D4b N0) and 0x2AC68 (in the duplicate-PID span, unreachable per inherited TRACE-2026-09-06). **0 readers.** Matches D4. | **0** |
| absolute 32-bit literal | 0 | 0 |
| movhi 0xFEDF + 2nd instruction within ±0x100 | 14 pairs. **All 14 are Format VIII bit-ops (op 0x3E, r18 base) on bytes 0xFEDF156C/156D/1688.** Width 1 and a fixed displacement put them 0x61–0xBA away from the word. **Adjudicated: not accessors.** D4 did not list them. | 0 |
| gp-base materialisations within ±0x100 | 0x36D1C–0x36D30 and 0x41F12–0x41F22 (both adjudicated by D4). Also **0x45630 (gp-0x6944) and 0x45650 (gp-0x693c)**, which D4's window missed. Ghidra dry-run on `code.bin` shows `movea base,gp,ep ; add r6,ep ; sst.h …,0x0[ep]` with r6 = 2·idx, idx ≤ 1 and ≤ 2 after `cmp ; bh`. The offsets are positive and at most +4, so the word (0xEE/0xF6 *below* the base) is unreachable. **Adjudicated: not accessors.** | 14 bases at gp-0x6b4a…-0x6b56 (0x28AEE, 0x34376–0x34386, 0x34A94–0x34AA8, 0x36572–0x36586). All lie 0x7A–0xFA *above* the word. A positive index cannot reach it. **Not adjudicated by decode** (BELIEF: clean) |
| on-car precedent (lineage of record) | V288 rev 2 used it as filter state, hooked at the same 0x29D72, engage-init from the gp-0x6cf8 sentinel, and flew (r5e) | V289's notch state word (gp-0x6c44/-0x6c40/-0x6c3c), flew (r62/r63) |
| residual (the gp-0x1500 class) | A register-indirect access from an unmaterialised base cannot be excluded statically. Precedent: V288 flew. | Same. D5's own "owed" list still stands: a Ghidra decode of the 14 bases and the boot value. |

**GATE 1 verdict.**
- **D4b: PASS (static) with on-car precedent.**
- **D5a: static census clean.** Its decode adjudication is not done, so it is not cleared.
- Every other candidate adds **0** RAM words, and the cave writes no RAM:
  - D1c's listing has no `st.*` (designer H1 plus listing).
  - D3a, D5b and D1a are immediate-only.
  - D2 has no firmware change.

---

## 3. (c) Downstream interlock census: what changes a clamp, rail, A3 or ICL?

| candidate | clamp / rail / ICL / A3 change | downstream exposure vs the flown record | verdict |
|---|---|---|---|
| D1c | **A3 made asymmetric**: the inward bound is B = 1250 S ≤ V298's. ICL, the rail and the cap are unchanged. | The I magnitude is ≤ V298's in every state (EVIDENCE by the mirror's structure). The lane is ≤ the 2461 T rail, byte-identical since V282. | no new band |
| D1a / D5b | thresholds only | Same rail. The I keeps integrating more often, but within the unchanged A3 and ICL. | no new band |
| D3a | thresholds + G row 0 ×1.20 (≤ 3.1 m/s, tapering to ×1 at 8 m/s) | P and I per degree rise; PCL, SCL and OCL are unchanged. **The rail is the flown V282 rail.** V282 flew \|T\| ≥ 1277 for 2.3 s (lineage, V294 entry); V293's D1 shows the lane cap of 3072 cannot drive soft-EME wind-up. | no new band |
| D2 / D3a / D5b fork clip ×1.6 / ×1.76–1.61 / ×2.06 and caps 250–300 | none in firmware | P demand can reach 61–83 % of the rail at ≤ 8 m/s (V298 36–40 %). The ceiling is still the 2461 rail. **First time a V29x angle build may actually reach the rail on car** (r79 peak 59 %). | inside the flown envelope (BELIEF from the V282 record) |
| **D3b** | SCL/PCL 15360 → 19072, rail → 3057 T | **Opens 5120 < \|cmd\| ≤ ~5900** for the soft-EME integrator gp-0x3570, beyond V293's 5325 band. Not replayed. Override effort +24 %. | **DO NOT FLY** until the soft-EME replay is done |
| D4b / D4a | D4b: none. D4a: G ×1.3 at 10–17.5 m/s | as D3a | no new band |
| D5a | adds a friction term ±67·6 = ±402 S into D's operand, before DCL 10240 | inside DCL and the rail | no new band; GATE-2 margin +0.4° |

**No candidate edits a governor, EME, lockstep or DTC cell.** EVIDENCE: every changed byte sits in the cave, the version byte, the 0x14A cave, the 0x29D72 hook-adjacent st.h, or the D3b PCL/SCL. The full diffs are in `s3_bytes.txt`, with 0 bytes outside the CRC blocks.

**Version byte and interlock (EVIDENCE: fork `interface.py`/`carstate.py`, read-only).** Take an A16B image with an un-updated fork:
- **Switch on:** the result is `EPS_ANGLE_LOOP_FW_MISSING`, a permanent steer fault (fail-safe).
- **Switch off:** the fork sends torque-mode frames, which do not pass `angle_arm`. The cave's camera gate (arm ≠ 2) then holds the lane inert (BELIEF on the packer default of the arm bits; it is V298's declared F10 premise).

**So bumping to A16B is fail-safe.** D1c leaves the bump open. **S3 recommends A16B** (+1 B, plus a one-line fork tuple), so that carFw attributes the build. Without it, attribution rests only on the replay test.

---

## 4. (d) The fork changes

### 4.1 The bar sign (EVIDENCE: `s3_bar_sign`, route 79, 11,628 steady hands-off hold frames)

| quantity | result |
|---|---|
| sign(0x1AB tap s10) = sign(angle), with angle + = left | **0.0015**, so tap + = RIGHT |
| sign(today's angle-mode bar) = sign(angle) | **0.056**, so today's bar + = RIGHT (`desiredCurvature` on this fork has the opposite sign to the angle; r79 cache README) |
| **D1** bar = +8·s10/2461 agrees with today's bar | **0.942**: correct convention |
| **D2** eps = −8·s10, bar = +eps/2461 | **0.058**: **INVERTED**. D2 states "+ = left like the current angle branch". The current branch is + = right. |
| **D5** eps = −T, bar = +eps/2461 | **0.058**: **INVERTED**. This is D5's own open item P1, now resolved against it. |

**Fix for D2/D5.** Keep `steeringTorqueEps = −8·s10`, which is + = left as openpilot's carState expects, and draw the bar as **−eps/2461**. D2's own mandated unit test would catch this; D5's P1 test would too.

**`steeringTorqueEps` has no Honda consumer today.** The Honda port does not read it, so populating it changes only the UI. EVIDENCE: fork source search. The consumers are the Toyota and Chrysler torque limiters and other carstates.

### 4.2 The parser coupling (EVIDENCE: `opendbc/can/parser.py` at Dom)

| claim | finding |
|---|---|
| "freq nan / 0 ⇒ optional, cannot affect `canValid`" (D1, D2) | **Half true.** `optional_msg = isnan(freq) or freq <= 0` gives `ignore_alive`, so no timeout check applies. **But `can_valid` also fails when any message's `counter_fail ≥ MAX_BAD_COUNTER (5)`, optional or not.** A 0x1AB counter fault would set `canValid` false, which is a fork disengage path. r79's counter was valid on 99.997 % (two skips at segment joins), so the risk is low. D1's F8 and D2's F4 already watch it. |
| D5: "50 Hz expected rate set in the message list" | That makes 0x1AB **non-optional**. An alive timeout (10 / 50 Hz = 200 ms) now joins `canValid`. Use `float('nan')` as the existing Honda entries do (`ACC_CONTROL`, `STEERING_CONTROL`). |
| implicit trap | `cp.vl["STEER_MOTOR_TORQUE"]` without a message-list entry **auto-adds the message as non-optional** (`VLDict.__getitem__` → `_add_message(key)` with freq None). It must be listed explicitly with nan. |
| DBC | `BO_ 427 STEER_MOTOR_TORQUE: 3 EPS`, `MOTOR_TORQUE 1\|10@0+` unsigned, in `_honda_common.dbc`. Sign-magnitude decoding (bit 9) is the designers' convention and is correct. |

### 4.3 Fork diff, toggle-config expressibility, override, and deleted vs gated

| candidate | fork edits (files) | toggle config? | driver override (Honda's 1200 raw) | deleted vs gated | panda / safety-model note |
|---|---|---|---|---|---|
| D1c / D1a | `carstate.py` parse + `torque_bar.py` | no separate param; tied to the existing `AccordEpsAngleLoop` path. **Recommend a param** (`AccordAngleBarFromEps`) so the bar can be reverted alone. | unchanged O1 (600 instant). The firmware freeze is now at 1229 = Honda; the fade is unchanged. | **The firmware opposing-hand freeze is deleted** and replaced by the asymmetric A3 bound, a new mechanism with N1 scored. Firmware cannot be param-gated. | the setpoint path is unchanged |
| D2a / D2b | `values.py`, `carcontroller._update_angle` (a1–a7), `carstate.py`, `torque_bar.py`; (b) also `latcontrol_angle.py` | **yes**: every term is a param with a V298 default. **Param clamps are specified** ([60, 450] deg/s, [1, 2]). | > 1200 instant; 600–1200 after 80 ms. The firmware freeze stays at 512 and the fade is unchanged. **Preserved.** | O1 lead 0.06 → 0 by param (gated). Nothing deleted. | The panda bounds nothing on the 0xE4 angle field (only bytes 0-1 = 0 while not allowed), so the fork's clamped params are the only backstop. **D2 specifies them.** |
| D3a / D3b | `values.py`, `carcontroller._update_angle` (K1–K4), K5 version line | yes, once coded (K5 is code) | **Weakest.** O1 needs \|τ\| > 1200 **held 100 ms**, or > 2500 at once. Hands of 600–1200 **never** yield the setpoint, while P can reach 75 % of the rail at 3.1 m/s plus the lead. The Honda fade still acts at once (×0.85 at 1216 → ×0.30 at 2289). **Physical override is preserved** (BELIEF on hand capability), but the setpoint follows a Honda-level hand ≤ 100 ms late. Needs an explicit operator ruling. | the V298 O1 600 path is replaced by K2 (param-gated) | **Param ranges unclamped** in the spec. **K5 accepts A16B unconditionally while K2 defaults off.** By D3's own sim, the D3 firmware with the default fork relays O1 on the twist. Couple them: accept A16B only with K2 on, or default K2 on when A16B. |
| D4a / D4b | `values.py` (`ANGLE_OVERRIDE_DEBOUNCE = 5`, version tuple), `carcontroller`, `interface.py` (`in`) | **NO**: code constants, against the operator's toggle-config preference. Add `AccordAngleOverrideDebounce`. | **All levels debounced 5 frames, with no instant hard path.** A > 1200 hand waits 50 ms for the setpoint. The firmware LP freeze reaches 512 in about 17 ms and the fade is immediate. Recommend D5's form (> 1200 instant). | nothing deleted; the opposing freeze is gated by motion | — |
| D5b / D5a | `values.py`, `carcontroller._update_angle` (O1, cap, clip, lead), `carstate.py`, `torque_bar.py` | **yes**, plus a REVERT config | > 1200 instant; 600–1200 after 60 ms; firmware freeze 1229; fade unchanged. **Preserved, best-formed.** | **The opposing freeze is made unreachable** (dead branch), with its N1 job moved to fork O1. See §5. | ranges for `AccordAngleRateCap` / `ClipLowScale` / `LeadGain` unclamped in the spec |

---

## 5. Cross-candidate conflict the judges must resolve (decision-bearing)

**D5b's firmware edit is byte-for-byte D1a.** Both have FZ1 = FZ2 = 1229; D5b adds A16B.

**D1 measured D1a as FAILING its N1 lens.** EVIDENCE from `d1_n1`, worst member, Lane3 control equal to V298 bit for bit:

| scenario | D1a lurch | V298 lurch |
|---|---|---|
| outward 2× hold of a 511-word hand at 12.5–22 m/s | 15.9° | 4.7° |
| nudge | 8.0° | 0.8° |

**D4 corroborates the class:** raising only the opposing threshold to 450 gives +10.4° outward lurch.

**D5's own lens reports no regression.** Its scenario is light opposing 400/700/1000 for 1 s, release, ≤ 2.6°. That is a different scenario: an inward hold, 1 s, at 5 m/s.

**D5's fork O1 does not cover a 511-word hand.** That is about 500 raw, below the 600 ON level. The 60 ms debounce only delays.

**S3 marks D5b "PENDING DISQUALIFIER"** until D5b (firmware plus its fork) is scored on D1's `rb_n1` out_2_511 / out_1.5 / nudge lens. **D3a (opposing at 800) needs the same check:** its own heavy-member 511-word lurch already rises 7.4° → 9.5°.

---

## 6. (e) Instruments: is every new term visible from one short drive?

| candidate | new term | signal | observable? |
|---|---|---|---|
| D1c | freeze rule + asymmetric bound | M3-style rule-identity replay vs the 0x1AB tap (V298 rule wins 18/18 r79 windows; dR² +0.605) | yes (inert, zero bytes) |
| D2 | O1 gate, takeover, cap/clip binding, lead, bar | `co_tq` status bits, `ang_output`, `cs_tqeps`, `ld_lat` = 0.45. **All free on r79** (EVIDENCE: 0 nonzero rows of 121,383 / 121,443; `ld_lat` constant 0.35). | yes |
| D3a | thresholds, G row, K1–K4 | P-slope regression (+20 % at 3.1 m/s predicted vs V298 delivering 0.93–0.96 of design: detectable); rule replay; lead = −raw/10 − co_ang; K2 reconstructed (no explicit bit) | yes |
| D4b | state word h + motion gate | **0x14A b4.7 = sign(h)** in the same build (comparator vs the h rebuilt from 0x18F) + rule replay (p99 70 LSB separation) | yes. Sign only, magnitude by comparator. Repoints V282's unused sign(gp-0x6b4c) rung. |
| D5b | thresholds + fork O1/cap/clip/lead/bar | rule replay (R² 0.927 vs 0.128) + `limiter_reconstruct` reproducing `co_ang` | yes |
| D5a | washout D, friction add | washout replay vs tap (R² 0.926 vs 0.419) | yes |

---

## 7. Defects to carry into the build round

| # | candidate | defect | severity |
|---|---|---|---|
| S3-1 | D2, D5 | Bar sign inverted relative to today's bar (0.058 agreement); use bar = −eps/2461. | must-fix before flight (note 3 is the goal) |
| S3-2 | D2 | "freq 0 ⇒ never affects can_valid" is false for the COUNTER path (`MAX_BAD_COUNTER` 5) | report; F4 covers it |
| S3-3 | D5 | parser freq 50 Hz makes 0x1AB non-optional (adds an alive timeout to `canValid`) | must-fix: use nan |
| S3-4 | D5b, D3a | N1 outward light-hold regression measured by D1 for this exact firmware (D5b) or class (D3a); not scored on that lens | **pending disqualifier (D5b)** / must-score (D3a) |
| S3-5 | D3a | O1 at Honda's level is held 100 ms; 600–1200 never yields; A16B accepted without K2; param ranges unclamped | operator ruling + fork fix |
| S3-6 | D4a, D4b | fork terms are code constants (not toggle-expressible); no instant > 1200 O1 path | should-fix |
| S3-7 | D1c | version A16A kept leaves carFw attribution blind; recommend A16B (+1 B) | should-fix |
| S3-8 | D3b | soft-EME 5120–~5900 band unreplayed | do-not-fly (designer agrees) |
| S3-9 | D5a | GATE 1 decode adjudication of 14 nearby bases owed (static census clean) | blocks (a) only |
| S3-10 | all firmware | pattern `20 6e 00 02` also at Honda 0x6271E: patch by address; every relinked cave (D1c, D4b, D5a) must re-run H1 + the Ghidra decode on the BUILT image and the adversarial pass | process |
| S3-11 | all | no golden-model mirror is in `eps_chain_control.py` yet (designers were barred); each candidate's mirror (D1c `d1c_cave`, D3 snippet, D4b `d4b_ref`, D5b `v299b_frozen`) must be grafted with a `_self_check_v299` before the build | process |

**Not verified by S3 (BELIEF, inherited from the designers):**
- The 0x1AB checksum and counter validity. Three designers measured it independently (D1 and D2 on 61,113 frames, D5 on 6,000); the S3 cache holds bytes 0–1 only.
- The designers' H1 interpreter runs.
- GATE 2 numbers.
- Simulation results.
