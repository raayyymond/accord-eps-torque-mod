---
name: reference-accord-can-tx-trigger-path
description: 2020 Accord TVA-A160 (V850E2) — every found writer of FCN0M{N}CTL / CSETR (the "set transmit request" bit-2 register at 0xFF489038+N*0x40), and the verdict on whether internal-only CAN IDs (0x660/0x19F/0x32E/0x64D) are built+buffered but never given a transmit request. Finding: the confirmed per-frame DATA writer FUN_0001d68e (shared by car-facing 399 and internal 0x660 via the same hardcoded mailbox 6) NEVER writes CTL/CSETR. All genuine CSETR writes found are boot-time, buffer-index-keyed, not message-ID-keyed.
metadata:
  type: reference
---

# Accord TVA-A160 CAN TX trigger path: FCN0M{N}CTL / CSETR writers (Segment 1, 2026-07-07 swarm)

Platform: 2020 Honda Accord 39990-TVA-A160, Renesas uPD70F3508/V850E2. All addresses verified on
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (flat, file offset == address) with
`r2 -a v850.gnu -b 32 -m 0 -s <addr> -c 'pd N' code.bin`. gp(r4)=0xFEDF8000, tp(r5)=0xBF000.
SVD: `analysis-2020accord/reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`.

**Mission:** find every write to `FCN0M{N}CTL` (SVD addressOffset `0x09038+N*0x40`, absolute
`0xFF489038+N*0x40`, "bit-set/clear mechanism" register) — especially writes that set `CSETR`
(bit 2, "Set/cancel transmit request", value `0x04`) — and determine whether that write is
unconditional-per-buffer or gated, and whether the internal-only IDs' mailbox(es) ever actually
get a transmit request during normal operation.

Builds on the prior 2026-07-07 swarm's finding (`reference_accord_can_tx_fcn0_forward_verify.md`,
`reference_accord_can_tx_segmentC_driver_hw_mailbox.md`): the live TX dispatch path is
Table B (CAN-ID `0xB721C` / DLC `0xB71B8` / builder-ptr `0xB72AC`, 17 entries) → `FUN_0001d68e`
(HW mailbox byte-scatter DATA/DLC writer) → `0xFF481000+mailbox_idx*64`, and the ONE confirmed
live call site (`0x1dc8e`) hardcodes `mailbox_idx=6` as a compile-time literal for ALL currently
populated logical slots (both car-facing 399/427/0x14A and internal 0x660/0x64D/0x32E/0x19F).

## ⚠ Tooling caveat, load-bearing for everything below

`v850.gnu` (r2 5.5.0) fails to decode a recurring family of V850E2 instructions — they show as
1-byte `invalid` + 1-byte `unaligned` pairs, always adjacent to `ep`-relative short loads/stores
(e.g. raw bytes `ac 07`, `a5 07`, `84 07`, `9c ..`, `bb ..`). This is the SAME phenomenon Segment A
flagged at `0x5221c` ("almost certainly a real V850E2 instruction... not a true misalignment").
Manual bit-decoding of a few of these (`XX 07` 2-byte forms) is CONSISTENT with a `MOV regA,ep`
register-move idiom (reg2 field always resolves to `ep`=r30 given byte1=0x07), but I could not
independently confirm this against a clean, unambiguous example — **treat any "mov X,ep" reading
derived from a garbled byte as INFERRED, not CONFIRMED.** Where a CTL value flows through a
CLEANLY decoded, unambiguous store (`st.h`/`sst.h` with a base register set by an unambiguous
`mov 0x<imm32>,rX` literal, not by a garbled `ep`-setup instruction), I mark it CONFIRMED. Where
the instruction feeding the store's base register is itself one of these garbled forms, I mark it
INFERRED and flag the gap explicitly.

Empirical cross-check that r2's *displacement* fields (not the garbled base-setup opcodes) are
trustworthy here: `sst.h rX,16[ep]` where `ep=0xFF489028` (MID0H) resolves to `0xFF489038` = CTL —
an EXACT match to the SVD's stated register layout (`MID0H@0x09028`, `CTL@0x09038`, delta
`0x10`=16 decimal). This rules out the rizin-0.8.2 "×2 halfword-scaling" bug documented in
`analysis-2020accord/reference/fw_inventory/decompilation/disasm_v850.py` (a DIFFERENT tool/version) for
THIS session's r2 v850.gnu build — displacements are trustworthy, only certain base-setup opcodes
are unrecognized.

## CONFIRMED: FUN_0001d68e (the per-frame DATA/DLC writer) NEVER writes CTL/CSETR

Full clean disassembly of `FUN_0001d68e` (`0x1d68e`-`0x1d82a`), the function independently
confirmed by 3 prior segments as the sole writer of `DATxB`/`DTLGB` for every Table-B message
(399, 0x660, all others):

- `0x1d68e`-`0x1d7ba`: prologue, DLC/CAN-ID table lookups (`0xb721c`/`0xb71b8`), content-builder
  indirect call (`jmp [r25]`), then the 8 `sst.b` payload-byte stores to
  `0xFF481000+mailbox_idx*64+{0,4,8,...,0x1C}` (re-confirms `reference_accord_can_tx_fcn0_forward_verify.md`
  finding #2, freshly re-read this session, byte-identical).
- `0x1d7ba`: `bl 0x1d7c0` / `0x1d7bc`: `ei` — first critical section ends.
- `0x1d7c0`: `jarl 0x1f98e,lp ; di` — a SECOND critical section opens immediately after the first.
  This is the section the mission brief predicted might hold the CSETR write. It does not:
  ```
  0x1d7c8: mov r27,r14 ; shl 1,r14          ; r14 = mailbox_idx * 2
  0x1d7cc: mov 0xfedf68bc,ep ; add r14,ep    ; ep = 0xFEDF68BC + mailbox_idx*2  <- RAM, not the 0xFF48xxxx SFR block
  0x1d7d4: sld.hu 0[ep],r6                    ; r6 = RAM_table[mailbox_idx]  (a software "which logical msg owns this mailbox" record)
  0x1d7d6: cmp r23,r6 ; bne 0x1d806           ; r23 = logical_idx (arg2). mismatch -> 0x1d806
  ```
  Match path (`r6==r23`, garbled `0x1d7da`-`0x1d802`, but bracketed by clean instructions on both
  sides confirming NO write anywhere near `0xFF48xxxx`): sets `r8=1`, returns.
  Mismatch path (`0x1d806`-`0x1d828`, cleanly decoded): re-reads the same RAM table entry,
  `cmov z,5,r0,r8` (r8=5 if it now matches, else 0), then **unconditionally writes `0xFFFF` to
  the SAME RAM table entry** (`st.h r15,0[r14]`, `r15=0xFFFF`) and returns `r10=r8` (0 or 5).
- `0x1d82a`: `dispose ...,lp` — function returns. **No instruction between `0x1d68e` and `0x1d82a`
  ever forms an address in the `0xFF48xxxx`/`0xFF49xxxx` range after the initial DATA-byte stores.**
  The only address space touched by this second critical section is RAM (`0xFEDF68BC`+idx*2), a
  software mailbox-ownership/claim table, structurally unrelated to `FCN0M{N}CTL`.

**This is the central, highest-confidence finding of this segment: writing fresh DATA/DLC for a
CAN-TX message and asserting the hardware transmit request are DISJOINT operations in this
firmware — exactly as the mission brief hypothesized — but the disjunction is temporal
(init-time vs never-again), not per-message/per-ID.**

## CONFIRMED: the conditional post-call function (FUN_0001e9fc) is also NOT a HW writer

At the live call site `0x1dc8e` (`mov r26,r7 ; mov 6,r6 ; jarl 0x1d68e,lp`), the caller checks the
return value and conditionally calls a second function:
```
0x1dc92: cmp 5,r10 ; bne 0x1dca6         ; if FUN_0001d68e's return != 5, skip straight to dispose
0x1dc96: mov r26,r6
0x1dc98: jarl 0x0001e9fc,lp              ; ONLY when return==5
```
`FUN_0001e9fc` (`0x1e9fc`-`0x1ea82`, cleanly decoded, zero garbling) is a straight-line sequence of
11 `cmp`/`st.b` pairs: compares `r6` (arg = logical_idx) against 11 ROM constants at
`tp-29588, tp-29586, ..., tp-29568` (2-byte stride, 11 entries — matching Table B's exact 11
TX-capable logical slots, idx0-10), and on each match, writes a ZERO byte to a corresponding flag
at `gp-5780, gp-5779, ..., gp-5770` (11 consecutive bytes). **This clears a per-message
software "pending" flag array. It touches zero addresses in the `0xFF48xxxx` range.** Not a CSETR
writer. The `return==5` condition that gates this call corresponds to the "ownership table was
stale and got invalidated" branch inside `FUN_0001d68e` (see above) — an edge/reclaim case, not
the steady-state per-frame path (steady state returns 1, which skips this call entirely).

## CONFIRMED: genuine CTL/CSETR writes exist, but ALL are boot-time / buffer-index-keyed

Found via (a) exhaustive 4-byte-LE literal scan for `0xFF489038+idx*0x40` for all idx 0-63, and
(b) following the two other exhaustive-literal hits for `0xFF489028` (MID0H base) and
`0xFF489000` (buffer-0 status block base) found by the prior swarm. Every hit resolves to one of
FOUR boot-time locations, all well before (lower address than) the `0x1d68e` driver cluster and
occurring in the same program region as the confirmed one-time FCN0/FCN1 register zero-fill loop
(`0xcf6`-`0xd08`, byte-verified by Segment A):

### Site 1 — boot loop `0x9ba`-`0xa46` (byte-verified, minimal garbling)
```
0x9ba: mov r1,r15 ; shl 6,r15                    ; r15 = idx*64  (r1 = loop counter)
0x9be: mov 0xff489028,ep ; add r15,ep             ; ep = MID0H(idx)
0x9c6: mov 1,r16 ; sst.h r16,16[ep]                ; CTL(idx) = 1        (SERY only, "arm")
0x9ca: sld.hu 16[ep],r16 ; shr 1,r16 ; bl 0x9ba     ; spin-poll
...
0x9dc: cmp r12,r1 ; bnl 0xa34                       ; r12 = runtime byte @ gp+0x7E24 (0xFEDFFE24)
  idx < r12 branch (falls through):
    0x9e2-0x9ec: STRB(idx) = ((idx+2)<<3)|0x81       ; SSOW(TX-direction, bit7) SET
    0x9f6-0xa04: zero-clear DAT0-DAT7 (8 bytes)
    0xa0c-0xa2a: ID-table lookup (source table NOT identified this session, see prior memory's
                 open item) conditionally writes MID1H/MID0H
    0xa2e: r16 = 2310 (0x906)
  idx >= r12 branch (0xa34):
    0xa34-0xa36: STRB(idx) = 1                       ; SSOW NOT set (non-TX-direction)
    0xa3a: r16 = 286 (0x11E)
  converge 0xa3e: add 1,r1 ; addi -64,r1,r0 ; sst.h r16,16[ep] ; bnl 0x9ba   ; CTL(idx) = r16, loop idx=0..63(ish)
```
`2310 = 0x0906` = bits {1,2,8,11} set → **CSETR (bit2) SET**.
`286 = 0x011E` = bits {1,2,3,4,8} set → **CSETR (bit2) SET.**
Both final per-iteration CTL writes assert CSETR, REGARDLESS of the idx-vs-r12 branch — the
differentiator between the two branches is `STRB.SSOW` (genuine TX direction), not CSETR. Per SVD
field naming (`CSETR`="Set/cancel transmit request", meaningful only for a TX-direction buffer),
this is consistent with: CSETR being written as a side effect of a combined-bitfield struct store
(only bit2 is a documented write-position; bits 1/8/11 sit at documented READ-only positions —
TCPF/RDYF/IENF — and are inferred, not proven, to be don't-care on write) while the REAL
TX-vs-not gate is `STRB.SSOW`. **INFERRED, not proven**: I do not have datasheet text confirming
write-don't-care semantics for the undocumented-for-write bit positions, only the SVD's field-name
split between read and write roles.
`r12`'s numeric value was NOT pinned this session (same open item as the prior swarm) — it is a
runtime RAM byte, not a static literal.

### Site 2 — second boot loop `0xa8c`-`0xad6` (byte-verified, minimal garbling)
Same `0xff489028`-literal addressing idiom, different buffer sub-range/purpose (writes ID-related
halfwords at `ep+8`/`ep+0` before reaching CTL):
```
0xad4: mov 4,r2
0xad6: sst.h r2,16[ep]     ; CTL(idx) = 4   <- PURE CSETR, bit2 ONLY, nothing else set
```
Cleanest single-purpose CSETR assertion found this session — unambiguous, no other bits set.

### Site 3 — buffer-0-specific + buffer-3..N loop `0xdfa0`-`0xe250`+ (mostly clean, some garbling)
Runs immediately after the FCN0/FCN1 zero-fill loop, still early boot. Two distinct sub-sequences:
- **Buffer 0 specifically** (literal `0xff489000`, offset `56`=`0x38`=CTL, hit at `0xdfb6`/`0xdff4`):
  `CTL(0)=2` (0xdfbc, bit1 only, no CSETR) → [channel-A/B control-block writes] → `CTL(0)=1`
  (0xe008, arm) → `CTL(0)=28` (0xe01c, `0x1C`=bits{2,3,4} → **CSETR SET**) → STRB(0)=1 (0xe026) →
  **`CTL(0)=2048`** (0xe034, `0x800`=bit11 only → **CSETR CLEAR**, the apparent FINAL write for
  buffer 0 in this pass).
- **Buffer 3 onward**, loop-computed `ep=0xff489000+idx*64` (idx starts at 3, `0xe036`/`0xe06c`
  literal hits at buf3's block `0xff4890c0`): `CTL(3)=1` (0xe03e, arm) → poll → `CTL(3)=30`
  (0xe04e, `0x1E`=bits{1,2,3,4} → **CSETR SET**). A subsequent inner loop (`0xe074`-`0xe0c8`,
  bound `cmp 3,r1` NOT `cmp 64,r1` — **I could not confirm this iterates over ALL buffer indices
  up to 64; the loop-bound register reuse in this region is genuinely ambiguous, flagged OPEN**)
  repeats the same `CTL=1→30` pattern, then at `0xe0da` transitions into what looks like RX
  acceptance-filter/mask setup (writes at `0xff488240+{192,200,208,216,224,232}`), i.e. this
  sub-loop's scope is SMALLER than "all 64 buffers" and its exact extent is unresolved.

**Buffer 0 is structurally singled out and left with CSETR CLEARED** (`2048`) at the end of this
pass — this exact "ends CSETR-clear" behavior for buffer 0 independently repeats at Site 4 below,
which is reassuring corroboration rather than a fluke.

### Site 4 — `0x1cfd2`-`0x1d0c0`ish (heaviest garbling, buffer-0-specific, INFERRED conclusions)
Same driver-cluster region Segment C flagged as containing an "unrolled 0-6 status-polling loop"
(`0x1dcd0`-`0x1ddb0`) and the channel-A control-block read (`0xFF480240`, seen here at `0x1cffe`,
matching Segment C's `0xFF480240` note at `0x1d912`). Two CTL writes are UNAMBIGUOUS because they
use a direct, literal-loaded base register (`r22 = 0xff489038`, loaded cleanly at `0x1d034` via
`mov 0xff489038,r22`) rather than a garbled `ep`-setup instruction:
```
0x1d084: movea 94,r0,r8 ; 0x1d088: st.h r8,0[r22]     ; CTL(buf?) = 94  (0x5E = bits{1,2,3,4,6} -> CSETR SET)
0x1d090: movea 2048,r0,r6 ; 0x1d094: st.h r6,0[r22]    ; CTL(buf?) = 2048 (bit11 only -> CSETR CLEAR)  <- final write
```
The loop variable is `r28` (`addi 1,r28,r26` at `0x1d098`) but I could not confirm this loop's
buffer-index range or its exact caller (boot-once vs re-entrant) — the loop-bound
compare/branch past `0x1d098` was not resolved this session (garbled region). Given `r22` is
fixed to the buffer-0 CTL literal throughout the excerpt actually read, and the intervening
`ep`-based instructions (whose target buffer is ambiguous per the tooling caveat) may cover OTHER
buffer indices via a separate, unresolved addressing path, **I am NOT asserting this is a flat
"buffer r28" loop with confidence — flagging this whole site as INFERRED/OPEN**, kept in the
record because its two unambiguous CTL writes (94 then 2048, same "assert-then-clear" shape as
Site 3's buffer-0 sequence) corroborate the buffer-0-specific pattern independently.

## Verdict on the mission hypothesis

**"Internal IDs are built+buffered but their CSETR transmit-request is never set (or is gated
off) in normal driving."**

**REFUTED, scoped to the code paths traced this session — with an important caveat.**

- The per-frame DATA writer (`FUN_0001d68e`) that BOTH 399 (car-facing, table-A idx9) and 0x660
  (internal, table-A idx4) go through — via the SAME hardcoded `mailbox_idx=6` literal at the one
  confirmed live call site `0x1dc8e` — **never writes CTL/CSETR, for either group, ever.** There
  is no per-message, per-ID, or car-facing-vs-internal branch anywhere in this function or its
  immediate call sites that could differentially gate a transmit request. If a CSETR gate on
  internal IDs exists, it is NOT here.
- Every genuine CSETR write found this session is **boot-time initialization**, addressed by RAW
  BUFFER INDEX (loop counters 0..~64, or a runtime-RAM threshold `r12`), never by CAN ID or
  logical-message identity. Buffer 6 — the one mailbox confirmed to carry BOTH car-facing and
  internal live traffic per the prior swarm — is NOT buffer 0 (the one buffer shown, twice
  independently, to end boot init with CSETR explicitly CLEARED). Buffer 6 falls within the
  "idx < r12" / "idx >= 3" ranges that DO get CSETR asserted (2310, 286, or 30, all CSETR-SET) in
  at least 2 of the 4 sites found — **INFERRED, not a pinned-literal proof**, since `r12`'s exact
  value and the Site-3 inner loop's true extent remain unresolved.
- **Structural conclusion: to the extent CSETR gates transmission at all, it is asserted ONCE at
  boot for buffer 6 (shared by both message groups) and never touched again in the traced
  per-frame path.** This means CSETR cannot be the mechanism that keeps 0x660/0x19F/0x32E/0x64D
  off the comma bus while letting 399/427/0x14A through — **both groups share buffer 6's boot-time
  arm state identically**, per the "single shared mailbox 6" premise this segment inherited from
  the prior swarm.

**Caveat that keeps this from being a clean "impossible" verdict:** this refutation is
CONDITIONAL on the prior swarm's "mailbox_idx=6 is genuinely shared across all live logical
messages" finding holding up. That finding itself carries an explicit OPEN flag in
`reference_accord_can_tx_fcn0_forward_verify.md` (open item #1: whether 6 is a true shared
mailbox or just the one this session's traced branch happened to hardcode; call site 2's mailbox
index provenance is unresolved). **If mailbox assignment turns out to differ between car-facing
and internal messages** (e.g., if call site 2, `0x1db32`, uses a different literal or a
computed mailbox index for some subset of Table-B's logical slots), then the differentiator could
still live in mailbox-index ASSIGNMENT rather than CSETR gating — a structurally different
mechanism this segment did not rule out (it was out of scope: this segment's remit was strictly
the CTL/CSETR write, not logical-to-physical mailbox assignment). **Recommend whichever segment
covers mailbox-index assignment treat this as the concrete next question**: does call site 2
(`0x1db32`) ever pass a mailbox index other than 6 for any of Table B's 17 logical slots?

## OPEN — what would close remaining gaps

1. **`v850.gnu`'s incomplete V850E2 opcode coverage** blocked full resolution of Sites 3's inner
   loop bound and Site 4's loop extent/caller. Next step: either hand-derive the missing opcode
   encodings from more examples (the recurring `XX 07` 2-byte pattern, tentatively `MOV regA,ep`),
   or get a Ghidra decompile of the `0x1cfa0`-`0x1d068` and `0xe074`-`0xe250` ranges (GhidraMCP,
   per the tool-order fallback in the skill doc) to cross-check the garbled regions.
2. **`r12` (gp+0x7E24 / 0xFEDFFE24) numeric value** — a runtime RAM byte gating the Site-1 boot
   loop's idx<r12 vs idx>=r12 branch — not statically pinned. A live memory read (out of this
   session's read-only-static scope, and no CAN write is authorized regardless) or a full
   data-flow trace of every writer of that RAM byte would resolve it.
3. **Whether "arm once at boot, never re-assert CSETR" is a correct model of this CAN peripheral's
   behavior**, or whether a real per-frame re-trigger exists somewhere entirely unexamined this
   session (e.g. inside one of the ROM-scheduler builder functions at `0x522xx`-`0x53exx` that
   Segment A/B found and the synthesis document re-classified as RX-validation — re-open this
   ONLY if Segment 1's "boot-arm-once" model is later contradicted by evidence that messages
   change CONTENT at runtime without re-touching CTL, which is exactly what `FUN_0001d68e`'s
   clean DATA-only writes already show — so this is a low-priority reopen, included for
   completeness).
4. **Call site 2 (`0x1db32`)'s mailbox-index provenance**, per the Caveat above — the single
   biggest remaining structural unknown for the car-facing/internal-split question as a whole.

## Cross-references
- `reference_accord_can_tx_fcn0_forward_verify.md` — this segment's starting point; its "boot-time
  per-buffer TX-init loop" finding (§6) is Site 1 above, now traced through to its actual CTL/CSETR
  bit values (was previously described only as "sets STRB.SSOW=1", CSETR wasn't checked).
- `reference_accord_can_tx_synthesis_2026-07-07.md` — the swarm rollup; this document supplies the
  missing "does DATA-write equal transmit" verification the synthesis flagged as needed.
- `reference_accord_can_tx_segmentC_driver_hw_mailbox.md` — original `FUN_0001d68e` trace and the
  17-entry Table B; this document extends it past the function's return into the caller
  (`0x1dc8e`'s conditional `FUN_0001e9fc` call) and rules that function out as a HW writer too.
