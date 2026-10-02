# ADVERSARY INTERLOCKS-GATES: V297 (C3-rev2): verdict **DO_NOT_FLASH**

2026-10-01. Read-only. Scope: interlocks, downstream consumers, GATE 1 and GATE 2 on the BUILT image V297.
Script beside this file: `adv_ig_v297_inputs.py` (stdout only, writes nothing).

## 0. FAIL criteria

The criteria were framed before the first check ran. This file was written after the checks, and that is stated here openly.
Any ONE of these means DO_NOT_FLASH. DO_NOT_FLASH is also the default, reached unless every row is cleared on the image.

| id | FAIL looks like |
|---|---|
| F0 | **No artifact.** No V297 plain image, .rwd or build script exists, so there is nothing that passed any gate. |
| F1 | **Orphan artifact.** A V297-named file exists although the builder reported none written. |
| IG1 | **Stale link in the image.** The table pointer `mov imm32,r9` does not equal the first table byte in the image, or any `jr` out of the cave does not land on the design return (0x29D7A / 0x29D7E / 0x2A164) on an instruction boundary. |
| IG2 | **Liveness.** The hook clobbers a register live at 0x29D7A/0x29D7E (r25 live; r14 = ramp; r6/r10 at the `cmp r10,r6`), or the cave reads a register the hook did not set. |
| IG3 | **GATE 1.** A RAM word written by the cave has another writer, or no engage/disengage/bail initialiser. Or the census null had no positive control (Ghidra plus Python disp16, plus the 6-byte form, plus register-indirect). |
| IG4 | **int32.** An intermediate overflows, sign-extends or truncates within the reachable input box. |
| IG5 | **Guards.** The A2/B2/op-skip guard is not on the real control flow of the image, or the skip epilogue (0x2A164) does not zero I8 and set the sentinel as the design says. |
| IG6 | **Fail-safe.** Any torque path reaches the motor with no valid, current setpoint: 0xE4 timeout, fault, preemption, gp-0x67fe != 2, mode == 3, or a wrong-payload source. |
| IG7 | **Downstream.** A changed cell has an EME, governor, lockstep or DTC consumer not proven by census. |
| IG8 | **GATE 2.** The common frequency scorer, run on the cals and table READ FROM THE IMAGE, fails on magnitude or phase in any loop. |

## 1. Result: F0 fires, and no IG row can be evaluated

- **No V297 artifact exists.** EVIDENCE, three methods:
  - a `find`/glob over both repos (`_v297*`, `*V297*`, `*A16A*`, `*REHEADERED*`, `build_v297*`) returned nothing;
  - no `.bin`, `.rwd` or `.hex` was modified on 2026-10-01 in either repo, `_scratch` included;
  - `git status` is clean in both repos. The heads are kit `8dc8bf1` and firmwares `9567a84` (V295).
- This agrees with the builder's own report ("NOT BUILT … stopped during the design read").
- **IG1 to IG8 are therefore NOT EVALUATED.** Each one is defined on the built image, and there is none.
  - No Ghidra import of a V297 image, no decompile of FUN_00028ea6 or the cave on it.
  - No liveness trace, no GATE 1 census, no int32 sweep, no guard trace, no 0xE4 fault-path walk, no consumer census.
  - No GATE 2 run on image-read cals.
  - **None of this is a pass.** A null from the wrong image is not a null.

## 2. Safe-direction checks on the INPUTS a build would consume

Every check here is EVIDENCE from bytes, independent of rb_build/e2_asm/ds_asm, with no kit imports.

1. **The revert originals are intact.** sha256 of each file against the recorded value:

   | file | sha256 | recorded |
   |---|---|---|
   | V295 plain image | `5c044d65…` | OK |
   | V295 .rwd | `f42a06bd…` | OK |
   | V294 plain image | `3143616d…` | OK, = `BASE_SHA` in build_v295_tva.py |
   | V294 .rwd | `a2b418f0…` | OK, = `V294_RWD_SHA` |

2. **C3B-F (fallback, default 220 B).**
   - The flight hex equals the score hex byte for byte; sha256[:12] = `9de9365fa952` for both.
   - The table pointer `mov imm32,r9` = 0xC4CB2.
   - The freeze-return `jr disp22` at 0xC4CAC lands on **0x29D7E** (FRZ_RET), which is correct.
   - The builder's claim (b) holds.
3. **C3B-P (primary): the known relink defect, independently re-confirmed.**
   - Flight sha `9a10cdc4ec75` is 240 B; score sha `b5a1d0ce1e0e` is 238 B.
   - The splice is at cave offset 0x12 (pc 0xC4C12): `e0 d7 36 d3` (cmovh) became `b3 05 b6 07 50 55` (bnh; jr 0x2A164).
   - `flight[:0x12] == score[:0x12]` and `flight[0x18:] == score[0x16:]`. The tail is a pure +2 shift with nothing relinked.
   - **Table pointer.** The flight `mov imm32,r9` @0xC4C1C still loads **0xC4CC4**, but the table now begins at **0xC4CC6** (stale by −2).
     - At 0xC4CC4 sit `66 00 | ca 02 9a 04 …`: the last code halfword, followed by the table one halfword late.
     - Every G lookup would be misaligned.
   - **Freeze return.** The flight `jr` @0xC4CC0 lands on **0x29D80** instead of 0x29D7E.
     - Ghidra dry-run decode of V294 0x29D72–0x29D8B, cross-checked by a Python byte read showing V295 identical there (`ea 31 00 4a d7 05`):
       - 0x29D7E is `cmp r10, r6` (2 B);
       - 0x29D80 is `mov 0x0, r9`;
       - 0x29D82 is `ble 0x29D8C`.
     - So the stale return lands on an instruction boundary (no decode fault), but **it skips the `cmp`**, and the `ble` branches on whatever flags the cave left.
     - That is silent control-flow corruption, invisible to any scorer that runs the score cave.
   - Positive control for the `jr` scan: the score cave's own `jr` @0xC4CBE resolves to 0x29D7E.
   - The `jr disp32` scan found nothing even in the score cave. **That null is void** and was replaced by the Format V scan.
4. **The hardened fallback cannot come from `add_opskip`.**
   - The C3B-F cave contains **0** copies of the cmovh `e0 d7 36 d3` that `add_opskip` searches for (P_score has 1).
   - So the helper would trip its own assert ("cmovh not uniquely found") on the held-D cave.
   - The ~+20 B validity-read op-skip the merged page recommends is new cave code with no byte listing.
   - This backs the builder's STOP: the hardened fallback needs an orchestrator ruling or a byte-exact listing first.
5. **Provenance label (low).**
   - `rb_final.py` gives the C3B-P frequency Spec `src="c3b_cave_C3B-P.hex"`, which is the FLIGHT hex.
   - `score_freq.py` uses `.src` only as a label (one use, in the summary dict), and the C3B rows come from `rb_table`. The score is therefore unaffected.
   - However, `score_freq.cave_table()` reads the table through the cave's own `mov imm32,r9`. Pointed at the P flight hex, it would silently read the shifted rows. Do not rewire it to the flight hex.

## 3. What a V297 build must clear before this adversary can return anything but DO_NOT_FLASH

- A built image plus its .rwd, with the image hash stated.
- Then IG1 to IG8, run on that image. IG1 is the cheap first gate for each cave:
  - read `mov imm32,r9` from the image and check it equals the first table byte;
  - resolve every Format V `jr` (hw1 & 0xFFC0 == 0x0780, hw2 bit 0 == 0) to 0x29D7A, 0x29D7E or 0x2A164;
  - the score-cave positive control above.
- Open operator rulings remain open and are not this adversary's to make:
  - the fork angle integral (none, or τ_o ≥ 6 s);
  - the camera relay-close hazard (procedure, or the R1-P-cam interlock variant).
