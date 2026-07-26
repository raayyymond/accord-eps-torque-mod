---
name: reference_accord_deliver_commit_gate5_gate7_trampoline_anchors
description: Byte-exact disasm of deliver-commit Gate 5 (|column torque| gp-0x4f68) and Gate 7 (voter-AVG gp-0x6a5e) in FUN_0003d04c, 39990-TVA-A160, with trampoline-anchor feasibility verdict
metadata:
  type: reference
---

# Deliver-commit Gate 5 / Gate 7 — byte-exact disasm + trampoline anchor audit (2026-07-13)

Platform: 2020 Accord `39990-TVA-A160`, V850E2. Verified via GhidraMCP `program="master.bin"` (== program
name `code.bin`, stock, path `/master.bin`) — NOT the currently-active `_uds_telem_plain_image.bin`. Read-only:
`disassemble_function`, `disassemble_bytes`, `read_memory` only, no writes. Confirms and extends
`docs/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` (D5/D7 rows) and `docs/HANDOFF-2026-07-05-v35.md`.

## Function: `FUN_0003d04c` (0x3d04c–0x3d1f4), called `(4,0)` from `FUN_00041222`@`0x412ae`

Confirmed call site (fresh disasm, not just cited from memory):
```
000412a6  mov 0x0, r7          ; param2 (r26 inside callee, sxh) = 0
000412ac  mov 0x4, r6          ; param1 (r28 inside callee, zxb) = 4
000412ae  jarl 0x0003d04c, lp  ; bfff9ebd
000412b2  ld.bu -0x67fe, gp, r15   ; <-- immediately reads TRUMP var, NOT r10
```
**r10 (the deliver-commit return code) is discarded by the caller** — confirms the map's §4 "unclosed structural
link" independently. Callee prologue: `mov r6,r28 / zxb r28` (case selector), `mov r7,r26 / sxh r26`.

## Gate 5 — `gp-0x4f68 ≥ cal 0xC61EA (4096)` — byte-exact

```
0003d08c  ld.hu 0x71ea[tp], r9    e5 4f eb 71   len4   ; r9 = cal tp+0x71ea = 0xBF000+0x71EA = 0xC61EA
0003d090  ld.hu -0x4f68[gp], r11  e4 5f 99 b0   len4   ; r11 = gp-0x4f68 (0xFEDF3098), |column torque|
0003d094  cmp r11, r9             eb 49         len2   ; flags = r9 - r11  (cal - signal)
0003d096  bh 0x0003d09c           bb 05         len2   ; taken (cal>signal, unsigned) => CONTINUE (no bail)
0003d098  jr 0x0003d1ea           80 07 52 01   len4   ; NOT-TAKEN fallthrough = FIRED path (signal>=cal, BAIL)
```
Cal value verified by direct `read_memory` at `0xC61E8` (8 bytes `00 06 00 10 00 0e 00 10`): bytes at
+2/+3 = `00 10` LE = `0x1000` = **4096**. Matches map doc.

**Fired-path confirmation:** the `jr` at `0x3d098` (fall-through of `bh`, i.e. signal ≥ cal) lands at `0x3d1ea`,
a **shared** return block also reached by gate D4 (`gp-0x4e5f != 1`, its own `jr 0x3d1ea` at `0x3d088`):
```
0003d1ea  mov 0x3, r10   03 52   len2   ; return code = 3 (shared D4/D5 bail code)
0003d1ec  br 0x0003d1f4  c5 05   len2   ; -> universal epilogue
```
Confirmed: reaching this block **skips** the commit switch (`0x3d0b8`–`0x3d1a8`, the case-0..9 dispatch on r28)
that performs the actual mode-byte writes (`st.b r10,-0x6770[gp]`, `-0x6858[gp]`, `st.h -0x69ce[gp]`, and calls
to `FUN_0003c4e2`/`FUN_0003c6a4`/`FUN_0003c7fc` for several cases) — i.e. bail = commit genuinely not performed,
consistent with the map's D5 row. The further downstream link (mode byte → `gp-0x6772` FOC-mode → `gp-0x6809`
deliver flag → arbitration zero) remains **inferred, not re-traced this session** — same residual as map §4.

## Gate 7 (voter-AVG) — `gp-0x6a5e ≥ cal 0xC62FE (320)` — byte-exact

```
0003d0a8  ld.hu 0x72fe[tp], r14   e5 77 ff 72   len4   ; r14 = cal tp+0x72FE = 0xBF000+0x72FE = 0xC62FE
0003d0ac  ld.hu -0x6a5e[gp], r16  e4 87 a3 95   len4   ; r16 = gp-0x6a5e (0xFEDF15A2), voter AVG torque
0003d0b0  cmp r16, r14            f0 71         len2   ; flags = r14 - r16 (cal - signal)
0003d0b2  bh 0x0003d0b8           bb 05         len2   ; taken (cal>signal) => CONTINUE
0003d0b4  jr 0x0003d1e6           80 07 32 01   len4   ; NOT-TAKEN = FIRED path (signal>=cal, BAIL)
```
Cal value verified by direct `read_memory` at `0xC62FC` (8 bytes `18 00 40 01 80 0c 18 00`): bytes at +2/+3 =
`40 01` LE = `0x0140` = **320**. Matches map doc / V35 handoff.

Fired path lands at `0x3d1e6`, shared with gate D6 (`gp-0x67f4 != 1` plausibility, `jr 0x3d1e6` at `0x3d0a4`):
```
0003d1e6  mov 0x2, r10   02 52   len2   ; return code = 2 (shared D6/Gate7 bail code)
0003d1e8  br 0x0003d1f4  e5 05   len2   ; -> universal epilogue
```
Same skip-the-commit-switch confirmation applies.

## Universal epilogue (all paths converge, gate or not)

```
0003d1f4  dispose 0x0,{r26,r28,lp},[lp]   40 06 bf 20   len4
```
`dispose` restores `r26/r28/lp` from the stack and returns indirectly via `lp` — it is **not** a pc-relative
branch (reads `sp` implicitly, jumps via register), unlike `jr`/`br`/`bcc`/`jarl`.

## Trampoline-anchor verdict — NO branch-free anchor exists that is exclusive to one gate

For both Gate 5 and Gate 7, the only instruction executed **exclusively** on the fired path (between the `bh`
decision and the shared return block) is the `jr` itself — which is pc-relative and explicitly disqualified.
The next candidate (`mov <code>,r10` + `br 0x3d1f4`, 4 bytes) is non-branch-only-in-part: the `mov` is clean
and relocatable, but the trailing `br` is pc-relative (2-byte short form, disp = `0x3d1f4 - <site+2>`, well
within disp9 range — same re-encoding technique already used for the `jarl` in
`reference_accord_telemetry_ram_hook_a160.md`'s `0x4141E` hook). **And** that block is shared with a sibling
gate (D4 for Gate5, D6 for Gate7) — hitting it does not by itself disambiguate which of the two bailed.

Ranked recommendation:
1. **Preferred:** anchor = shared return block (`0x3d1ea` for Gate5/D4, `0x3d1e6` for Gate7/D6), 4 bytes
   (`mov`+`br`). Requires re-encoding the trailing `br` for the cave (same technique as the existing `jarl` hook).
   Disambiguate Gate5-vs-D4 (or Gate7-vs-D6) in the stub by having it *also* read `gp-0x4f68` vs 4096 (or
   `gp-0x6a5e` vs 320) directly from RAM at hook time — cheap, register-independent, unambiguous. `r10` at the
   hook already holds the shared return code (3 or 2) for free cross-check.
2. **Zero-branch-re-encode fallback:** anchor = universal epilogue `dispose` at `0x3d1f4` (4 bytes, NOT
   pc-relative). Fires on **every** call (bail or commit), but `r10` (0/2/3/5/6, one value per gate pairing)
   plus direct RAM reads of `gp-0x4f68`/`gp-0x6a5e`/`gp-0x67f4`/`gp-0x4e5f` fully disambiguates in post-processing.
   Costs more stub complexity (must perform the frame teardown itself — restore r26/r28/lp, deallocate frame,
   return via lp — since `dispose` itself is being replaced).
3. **Not recommended, flagged per the "if the only candidate is a branch, say so" clause:** the `jr` at
   `0x3d098`/`0x3d0b4` is the ONLY gate-exclusive instruction; it is pc-relative and would need full re-encoding
   plus the stub reproducing exactly the semantics of a 4-byte `jr` — feasible (same disp22 re-encode formula
   documented in `reference_accord_telemetry_ram_hook_a160.md`: `word0=0xF800|0x780|((disp>>16)&0x3F)`,
   `word1=disp&0xFFFF`) but not "branch-free" as the constraint requested.

## PSW / register notes

- `cmp` at `0x3d094`/`0x3d0b0` sets PSW consumed **only** by the immediately-following `bh` (2 bytes later) —
  by the time execution reaches the anchor candidates (`0x3d1ea`/`0x3d1e6`, or the epilogue), that PSW is
  **already consumed and dead**. No downstream code depends on it.
- Anchor candidate 1 (`mov`+`br`) reads **no GPRs** (mov is immediate-literal, br is unconditional) and writes
  only `r10`.
- The control-flow successor after either anchor is the epilogue `dispose 0x0,{r26,r28,lp},[lp]`, which reads
  **only `sp`** (implicit) and the saved-register slots for `r26`/`r28`/`lp` — it does **not** read `r10`, so a
  stub is free to use `r10` as scratch as long as it restores the correct return-code value before falling
  through (the value is currently unused by the caller anyway — see call-site confirmation above — but
  preserving it costs nothing and keeps the function's contract intact for any future caller).
- Function entry `prepare {r26,r28,lp},0x0` establishes the frame the epilogue tears down; a stub hooking the
  epilogue must not disturb that frame's stack slots — push/pop its own scratch strictly above them.

## Cross-reference
- `docs/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` — D4/D5/D6/D7 rows (Stage D table).
- `docs/HANDOFF-2026-07-05-v35.md` — Gate 7 identity/history (`0xC62FE` V35 target), Gate 5 residual note.
- `reference_accord_telemetry_ram_hook_a160.md` — the existing `0x4141E` per-cycle hook + jarl disp22
  re-encoding formula, reused here for the `br` re-encoding recommendation.
