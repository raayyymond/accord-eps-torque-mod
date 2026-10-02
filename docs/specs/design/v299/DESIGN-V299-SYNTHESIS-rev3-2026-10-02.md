# DESIGN V299 — SYNTHESIS rev 3 (2026-10-02): the build brief, the criteria and the hand layer resolved

**Status: BUILD BRIEF. Nothing built, flashed, sent or committed. The fork, firmware, golden model, STATE, lineage and git are untouched.**
**The firmware is unchanged from rev 2:** same 67 bytes, image `30ff05fa…`, cave `e22193b9…`, trailer `95 3b dd 70`. §1 is
rev 2's, carried verbatim.

**Author.** The REVISER (rev 3) subagent.

**Supersession.** This supersedes rev 2 (`DESIGN-V299-SYNTHESIS-rev2-2026-10-02.md`) as the brief. Rev 1 and rev 2 stay as the record.

**Inputs.**
- The three rev-2 re-refutations (`v299_design/refute/REFUTE-V299-rev2-*.md`): firmware PASSED every dynamics attack; the open items were the criteria and the hand layer.
- The operator's rulings of 2026-10-02.

**What counts as EVIDENCE:**
- image bytes;
- the Ghidra listing (rev 2, re-done by the bytes refuter);
- the route-79 caches;
- fork source at Dom `2712e1336`;
- a script run this session, named in §A with its wall time.

**What counts as BELIEF:**
- a model: the r71b plant family, the S2 stiff-hand model, the RSN engine's force hand;
- an inference.

Bands are scored here; the operator scores symptoms. **Classifier interruptions in this revision: 0.**

---

## 0. What changed from rev 2 (every open item → its resolution; nothing waived)

**Binding operator rulings (2026-10-02):**
- **(i) No fork override.** The EPS hand fade plus the firmware freeze above raw 1229 *are* the override.
- **(ii) The hard-turn 1.6–3 Hz criterion is REPLACED** by the stutter readouts:
  - stall-surges per minute;
  - ratchet trains per minute of turning;
  - 4–8 Hz wheel-rate modulation;
  - dwells per minute.

  Each is scored against V282 (r6c/r39). There must also be no surge enrichment within ±0.25 s of a hand-torque threshold crossing, now at 1229.
- **(iii) Drive 2 flies config A** (the bar, no override). Cap 250 is an OPTIONAL later dose on the same firmware (§7.3).

| open item (re-refuter) | resolution in rev 3 | § |
|---|---|---|
| D-N1 (stab, HIGH): F3/F5 as written read the hand's own hold, not a lurch, so they fire by construction | **Redefined relative to the release edge.** F3 = the swing *past θsp, away from the hand side*, within 1.5 s. F5 = (θsp − θ) toward centre at release + 1.5 s. The release edge is defined (§7.1). Both are re-predicted from the S2 hand rows and cross-checked on RSN (`r3_release_rows.py`) | 3.5, 7 |
| N6 (fork, MED): F3 fires with no wheel motion (38/155 r79 releases start > 8° from θsp) | Same fix. The release-instant gap is now printed as information (`gap`), never as a criterion | 3.5, 7 |
| D-N2 (stab, HIGH): the outward light co-steer release lurch was under-sized | **Re-sized at realistic holds**: 8 m/s 20°, 10 m/s 15°, 15 m/s 8° (plus 5/12.5/25 m/s), ages 1–4 s, both members, both engines (agree within 0.4°). **Heavy member: 9.7–10.4° at 5–10 m/s; r79F: 4.4–6.1°.** Stated as a predicted cost with speed-banded bars (12/9/8°). The operator decides it before the drive (escalation 1) | 3.5, 7, 10 |
| D-N3 (stab, MED): the F4 re-scope contradicted itself | **F4 split into three cells**, no contradiction: F4a ≥ 45° ≤ 10 m/s, bar 6° (pred ≤ 5.2°); **F4b 20–45° ≤ 4.5 m/s, its own bar 8.5°** (pred 7.0° heavy); F4c 20–45° at 4.5–10 m/s, bar 6° (pred ≤ 4.6°). **The 15 % clause is deleted explicitly**: at ≥ 45°, 15 % ≥ 6.75° > 6°, so it could never bind first | 7 |
| D-N4 (stab, MED): the cap shortfall was under-sized | **Printed at its real size:** 3–7° at 8–10 m/s on 2.5 m/s² curves (ms_free members), up to 7.4° at 3.5 m/s². Nominal r79F: 3.2° at 8 m/s, ≤ 0.1° at 10 m/s. The drive-read null sentence that licenses 7168 is given (§6.2) | 3.3, 6.2 |
| D-N5 (stab, LOW): A3-edge toggles inflate a freeze-onset count | **F6b counts only \|w\| > 1229 hard-freeze onsets.** The A3-bound "wind" freezes, which toggle 33–45 /s at the 2880 edge under v-word jitter with ≤ 0.09 deg/s of 1–10 Hz rate, are excluded | 7 |
| D-N6 (stab, LOW): tap peak predicted 175–180 | **Corrected to ≤ 207 LSB** (both engines, 15 m/s; 184–193 at 6–8 m/s; r79 replay max 205). F9's 250 bar holds | 3.2, 7 |
| D-N7 (stab, LOW): the DRIVE row's 1.6–3 Hz cell was blank | **Filled as a readout**, from the re-refuter's §2. It is not a criterion (ruling ii) | 3.2 |
| moderate-hand band (fork §4, stab §3) | **Stated as the ruling's declared cost:** 37–60 % of rail against a drag at 5–8 m/s in rev 2's rows; 53–63 % residual and 66–82 % max at the realistic holds; 2–3.6× V298's hand force. r79 exposure: 22.1 s per 11 min. Model-based. **F7b is now an OBSERVATION; the operator's own report (R9: "fights my hands") is the criterion** | 3.5, 7 |
| N2 / bytes §6: "0x1AB has no CHECKSUM" was false | **Corrected.** Both DBCs declare `CHECKSUM 19\|4`, and the parser checks it. Rev 3 sets **`ignore_checksum = True` and `ignore_counter = True`** so `vl_raw` always refreshes. The carstate `honda_checksum` is the single meaningful gate; it is the same function as opendbc's for an 11-bit address (EVIDENCE, both read) | 2.1 |
| N1: the F12 differential cannot pass as written (5.72 % of out-of-O1 frames differ) | **Exact identity test:** the vendored `2712e1336` `_update_angle` with `ANGLE_OVERRIDE_ON = ANGLE_OVERRIDE_OFF = inf` must be identical on **100 %** of frames. The false header sentence is removed | 2.2 |
| N3: `is_angle_fw` vs the padded fwVersion `…A16A\x00\x00` | **`v = v.rstrip(b"\x00")` inside the predicate.** The padded r79 literals are added to the test | 2.2 |
| N4: the old test file asserts O1 | **`tests/test_honda_accord_angle_loop.py` is rewritten** in the same commit: O1 tests deleted; census → `{"apply_angle_last"}`; FW import → the family helper | 2.2 |
| N5: V294 revert not re-headered for A16B | **V294 retired as a revert target** (declared). The reverts are V298 (primary) and V295 | 11.2 |
| N7: the extractor lacks `accordAngleStatus` | Pin `FORK_COMMIT` to the V299 commit, add the field, and assert presence ≥ 99 % before F1 is scored | 6, 11 |
| N8: the bar freezes if 0x18F stops | The bar is 0 when `not CS.canValid` | 2.2 |
| the V299 rule in the drive read | **Implemented and checked.** See the note below this table | 6.1, A |
| REVERT | **Re-headered V298 rwd (lists A16B) + Dom `2712e1336` + `toggle-config_V298_angle_loop.json`.** The override removal is code, so the fork must roll back too | 10, 11.2 |

**The V299 rule in the drive read (row above), in detail.**
- **Where:** `drive_read_fastlane.py` now carries `ARB_V299`, `static_freeze`, `arb_bound` and `v299_cand`, and `angle_loop_drive_read.replay_cands()["V299"]` exposes it.
- **Equality with the bytes:** the rule equals `cave_rev2` on 0/6000 random and edge cases. H1 already proved `cave_rev2` equal to the rev-2 bytes.
- **The check can fail:** it shows 81 mismatches against the rev-1 caps and 1236 against V298's rule.
- **The V298 lane did not move:** 0 differing words on r79, and the full read gives 7/7 cache hits at 6.7 s.
- **It discriminates:** on route 79 (V298 flew), V298's rule wins 23/25 windows.

---

**§1 below is rev 2's, carried verbatim (the bytes, the hashes, the mirror and its verification); the bytes re-refuter independently rebuilt it bit-exact (`refute/rev2_bytes/re_build.py`: cave `e22193b9…`, image `30ff05fa…`, trailer `95 3b dd 70`, 67 bytes, 26/26 old-byte asserts) and re-decoded it in Ghidra on a fresh analysis-free import (PASS_WITH_DEFECTS; its one defect is the 0x1AB text, fixed in §2.1).**

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

## 2. Fork update (StarPilot Dom on `2712e1336`; one commit; every param defaults to V298's value)

**What the override removal changes.** The O1 episodes themselves, and the limiter's continuation after each of V298's O1
releases. V298 restarted the limiter from the wheel at every release; V299 continues from its own clipped last output. On r79
the post-release divergence windows run p50 6, p90 13 and max 167 frames, and 5.72 % of the out-of-O1 frames differ
(fork re-refuter N1, EVIDENCE). With the override disabled in V298's own code, the new limiter is identical (§2.2 F12a).

### 2.1 0x1AB (427 STEER_MOTOR_TORQUE), corrected (EVIDENCE: the DBC, the generator source and the parser at `2712e1336`)

- **The message.** `honda_accord_2017_can_ext_generated.dbc` and `_honda_common.dbc` both declare, on `BO_ 427`:
  - `CHECKSUM 19|4@0+`
  - `COUNTER 21|2`
  - `MOTOR_TORQUE 1|10@0+`
  - `CONFIG_VALID 7|1`
  - `OUTPUT_DISABLED 22|1`

  **Rev 2's "there is no CHECKSUM" was wrong.** Both re-refuters caught it.
- **How the parser treats it.** `can/dbc.py get_checksum_state` attaches `honda_checksum` to any signal named CHECKSUM in a `honda_*` DBC. `MessageState.parse` drops a frame with a bad checksum *without updating `vl_raw`*, unless `ignore_checksum` is set.
- **The fix.** On the 0x1AB state set **both `ignore_checksum = True` and `ignore_counter = True`**, as is already done for 0x201. Then `vl_raw` refreshes on every frame.
  - The carstate check `hondacan.honda_checksum(0x1AB, None, raw) == raw[2] & 0xF` becomes the single gate.
  - Bit 8 then means **stale OR bad**, and both meanings can fire.
- **The checksum function is the same one** (EVIDENCE, both sources read). For an address ≤ 0x7FF, opendbc's `honda_checksum` reduces to the kit's `d1_427_check.honda_checksum`: the nibble sum of the address, then of every byte with the last byte's high nibble only, then `(8 − s) & 0xF`. The extended-address branch does not apply to 0x1AB. So route 79's **100.000 %** checksum pass carries over to the fork's own check.
- **No effect on `canValid`.** 0x1AB is listed with `float("nan")`, so `ignore_alive` is set, and the counter is ignored. It can never drop `canValid` (EVIDENCE, bytes re-refuter §6).
- **Staleness** is clocked against 0x18F's timestamp. On route 79 the 0x1AB gaps run p50 20.1 ms and p99.9 30.8 ms, and the only two gaps > 100 ms coincide with 0x18F's own. If `not CS.canValid`, the bar is 0 (N8).

### 2.2 The change table (ruling (i): no override state)

| # | file / function | the diff in words | param (default → config A) |
|---|---|---|---|
| F1 | `values.py CarControllerParams`; `CarController.__init__` | per instance `ANGLE_LIMITS = dataclasses.replace(…, MAX_ANGLE_RATE = rate/100)`; `apply_steer_angle_limits_vm` keeps `min(VM jerk, MAX_ANGLE_RATE)`. **Later dose only** (§7.3) | `AccordAngleMaxRate` 120 → 120; clamp [60, 250] |
| F2 | `_update_angle` (error clip) | `error_max = interp(v, BP, V_s)`, V_s = the knots at BP ≤ 11.75 × s, 17.5/26.9 unchanged; exact band 11.75–17.5 m/s: 17·s + (8.5 − 17·s)(v − 11.75)/5.75. **Later dose only** | `AccordAngleClipScale` 1.0 → 1.0; clamp [1.0, 1.6] |
| F3 | `_update_angle`; `values.py` | **override removed (ruling i):** delete `self.angle_override`, the O1 branch (`θ + rate·lead`) and `ANGLE_OVERRIDE_ON/OFF/LEAD_S`. The limiter restarts from the wheel only on the first frame and the latActive rising edge (with latActive false `apply_steer_angle_limits_vm` returns the wheel angle, `lateral.py`). The clip is the only setpoint–wheel bound | — (code) |
| F6 | `carstate.py get_can_parsers` + `update` | only when `CP.flags & EPS_ANGLE_LOOP_FW`: list `("STEER_MOTOR_TORQUE", float("nan"))` on pt, then **`ms = message_states[0x1AB]; ms.ignore_checksum = True; ms.ignore_counter = True`**. In `update`: a frame is good if `len(raw) == 3` and `honda_checksum(0x1AB, None, raw) == raw[2] & 0xF`; on a good new frame store `s10 = (−1 if raw10 & 0x200 else 1)·(raw10 & 0x1FF)` and its ts. `fresh = ts(STEER_STATUS) − ts_good ≤ 100 ms and CS.canValid`; `ret.steeringTorqueEps = −8·s10 if fresh else 0.0` (+ = left) | — |
| F7 | `selfdrive/ui/onroad/starpilot/torque_bar.py` | helper `accord_eps_bar(sm, CP)` → `clip(−carState.steeringTorqueEps/2461, −1, 1)` when angle mode + angle-loop FW + the param, else None; `TorqueBar._update_state` uses it before the lateral-accel branch. The mici HUD imports the same `TorqueBar` (EVIDENCE). Test: sign agreement with today's bar ≥ 0.85 on r79 (0.854) | `AccordAngleBarFromEps` false → **true**; read once (UnknownKeyName → false) |
| F7m | `selfdrive/ui/mici/onroad/model_renderer.py ModelRenderer._render` | `self._torque_filter.update(b if (b := accord_eps_bar(...)) is not None else -actuatorsOutput.torque)`; param off: 0 as today (r79: `actuatorsOutput.torque` 0 on all 121,383 frames) | same |
| F8 | `cereal/custom.capnp StarPilotCarState` + `card.py` + `carcontroller.py` | **`accordAngleStatus @31 :UInt16`** (`@31` free, EVIDENCE) = 4·rate/jerk-bound + 8·EPS-torque stale-or-bad + 16·clip-bound (1/2/32/64 reserved, 0); card sets it before publishing. `actuatorsOutput.torque` untouched | — |
| F9 | `values.py`, `interface.py _get_params` | `FAMILY = b"39990-TVA,A16"`; **`def is_angle_fw(v): v = v.rstrip(b"\x00"); return v.startswith(FAMILY) and len(v) == 14 and 65 <= v[13] <= 90`**. The car reports `b'39990-TVA,A16A\x00\x00'` (16 B, r79 EVIDENCE). A160 ('0' = 48) is excluded, which the bare prefix would not do | — |
| F10 | `params_keys.h`; `safe_mode.py`; `device_settings_layout.json` | the three keys (as AccordDobHz), in `SAFE_MODE_MANAGED_KEYS`; AccordEpsAngleLoop text: "A16A/A16B", "no fork override: the EPS fade is the override" | — |
| F11 | `CarController.__init__` | each param read once: `try … except UnknownKeyName → default`; `math.isfinite` else default; clamp | — |
| F12 | `opendbc/car/honda/tests/test_angle_v299.py` **and the existing `tests/test_honda_accord_angle_loop.py`** | (a) **exact identity**: a vendored `2712e1336` `_update_angle` with `ANGLE_OVERRIDE_ON = ANGLE_OVERRIDE_OFF = float("inf")` (O1 can never fire, so no release restart) vs the new code on an r79 fixture (carState i−1 pairing, ≤ 1 MB): **identical raw on 100 % of frames**; (b) the new code vs recorded `torqueOutputCan` only on frames outside V298's O1 episodes **and** outside each post-release convergence window (until the two first agree), ≥ 99.99 %; (c) `is_angle_fw`: `b'39990-TVA,A16A'`, `b'39990-TVA,A16B'`, **`b'39990-TVA,A16A\x00\x00'`, `b'39990-TVA,A16B\x00\x00'`** true; `b'39990-TVA,A160'`, **`b'39990-TVA,A160\x00\x00'`**, `39990-TVA-A160`, A110, A150 false; (d) bar sign ≥ 0.85; (e) **the old file rewritten**: O1/lead tests deleted, the state census → `{"apply_angle_last"}`, `HONDA_ACCORD_EPS_ANGLE_LOOP_FW` → `is_angle_fw` (its padded fixture is the right shape); (f) 0x1AB: a frame with a corrupted checksum leaves `steeringTorqueEps` at its last good value until 100 ms, then 0, and never drops `canValid` | — |

**Not changed:**
- SteerDelay / plan lead (later work);
- the `SteerRatio` 16.84 pin.

**Toggle configs:**
- **Config A:** `toggle-config_V299-A_bar.json` = `toggle-config_V298_angle_loop.json` (rev 2) + {BarFromEps true, MaxRate 120, ClipScale 1.0}. MaxRate and ClipScale equal their defaults, so the only live entry is `AccordAngleBarFromEps true` (EVIDENCE, the Galaxy coercion path; fork re-refuter §2 row 9).
- **REVERT is not a toggle config.** It needs the `2712e1336` fork (§11.2).
- **Config B (cap 250)** is not written until drive 2 passes (§7.3).

**The override is the EPS (ruling i).**
- **The fade.** The dir-2 fade record 0xE54FC (sel 7; X words 512/832/1216/1536/2048/3072, Y 255/243/218/179/77/77) scales the lane by ×0.99 at 600 words, ×0.86 at 1200, ×0.70 at 1536, and ×0.30 at ≥ 2048.
- **The freeze.** The I freezes within a tick at raw 1229 (= Honda `steeringPressed`).
- **The request drop.** The 0.5 s request-drop ramp is unchanged.
- **The setpoint never follows the hand.** The clip (17° at 3.1 m/s … 4.5° at 26.9 m/s) therefore bounds what P can demand against it.

---

## 3. Stability and the time criteria (config A on rev 2's firmware = THE DRIVE)

### 3.1 GATE 2 — unchanged from rev 2 (the bytes did not move)

**Rev 1's linear blocks, inherited.** No gain, table, clamp or operand changed, so every linear block is rev 1's:
- inner PID: 0 R2-box fails (worst PM 39.1°);
- PD: +17.1°;
- clip loop: 64.1 / 44.3 / 33.1°;
- path loop: 59.3°.

The O1 loop no longer exists. The cap only switches PID ↔ PD.

**Declared inherited shortfalls:**
- ms_free curve hold: PM 6.1–6.3°.
- At r79's D fraction: PID PM 1.6° on b_lo×ms_free, 11 m/s; 24.5° on non-ms_free.
- On ms_free holds at 8–12.4 m/s the I sits at the bound (A3 duty 1.00, re-refuter §4), i.e. in PD (PM ≥ 39°).

**Re-refuter RA (a new linear-loop margin failure) did not fire.**

### 3.2 The composite on the common S2 scorer (rev 2's rows; one cell filled, one corrected)

| cand | t90 s 3/8 | ovs [worst] | tap % [worst] | frz tog/s | stall-surge 3/8 | O1 3/8 | r4–8 3/8 | **r1.6–3 3/8 (readout)** | unwind @3 | LH worst | OV tap % @5 | OV hand T @5 | C2 slow 15/25 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V298 | 1.77/1.80 | 1.6 [2.5] | 54 [60] | 14.7/16.1 | 11/18 | 25/29 | 8.5/9.1 | 5.1/6.5 | 4.2 | 13.9 | 47 | 372 | 0.99/0.60 |
| **DRIVE = rev 2 fw + no-override fork** | **0.68/0.67** | 1.7 [2.9] | 57 [58] | 0/0 | **0/0** | **0/0** | **1.5/2.1** | **4.7 / 5.9** † | 0.6 | 9.1 † | **69** | **1033** | 0.95/0.53 |

† **r1.6–3**, from the re-refuter's §2 grid (linear plan, 60/90°, median over members × seeds; a different aggregation from
the row's other cells):

| engine | system | 3 m/s | 5 m/s | 8 m/s |
|---|---|---|---|---|
| S2 | R2 | 4.7 | 4.8 | 5.9 |
| S2 | V298 | 6.1 | 6.1 | 5.6 |
| RSN | R2 | 3.9 | 4.0 | 4.9 |
| RSN | V298 | 5.3 | 5.5 | 5.5 |

Units are deg/s.
- **The re-refuter's "lower at every speed" is not quite right.** S2 at 8 m/s is +0.3 deg/s *above* V298.
- **This is a readout under ruling (ii), not a criterion.** On the car, V298 read 8.48 against V282's 3.45–4.02.

† **"LH worst" 9.1°** was rev 2's S2 light-hand lurch at S2's small holds. **The realistic-hold numbers are in §3.5**: up to 10.4° on the heavy member.

**Tap peak (corrected, D-N6).** The maximum over the whole re-refuter grid is **207 LSB** in both engines, at 15 m/s.
That equals V298's simulated 207; V298 reached 226/230 elsewhere in the grid.
- At 6–8 m/s the turn-ins reach 184–193.
- The open-loop replay on route 79 peaks at 205.
- **0 of 768 columns exceed 250.**
- Rev 2's "≈ 175–180" is withdrawn.

**F4 grid (re-refuter `rr_t1`, max over members × 2 seeds × 3 plan shapes, RSN | S2).**

| turn | 3 m/s | 4 | 5 | 6.1 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| 30° | **7.0 \| 7.0** | 5.8 \| 5.7 | 4.6 \| 4.6 | 4.0 \| 3.9 | 3.3 \| 3.3 | 2.8 \| 2.8 | 1.7 \| 1.9 | 2.3 \| 2.5 |
| 45° | 5.2 \| 5.2 | 3.4 \| 3.4 | 1.8 \| 1.8 | 4.6 \| 4.7 | 3.7 \| 3.8 | 3.1 \| 3.1 | 3.0 \| 3.0 | 3.1 \| 3.3 |
| 60° | 2.8 \| 2.8 | 0.6 \| 0.5 | −1.5 | 1.9 | 1.0 | 0.5 | 0.9 \| 0.8 | 3.0 \| 2.9 |
| 90° | −0.8 | −3.8 | −6.3 | −1.9 | −2.5 | −2.4 | −1.0 | 1.4 |

- **V298** on the same grid: 30° ≤ 3.0°; 60° at 10 m/s 6.4–7.4°; 90° at 10 m/s 8.8–9.0°, which is the rev-1 F4 failure the cap removes.
- **The 30°/3 m/s cell is R1N = R2.** It comes from the 1229 freeze and the asymmetric bound, not from the cap.

### 3.3 The cap's hold cost, at its real size (D-N4; re-refuter `rr_t4_msfree.py`, steady sp − θ, R2 vs V298 ≤ 0.1°)

| member | a_lat (m/s²) | 8 m/s | 9 m/s | 10 m/s | 11 m/s |
|---|---|---|---|---|---|
| r79F (nominal) | 1.5 / 2.5 / 3.5 | 0.8 / **3.2** / 3.9 | 0.1 / 0.9 / 1.7 | ≤ 0.1 | ≤ 0.3 |
| ms_free_r79F | 1.5 / 2.5 / 3.5 | 3.2 / **6.4** / 7.4 | 2.0 / **5.8** / 7.3 | 0.6 / **5.1** / 7.3 | 0.4 / 2.8 / 5.4 |
| b_lo×ms_free_r79F | 1.5 / 2.5 / 3.5 | 3.6 / **6.3** / 7.4 | 1.3 / **4.0** / 5.7 | 0.5 / **2.7** / 5.3 | 0.3 / 1.9 / 2.9 |
| b_lo×ms_free | 1.5 / 2.5 / 3.5 | 2.3 / **5.3** / 6.3 | 0.8 / **4.3** / 5.4 | 0.0 / **3.5** / 4.9 | 0.0 / 1.8 / 3.3 |

**Reading:**
- **On 2.5 m/s² curves at 8–10 m/s the shortfall is 3–7° on the ms_free members** (2.7–6.4°).
- At 3.5 m/s² it reaches **7.4°**.
- On the nominal member it is **3.2° at 8 m/s** and ≤ 0.9° from 9 m/s.

The angles are large (8 m/s at 2.5 m/s² ≈ 108° of wheel), so this is 3–7 % of the hold. In the 90° big-turn holds at 6.1–8 m/s
the shortfall is 3.5–4.7°. The inherited ≤ 6 m/s 4096 ceiling is unchanged: 9–27° on 115–190° low-speed curves, R2 ≈ V298.

**BELIEF:** the fork's path loop (τ_o 1 s) re-asks for the missing angle on the car, which these fixed-plan sims do not model.
§6.2 reads it.

### 3.4 The ms_free curve-hold ring (F10) — unchanged

R2 never fires F10 at ≤ 12.4 m/s on any member at 1.5, 2.5 or 3.5 m/s². V298 fires at 11.75–12.4 m/s on two ms_free members.
Above 12.5 m/s R2 fires on b_lo×ms_free:
- 12.6 m/s, at 2.5 and 3.5 m/s²: first half-peak 2.69°;
- 13 m/s, at 2.5 m/s².

This is declared (M7). F10 is a plant-family discriminator, not a predicted failure on the nominal member.

### 3.5 Hands and releases on the no-override fork — the realistic holds (`v299_build/rev3/r3_release_rows.py`)

**Method:**
- **Engines:** S2 (common scorer, via the reviser's loader, which the re-refuter proved equal to its own lane: 0 mismatches) and RSN (the stability refuter's engine, unchanged).
- **Hand:** S2's stiff position hand, Kh 2000 T/deg, Bh 30. BELIEF.
- **Timing:** the word ramps on over 0.3 s, holds 1/2/3/4 s, and releases in 30 ms.
- **Holds** at the curve angle of each speed: 5 m/s 30°, 8 m/s 20°, 10 m/s 15°, 12.5 m/s 10°, 15 m/s 8°, 25 m/s 4°. S2 also ran its own 0.5·A_turn holds.
- **Words:** 300, 550, 800, 1150 (light; no freeze) and 1500, 2500 (firm; pressed).
- **Directions:** co-steer 30 % toward centre (c), co-steer 30 % outward (o), drag to centre (ov).
- **Members:** r79F and b_lo×J_hi.
- **Metrics:** read on the SENT setpoint, as the drive read will. The two engines agree within 0.4°.

**F3 (the swing past θsp away from the hand side, within 1.5 s of release), R2, max over words 300–1150 by hold age 1 / 2 / 3 / 4 s (S2; RSN in brackets where it differs by > 0.2°):**

| hold | member | outward (o) | centre-ward (c) | drag (ov) | firm 1500/2500 (o) | V298, light o (for scale) |
|---|---|---|---|---|---|---|
| 5 m/s 30° | r79F | 4.9 / 4.9 / 4.9 / 4.9 | 1.9 | 1.9 | ≤ 4.9 | 8.9–16.5 |
| 5 m/s 30° | heavy | **10.3 / 10.3 / 10.3 / 10.2** [10.4] | 4.0 | 5.0 | ≤ 10.2 | 13.2–19.0 |
| 8 m/s 20° | r79F | 5.6 / 5.6 / 5.6 / 5.6 | 1.7 | 1.3 | ≤ 4.6 [5.5] | 6.0–16.0 |
| 8 m/s 20° | heavy | **9.9 / 9.9 / 9.9 / 9.9** [10.0] | 3.0 | 3.9 [4.2] | ≤ 8.7 | 9.9–19.0 |
| 10 m/s 15° | r79F | 4.4 / 6.1 / 6.1 / 6.1 | 1.6 | 1.3 | ≤ 1.4 [2.8] | 2.5–11.4 |
| 10 m/s 15° | heavy | **8.4 / 9.7 / 9.8 / 9.7** | 3.0 | 2.1 | ≤ 4.6 | 5.5–17.8 |
| 12.5 m/s 10° | r79F | 1.7 / 4.5 / 5.4 / 5.4 | 0.5 | 0.5 | ≤ 0.4 [1.0] | 1.2–5.7 |
| 12.5 m/s 10° | heavy | 4.2 / 7.7 / 7.9 / 7.9 | 1.7 | 0.9 | ≤ 2.2 | 3.1–8.9 |
| **15 m/s 8°** | r79F | 1.4 / 3.3 / 4.8 / 4.8 | 2.4 | 0.7 | ≤ 0.4 [0.9] | 1.1–4.4 |
| **15 m/s 8°** | heavy | **3.0 / 5.3 / 6.5 / 6.5** | 4.1 | 0.7 | ≤ 1.8 | 2.5–6.4 |
| 25 m/s 4° | r79F | 0.8 / 1.8 / 1.9 / 1.8 | 1.0 | 0.6 | ≤ 0.5 | 0.5–3.1 |
| 25 m/s 4° | heavy | 1.9 / 2.8 / 2.8 / 2.7 | 1.7 | 0.7 | ≤ 1.0 | 1.3–3.8 |

**On a straight** (re-refuter `rr_t3_straight`): R2 never swings > 5° (0/360; max 4.1° at 8 m/s, ≤ 2.0° at 15–25 m/s). V298
fired 15/360, max 9.9°.

**F5 ((θsp − θ) toward centre at release + 1.5 s), R2, max over all words and ages:**
- ≤ 2.0° at ≤ 10 m/s.
- **3.2°** at 12.5 m/s (r79F, outward 10° hold, both engines).
- 2.6° at 15 m/s.
- ≤ 0.8° at 25 m/s.
- Centre-ward holds and drags end on or past the setpoint: ≤ 0.1°.

**The margin to the 4° bar is 0.8° at 12.5 m/s.** V298's same metric was up to 14.4° (the O1 setpoint left at the wheel).

**The release-instant gap |θ − θsp| (information only; rev 2's literal F3 read this):**
- 15.5–16.5° on drags at 5–8 m/s;
- 9.9° on drags at 12.5 m/s;
- 4.3–8.7° on co-steers.

This is the clip-bounded hold, not motion.

**F7 (pressed and the tap ≥ 50 % opposing), longest run:**
- **97 ms (S2) / 130 ms (RSN)**, on 1150-word drags whose torque word spikes past 1229 at 5 m/s;
- 26–27 ms for V298.

**Predicted not to fire (bar 500 ms).**

**The moderate band, the ruling's declared cost (BELIEF; the S2 / RSN hand models):**
- **At 5–8 m/s against a 550–1150-word drag:**
  - opposing lane tap: max **66–82 %** of rail, residual **53–63 %** (this revision, realistic holds);
  - rev 2's rows (S2's small holds): 53–75 / 47–60;
  - the re-refuter: 68–82 / 55–63.
- **Hand force to hold:** 1128–1677 T against V298's 317–671 (**×2–3.6**).
- **F7b-type runs** (|wire| > 600, tap ≥ 40 % opposing, not pressed): 550–1560 ms at 800 words; up to the whole hold at 1150 words.
- **A 1500-word drag (pressed, frozen, fade ×0.70):** max 59–74 %, residual 43–46 %.
- **A 2500-word drag:** 26–52 % max, 19 % residual.
- **Centre-ward co-steer at 5 m/s:** up to 47 % max.
- **At ≥ 10 m/s:** ≤ 42 % max, falling with speed.
- **Route-79 exposure** (fork re-refuter, EVIDENCE for the exposure): 22.1 s of the 662 s latActive, in 538 runs, only 4 longer than 0.3 s. On 67 % of those frames the no-override setpoint would sit at the clip, opposite the hand.

**Under ruling (i) this is the stated price of having no fork override.** Rev 3 records it, makes F7b an OBSERVATION, and makes the operator's report the criterion (R9).

**Mechanism of the outward release lurch** (EVIDENCE for the rule, from the bytes; BELIEF for the size):
1. Under an outward hand, E′ is opposite in sign to θ.
2. So the asymmetric bound is B = 1250 S.
3. The I unwinds from its holding value +X down to −1250 S while the hand holds the wheel.
4. On release, self-alignment plus the negative I swing the wheel past the path toward centre.
5. The swing ≈ (X + 1250) S / stiffness, so it grows with the hold angle and saturates once the I reaches −B (age ≥ 1–2 s).

**V298 avoided this only through the opposing freeze** (the twist relay that ruling (i) and route 79 removed). For a ≤ 300-word
hold, V298 swings 13–19°. **R2 is better than V298 for the weakest hands and worse for 550–1150 words on the heavy member.**
The only firmware remedy is to freeze the I under a light opposing hand, which is the twist-relay class (D4b's LP + motion gate).
**It is not in V299.**

---

## 4. Route-79 counterfactuals (rev 2's, unchanged; plus the fast lane's identity check)

| quantity | V298 | rev 1 (D1c) | **rev 2 rule (= V299)** |
|---|---|---|---|
| hands-off hand-freeze duty / discarded / toggles per min | 11.4 % / 28.3 % / 325 | 0.4 / 0.8 / 13 | **0.4 / 0.8 / 13** (pressed kept 97.3 %) |
| replay tap, hands-off manoeuvres, p50 / p99 / max (LSB) | 46 / 149 / 199 | 57 / 194 / 245 | **53 / 159 / 205** |
| \|I>>7\| p90 (S) / at the A3 bound | 5531 / 4.2 % | 7979 / 19.8 % | **6145 / 29.1 %** |
| rule identity vs V298, `rev_r79.py` (d1 replay) | true | V298 wins 18/18 | **V298 wins 18/18, dR² p50 +0.541** |
| **rule identity vs V298, the drive read's fast lane** (`r3_fastlane_v299.py`, dir-2 ramp, 30-s windows ≥ 200 tap frames) | true | — | **V298 wins 23/25, dR² p10 +0.089, p50 +0.450; the two replays differ on 53.7 % of frames** |
| fork O1 episodes | 415 | 79 (G4) | **0** |

---

## 5. Hazards and fail-safe paths (rev 2 §5, with rev 3's changes in bold)

| path | V299 | evidence |
|---|---|---|
| big turn at 6–12.5 m/s | I ≤ 6144 S same-sign (≈ 983 T, 40 % rail), was ≤ ICL 8192; ≤ 6 m/s and > 12.5 m/s = V298 byte for byte | §1 |
| real hand ≥ 1200 wire | I frozen within a tick; fade ×0.86 → ×0.30; setpoint does not follow (clip-bounded); **F7 runs ≤ 97–130 ms**; lane residual ≤ 19 % against a 2500-word drag, 43–46 % against 1500 words at 5–8 m/s | §2.2, §3.5 |
| moderate hand 550–1150 raw | no freeze, no setpoint yield, fade ≥ ×0.70: **lane 53–63 % residual / 66–82 % max opposing at 5–8 m/s (BELIEF)**; the driver still wins (≤ rail) | §3.5; escalation 2 |
| **light outward hold, release** | **swing past the path toward centre: heavy member 9.7–10.4° at 5–10 m/s, 6.5° at 15 m/s; r79F 4.4–6.1° (BELIEF)** | §3.5; escalation 1 |
| mis-deploy | new fork on V295 (A160) + switch ON → FW_MISSING fault; old fork on A16B + switch ON → fault, switch OFF → torque frames that the camera gate zeroes (engaged, no steering, no fault). **Card: pull Dom before flashing; reflash V298 before an old fork** | F9 |
| 0x1AB dead / bad | never touches canValid (nan, ignore_counter, **ignore_checksum**); bar 0 after 100 ms or on `not canValid`; bit 8 | §2.1 |
| the deleted opposing freeze / the deleted fork override | gated only by a reflash to V298 + the `2712e1336` fork | §11.2 |
| authority | rail 2461 T, OCL 3072, EME/governor/lockstep untouched; **tap peak ≤ 207 LSB (sim), 205 (r79 replay)** | §3.2 |

---

## 6. The instrument

### 6.1 What the drive read adds (`angle_loop_drive_read.py` + `drive_read_fastlane.py`, after C13's repairs)

1. **Rule identity (F1's instrument) — IMPLEMENTED this revision.** `drive_read_fastlane.ARB_V299 = (6, 4, 2880, 1250, 2880, 6144, 1, 1382, 4096)` (the 9-tuple: asym flag + two-level cap), `static_freeze()` and `arb_bound()` (factored out of `cand_lane`, which now calls them), `v299_cand()`; `replay_cands()["V299"]`, NOT in the default `replay()` set (every pre-V299 read is unchanged). Use: `components(W, ref="V299", ramp_steps=<the read's arm-2 steps>, q_lead=<its lead>)` beside `ref="C3B-P"`, R² of the tap per 30-s hands-off settled window. **Checks (`r3_fastlane_v299.py`, 6.0 s): K0 the C3B-P (V298) lane on r79 differs from the pre-edit snapshot in 0 words (both ramps; the full read then ran in 6.7 s with 7/7 replay-cache hits = unchanged keys); K1 the fast lane's V299 freeze decision vs `cave_rev2` 0/6000 (random + 1381–1383 / 2879–2881 / θ extremes / \|hand\| 1228–1230 / I within ±2 S of the bound); N1 vs rev-1 caps 81 > 0; N2 V298's rule vs `cave_rev2` 1236 > 0; positive control on r79: V298 wins 23/25.** The fast lane has no source fallback for V299 (the source lane cannot take the 9-tuple): if the drift guard trips, the V299 replay raises rather than silently using V298's rule.
2. `starpilotCarState.accordAngleStatus` decoded — **the extractor (`v298_flight/r79_extract_fork.py`) pinned to the V299 fork commit, the field added, presence ≥ 99 % asserted before F1 is scored** (N7; the kit's own cereal reuses the struct id, so decode with the fork's schema only). *Observed in the working tree while this revision ran, not written or verified by me:* another agent has generalised `r79_extract_fork.py` (`--route`, `--commit auto` = the route's own initData GitCommit read via `git show`, new keys `cs_canvalid` and `spcs_angstat`); the prerequisite stands until that work is checked (§11.1 item 7).
3. `cs_tqeps == −8·tap` on bit-8-clear frames; bit-8 duty; the drawn bar's sign vs the tap.
4. **The stutter readouts (ruling ii), each per band vs V282 r6c/r39:** stall-surges/min; ratchet trains/min of turning; in-turn 4–8 Hz wheel-rate rms; dwells/min at 0.25 deg/s; surge enrichment within ±0.25 s of \|bar\| 300/512 crossings (V299 has no threshold there: expected flat) and of **\|w\| > 1229 hard-freeze onsets only** (F6b).
5. Per hands-off turn-in: t90, wheel peak, tap peak, overshoot (F4a/b/c by turn size and speed), unwind past centre.
6. **Hold error in hands-off curve holds at 8–12.5 m/s with the replayed V299 A3 bound active** (§6.2).
7. The ms_free ring (F10): θ − θsp band-passed 0.4–0.8 Hz in sustained hands-off holds (\|a_lat\| ≥ 1.5 m/s², 10–13 m/s, ≥ 3 s).
8. **Per release (§7.1's edge): F3 swing, F5 residual, the release-instant gap (information), hold age, hand side, hand word p50; and every F7 / F7b run with its hand word** — the §3.5 map, on the car.
9. R4 5–30 Hz lines, 13–17 / 18–22 Hz eng/dis; carFw; `ld_lat` 0.35.
10. Information: the 1.6–3 Hz hard-turn wheel-rate (no longer a criterion).

### 6.2 The sentences a null licenses (pre-registered)

- **Stutter.** *If F1 passes and the surge enrichment at 300/512 crossings is flat, yet the operator still reports ratcheting or stutter, the freeze relay was not the ratchet's mechanism*: stop iterating the integral policy; next is the small-correction stick (M1).
- **The cap (licenses 7168).** Take every hands-off curve hold at 8–12.5 m/s with \|a_lat\| ≥ 2 m/s² for ≥ 3 s. *If, in ≥ 50 % of them, the replayed V299 I sits at the 6144 bound for ≥ 80 % of the last second AND \|θsp − θ\| (0.5 Hz LP) > 3° there*, the car is ms_free-like and 6144 is too low: the next dose is 7168 at the upper level, **licensed for re-scoring, not for flight** — 7168 trips F4 at 10 m/s in sim (5.6 [6.6] on 4/8 S2 columns), so it flies only if the re-score with drive 2's own 10 m/s turn-in overshoot (< 3°) shows F4a margin. *If the bound is active but the shortfall is ≤ 3°*, 6144 suffices (no dose). *If the bound is active in < 50 % of those holds*, the cap is not what limits holds: the shortfall belongs to the plant / outer loop, not the integral policy.
- **The release lurch.** *If every light outward release at 5–10 m/s swings ≤ 6.1° (F3) the car is r79F-like and the heavy-member cost did not materialise; 6.5–12° is the heavy member as predicted (observation, the operator's report decides); > 12° is beyond both members (F3 fires).*

---

## 7. Pre-registered criteria (final)

### 7.1 Definitions the drive read applies

- **Hands-off frame:** latActive, \|wire\| < 300, not `steeringPressed`, \|bar\| < 300 for the preceding 0.5 s.
- **Release edge:** the first frame with \|wire\| < 150 after a hand episode (latActive, \|wire\| > 300 for ≥ 0.5 s). The hand side = the sign of the mean wire over the episode's last 0.3 s. A release whose next 1.5 s contains \|wire\| > 300 again (a re-grab) is excluded and counted.
- **θsp** = the setpoint the fork sent (0xE4, `co_ang`); θ = the EPS angle (0x14A); + = left for both and for the wire torque.
- **Turn-in:** a hands-off setpoint excursion ≥ 20° that settles (\|dθsp/dt\| < 5 deg/s for ≥ 1 s); overshoot = max (θ − θsp_final)·sign(turn) in the 3 s after θ first reaches 90 % of it.

### 7.2 The criteria (drive 2, config A) — "revert" = do not fly this pair again; R9 outranks everything

| # | criterion | predicted (BELIEF, both members, both engines unless marked) | means |
|---|---|---|---|
| F1 | the V299-rule replay does not beat the V298-rule replay (pooled dR² (V299 − V298) < +0.05, or V299 wins < 2/3 of the 30-s hands-off windows with ≥ 200 tap frames), carFw ≠ `39990-TVA,A16B`, `accordAngleStatus` absent on > 1 % of latActive frames, or any O1-like setpoint snap (\|Δθsp\| > 1.2° in one frame toward the wheel, outside the first frame and the latActive rising edge) | V299 wins; on r79 the same instrument gives V298 23/25 (the positive control) | not live / mis-built: interpret nothing else |
| F2 | ring presence > 0.5 %, F7(ring) > 0 per 100 s, a new 5–30 Hz line; 18–22 Hz eng/dis > 2.5 or 13–17 Hz > 3.5 | none (bytes of the loop unchanged; V298 r79: 0 %, 0, none, 1.83) | revert |
| **F3** | after a release (§7.1): the swing past θsp **away from the hand side** within 1.5 s exceeds **12° at 5–11 m/s, 9° at 11–15 m/s, 8° at ≥ 15 m/s, or 5° on a straight (\|θsp\| < 3°)**; or the operator reports a lurch or snap | outward light holds: heavy 9.7–10.4° at 5–10 m/s, 7.9° at 12.5, 6.5° at 15, 2.8° at 25; r79F 4.4–6.1° / 5.4 / 4.8 / 1.9; centre-ward ≤ 4.9 (≤ 4.1 at 15); drags ≤ 5.3; straight ≤ 4.1 | revert |
| **F5** | (θsp − θ) toward centre at release + 1.5 s > **4°** at ≥ 5 m/s | ≤ 2.0° at ≤ 10 m/s; **3.2° at 12.5 m/s** (margin 0.8°); 2.6° at 15; centre-ward/drags ≤ 0.1° | revert |
| **F4a** | a hands-off turn-in ≥ 45° at ≤ 10 m/s overshoots θsp by > 6° | ≤ 5.2° (45°, 3 m/s); ≤ 4.7° at 6.1 m/s; ≤ 3.3° at 7–10 m/s | windup beyond the model; revert |
| **F4b** | a hands-off turn of 20–45° at ≤ 4.5 m/s overshoots by > **8.5°** | **7.0° (heavy member, 30°, 3 m/s; RSN 2/12, S2 1/12 columns over 6°), 5.8° at 4 m/s; r79F ≤ 4.2°; V298 ≤ 3.0°** — a declared cost (M4) | revert |
| **F4c** | a hands-off turn of 20–45° at 4.5–10 m/s overshoots by > 6° | ≤ 4.6° (5 m/s), ≤ 4.0° (6.1), ≤ 3.3° above | revert |
| (F4 %) | **deleted** — at ≥ 45° the 15 % clause (≥ 6.75°) can never bind before F4a's 6°; below 45° F4b/F4c replace it | — | — |
| F6 | ratchet trains ≥ 4.7 per minute of turning at 5–10 m/s, or in-turn 4–8 Hz wheel-rate rms ≥ 7.09 deg/s at 5–10 m/s (both = V298 on r79: no better than V298), or stall-surges within ±0.25 s of \|bar\| 300/512 crossings ≥ 2× the free rate | sim: 0 stall-surges/turn (V298 1.75–6.1), 4–8 Hz 1.0–1.3 deg/s (V298 3.2–6.0; sim metric) | the freeze was not the mechanism; stop this class |
| **F6b** | stall-surges within ±0.25 s of **\|w\| > 1229 hard-freeze onsets** ≥ 2× free, or hands-off **\|w\| > 1229** onsets > 20 per minute of turning. **A3-bound (wind) freezes are NOT counted** (they toggle 33–45 /s at the 2880 edge under v-word jitter, harmlessly: 1–10 Hz rate ≤ 0.09 deg/s) | onsets rare (hands-off twist p90 607–681 words below 8 m/s on r79) | relay one level up → D4b's LP + motion gate |
| F7 | `steeringPressed` with the tap ≥ 50 % of rail opposing for > 0.5 s | **no: longest 97 ms (S2) / 130 ms (RSN)** | revert (firmware + the `2712e1336` fork) |
| F8 | `cs_tqeps ≠ −8·tap` on > 0.1 % of bit-8-clear frames, bit 8 on > 0.1 % of latActive frames, any canValid drop in angle mode, or the bar's sign disagreeing with the tap | none (checksum 100.000 % on r79; gaps ≤ 30.8 ms p99.9) | revert the bar/parser change only |
| F9 | lane tap > 250 LSB on any hands-off frame, or ≥ 230 for > 0.3 s | **peak ≤ 207 LSB** (184–193 at 6–8 m/s); r79 replay max 205 | authority beyond the envelope; revert |
| F10 | sustained hands-off curve hold at 10–13 m/s: the 0.4–0.8 Hz component of θ − θsp has a half-peak > 1°, or > 2 consecutive half-cycles ≥ 0.5° | no on r79F (≤ 0.34°); no on any member ≤ 12.4 m/s; yes on b_lo×ms_free at 12.6–13 m/s (2.69°) | the car is ms_free-like and V299 removed V298's incidental damping; revert |
| **F7b — OBSERVATION** | \|wire\| > 600 for > 0.3 s with the tap ≥ 40 % of rail opposing, not pressed: **reported with its hand word, speed and duration; NOT a revert criterion** | **predicted to occur** on moderate drags at 5–8 m/s (550–1560 ms at 800 words; up to the whole hold at 1150) — the ruling's declared cost | the operator's R9 decides |
| **R9** | **the operator reports grinding, vibrating, ratcheting, stutter, a lurch, "fights my hands", or anything new** | — | **his call; outranks every band** |

**Goal readouts (scored per band against V282, not revert criteria):** stall-surges/min, ratchet trains/min of turning,
in-turn 4–8 Hz rms, dwells/min (each ≤ V282 r6c/r39 = the goal); tracking 0.95–1.05 and turn-hold ≥ 0.90 at ≥ 8 m/s; the
cap's hold cost (§6.2); the 1.6–3 Hz readout (information).

### 7.3 The OPTIONAL later dose — config B = cap 250, one change, same firmware (pre-registered now, flown only after drive 2 passes F1–F10 and R9)

- **The change:** `AccordAngleMaxRate` 120 → 250 only (`AccordAngleClipScale` stays 1.0; the clip dose is a separate, later drive). Written as `toggle-config_V299-B_cap250.json` **after** drive 2, and scored first (S2 + RSN, the §3.2/§3.5 grids) with drive 2's measured member.
- **Its readout:** t90 of hands-off 60–90° turn-ins at 3–8 m/s (expected faster than drive 2's), the number of hands-off **\|w\| > 1229** freeze onsets per turn-in at ≤ 8 m/s, stall-surges per turn, and the release table of §6.1 item 8.
- **X3 (stop the dose):** \|w\| > 1229 freeze onsets on ≥ 50 % of hands-off turn-ins at ≤ 8 m/s (the faster slew's reaction twist, p99 1100–1240 in sim, straddles 1229), or stall-surges per turn ≥ 2× drive 2's, or any F1–F10 firing. **The sentence a null licenses:** if t90 does not fall by ≥ 20 % vs drive 2 at 3–8 m/s, the 120 deg/s cap was not the note-2 binder on this firmware — the next lever is the error clip (F2), not a higher cap.

---

## 8. Declared misses (each sized, each covered)

| id | miss | size | cover |
|---|---|---|---|
| M1 | small-correction stick not addressed | r79: dwells 4.7/1.2/4.5/3.5 per min vs V282 0.24–0.84 | next class (fork quantiser + breakaway) |
| M2 | 1.6–3 Hz: replaced by the stutter readouts (ruling ii) | sim R2 4.7/5.9 vs V298 6.1/5.6 (S2 3/8 m/s) | readout 10 |
| M3 | hand-steered turns: no co-steer authority | unchanged | escalation 3 |
| M4 | 20–45° turns at ≤ 4.5 m/s on the heavy member overshoot up to 7.0° (V298 ≤ 3.0°) | §3.2 | F4b (8.5° bar) |
| M5 | **moderate-hand resistance with no override**: 53–63 % residual / 66–82 % max of rail at 5–8 m/s, hand force ×2–3.6 V298's | §3.5 | F7b observation, R9, escalation 2 |
| M6 | **cap hold shortfall at 8–10 m/s: 3–7° on 2.5 m/s² curves (ms_free members), to 7.4° at 3.5 m/s²; nominal 3.2° at 8 m/s; 90° big turns 3.5–4.7° at 6.1–8 m/s**; inherited ≤ 6 m/s ceiling (9–27° on 115–190° curves) | §3.3 | readout 6 + §6.2's 7168 sentence |
| M7 | ms_free ring above 12.5 m/s (2.69° at 12.6 m/s on b_lo×ms_free) | §3.4 | F10 |
| M8 | highway authority and the later dose untested | — | §7.3 |
| M9 | SteerDelay / plan lead left out | — | later |
| M10 | plant family matches r79 only at 10–13 m/s; twist R² 0.31; the hand models are BELIEF | — | every sim number is BELIEF |
| **M11** | **outward light co-steer release lurch: heavy member 9.7–10.4° at 5–10 m/s, 6.5° at 15 m/s; r79F 4.4–6.1°** | §3.5 | F3 (12/9/8° bars), escalation 1 |

---

## 9. Class and arc (unchanged from rev 2)

V298's angle loop byte for byte; only the **integral policy** changes: which hand stops the I (Honda's level 1229), how far it
winds (the asymmetric bound; a two-level cap through 12.5 m/s). Not a dose on a flown lever: the opposing freeze was V298's own
and route 79 measured it as the ratchet's mechanism; the sign-of-angle bound and a cap above 6 m/s are carried by no image. Arc:
V38–V52 authority / filters / caves · V53–V61 probes · V62–V73 rate lane · V74–V84 damper · V282–V292 the EPS rate loop · V293
torque mode · V294/V295 accel trim (failed their goal) · V298 the angle loop. Dropped: the 300 opposing and 512 hard freezes, the
fork's override (ruling i), config B for drive 2. Kept on evidence: the ≤ 6 m/s cap 4096, Kd 48, the clip, the camera gate, the
op-skip, A2/B2, the fade. One cave, 260 B, 0 RAM.

---

## 10. Escalations — decided by the operator BEFORE the drive

1. **The outward release lurch (M11; re-refuter D-N2).** With no override and no freeze below 1229, a light outward hold of ≥ 1 s at 5–10 m/s releases with a swing past the path toward centre of **up to 10.4° on the heavy member** (4.4–6.1° on r79F). Rev 3 sets F3's bars above the heavy-member prediction (12° at 5–11 m/s) so that the predicted cost does not revert the build by construction. **Options:** (a) fly with F3 as written here and let R9 decide how it feels; (b) keep an 8° bar at 8–11 m/s and accept that the heavy member would revert by construction; (c) a firmware freeze under a light opposing hand (the twist-relay class, D4b's LP + motion gate) — a new build, not V299.
2. **The moderate-hand band (M5).** 53–63 % of rail opposing a 550–1150-word drag at 5–8 m/s, ×2–3.6 V298's hand force; F7b is an observation and R9 is the criterion (orchestrator's resolution of rev 2's escalation 1, under ruling (i)).
3. **Note 2 under a hand.** Every design yields to a firm hand; r79's hard manoeuvres were hand-steered; co-steer authority is unproposed.
4. **The cap structure** stays rev 2's two-level form (the 4-byte form trips F4 at 3 m/s).
5. **REVERT needs a fork too:** V298 (re-headered, A16B) + Dom `2712e1336` + `toggle-config_V298_angle_loop.json`.
6. **V294 retired as a revert target** (N5): only V298 and V295 are re-headered for A16B.

---

## 11. Build round — prerequisites, rwd plan, CRC plan ("do not flash" reachable at every step)

### 11.1 Prerequisites (each must PASS before anything is offered for flashing)
1. **Golden model:** `_self_check_v299` mirroring `cave_rev2` (§1.3) bit for bit against `rev_h1`'s cases. Contract **94 → 95 symbols**. `_self_check()` + `_demo()` stdout hash `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` **unchanged**.
2. **Build script** (`builds/v108_plus/build_v299_tva.py`, from V298's): patch **by address** (assert old bytes); assert image **`30ff05fa…`**, cave **`e22193b9…`**, trailer `95 3b dd 70`, diff = the 67 attributed bytes; census the assertions.
3. **H1 on the BUILT image:** `rev_h1.py` reading the cave from the written image. 0 mismatches random + targeted; negatives > 0.
4. **Ghidra** decode of the BUILT image 0xC4C00–0xC4CD9 = §1.1.
5. **Four-lens adversarial pass on the built image** (arithmetic / unit-scale / build-script audit / interlocks), each writing its FAIL condition first.
6. **Fork:** F12 (a)–(f) pass, including the exact identity with the override disabled (100 %) and the rewritten old test file.
7. **The drive read:** `r3_fastlane_v299.py check` re-run (K0 = 0, K1 = 0, N1/N2 > 0, r79 positive control); the extractor pinned to the V299 fork commit with `accordAngleStatus` (§6.1 item 2).
8. **The 0x1AB checksum**: the F12(f) test with a corrupted frame; the identity of the two `honda_checksum` functions for 11-bit addresses stays EVIDENCE by source reading (§2.1).

### 11.2 rwd plan (template = the V38 container as V298's build; `encode_x31`/`parse_x31`)

| file | '/' header (read back by `parse_x31` and asserted) | payload assertion |
|---|---|---|
| V299 `39990-TVA,A160-V299-…-0x13000-0x100000.rwd` | `39990-TVA-A110`, `39990-TVA,A160`, **`39990-TVA,A16A`**, **`39990-TVA,A16B`** | decodes byte-identical to `30ff05fa…` |
| V298 revert `…V298-REHEADERED-FOR-REVERT-FROM-V299-A16B-…rwd` | the V298 rwd (sha `1a69b927…`; A110, A160, A16A) **+ A16B** | `encs` == the V298 rwd's; decodes to `177abf04…` |
| V295 revert `…V295-REHEADERED-FOR-REVERT-FROM-V299-A16B-…rwd` | the original V295 rwd (`f42a06bd…`; A110, A160) + A16A + **A16B** | `encs` == the original's; decodes to `5c044d65…` |
| ~~V294~~ | **retired as a revert target (N5)**; its A16A re-header from V298's build stays on disk but is NOT flashable once the car reports A16B | — |

Generalise `header_add_a16a` to `header_add(headers, [strings])`. Exactly one flashable `.rwd` per build number. Push the image and the rwds to `accord-firmwares`.

**REVERT = the V298 re-headered rwd + Dom `2712e1336` + `toggle-config_V298_angle_loop.json`** (the override removal is
code). Second level: the V295 re-headered rwd + `toggle-config_V298_angle_loop_REVERT_to_V295_r2.json` (switch off; either fork).

### 11.3 CRC plan
1. Recompute the main trailer [0x13000, 0xC4FFC) → `95 3b dd 70`.
2. Assert `walk_all_blocks(img) == 0` (chain 50/50) and `walk(img) == 0` (bootloader replay 49/49) on the built image (the bytes re-refuter ran both on its independent rebuild: 0 bad).
3. Assert no edit straddles a block.

---

## A. What I ran (all < 30 s; scripts in `analysis-2020accord/studies/angle_loop/v299_build/rev3/`, outputs in `_scratch/v299_REV3/`)

| script | does | wall |
|---|---|---|
| `r3_release_rows.py S2` | §3.5 on the common scorer: 6 speeds × 2 hold angles × 3 directions × 6 words × 4 ages × 2 members × 2 systems; F3 / F5 / gap / F7 / F7b / tap | 15.0 s |
| `r3_release_rows.py RSN` | the same on the stability refuter's engine (realistic holds) | 9.8 s |
| `r3_fastlane_v299.py snap` | the C3B-P lane on r79 through `FL.cand_lane` before the fast-lane edit (both ramps) | 4.9 s |
| `r3_fastlane_v299.py check` | K0 / K1 / N1 / N2 and the r79 rule-identity positive control (§6.1) | 6.0 s |
| `angle_loop_drive_read.py r79_a1f5d2_al` | the full read after the edit (to `_scratch/v299_REV3/read_r79_after_edit.*`) | 6.7 s (7/7 cache hits) |

**Inherited (cited, not re-run):**
- the re-refuters' `rr_t1_turnin` (F4 grid, tap, 1.6–3 Hz);
- `rr_t3_straight`;
- `rr_t4_msfree` (§3.3);
- `rr_t5_vedge` (the A3-edge toggles);
- `rr2_f12_differential`;
- `rr2_moderate_band_r79`;
- rev 2's §1 checks and `rev_r79`.

**The code edit this revision made** (additive; the V298 path is proven unchanged by K0):
- `rlog-tools/studies/angle_loop/drive_read_fastlane.py`: `ARB_V299`, `static_freeze`, `arb_bound` and `v299_cand`, with `cand_lane` refactored to call the first two;
- `rlog-tools/studies/angle_loop/angle_loop_drive_read.py`: one line in `replay_cands`.
