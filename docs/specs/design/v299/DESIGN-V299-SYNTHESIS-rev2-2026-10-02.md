# DESIGN V299 — SYNTHESIS rev 2 (2026-10-02): the build brief, every refuter finding resolved

**Status: BUILD BRIEF. Nothing built, flashed, sent or committed; fork, firmware, golden model, STATE, lineage, git untouched.**
Author: the REVISER subagent. Supersedes rev 1 (`DESIGN-V299-SYNTHESIS-2026-10-02.md`) as the brief; rev 1 stays the record. **EVIDENCE** = image bytes, Ghidra listing, route-79 caches, fork source at Dom `2712e1336`, or a script
I ran this session (named in §A with its wall time). **BELIEF** = a model (the r71b plant family; M3's twist fit, R² 0.31; S2's
stiff-hand model) or an inference. Bands are scored here; the operator scores symptoms. Classifier interruptions: 0.

---

## 0. What changed from rev 1 (every refuter finding → its resolution; nothing waived)

**Two operator rulings of 2026-10-02 reached the record during this revision** (`memory/feedback/process/feedback-no-fork-
override-…` and `…-1-6-3hz-replaced-by-stutter-readouts`). They bind this brief: (i) **no fork-side override** — no O1 gate,
lead, debounce or takeover; the EPS fade + the firmware freeze at raw 1229 are the override; the error clip bounds the stored
error; (ii) the hard-turn 1.6–3 Hz criterion is replaced by the stutter readouts. The orchestrator's G4 / lead / takeover items
are therefore resolved by removal; their sims stay as the record (§3.6). **The no-override fork was scored (§3.2, §3.5): best
of all hands-off, but a moderate hand meets 37–60 % of rail — escalation 1.**

| finding | resolution | § |
|---|---|---|
| orchestrator (1): config B re-arms the twist relay | **config A only** (= cap 120, clip ×1.0, no override, the bar); cap 250 / clip ×1.6 a later dose, one at a time (X3) | 2, 7 |
| stab D1 (FC): F4 trips at 10 m/s, 60° | A3 cap through 12.5 m/s as a **two-level** cap (4096 S ≤ 6 m/s unchanged, 6144 S 6–12.5 m/s). The 4-byte single value also lifts ≤ 6 m/s and **trips F4 at 3 m/s** | 1.2 |
| stab D2/D3/D7 (FD): B relays, B no faster | B dropped; with no override there is no O1 relay at all (0 O1, 0 stall-surges in sim) | 3.2 |
| stab D4: ms_free curve-hold ring | F10; the cap removes it ≤ 12.5 m/s on that family for a 1.4–3.5° hold shortfall | 3.4 |
| stab D5/D6/D8/D9/D10 | GATE 2 shortfall declared; unwind per member; F3 per member; O1 GM moot (no O1); scripts < 30 s | 3.1, 3.3, 3.5, A |
| fork P5/D1: bits in `actuatorsOutput.torque` | bits → `starpilotCarState.accordAngleStatus`; the mici cue gets the bar | F8, F7m |
| fork D2: no rwd re-header plan | V299 lists A16A + A16B; V298 and V295 reverts re-headered + A16B; read back | 11.2 |
| fork D3: moderate band unsimulated / unseen | S2 rows 550–2500 words × c/o/drag × 5/8/15/25 m/s; F7b; highway light hold on the card | 3.5, 7, 6 |
| fork D4 vs bytes D1: 0x1AB | from the DBC: COUNTER defined, no CHECKSUM → `ignore_counter`; checksum checked in carstate; bar 0 at > 100 ms | 2.1 |
| fork D5/D11 (takeover), lead fallback, G4 | **removed by ruling (i)**; the sims (keep 0.4 s) are recorded | 3.6 |
| fork D6/D8/D9/D10/D12–D14 | clip band exact; guarded reads, envelope clamps, Safe Mode keys; deletion's gate = reflash; raw 1229 ↔ wire 1200 | 2.2, 5 |
| fork D7: old fork + A16B | family match + card order. **Correction:** the bare prefix `39990-TVA,A16` also matches V295's `A160` → prefix **+ a letter** | F9 |
| bytes D2/D3: build gates; CRC chain | §11 prerequisites; chain 50/50 + bootloader 49/49 asserted (both 0 bad already) | 11 |

---

## 1. Firmware: V299 = V298 + 67 bytes (cave 62 + F181 1 + trailer 4), one 260-B cave, no relink, 0 RAM

### 1.1 Every byte (V298 `177abf04…`; old bytes re-read LE and asserted; new bytes decoded by Ghidra dry-run on a disasm-only scratch copy)

**Outside the span:** 0xC4C64–65 `00 02` → `cd 04`: imm16 of `movea …,r0,r13` @0xC4C62, 512 → 1229. The hard freeze fires iff raw \|gp-0x4f68\| > 1229 ⇔ wire ≥ 1201 ⇔ Honda `steeringPressed`. · 0x1310D `41` → `42`: F181 `39990-TVA,A16A` → `…A16B`. · 0xC4FFC–FF `f3 d8 7c 6b` → **`95 3b dd 70`**: crc32 of [0x13000, 0xC4FFC).

**The span 0xC4C6A–0xC4CAB (66 B), re-laid out in place.** It holds 24 instructions, all of forms V298's cave already executes. Nothing outside the span branches into it. The table pointer `mov 0xC4CDA,r9` @0xC4C1C, the GB-P rows, the FRZ/CAM/DONE tails and the op-skip are byte-identical to V298 (asserted).

| V298 (addr bytes: instruction) | V299 rev 2 (addr bytes: instruction) | loop term |
|---|---|---|
| C6A `206e2c01` movea 0x12c,r0,r13 | C6A `244f0096` ld.h -0x6a00[gp],r9 | θ (0.1°/count) |
| C6E `ed41` cmp r13,r8 | C6E `e081` cmp r0,r16 | sign of E′ |
| C70 `d305` bnh C7A | C70 `ae05` bge C74 | |
| C72 `244fa0b0` ld.h -0x4f60[gp],r9 | C72 `8049` subr r0,r9 | r9 = θ·sgn(E′) |
| | C74 `e049` cmp r0,r9 | |
| C76 `3049` xor r16,r9 | C76 `ae05` bge C7A | |
| C78 `d625` blt CC2 | C78 `004a` mov 0,r9 | r9 = max(θ·sgn E′, 0) = rev 1's asym + abs, in all cases |
| C7A `244f0096` ld.h -0x6a00[gp],r9 | C7A `e447a395` ld.hu -0x6a5e[gp],r8 | v-word |
| C7E `e049` cmp r0,r9 | C7E `206e400b` movea 0xb40,r0,r13 | 2880 = 12.5 m/s |
| C80 `ae05` bge C84 | C82 `ed41` cmp r13,r8 | |
| C82 `8049` subr r0,r9 | C84 `9b15` bh CA6 | v > 2880: shl 6, no cap |
| C84 `e447a395` ld.hu -0x6a5e[gp],r8 | C86 `c44a` shl 4,r9 | |
| C88 `206e400b` movea 0xb40,r0,r13 | C88 `094ee204` addi 0x4e2,r9,r9 | + B (1250) |
| C8C `ed41` cmp r13,r8 | C8C `206e6605` movea 0x566,r0,r13 | 1382 = 6.0 m/s |
| C8E `bb05` bh C94 | C90 `ed41` cmp r13,r8 | |
| C90 `c44a` shl 4,r9 · C92 `a505` br C96 | C92 `cb05` bh C9A | v > 1382: the upper level |
| C94 `c64a` shl 6,r9 | C94 `206e0010` movea 0x1000,r0,r13 | cap 4096 at v ≤ 6 m/s (= V298) |
| C96 `094ee204` addi 0x4e2,r9,r9 | C98 `b505` br C9E | |
| C9A `206e6605` movea 0x566,r0,r13 | C9A `206e0018` movea 0x1800,r0,r13 | **cap 6144 at 6 < v ≤ 12.5 m/s (NEW)** |
| C9E `ed41` cmp r13,r8 · CA0 `eb05` bh CAC | C9E `ed49` cmp r13,r9 | |
| CA2 `206e0010` movea 0x1000,r0,r13 | CA0 `ed4f364b` cmovh r13,r9,r9 | bound := min_u(bound, cap) |
| CA6 `ed49` cmp r13,r9 | CA4 `c505` br CAC | |
| CA8 `ed4f364b` cmovh r13,r9,r9 | CA6 `c64a` shl 6,r9 · CA8 `094ee204` addi 0x4e2,r9,r9 | the v > 2880 path, no cap (= V298) |

Word-by-word V298/rev1/rev2: `_scratch/v299_REV2/rev_bytes.txt`; the span differs from rev 1 in 56 of 66 bytes, from V298 in 60. **Patch by address:** `movea 4096` also occurs at Honda 0x31C74, and `movea 512` at 0x6271E (Python census). `movea 6144` occurs nowhere in V298.

**Hashes (EVIDENCE, `rev_bytes.py`; a second splice method agrees):** cave (260 B) `e22193b9dd2999c6ee4e8a7f8928feb3ea15ddc71cfacbbdab672aa0f1133608`;
predicted image **`30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08`** (not written; a disasm-only copy is in
`_scratch/v299_REV2/`); trailer `95 3b dd 70`; `walk_all_blocks` 0 bad (50/50); `walk` 0 bad (49/49); 67 bytes vs V298, no stray.

Controls: rev 1 rebuilt by the same script reproduces the synthesis' `ac15b533…` / cave `0ea16bde…` / trailer `2d ad cf 2e`. The rejected 4-byte form (**alt4**: rev 1 + 0xC4C9C `6605`→`400b`, 0xC4CA4 `0010`→`0018`) gives image `7e827872…`, trailer `95 43 0b c6`, 50/50 and 49/49.

### 1.2 Why two levels and not the 4-byte edit (EVIDENCE for the arithmetic, BELIEF for the plant)

One immediate sets **one cap for every v-word ≤ the gate**, so the 4-byte edit (gate 1382 → 2880, value 4096 → 6144) also lifts the cap at 3–6 m/s, where 4096 was kept on evidence (rev 1 M9); the refuter never ran that band. `rev_cap_size.py`, 60° hands-off turn-in, hold 4 s, both members × 2 seeds per engine; cell = max overshoot ° [F4 columns of 4] / max \|hold error\| at 4 s:

| system (S2 engine; RSN in brackets where it differs) | 3 m/s | 4 | 6 | 8 | 10 | 11.75 | 12.5 |
|---|---|---|---|---|---|---|---|
| V298 | 2.8 [0] / 0.0 | 0.6 / 0.2 | −2.9 / 4.5 | 3.2 / 0.0 | 6.0 [0] (RSN 7.2 [1]) / 0.9 | 10.9 / 2.5 | 11.2 / 2.1 |
| rev 1 (synthesis) | 2.9 [0] / 0.1 | 0.6 / 0.2 | −2.9 / 3.7 | 5.0 / 0.1 | **7.5 [4]** / 1.2 | 10.8 / 3.0 | 9.4 / 2.0 |
| alt4 (6144 single, 4 B) | **8.3 [4]** (RSN 7.2 [3]) / 0.1 | 5.9 / 0.1 | 2.1 / 0.0 | 0.5 / 1.5 | 3.0 [0] / 0.3 | 7.7 / 1.1 | 3.9 / 1.2 |
| single 5120 (4 B) | 5.6 [0] / 0.1 | 3.3 / 0.1 | −0.4 / 1.4 | −2.0 / **3.6** | −1.1 / 1.5 | 3.2 / 0.6 | 0.0 / **3.5** |
| single 4096 to 12.5 (2 B; `rev_turnin.py`, \|err\| at 6 s) | = rev 1 | | | −4.5 / **5.8** | −5.4 / **5.9** | −1.6 / 5.2 | −5.6 / **8.9** |
| **rev 2 (two-level)** | **2.9 [0] / 0.1** | 0.6 / 0.2 | −2.9 / 3.7 | **0.5 / 1.5** | **3.0 [0] / 0.3** | 7.7 / 1.1 | 3.9 / 1.2 |

At 45° and 3–4 m/s, every single value ≥ 5120 also trips F4: alt4 7.7 [2] / 6.5 [2], single 5120 7.6 [2] at 3 m/s (S2; RSN at 3 m/s: alt4 8.8 [1], single 5120 7.7 [2]). Rev 2 gives 5.2 / 3.4, which equals rev 1.

**Reading.** No single value satisfies both bands:
- ≥ 5120 trips F4 at 3–4 m/s;
- 4096 holds a 60° turn 5–10° short at 8–12.5 m/s;
- 7168 trips F4 at 10 m/s (5.6 [6.6], 4/8 S2 columns; `rev_turnin.py`).

The two-level form leaves ≤ 6 m/s byte-for-byte V298's and puts 6144 where the refuter designed it. **Why 6144 for the upper level:** 7168 trips F4 at 10 m/s, and 5632 doubles the 8 m/s 60° hold shortfall (2.5 vs 1.5°). The structure, not the value, was the constraint (CLAUDE.md 2026-09-30): 38 more bytes than the 4-byte form, all inside rev 1's span.

### 1.3 The cave, integer-exact (the spec's mirror = `revise/rev_h1.py cave_rev2`, the golden model's `_self_check_v299`)

```python
def cave_rev2(sp, r26, ramp, r25, abe, v, a4f68, th, I8, G):          # r16 = sp in, G = GB-P walk at v (unchanged)
    E  = s32(s32(sp << 2) - r26)                                      # 0xC4C00 shl 2,r16 ; sub r26,r16   E = 16(th_sp - th)
    op = s16(abe)                                                     # 0xC4C04 ld.h -0x6abe[gp],r26
    if ((op + 13000) & 0xFFFFFFFF) > 26000: return SKIP_0x2A164       # 0xC4C08..14 op-skip -> Honda epilogue (I8 := 0)
    Ep = s32(E * G) >> 8                                              # 0xC4C54 mul r8,r16 ; sar 8
    if r25 == 0: return FRZ, r16=0, r26=0, r6=s32(-(I8 >> 6))         # 0xC4C5A be 0xC4CC8  camera gate
    if (a4f68 & 0xFFFF) > 1229: return FRZ, r6=0                      # 0xC4C5E..68  hard freeze (raw 1229 = wire 1200)
    r9 = s16(th)                                                      # 0xC4C6A
    if Ep < 0: r9 = -r9                                               # 0xC4C6E cmp r0,r16 ; bge ; subr r0,r9
    if r9 < 0: r9 = 0                                                 # 0xC4C74 cmp r0,r9 ; bge ; mov 0,r9
    vv = v & 0xFFFF                                                   # 0xC4C7A ld.hu -0x6a5e[gp],r8
    if vv > 2880: r9 = s32((r9 << 6) + 1250)                          # 0xC4C84 bh -> 0xC4CA6 shl 6 ; addi 1250 (no cap)
    else:
        r9 = s32((r9 << 4) + 1250)                                    # 0xC4C86 shl 4 ; addi 1250
        cap = 4096 if vv <= 1382 else 6144                            # 0xC4C8C..0xC4C9A movea 1382 ; cmp ; bh ; movea 4096 | 6144
        if (r9 & 0xFFFFFFFF) > cap: r9 = cap                          # 0xC4C9E cmp r13,r9 ; cmovh r13,r9,r9
    t = s32(I8) >> 10                                                 # 0xC4CAC ld.w -0x6dd0[gp] ; sar 10
    if Ep < 0: t = -t                                                 # 0xC4CB2..B6
    if t >= r9: return FRZ, r6=0                                      # 0xC4CB8 bge FRZ   (winding past the bound)
    if (ramp & 0x8000) == 0: return FRZ, r6=0                         # 0xC4CBC  ramp-in freeze
    return DONE_0x29D7A                                               # Honda I: inc ((E'>>5)*40)>>3, ICL 8192; P/D/sum as V298
# bound (S = I8>>10): B=1250 when sign(th) != sign(E'); else 16|th|+B capped 4096 (v<=6 m/s) / 6144 (6..12.5 m/s); 64|th|+B above
```

### 1.4 Verification of the construction (EVIDENCE, this session)

| check | method | result |
|---|---|---|
| decode | Ghidra dry-run 0xC4C5E–CD9 on `V299R2_DISASM_ONLY_NOT_AN_ARTIFACT.bin` (raw V850:LE:32 import, no analysis, `/v299rev2scratch`, closed) | §1.1's 24 instructions exactly; tail from 0xC4CAC = V298 |
| branch census | V298 listing (bytes refuter §3) + rev-2 listing | only the span's own branches target it, before and after; new targets are in-span or 0xC4CAC; entry only `jarl 0xC4C00,r6` @0x29D76 |
| bytes = mirror | `rev_h1.py` (4.9 s): the kit's V850E2 interpreter (score_time.Cpu2) on the rev-2 cave vs `cave_rev2`: exit pc, r16, r26, r6, no RAM written, all other non-scratch registers unchanged | random: **0/2941 + 0/2913 valid, 0/5417 op-skip, 0/729 camera**; targeted (1382 < v ≤ 2880 and the 1381–1383 / 2879–2881 edges, I straddling 4096–6144): **0/4000** |
| the check can fail | the same harness, crossed | rev-2 bytes vs the rev-1 mirror **69/2000** (targeted); vs the single-6144 mirror **65/2000**; rev-1 bytes vs the rev-2 mirror 1/1467 (random) |
| controls | — | the mirror at rev-1 caps == `d1_time.D1Lane` (D1c) on 9781/9781; V298 bytes vs V298 mirror 0/968/899/133; rev-1 bytes 0/1501; alt4 bytes vs its mirror 0/1478 |
| exit registers | `rev_h1_regs.py` (2.1 s): rev 1 vs rev 2 bytes, 3000 cases | identical on 2947; the 53 others are the cap-changed freezes; r9 differs only at 1382 < v ≤ 2880 |
| GATE 1 | listing + H1 | 0 `st.*`, 0 new RAM or state word; read set = rev 1's; gp-0x6dd0 Honda's, zeroed by the 0x2A164 epilogue |
| CRC | §1.1 | one block; chain 50/50, bootloader 49/49 (0 bad) |

---

## 2. Fork update (StarPilot Dom on `2712e1336`; one commit; every param defaults to V298; the override removal changes only frames inside V298's O1 episodes)

### 2.1 0x1AB, reconciled from the DBC (EVIDENCE)

The Accord's pt DBC is `honda_accord_2017_can_ext_generated.dbc` (values.py `HONDA_ACCORD` → `radar_dbc_dict('honda_accord_2017_can_ext_generated')`). It imports `_honda_common.dbc`, which defines:

`BO_ 427 STEER_MOTOR_TORQUE: 3 EPS` = `CONFIG_VALID 7|1`, `MOTOR_TORQUE 1|10@0+`, `OUTPUT_DISABLED 22|1`, `COUNTER 21|2`. **There is no CHECKSUM.**

`can/dbc.py set_signal_type` types `COUNTER` as a counter and a CHECKSUM only by name. `MessageState.parse` therefore checks **only the 2-bit counter**: `update_counter`, `MAX_BAD_COUNTER` 5, and `can_valid` drops the whole pt parser.

- The bytes refuter ("no CHECKSUM, no COUNTER, single signal") was **wrong** on COUNTER.
- The fork refuter was right on the counter path. Its "keep the checksum" has no parser checksum to keep: route 79's 100.000 % checksum figure is the kit's own `honda_checksum` over byte 2's low nibble (`d1_427_check.py`), which the DBC does not declare.

Resolution:
- `ignore_counter = True`.
- **The checksum is verified in carstate on the raw frame** (`cp.vl_raw`, which `CANParser.update` stores on every parsed frame), using `hondacan.honda_checksum(0x1AB, None, raw) == raw[2] & 0xF`.
- Staleness is clocked against 0x18F's timestamp. On route 79, 0x1AB gaps run p50 20.1 ms and p99.9 30.8 ms; the only two gaps > 100 ms coincide with 0x18F's own (`rev_1ab_gap.py`), so a 100 ms rule never trips on r79.

### 2.2 The change table (ruling (i): no override state)

| # | file / function | the diff in words | param (default → config A) |
|---|---|---|---|
| F1 | `values.py CarControllerParams`; `CarController.__init__` | per instance `ANGLE_LIMITS = dataclasses.replace(…, MAX_ANGLE_RATE = rate/100)`; `apply_steer_angle_limits_vm` keeps `min(VM jerk, MAX_ANGLE_RATE)`. **Later dose only** | `AccordAngleMaxRate` 120 → 120; clamp [60, 250] |
| F2 | `_update_angle` (error clip) | `error_max = interp(v, BP, V_s)`, V_s = the knots at BP ≤ 11.75 × s, 17.5/26.9 unchanged; **exact band** 11.75–17.5 m/s: 17·s + (8.5 − 17·s)(v − 11.75)/5.75 (14 m/s: 13.7° at s 1.0, 19.9° at 1.6). **Later dose only** | `AccordAngleClipScale` 1.0 → 1.0; clamp [1.0, 1.6] |
| F3 | `_update_angle`; `values.py` | **override removed (ruling):** delete `self.angle_override`, the O1 branch (`θ + rate·lead`) and `ANGLE_OVERRIDE_ON/OFF/LEAD_S`. The limiter restarts from the wheel only on the first frame and the latActive rising edge (already implicit: with latActive false `apply_steer_angle_limits_vm` returns the wheel angle, lateral.py). The clip stays the only setpoint–wheel bound | — (code) |
| F6 | `carstate.py get_can_parsers` + `update` | only when `CP.flags & EPS_ANGLE_LOOP_FW`: list `("STEER_MOTOR_TORQUE", float("nan"))` on pt (never unlisted: `VLDict` auto-adds non-optional), then `message_states[0x1AB].ignore_counter = True` (as 0x201). In `update`: a frame is good if `len(raw)==3` and the checksum matches; on a good new frame store `s10 = (−1 if raw10 & 0x200 else 1)·(raw10 & 0x1FF)` (the kit's tap decode) and its ts. `fresh = ts(STEER_STATUS) − ts_good ≤ 100 ms`; `ret.steeringTorqueEps = −8·s10 if fresh else 0.0` (+ = left; tap + = right: sign(tap) = sign(+left angle) on **2.9 %** of 31,987 r79 frames, `rev_bar_sign.py`) | — |
| F7 | `selfdrive/ui/onroad/starpilot/torque_bar.py` | helper `accord_eps_bar(sm, CP)` → `clip(−carState.steeringTorqueEps/2461, −1, 1)` when angle mode + angle-loop FW + the param, else None; `TorqueBar._update_state` uses it before the lateral-accel branch (2461 T = SCL 15360 × 5346/32768). Test: sign agreement with today's bar ≥ 0.85 on r79 (0.854) | `AccordAngleBarFromEps` false → **true**; read once (UnknownKeyName → false) |
| F7m | `selfdrive/ui/mici/onroad/model_renderer.py ModelRenderer._render` | `self._torque_filter.update(b if (b := accord_eps_bar(...)) is not None else -actuatorsOutput.torque)`: the orange cue marks lane torque > 60 % of rail, torque-mode sign (+ = right); param off: 0 as today | same |
| F8 | `cereal/custom.capnp StarPilotCarState` + `card.py Car.state_publish` + `carcontroller.py` | new **`accordAngleStatus @31 :UInt16`** = 4·rate/jerk-bound + 8·EPS-torque stale/bad (from CS) + 16·clip-bound (1/2/32/64 reserved, 0); card sets `FPCS.accordAngleStatus = int(getattr(self.CI.CC, "angle_status", 0))` before publishing (carOutput's pairing). **`actuatorsOutput.torque` untouched** | — |
| F9 | `values.py`, `interface.py _get_params` | `FAMILY = b"39990-TVA,A16"`; `is_angle_fw(v) = v.startswith(FAMILY) and len(v) == 14 and 65 <= v[13] <= 90` (A16A, A16B…). **A160 (V294/V295 `39990-TVA,A160` @0x13100, EVIDENCE) excluded**, which the bare prefix would not do | — |
| F10 | `params_keys.h`; `safe_mode.py`; `device_settings_layout.json` | the three keys `{PERSISTENT, FLOAT/BOOL, default, default, 2, SETTINGS_SIMPLE}` (as AccordDobHz), in `SAFE_MODE_MANAGED_KEYS`; AccordEpsAngleLoop text: "A16A/A16B", "no fork override: the EPS fade is the override" | — |
| F11 | `CarController.__init__` | each param read once: `try … except UnknownKeyName → default`; `math.isfinite` else default; clamp | — |
| F12 | `opendbc/car/honda/tests/test_angle_v299.py` | (a) differential vs a vendored `2712e1336` `_update_angle` on an r79 fixture (carState i−1 pairing, ≤ 1 MB): identical raw on every frame outside V298's O1 episodes (inside them the new code follows the limiter, by design); (b) vs recorded `torqueOutputCan` ≥ 99.99 % on the same frames (m4_common: 100 / 99.994 %); (c) `is_angle_fw` A16A/A16B true, A160 / `39990-TVA-A160` / A110 false; (d) bar sign ≥ 0.85 | — |

**Not changed:** SteerDelay / plan lead (later); `SteerRatio` 16.84 pin. **Toggle configs:** `toggle-config_V299-A_bar.json` =
V298 rev-2 config + {BarFromEps true, MaxRate 120, ClipScale 1.0}; REVERT = V298 rev-2 config **and a fork with the override**
(Dom `2712e1336`) — the removal is code, not a toggle. Config B is not written.

**The override is the EPS (binding rule, ruling (i)).** The dir-2 fade record 0xE54FC (sel 7, re-read: X words 512/832/1216/1536/
2048/3072, Y 255/243/218/179/77/77) scales the lane ×0.99 at 600 words, ×0.86 at 1200, ×0.70 at 1536, ×0.30 at ≥ 2048; the I
freezes within a tick at raw 1229 (= Honda `steeringPressed`); the 0.5 s request-drop ramp is unchanged; the setpoint never
follows the hand, so the clip (17° at 3.1 m/s … 4.5° at 26.9 m/s) bounds what P can demand against it. The lane is ≤ 2461 T.

---

## 3. Stability and the time criteria (config A on rev 2)

### 3.1 GATE 2

No gain, table, clamp or operand changes, so every linear block is rev 1's (S1): inner PID 0 R2-box fails (worst PM 39.1°),
PD +17.1°, clip loop 64.1/44.3/33.1°, path loop 59.3°; the O1 loop no longer exists (ruling (i); V298's at lead 0.06 had GM
3.2–1.0 dB). The cap only switches PID ↔ PD. **Declared inherited
shortfalls:** ms_free curve hold PM 6.1–6.3°; at r79's D fraction (D ×0.55, P ×0.93) PID PM **1.6°** (b_lo×ms_free, 11 m/s,
a 2.5, age 10) and **24.5°** non-ms_free (b_lo×J_hi, 8 m/s curve hold; refuter T5). What changes is *occupancy*: V298 sat in PD
5–12 % of hands-off time by the twist freeze, V299 ≈ 0; but on ms_free curve holds at 10–12.5 m/s rev 2's I sits at the 6144
bound 97–100 % of the time (`rev_msfree.py`), i.e. in PD (PM ≥ 39°), not at the 1.6–6.3° PID point. Above 12.5 m/s: PID, as rev 1.

### 3.2 The composite on the common S2 scorer (`rev_s2_row.py` 9.2 s, `rev_noO1.py S2` 11.3 s)

Member r79F, median of seeds 1–3, [worst] both members; stall-surge / O1 = per-speed sums over the r79F seed-1 turn-in + unwind
(rev 1 printed 5/9 and 11/14 for V298 there, an aggregation I could not reproduce; every other V298 cell equals rev 1's).

| cand | t90 s 3/8 | ovs [worst] | tap % [worst] | frz tog/s | I kept 3/8 | stall-surge 3/8 | O1 3/8 | r4–8 3/8 | r1.6–3 3/8 | unwind @3 | LH worst | LH o5 | OV tap % @5 | OV hand T @5 | OV rel ovs | C2 slow 15/25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 1.77/1.80 | 1.6 [2.5] | 54 [60] | 14.7/16.1 | 0.57/0.52 | 11/18 | 25/29 | 8.5/9.1 | 5.1/6.5 | 4.2 | 13.9 | 7.0 | 47 | 372 | 4.4 | 0.99/0.60 |
| rev 2 + G4 fork (record) | 0.99/0.97 | 1.7 [2.9] | 57 [58] | 0/0 | 0.58/0.80 | 2/2 | 2/2 | 3.8/4.6 | 9.0/8.7 | 0.6 | 9.1 | 3.5 | 48 | 425 | 5.1 | 0.95/0.53 |
| **DRIVE = rev 2, no override** | **0.68/0.67** | 1.7 [2.9] | 57 [58] | 0/0 | — | **0/0** | **0/0** | **1.5/2.1** | — | 0.6 | 9.1 | 4.2 | **69** | **1033** | 5.3 | 0.95/0.53 |

Hands-off, the no-override fork is the best row: no relay of any kind and the lowest 4–8 Hz of the three (sim metric; not
comparable with the drive read's on-car 4–8 Hz). The price is under a hand (§3.5). **F4 grid** (§1.2 for rev 2; `rev_noO1.py TI` 8.2 s re-ran it with no override): within
0.2° of the G4 fork everywhere, **0 F4 columns at 45/60/90° ≤ 10 m/s in both engines**. The requested grid (60°, hold 6 s,
`rev_turnin.py`, S2 median [max]; RSN within 0.1°):

| v m/s | 6 | 8 | 10 | 11.75 | 12.5 |
|---|---|---|---|---|---|
| overshoot | −3.0 [−2.9] | 0.2 [0.5] | 2.4 [3.0] | 5.8 [7.7] | 2.5 [3.9] |
| hold error @6 s | 3.3 [3.7] (= V298 3.3 [4.3]) | 0.8 [1.5] | 0.2 [0.3] | 0.6 [1.2] | 0.2 [0.4] |
| unwind past 0, max | 4.7 | 3.6 | 2.3 | 2.6 | 1.5 |
| F4 (≤ 10 m/s) | 0/8 | 0/8 | 0/8 (rev 1 8/8) | — | — |

### 3.3 Costs the cap edit adds, and the unwind per member (EVIDENCE in sim, BELIEF on the car)

**Hold shortfall** in big turns at 6–12.5 m/s, \|err\| @4 s max:
- 60°: 0.3–1.5° (rev 1 0.0–0.1 at 6.5–8 m/s; at 10–12.5 m/s rev 1 is still settling from its overshoot, 1.2–3.0);
- 90°: 3.9–4.3° at 6.5–8 m/s (rev 1 0.1–0.2);
- the inherited ≤ 6 m/s shortfall is unchanged (60° 2.3–3.7°, 90° 4.6–8.6°, V298's 4096 cap).
- On the fork, the path loop (τ_o 1 s) re-asks for the missing angle (BELIEF).

**Unwind past centre after 60°**, median [max] (S2; RSN agrees within 0.6°):

| | 3 | 5 | 8 | 10 | 12.5 m/s |
|---|---|---|---|---|---|
| r79F, V298 → rev 2 | 3.9 [6.2] → 0.6 | −6.0 → 0.6 | −5.1 → 1.2 | 2.6 → 1.6 | 0.8 → 1.5 |
| b_lo×J_hi, V298 → rev 2 | 6.5 [9.1] → 3.8 | 3.7 → 4.4 | 1.3 → 3.6 | −0.1 → 2.3 | −0.6 → 1.0 |

### 3.4 The ms_free curve-hold ring (refuter D4), rev 2 (`rev_msfree.py`, 19.0 s; 2.5 m/s² hold, 1° step, age 10)

- **b_lo×ms_free (friction off):** at 10–12.5 m/s rev 2 has **no ring** (I at the bound, A3 duty 0.97–1.00) but a **steady
  shortfall +3.4 / +1.8 / +0.4 / +2.7°** at 10 / 11 / 11.75 / 12.5 m/s (rev 1 rings 1.0–6.8° first half-peak; V298 0.05–4.1°).
  At 13 m/s rev 2 = rev 1: half-peaks [1.6, 0.76, 0.26] (V298 [0.67, 0.33, 0.09]).
- **b_lo×ms_free_r79F:** no ring and +1.4 to +2.8° shortfall at 10–12.5 m/s; at 13 m/s [0.61, 0.53], 1 tail cycle.
- **r79F (nominal):** rev 2 = rev 1 = V298 within 0.1° (peaks ≤ 0.34°, shortfall ≤ 0.25°).

**Reading.** Rev 2 replaces the ring by a hold shortfall on the ms_free family below 12.5 m/s. F10 is predicted to fire only on that family, and only above 12.5 m/s (13 m/s in the sim). That is a plant-family discriminator, not a predicted failure on the nominal member.

### 3.5 Hands on the no-override fork (fork D3; `rev_noO1.py S2`, `rev_hands.py`; S2 stiff-hand model, BELIEF)

Words 550–2500 raw (wire = raw/1.024), a co-steer 30 % toward centre (c) / outward (o) or a drag to centre (ov), held 1.5–2 s,
released; both members. DRIVE (rev 2, no override) vs V298 (O1 at 600 wire, freeze 512/300):

| hand | 5–8 m/s DRIVE (V298) | 15 / 25 m/s DRIVE |
|---|---|---|
| tap opposing the hand, max / residual at the end | drag 550–1150: **53–75 % / 47–60 %** (V298 34–74 / 13–27); drag 1500: 48–66 / 37–40 (12–21 / 10–12); drag **2500: 23–33 / 17–18** (7–10 / 5); co-steer c 11–43 / 8–42; o ≤ 24 | ≤ 22 / ≤ 21 |
| hand force to hold | drag 550–1150: **1128–1442 T** (V298 317–671, ×2–3.6); drag 2500: 459–535 (159–214); co-steer 62–911 (20–444) | ≤ 467 T |
| **F7** (pressed, ≥ 50 % opposing > 0.5 s) | **no**: longest 40 ms (the fade at > 1229 raw) | 0 |
| **F7b** (\|wire\| > 600 > 0.3 s, ≥ 40 % opposing) | **fires on drags**: 800 words 820–840 ms; 550: 150; 1150: 230 (V298 ≤ 14 ms) | 0 |
| release lurch, max | outward 550–1150: **8.0–9.0°** (V298 1.2–2.9; G4 fork 1.3–8.4); drags 3.5–5.3°; back within 1° in 0.07–0.28 s | ≤ 2.0° |

The ruling's stated consequence (≤ ~20 % of rail under a firm hand) holds for a **firm** hand (2500 words: 17–18 % residual at
5–8 m/s). In the **550–1500-word band** the lane holds 37–60 % of rail against a drag at 5–8 m/s and the hand needs ×2–3.6
V298's force, because neither the setpoint (no override) nor the I (no freeze < 1229) nor the fade (≥ ×0.70) yields much there.
**F3 (> 8° at ≥ 8 m/s) sits at its bar** for outward co-steer at 8 m/s (8.0°; heavy member 9.6° in the G4-fork run), r79F ≤ 4.4°.

### 3.6 The takeover rule (fork D11) — moot under ruling (i); the record

With a G4 override, skipping the 0.4 s ramp after < 50 ms O1 episodes cut post-release stall-surges 7–13 → 3–5 per 12 turns
(refuter's engine) but raised 4–8 Hz at 8 m/s 4.6 → 7.3 and the OV tap 48 → 62 % (S2); T 0.2 s doubled to quadrupled them
(`rev_takeover.py` 9.8 s). Decision had an override been kept: 0.4 s after every release.

---

## 4. Route-79 counterfactuals (EVIDENCE for the rule arithmetic, open loop for torque; `rev_r79.py` = d1_r79 + the rev-2 rule, 3.6 s)

| quantity | V298 | rev 1 (D1c) | **rev 2** |
|---|---|---|---|
| hands-off hand-freeze duty / discarded / toggles per min | 11.4 % / 28.3 % / 325 | 0.4 / 0.8 / 13 | **0.4 / 0.8 / 13** (pressed kept 97.3 %) |
| replay tap, hands-off manoeuvres, p50 / p99 / max (LSB) | 46 / 149 / 199 (R² 0.928) | 57 / 194 / 245 | **53 / 159 / 205** |
| \|I>>7\| p90 (S) / at the A3 bound | 5531 / 4.2 % | 7979 / 19.8 % | **6145 / 29.1 %** |
| rule identity vs V298 (F1's instrument; 30-s windows) | true | V298 wins 18/18, dR² +0.605 | **V298 wins 18/18, dR² p50 +0.541, p10 +0.165** |
| fork O1 episodes / no-press (`cf_fork_r79`) | 415 / 347 | 79 / 30 (G4) | **0 (no override)** |
| stall-surges near a toggle (0–5 · 5–10 · 10–20 m/s) | 22/27 · 56/68 · 6/9 | 9/27 · 26/68 · 1/9 | same |
| bar pinned ≥ 0.9 / p50 / p99 / max | 59.7 % | 0 % / 0.05 / 0.35 / 0.59 | same |

---

## 5. Hazards and fail-safe paths (changes from rev 1 §5; every other row stands)

| path | V299 rev 2 | evidence |
|---|---|---|
| big turn at 6–12.5 m/s | I ≤ 6144 S same-sign (≈ 983 T, 40 % rail), was ≤ ICL 8192; ≤ 6 m/s and > 12.5 m/s = V298 byte for byte | §1 |
| real hand ≥ 1200 wire | I frozen within a tick; fade ×0.86 → ×0.30; **setpoint does not follow** (ruling): clip-bounded; lane ≤ 18 % of rail opposing a 2500-word hand at 5–8 m/s | §2.2, §3.5 |
| moderate hand 550–1500 raw | no freeze, no setpoint yield, fade ≥ ×0.70: lane 37–60 % opposing at 5–8 m/s (BELIEF); the driver still wins (≤ rail) | §3.5; escalation 1 |
| mis-deploy | new fork on V295 (A160), switch ON → FW_MISSING fault; old fork on A16B, switch ON → fault, OFF → torque frames, camera gate zeroes the lane (engaged, no steering, no fault). **Card: pull Dom before flashing; reflash V298 before an old fork** | F9; D7 |
| 0x1AB dead / bad | never touches canValid (ignore_counter, nan); bar 0 after 100 ms; bit 8 | §2.1 |
| the deleted opposing freeze / the deleted fork override | gated only by a reflash to V298 + the 2712e1336 fork (§11.2) | D12 |
| authority | rail 2461 T, OCL 3072, EME/governor/lockstep untouched; tap peak 57 [58] % | §3.2 |

---

## 6. The instrument and the drive card

**The drive read adds** (`drive_read_fastlane.py` / `angle_loop_drive_read.py`, after C13's repairs):
1. **Rule identity with the rev-2 rule** (`rev_r79.py`'s form): V299 vs V298 R² vs the tap per 30-s window (F1); rev 2 vs rev 1 where the bound is active (information).
2. `starpilotCarState.accordAngleStatus` decoded; `co_ang` = the limiter with no O1 on ≥ 99 % of latActive frames.
3. `cs_tqeps == −8·tap` on bit-8-clear frames; bit-8 duty; the drawn bar's sign vs the tap.
4. **The stutter readouts (ruling (ii)), each vs V282:** stall-surges/min, ratchet trains/min of turning, 4–8 Hz wheel-rate modulation, dwells/min; surge enrichment within ±0.25 s of \|bar\| 300/512 (old relay: flat) and 1229 crossings.
5. Per hands-off turn-in: t90, wheel peak, tap peak, overshoot (F4), unwind past centre.
6. **Hold error in hands-off curve holds at 6–12.5 m/s with the replayed A3 bound active** (the cap's cost; §3.3).
7. **The ms_free ring** (F10): θ − θsp band-passed 0.4–0.8 Hz in sustained hands-off curve holds (\|a_lat\| ≥ 1.5 m/s², 10–13 m/s, ≥ 3 s).
8. **Lane torque opposing a hand vs the hand word** (F7, F7b; the §3.5 map on the car); release lurch after every hold (F3/F5).
9. R4 5–30 Hz lines, 13–17 / 18–22 Hz eng/dis; carFw; `ld_lat` 0.35.

**Drive card** (V299's first drive = the angle loop's drive 2; config A only; ~15–30 s of symptomatic frames per item; the operator stops at the first ratchet or grind):
- **Prerequisites:** car LKAS **off**; **pull Dom (F1–F12) and Rebuild Params BEFORE flashing**; flash V299 (operator names file
  and bus; openpilot killed), reboot; restore config A, reboot; check carFw `39990-TVA,A16B`, angle mode, `SteerRatio` 16.84,
  `accordAngleStatus` present, the bar moving with the wheel's push, no fault.
- **1, note 4:** 30 s of engaged turning at 3–10 m/s with hands verifiably off (hovering clear of the rim; the read keeps frames with \|wire\| < 300 and not pressed). Include two hands-off turn-ins ≥ 45° (one at ~3–5 m/s, one at ~8 m/s) and their returns.
- **2, note 2:** two hands-off 60–90° turns at ≤ 8 m/s, one ≥ 45° turn at ~10 m/s (F4's edge), and ≥ 3 s of hands-off sustained curve at 10–12.5 m/s (a roundabout or ramp: items 7 and 8).
- **3, hands (no fork override, ruling):** a light 1–2 s co-steer hold then release at ~5, ~15 and **~25 m/s**; one firm grab and a hand-steered turn. **Expect more resistance than V298 under a moderate hand** (§3.5); stop at "fights my hands" (F7/F7b).
- **4:** 60 s of highway hands-off lane keeping.
- Glance at the bar throughout: lane torque as a fraction of the 6× rail.

**The sentence a null licenses.** *If F1 passes and the surge enrichment at 300/512 crossings is flat, yet the operator still
reports stutter, the freeze relay was not the ratchet's mechanism*: stop iterating the integral policy; next is the small-
correction stick (M1). *If item 6 shows > 3° shortfall with the bound active in ≥ 50 % of 6–12.5 m/s curve holds*, 6144 is too
low for this car (the ms_free reading); the next dose is 7168, re-scored first against F4 at 10 m/s.

---

## 7. Pre-registered FAIL criteria — do not fly again if any holds

| # | criterion | means |
|---|---|---|
| F1 | the rev-2-rule replay does not beat the V298-rule replay (pooled dR² < +0.05, or < 2 of the ≥ 2-s hands-off windows), carFw ≠ A16B, `accordAngleStatus` absent, or any O1-like setpoint snap | not live / mis-built: interpret nothing else |
| F2 | ring presence > 0.5 %, F7 > 0 per 100 s, a new 5–30 Hz line; 18–22 Hz eng/dis > 2.5 or 13–17 Hz > 3.5 | revert |
| F3 | after a hand release: \|θ − θsp\| > 8° within 1.5 s at ≥ 8 m/s, a swing > 5° past the setpoint on a straight, or the operator reports a lurch. **Predicted:** 8.0° at 8 m/s for 550–1150-word outward holds (no override, at the bar); r79F ≤ 4.4°; the heavy member up to 9.6° (§3.5) | revert |
| F4 | a hands-off turn-in at ≤ 10 m/s overshoots θsp by > 6°, or by > 15 % on a turn ≥ 45°. **Re-scoped from rev 1:** on turns < 45° at ≤ 4 m/s only the 6° bar applies, because the % clause is predicted to fire there on the heavy member (rev 1 = rev 2: 4.1–6.8° at 30°; r79F ≤ 4.2°; V298 ≤ 2.9°). Predicted at ≥ 45°: ≤ 5.2° | windup beyond the model; revert |
| F5 | a light-hand episode (300 < \|word\| < 1229, ≥ 1 s, not pressed) ends > 4° behind θsp toward centre (G4-fork sim droop ≤ 2.6°; no override: back within 1° in ≤ 0.3 s) | revert |
| F6 | ratchet trains ≥ 4.7 per minute of turning at 5–10 m/s, or stall-surges near \|bar\| 300/512 crossings ≥ 2× the free rate | freeze was not the mechanism; stop this class |
| F6b | stall-surges near \|bar\| 1229 crossings ≥ 2× free, or hands-off 1229-freeze onsets > 20 per minute of turning | relay one level up → D4b's LP + motion gate |
| F7 | `steeringPressed` with the tap ≥ 50 % of rail opposing for > 0.5 s, or "fights my hands". Predicted: no (longest 40 ms) | revert (firmware + the 2712e1336 fork) |
| **F7b** | \|wire\| > 600 for > 0.3 s with the tap ≥ 40 % of rail opposing the driver (sign(tap) vs sign(wire)), not pressed. **Predicted to FIRE on a moderate drag** (800 words, 5–8 m/s: 820–840 ms; BELIEF) — escalation 1 decides whether it stands | the moderate band fights the hand; revert |
| F8 | `cs_tqeps ≠ −8·tap` on > 0.1 % of bit-8-clear frames, bit 8 on > 0.1 % of latActive frames, any canValid drop in angle mode, or the bar's sign disagreeing with the tap | revert the bar/parser change only |
| F9 | lane tap > 250 LSB on any hands-off frame, or ≥ 230 for > 0.3 s (predicted peak ≈ 175–180; r79 replay max 205) | authority beyond the envelope; revert |
| **F10** | in a sustained hands-off curve hold at 10–13 m/s: the 0.4–0.8 Hz component of θ − θsp shows a half-peak > 1°, or > 2 consecutive half-cycles ≥ 0.5°. Predicted: no on r79F (≤ 0.34°); yes on the ms_free family above 12.5 m/s (below it the I sits at the cap: no ring) | the car is ms_free-like and V299 removed V298's incidental damping; revert |
| X3 (**later dose only**: cap 250 OR clip ×1.6, one per drive) | hands-off 1229-freeze onsets on ≥ 50 % of turn-ins at ≤ 8 m/s (the faster twist, p99 1100–1240 in sim, straddles 1229), or stall-surges per turn ≥ 2× drive 2's | the dose re-arms a relay at 1229; stop the dose |
| R9 | the operator reports grinding, ratcheting, vibration or anything new | his call; outranks every band |

---

## 8. Declared misses (each sized, each covered)

| id | miss | size | cover |
|---|---|---|---|
| M1 | small-correction stick not addressed | C10 row 1 | next class (fork quantiser + breakaway) |
| M2 | 1.6–3 Hz criterion: **replaced by the stutter readouts (ruling ii)**; for the record DRIVE n/a, G4 fork 9.0/8.7 vs V298 5.1/6.5 | — | readout 4 |
| M3 | hand-steered turns: no co-steer authority | unchanged | escalation 2 |
| M4 | 30° turns at ≤ 4 m/s on the heavy member 4.1–6.8° | §1.2 | F4 re-scope |
| M5 | **moderate-hand resistance with no override**: 37–60 % of rail, hand ×2–3.6 V298's at 5–8 m/s; outward release 8–9° | §3.5 | F7b, F3, escalation 1 |
| M6 | hold shortfall 6–12.5 m/s (90°: 3.9–4.3°; ms_free holds 1.4–3.5°); inherited ≤ 6 m/s ceiling (90°: 4.6–8.6°) | §3.3–3.4 | readout 6; later 7168 |
| M7 | ms_free ring above 12.5 m/s (1.6° first half-peak at 13 m/s) | §3.4 | F10 |
| M8 | highway authority and the later dose untested | — | X3 |
| M9 | SteerDelay / plan lead left out | — | D2b later |
| M10 | plant family matches r79 only at 10–13 m/s; twist R² 0.31; stiff-hand model | — | every sim number is BELIEF |

---

## 9. Class and arc

V298's angle loop byte for byte; only the **integral policy** changes: which hand stops the I (Honda's level), how far it winds
(asymmetric bound; a cap through 12.5 m/s). Not a dose on a flown lever: the opposing freeze was V298's own and route 79 measured
it as the ratchet's mechanism; the sign-of-angle bound and a cap above 6 m/s are carried by no image. Arc: V38–V52 authority /
filters / caves · V53–V61 probes · V62–V73 rate lane · V74–V84 damper · V282–V292 the EPS rate loop · V293 torque mode ·
V294/V295 accel trim (failed their goal) · V298 the angle loop. **Dropped:** the 300 opposing and 512 hard freezes, the fork's
override (O1, lead; ruling), config B. **Kept on evidence:** the ≤ 6 m/s cap 4096, Kd 48, the clip, the camera gate, the
op-skip, A2/B2, the fade. One cave, 260 B, 0 RAM.

---

## 10. Escalations — the operator's (and the orchestrator's) decisions

1. **The no-override fork, scored (decision-bearing; BELIEF on the S2 hand model).** Hands-off it is the best candidate: 0 O1,
   0 stall-surges, 4–8 Hz 1.5/2.1 deg/s (V298 8.5/9.1), t90 0.68/0.67 s. Under a hand: firm (2500 words) ≤ 18 % residual, as the
   ruling said; **moderate (550–1500 words) 37–60 % of rail opposing a drag at 5–8 m/s, hand force ×2–3.6 V298's, F7b predicted
   to fire at 800 words**; OV drag at 1500 words 1033 T vs 372. Options: (a) fly as ruled and read F7b/§6 item 8 on the car;
   (b) re-scope F7b to "fights my hands" only; (c) a firmware step instead of a fork override (a lower freeze level or an earlier
   fade knee — re-arms the twist relay unless designed against it). Not decided here.
2. **Note 2 under a hand.** Every design yields to a firm hand; r79's hard manoeuvres were hand-steered; co-steer authority is unproposed.
3. **The cap structure (overrides the orchestrator's "2 immediates, 4 bytes").** The 4-byte form trips F4 at 3 m/s (§1.2); rev 2
   builds the two-level form (38 more bytes, same span, H1-exact). Alternative on file: alt4 `7e827872…` (re-score 3–4 m/s first).
4. **The family prefix:** `b"39990-TVA,A16"` literally matches V295's A160; rev 2 requires a trailing letter.
5. **F4 re-scoped** for turns < 45° at ≤ 4 m/s (§7). Accept, or fix the low-speed windup first.
6. **The ms_free trade:** ring at 10–12.5 m/s exchanged for a 1.4–3.5° shortfall on that family; rev 1's ms_free GATE 2 ruling stands.
7. **REVERT now needs a fork too** (the override removal is code): V298 + Dom `2712e1336`.

---

## 11. Build round — prerequisites, rwd plan, CRC plan ("do not flash" reachable at every step)

### 11.1 Prerequisites (each must PASS before anything is offered for flashing)
1. **Golden model:** `_self_check_v299` mirroring `cave_rev2` (§1.3) bit for bit against `rev_h1`'s cases. Contract **94 → 95 symbols**. `_self_check()` + `_demo()` stdout hash `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` **unchanged** (prints nothing).
2. **Build script** (`builds/v108_plus/build_v299_tva.py`, from V298's): patch **by address** (assert old bytes); assert image
   **`30ff05fa…`**, cave **`e22193b9…`**, trailer `95 3b dd 70`, diff = the 67 attributed bytes; census the assertions.
3. **H1 on the BUILT image:** `rev_h1.py` reading the cave from the written image, not the hex. 0 mismatches random + targeted. Negatives > 0: rev-2 bytes vs the rev-1 mirror ≥ 1 %, and vs the single-6144 mirror.
4. **Ghidra** decode of the BUILT image 0xC4C00–0xC4CD9 = §1.1.
5. **Four-lens adversarial pass on the built image:** arithmetic / unit-scale / build-script audit (independent rebuild to `30ff05fa…`, CRC chain, bootloader replay) / interlocks and downstream. Each writes its FAIL condition first; "do not flash" must be reachable.
6. **Fork:** F12 tests pass (the differential identical outside V298's O1 episodes).

### 11.2 rwd plan (template = the V38 container as V298's build; `encode_x31`/`parse_x31`; '!' kept parallel)

| file | '/' header (read back by `parse_x31` and asserted) | payload assertion |
|---|---|---|
| V299 `39990-TVA,A160-V299-…-0x13000-0x100000.rwd` | `39990-TVA-A110`, `39990-TVA,A160`, **`39990-TVA,A16A`** (what the car reports on V298), **`39990-TVA,A16B`** (re-flash) | decodes byte-identical to the built image `30ff05fa…`; x31 checksum; cipher validated non-circularly on V38 |
| V298 revert `…V298-REHEADERED-FOR-REVERT-FROM-V299-A16B-…rwd` | from the V298 rwd (sha `1a69b927…`, '/' = A110, A160, A16A — read this session) **+ A16B** | `encs` == the V298 rwd's; decodes to `177abf04…`; original re-hashed before and after |
| V295 revert `…V295-REHEADERED-FOR-REVERT-FROM-V299-A16B-…rwd` | from the original V295 rwd (`f42a06bd…`, '/' = A110, A160) + A16A + **A16B** | `encs` == the original's; decodes to V295 `5c044d65…`; original untouched |

Generalise V298's `header_add_a16a` to `header_add(headers, [strings])`. Exactly one flashable `.rwd` per build number. Push the image and the rwds to `accord-firmwares`.

### 11.3 CRC plan

1. Recompute the main trailer [0x13000, 0xC4FFC) → `95 3b dd 70`.
2. **Assert** `walk_all_blocks(img) == 0` (chain 50/50) **and** `walk(img) == 0` (bootloader replay 49/49, the NRC 0x72 predictor) on the built image. Both are 0 on the in-memory rev-2 image this session.
3. Assert no edit straddles a block: 0x1310D and 0xC4C64–CAB are in [0x13000, 0xC4FFC).

---

## A. What I ran (all < 30 s; `v299_design/revise/`; outputs `_scratch/v299_REV2/`)

`rev_control` 6.1 s (transformed engines == originals bit-exact; switches live) · `rev_bytes` 1.3 s (§1.1; rev 1 reproduces
`ac15b533`; chain/boot 0 bad; rwd headers) · Ghidra dry-run on the scratch import · `rev_h1` 4.9 s + `rev_h1_regs` 2.1 s (§1.4) ·
`rev_turnin` 17.9 s, `rev_cap_size RSN/S2` 12.5/8.2 s, `rev_summary` (§1.2, §3.2–3.3; S2 re-run bit-identical after the loader
change) · `rev_s2_row` 9.2 s · `rev_hands` 8.6 s · `rev_takeover` 9.8 s · `rev_noO1 S2/TI` 11.3/8.2 s · `rev_msfree` 19.0 s · `rev_r79` 3.6 s · `rev_bar_sign`,
`rev_1ab_gap` < 0.1 s. Inherited: S1's GATE 2 tables, `cf_fork_r79`, `d1_427_check`.
