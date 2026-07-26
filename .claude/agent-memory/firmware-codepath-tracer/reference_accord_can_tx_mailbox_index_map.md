---
name: reference-accord-can-tx-mailbox-index-map
description: 2020 Accord TVA-A160 (V850E2) — decodes the two bitmask-scan dispatchers feeding FUN_0001d68e call sites 0x1db32/0x1dc8e, resolves mailbox_idx/logical_idx provenance per call site, and finds a dynamic per-hardware-mailbox RAM registration scheme (0xFEDF68BC) that structurally explains why no static per-message mailbox/channel field exists anywhere in Table-B.
metadata:
  type: reference
---

# Accord TVA-A160 CAN TX — logical-ID -> hardware-mailbox-index map (2026-07-07, swarm segment 2)

Platform: 2020 Honda Accord 39990-TVA-A160, V850E2. All addresses verified on
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (flat, file offset == address) with
`r2 -a v850.gnu -b 32 -m 0 -s <addr> -c 'pd N' code.bin`. gp=0xFEDF8000, tp/r5=0xBF000.

**Builds on:** `reference_accord_can_tx_segmentC_driver_hw_mailbox.md`,
`reference_accord_can_tx_segmentD_known_frame_provenance.md`, `reference_accord_can_tx_fcn0_forward_verify.md`.

## ⚠ READ FIRST — this heavily overlaps 3 memories written concurrently by other segments of the SAME swarm

After writing most of this document I discovered `reference_accord_can_tx_trigger_path.md` (Segment 1),
`reference_accord_can_init_mid_pinmux_topology.md` (Segment 3), and `reference_accord_internal_id_lifecycle.md`
(Segment 4) already exist in memory and **independently found much of the same outer structure** —
credit belongs there, not here, for:
- **The outer per-tick coordinator `FUN_0001dcaa`** and its exact 7-iteration unrolled loop (poll
  `FCN0M{idx}CTL` bits TRQF(9)/TCPF(1), literal `mov idx,r6 ; jarl 0x1d96e,lp` for idx=0..6, then ONE
  unconditional `jarl 0x1db74,lp`) — Segment 4 §2/§4 found this in full, including the exact SVD field
  names for the poll. **My own "7-iteration literal mailbox loop" section below independently rediscovered
  the identical 7 call-site addresses and the same structure from a different entry point (JARL-scanning
  `FUN_0001d96e`'s callers rather than reading `FUN_0001dcaa` forward) — treat it as CONFIRMATION of
  Segment 4's finding, not a new discovery.**
- **`FUN_0001d82e` (call site `0x1d904`)'s true role** — Segment 4 §5 already fully characterized it as a
  SEPARATE CAN-driver bus/error-event dispatcher (12 callers enumerated, argument values 0/1/2/3/16/17,
  none in Table-B's 4-10 range) — a much deeper trace than this document's one-line "new lead, not chased"
  note on the same 12 callers. **Defer to Segment 4 for `FUN_0001d82e`; it is NOT a message-content path.**
- **The `0xFEDF68BC` RAM table's semantics as "mailbox ownership," not just "pending status."** Segment 1
  §"CONFIRMED: FUN_0001d68e never writes CTL/CSETR" independently disassembled `FUN_0001d68e`'s OWN second
  critical section (`0x1d7c0-0x1d828`) and found **`FUN_0001d68e` itself reads `RAM_table[mailbox_idx]`
  (its OWN arg1, `r27`) and compares it against `logical_idx` (its OWN arg2, `r23`)** — on mismatch it
  writes the `0xFFFF` sentinel back and returns a reclaim code (0 or 5) that gates the conditional
  `FUN_0001e9fc` cleanup call at the caller. This means the RAM table is a genuine **mailbox-ownership
  ledger** (`table[hw_mailbox] = currently-assigned logical Table-B index`), consistent with — and
  materially deepening — this document's own reading of `FUN_0001d96e`'s prologue (which reads the SAME
  table by `mailbox_idx` to get the registered `logical_idx` before dispatching). Segment 4 independently
  reached the same "ownership" framing from the consumer side (calls it `STATUS[idx]`). **All three
  documents (this one, Segment 1, Segment 4) now triangulate on the SAME table via 3 different entry
  points** — high confidence in this part.
- **The recurring "invalid+unaligned" 2-byte decode gap is not unique to this document.** Segment 1 (§
  "Tooling caveat") and Segment 3 (OPEN #3) independently flag the SAME symptom at different addresses
  (`ac 07`/`a5 07`/`84 07`/`a2 07` families) and both explicitly leave it unresolved ("no v850 target in
  this environment's objdump, no V850 support in capstone"). **This document's contribution is resolving
  ONE specific instance of this family** (the `ld.bu D16_16[ep],rX` 4-byte form used in the nibble-scan,
  see below) via the authoritative binutils opcode table — the first of the 4 segments to actually crack
  this gap rather than merely flag it. The other instances (`ac 07` etc., different bit patterns, possibly
  different opcodes) are NOT resolved by this document and may need separate hand-decodes.
- **Segment 1 explicitly asked**: *"does call site 2 (`0x1db32`) ever pass a mailbox index other than 6
  for any of Table B's 17 logical slots?"* (their Caveat + Open Item #4) — **this document's finding below
  (`r6 = NOT(r8)` at `0x1db32`, structurally different from `0x1dc8e`'s literal `mov 6,r6`) is a partial
  answer: YES, mailbox_idx is COMPUTED (not the literal 6) at this call site, differing structurally from
  the other live call site. The exact resolved number remains open (see below) but the qualitative answer
  to Segment 1's question is "the two live call sites do NOT use the same mechanism for mailbox_idx."**

This document's own genuinely NEW contributions, not covered by 1/3/4: the byte-level opcode resolution of
the 8-arm nibble-priority-encoder ("the nibble-decode tree," which Segment 4 §4's note explicitly left as
"NOT resolved this session") via the authoritative binutils `v850-opc.c`; the exact per-nibble-arm computed
addresses and their byte content (mostly erased flash); and the `r6=NOT(r8)` finding at `0x1db32` itself.

## ⚠ Tooling finding, load-bearing for all V850E2 EP-relative work — READ FIRST

**r2's `v850.gnu` mis-decodes `ld.bu D16_16[ep], rX` (the general-form byte-load with EP as the
explicit base register, opcode field `0x079e`-style, i.e. `R1=ep(30)`).** It splits the 4-byte
instruction into a spurious 2-byte `invalid`+`unaligned` pair followed by a 2-byte `sld.h N[ep],rX`
misread (r2 mis-tags the mnemonic as `sld.h`/halfword when the real opcode is a BYTE load `ld.bu`, and
the "138" displacement it prints is coincidentally close to but not the same field as the real 16-bit
signed displacement). **This is a NEW, distinct V850E2 decode gap from the ones in
`memory/reference_rizin_ghidra_v850_quirks.md`** (that doc covers `sld.hu`/`sld.bu`/`sld.w` compact-form
scaling bugs and `divq` semantics; this is r2 failing on the *general* `ld.bu`/`ld.b` D16_16/D23 formats
specifically when `reg1==ep`, a combination the compiler apparently uses but which trips up `v850.gnu`'s
table).

**Resolution method (reusable):** fetched the authoritative GNU binutils `opcodes/v850-opc.c` (via
`https://gitweb.gentoo.org/fork/binutils-gdb.git/plain/opcodes/v850-opc.c`, since GitHub raw/blob URLs
404'd through the proxy — the gitweb "plain" mirror worked) and hand-verified the bit-level match/mask
pairs and `insert_d16_16`/`extract_d16_16` functions directly:
```c
{ "ld.bu", two(0x0780,0x0001), two(0x07c0,0x0001), {D16_16, R1, R2_NOTR0}, 2, PROCESSOR_NOT_V850 },
extract_d16_16(insn): ret = ((insn>>16)&0xfffe) | ((insn>>5)&1); ret = (ret^0x8000)-0x8000;
```
Verified this EXACT formula reproduces the project's own self-check value (`0x410c0`
`ld.bu -26622[gp], r12`, bytes `84 67 03 98`) to the integer: `d16_16_extract(0x98036784) == -26622`
exactly. This is strong independent confirmation the formula and methodology are right, not just
plausible. **Any future V850E2 disasm session that hits an "invalid"+"unaligned" pair immediately before
what r2 renders as a compact `sld.*`/`sst.*` should suspect this exact gap — re-derive via the raw
`(word0, word1)` pair and the `extract_d16_16`/`extract_d23` formulas above before trusting r2's split.**

## CONFIRMED — the two dispatchers are byte-identical twins

`0x1d9a0-0x1dae6` (feeds call site `0x1db32`, inside `FUN_0001d96e`) and `0x1db90-0x1dc40` (feeds call
site `0x1dc8e`, inside a **separate function** `FUN_0001db74`) are **byte-for-byte identical** compiled
bodies (same relative offsets, same instruction bytes at every corresponding address, only the base
address differs) — confirmed by direct comparison of both hex dumps. This is a shared inline
macro/helper the compiler duplicated, not two independently-written dispatchers.

### Structure: 8-way nibble priority-encoder over a 32-bit word in `ep`

Elimination logic (all cleanly decoded, no ambiguity — standard `movhi`+`and`+`be` idiom):
```
test bits[31:16] (movhi -1,r0,r11; and ep,r11; be -> skip to bits[15:0] half)
test bits[31:24] (movhi -256,r0,r9; and ep,r9; be -> skip to bits[23:16])
test bits[31:28] (movhi -4096,r0,r7; and ep,r7; be -> skip to bits[27:24])
  -> nibble 28 arm
  -> nibble 24 arm
test bits[23:20] (movhi 240,r0,r16; and ep,r16; be -> skip to bits[19:16])
  -> nibble 20 arm
  -> nibble 16 arm
test bits[15:8]  (andi 0xff00,ep,r0; be -> skip to bits[7:0])
test bits[15:12] (andi 0xf000,ep,r0; be -> skip to bits[11:8])
  -> nibble 12 arm
  -> nibble 8 arm
test bits[7:4]   (andi 0xf0,ep,r0; be -> skip to bits[3:0])
  -> nibble 4 arm
  -> nibble 0 arm (implicit, no shr needed — bits[31:4] already proven zero)
```
Each arm: `shr N,ep ; add r5,ep` (`ep = tp(0xBF000) + nibble_raw_value(0-15)`), then a 4-byte
`ld.bu D16_16[ep], rDEST` (the mis-decoded instruction above), then `ld.b DISP16[r0], lp` (reads an SFR
byte in the `0xFFFFE6xx` range, e.g. `-6650[r0] = 0xFFFFE606` — a peripheral-adjacent read, side-effect
only, result discarded via `mov rX,r0` afterward — **INFERRED this is a "read-to-ack" hardware idiom, not
data flow**), then `br` to the merge point.

### Per-nibble destination register and computed table address (CONFIRMED via authoritative decode)

| nibble shift | dest reg (R2/R3 field, bits[26:22] of combined insn) | `D16_16` disp | computed addr = tp+disp (+nibble 0-15) | byte content at addr |
|---|---|---|---|---|
| 28 | r6  | 13380  | `0xC2444` | **0xFF-filled (erased/unprogrammed flash)** |
| 24 | r15 | 31812  | `0xC6C44` | real small-int data (`00 00 19 00 28 57 ff 00 ...`) |
| 20 | r13 | 27716  | `0xC5C44` | 0xFF-filled |
| 16 | r11 | 23620  | `0xC4C44` | 0xFF-filled |
| 12 | r9  | 19524  | `0xC3C44` | 0xFF-filled |
| 8  | r7  | 15428  | `0xC2C44` | 0xFF-filled |
| 4  | r16 | -31676 | `0xB7444` | all-zero (programmed, in the same neighborhood as Table-B's zero-fill region) |
| 0  | r28 | -7100  | `0xBD444` | structured data (`1b e4 53 3f 6d ca 53 3f ...` — possible float-stride table) |

**Note re: the mission brief's "4 sub-tables at `0xb71cc`/`0xb71e0`/`0xb71f4`/`0xb72f4`" framing —
this is NOT actually a correction, it's confirming what Segment 4 already established (§4 of
`reference_accord_internal_id_lifecycle.md`, "TABLE_1"/"TABLE_2"/"TABLE_3", byte-verified there first):
those 4 addresses are read by a separate, EARLIER code segment in the same function (`0x1d9c4-0x1da02`,
indexed by `r26`=`STATUS[idx]`, executed BEFORE the `cmp 6,r24` branch that falls into the nibble-scan
fallback), not by the 8-arm nibble encoder itself. Segment 4 explicitly flagged the nibble-scan's OWN
operand as unresolved ("What this classifier actually operates on was NOT resolved this session") — THAT
is the gap this document closes. The nibble-scan's own per-arm reads target a different address range
entirely (`0xB7444`-`0xC6C44`), only loosely neighboring the named 4 tables (only nibble-4's `0xB7444` is
even in the same `0xB7xxx` page). **Only 3 of the 8 nibble arms (24, 4, 0) land on non-erased flash; the
other 5 read blank 0xFF flash — consistent with only a subset of the 8 possible nibble positions being
"wired" in the current build, the rest reserved/unused.**

## CONFIRMED — the 4 named sub-tables (`0xb71cc`/`0xb71e0`/`0xb71f4`/`0xb72f4`), dumped and decoded

Raw byte dumps (`px` at each address):

- **`0xb71cc`** (read via `mov 0xb71e0,ep;add r26,ep;sld.bu 0[ep],ep` at `0x1d9c4-1d9cc` — wait, table
  base used there is `0xb71e0`, see below; `0xb71cc` itself dumped for completeness):
  `c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c1 c4 00 00 00 00 00 00 00 00 00 00 01 01 01 01`
  — **17 bytes of `0xC1`** (indices 0-16, exactly Table-B's 17-entry logical-index range), then `0xC4`
  at index 17 (Table-B's own sentinel position), then zero-fill, then `0x01` run. Byte-indexed by
  logical index (0-16) with a distinct terminator value — same shape as Table-B's own 17+1 structure.
- **`0xb71e0`** (read directly: `mov 0xb71e0,ep; add r26,ep; sld.bu 0[ep],ep` at `0x1d9c4-1d9cc`, indexed
  by `r26` = the RAM-registered per-mailbox value, see below): `00 00 00 00 00 00 00 00 01 01 01 01 01
  01 01 01 02 02 00 00 01 02 04 08 10 20 40 80 01 02 04 08` — bytes 0-7=`0x00`, 8-15=`0x01`, 16-17=`0x02`
  (a coarse "group" classifier, 3 groups over indices 0-17), then a **bitmask-power-of-2 sequence**
  (`1,2,4,8,16,32,64,128,...`) starting at `0xb71f0`.
- **`0xb71f4`**: two repeats of the power-of-2 bitmask sequence (`01 02 04 08 10 20 40 80` ×2, 16 bytes),
  then `01 02 00 00`, then **eleven bytes of `0x06`** at `0xb7208-0xb7212` followed by `0x05` at
  `0xb7213`. **This independently reproduces Segment D's already-confirmed "channel byte @ 0xb7208 = 6
  for all 11 TX-capable Table-B entries (idx 0-10)" finding, byte-for-byte, from a direct raw dump in
  this session** (not a re-quote) — `0xb71f4` and `0xb7208` are the same contiguous data blob, `0xb7208`
  sitting 20 bytes into it.
- **`0xb72f4`** (read via `mov r26,ep;shl2,ep;mov 0xb72f4,r7;add r7,ep;sld.w 0[ep],r22` at
  `0x1d9f6-0x1da02`, a **function-pointer table indexed by r26** — same per-mailbox RAM-registered value):
  **all-zero for at least `0x60` bytes** (`0xb72f4`-`0xb7350`), confirmed by direct dump. `0xb72f4` sits
  exactly at Table-B's own fn-ptr array end (`0xb72ac + 18*4 = 0xb72f4`), i.e. this "table" is the
  immediate zero-padding *past* Table-B's declared 17(+sentinel) entries, not a separate populated
  structure. **This makes the fn-ptr dispatch at `0x1da02-0x1da10` (`cmp r0,r22; be 0x1da12` /
  `jmp[r22]`) structurally DEAD for every currently-populated Table-B index (0-16)** — `r22` is always 0
  for those indices, so the `be 0x1da12` branch is always taken, falling into the nibble-scan. This is
  the SAME "call site 1 is dead" shape independently re-discovered at a different layer (matches
  Segment C/D's `0xb7208==6` dead-branch finding for call site `0x1d904`, and now shown to have a sibling
  dead branch inside the live-call-site function too).

## CONFIRMED — a per-hardware-mailbox RAM registration table drives BOTH dispatchers

`FUN_0001d96e(mailbox_idx)` prologue (`0x1d96e-0x1d992`):
```
0x1d972: zxh r6                          ; r6 = incoming param, zero-extended
0x1d974: mov r6,r10 ; shl 1,r10          ; r10 = mailbox_idx * 2
0x1d978: mov 0xfedf68bc,ep ; add r10,ep  ; ep = RAM base 0xFEDF68BC + mailbox_idx*2
0x1d980: sld.hu 0[ep],r26                ; r26 = registered "logical" value for this mailbox
0x1d982: mov r6,r24                      ; r24 = mailbox_idx, held for the REST of the function
...
0x1d99c: xori 0xffff,r26,r0 ; bne 0x1d9a6 ; if r26==0xFFFF (empty), skip to exit — else enter dispatcher-1
```
`gp`-relative: `0xFEDF68BC - 0xFEDF8000 = -0x1744 (-5956)`. **This is a genuine per-hardware-mailbox
software registration table, halfword stride, sentinel `0xFFFF` = "nothing registered for this mailbox
right now."** `r26` (the registered value) becomes `r7` (logical_idx) at BOTH live `FUN_0001d68e` call
sites (`mov r26,r7` at `0x1db30` and `0x1dc8a`).

**Could NOT find the writer of this table.** Exhaustive literal-scan for `mov 0xfedf68bc` (6-byte
absolute-immediate form) found exactly 8 occurrences in the whole image, all clustered `0x1d050-0x1d97a`
— **7 of them are READS/compares** (`sld.hu`/`ld.hu` + `cmp`, checking "does slot X already hold value Y"
— reverse-lookup / dedup checks), **none is a STORE**. This matches the exact same dead-end pattern prior
sessions hit for the `gp-13004+idx*44+6/8` RAM field (`reference_accord_can_tx_segmentA_channel_topology.md`
§4/§5d) and the boot-time `MID0H`/`MID1H` per-buffer writer
(`reference_accord_can_tx_fcn0_forward_verify.md` open item 1) — **a third independent RAM-registration
table in this exact driver cluster whose writer resists literal-scan.** Likely written via a
computed/pointer-parameterized store (folded constant or caller-supplied pointer), not a literal
`movea`/`mov`-absolute form. **Next step: Ghidra decompile of the functions with JARL callers into this
module (`0x1d050`, `0x1d0aa`, `0x1d11c`, `0x1d664`, `0x1d7ce`, `0x1d808` — all reads) to find their own
callers, one of which is plausibly the true registration/allocator.**

## CONFIRMED — call-site inventory (re-verified fresh this session, not re-quoted)

`FUN_0001d68e` has exactly 3 static JARL callers, confirmed again via the disp22 byte-scanner:
`0x1d904`, `0x1db32`, `0x1dc8e` (matches all prior sessions exactly).

| call site | enclosing fn | invocation pattern | r6 (mailbox_idx) | r7 (logical_idx) | live? |
|---|---|---|---|---|---|
| `0x1d904` | `FUN_0001d82e` | called from 12 sites incl. `0x55584-0x55596`. **Segment 4 already traced all 12 in full and found `FUN_0001d82e` occupies a SEPARATE index space tied to CAN-driver bus/error events (args 0/1/2/3/16/17, none in Table-B's 4-10 range) — it is NOT a message-content path, defer to their §5** | `mov r26,r6` (r26 = `0xb7208[r24]` channel byte) | `mov r24,r7` | **DEAD** — re-confirmed structurally consistent with Segments C/D: the `cmp 6,r26;bne` gate before reaching `0x1d904` early-returns for every populated Table-B entry (channel byte is uniformly 6) |
| `0x1db32` | `FUN_0001d96e`, called 7× with **literal** `mov N,r6` for N=0..6 by the outer coordinator `FUN_0001dcaa` (Segment 4's finding, independently reconfirmed here — see below) | `r7 = mov r26,r7` (r26 = RAM-registered value, see above). **`r6 = not r8,r6` at `0x1db10`** (bitwise complement, NOT a literal) | COMPUTED, not literal | **live** (reachable when the per-mailbox RAM slot is non-empty) |
| `0x1dc8e` | `FUN_0001db74`, called exactly **once**, unconditionally, immediately after the 7-iteration polling loop | `r7 = mov r26,r7` (own dispatcher-2's r26, same shape) | **`r6 = mov 6,r6`** — compile-time literal | **live** |

### `0x1db32`'s `r6 = NOT(r8)` — OPEN, could not pin the numeric value

Byte-confirmed clean decode (no invalid markers) at `0x1db10-0x1db12`:
```
0x1db10: 2830   not r8, r6      ; r6 = ~r8   (opcode 0x01, verified against v850-opc.c: NOT is OP(1))
0x1db12: 4651   and r6, r10     ; r10 = r10 & ~r8   (classic "clear bits of r10 that are set in r8" idiom)
```
No further write to `r6` occurs between `0x1db12` and the `jarl` at `0x1db32` (confirmed by full linear
read of the intervening bytes). **r8's last confirmed assignment is `mov 0xb71f4,r8` at `0x1d9e2`** (~600
bytes earlier, the literal table-base address used for the EARLIER `0xb71f4` table-context lookup) —
**a search for any intervening store to `r8` found none**, but several instruction clusters between
`0x1d9e2` and `0x1db10` remain only partially decoded (a recurring `invalid+unaligned+sst.b+tst1` shape
that this session tentatively identifies as an atomic status-bit-commit idiom, structurally unlikely but
not proven to touch `r8`). **Taking r8=0xb71f4 literally gives `NOT(0xb71f4) & 0xFFFF = 0x8E0B` (36363) —
not a plausible mailbox index** (`FUN_0001d68e` masks to 16 bits then does `idx*64 + 0xFF481000`, which
for idx=36363 would compute a wildly out-of-range hardware address). **This is flagged as a genuine open
item, not guessed away**: either (a) `r8` is reassigned somewhere in a still-undecoded byte cluster this
session could not fully resolve, or (b) the `not/and` pair is unrelated scratch (clearing bits of some
OTHER accumulator, e.g. `r10`) that happens to leave a stale, semantically-unintended value sitting in
`r6` at the point of the call — which would be surprising for production automotive firmware but cannot
be ruled out from static reading alone. **What would close this:** a Ghidra decompile of
`FUN_0001d96e`'s full body (this session used raw r2/hand-decode throughout, no Ghidra) to get proper
data-flow tracking through the `di`/`ei`-wrapped critical section, or a live register trace.

**Bearing on Segment 1's finding**: Segment 1 (`reference_accord_can_tx_trigger_path.md`) showed
`FUN_0001d68e` itself re-reads `RAM_table[mailbox_idx]` (its own arg1) and compares it against
`logical_idx` (its own arg2) as an internal ownership-consistency check. Whatever `r6` resolves to at
`0x1db32`, `FUN_0001d68e` will use it BOTH as the `0xFF481000+idx*64` hardware address AND as the index
into the SAME `0xFEDF68BC` table for that check. If `r6` really were the implausible `0x8E0B` from a
literal reading of `r8`, the function would fail its own ownership check on essentially every call (since
`RAM_table[0x8E0B]` has nothing to do with where `FUN_0001d96e` actually read `r26` from,
`RAM_table[0..6]`), forcing the "stale/reclaim" path every time. Given this is shipped, driving-vehicle
firmware, steady-state operation almost certainly requires `r6` to equal the ORIGINAL `mailbox_idx`
(0-6). **This is indirect but fairly strong evidence that `r8` IS reassigned somewhere this session
couldn't decode, such that `NOT(r8)` ends up equal to `r24` (the original 0-6 index) — plausibly `r8 =
NOT(r24)` or an equivalent construction, not the stale `0xb71f4` literal.** Still flagged OPEN because
this is an inference from expected correctness, not a directly read instruction.

### The 7-iteration literal mailbox loop (fresh byte-confirmation, matches Segment C's prediction exactly)

`FUN_0001d96e` callers, found via JARL disp22 scan: exactly 7, at `0x1dcee, 0x1dd10, 0x1dd32, 0x1dd54,
0x1dd76, 0x1dd98, 0x1ddba` — each preceded by a poll of `FCN0M{N}CTL` (`0xFF489000+N*0x40+0x38`, SVD
`FCN0M{N}CTL`) and a **literal** `mov N,r6` for N=0,1,2,3,4,5,6 respectively (byte-verified, e.g. `0x1dcec:
mov 0,r6 ; 0x1dcee: jarl 0x1d96e,lp`, `0x1ddb8: mov 6,r6 ; 0x1ddba: jarl 0x1d96e,lp`). **`FUN_0001db74`
has exactly ONE caller: `0x1ddc2`, immediately after this 7-iteration loop, unconditionally, with NO
literal `mov` setting `r6` at that call site** (whatever `r6` last held from the N=6 iteration's context
carries in, but `FUN_0001db74`'s OWN `mov 6,r6` at `0x1dc8c` before its internal `FUN_0001d68e` call is a
fresh literal, independent of the caller's `r6`).

## INFERRED (well-supported, not proven) — mailbox assignment is a runtime dynamic pool, not a static per-message property

Putting the confirmed facts together: **7 hardware mailboxes (0-6) are polled once per tick via the
unrolled loop; each poll calls `FUN_0001d96e(N)`, which looks up "what logical Table-B index is currently
registered to mailbox N" in a RAM table (`0xFEDF68BC`), and if something is registered, dispatches it
through `FUN_0001d68e` with a computed (not literal) mailbox index. Immediately after, `FUN_0001db74` is
called once, unconditionally, and ALWAYS uses hardware mailbox 6 (literal) for whatever it finds via its
own (structurally identical) dispatcher.** No field anywhere in Table-B (`0xB721C` ID / `0xB71B8` DLC /
`0xB72AC` builder-ptr) encodes a fixed hardware mailbox number — this matches every prior segment's
negative result (Segment C: "the logical table has no visible channel field"; Segment D: "no field
splits car-facing from internal"). **This session's contribution: it's not merely that no such field was
found — structurally, THERE ISN'T ONE, because which physical mailbox (0-6, or the mailbox-6 overflow
path) carries a given logical message is decided at RUNTIME by the RAM registration table, not at compile
time.** This directly explains why 4 independent agents across 2 sessions could not find a static
channel/mailbox selector: the mapping is not static.

## ANSWER TO THE MISSION'S KEY COMPARISON

**Does 399 (Table-B idx 9, car-facing) use a different mailbox index than 0x660 (idx 4, internal)?**

Based on the evidence above: **there is no fixed answer — neither message has a permanently assigned
hardware mailbox.** Both are logical Table-B entries (idx 9 and idx 4 respectively) whose CAN-ID/DLC/
builder-ptr are looked up identically regardless of which physical mailbox eventually carries them. Which
of the 7 pooled mailboxes (or the dedicated mailbox-6 overflow path) actually transmits either message at
any given moment depends on the runtime content of the `0xFEDF68BC` registration table, which this
session could not trace to its writer. **Mailbox index therefore does NOT correlate with the
car-facing/internal split** — not because they happen to collide on the same value, but because mailbox
index is not a per-message-identity property in this firmware's design at all.

## Open questions / next verification steps

1. **Find the writer of the `0xFEDF68BC` per-mailbox RAM registration table.** Literal-scan exhausted
   (8 hits, all reads). Next: Ghidra decompile of the 6 reader functions' own callers, or trace backward
   from the Table-B builder functions (`FUN_00055c42`=399, `FUN_000561b0`=0x660, etc.) to see if THEY
   call a registration/allocator function that writes this table with their own Table-B index — this
   would be the actual smoking gun connecting "which message" to "which mailbox, when."
2. **Resolve `0x1db32`'s `r6 = NOT(r8)` numeric value** — needs Ghidra's proper data-flow tracking through
   the `di`/`ei` critical section this session's raw r2 read could not fully unpick (see above).
3. ~~`FUN_0001d82e` (call site `0x1d904`) callers~~ — **RESOLVED by Segment 4** (already fully traced;
   it's a CAN-driver bus/error-event dispatcher, unrelated to Table-B message content). No further action
   needed here.
4. **The 5 "erased flash" nibble-arm addresses (`0xC2444`,`0xC5C44`,`0xC4C44`,`0xC3C44`,`0xC2C44`)** being
   blank in the current build is consistent with "unused/reserved nibble slots," but this was not
   independently confirmed by finding what code does with an 0xFF read result (no downstream consumer of
   the loaded byte was traced this session). Flagged as INFERRED, not proven.
5. **Byte content at `0xC6C44` (nibble-24 arm) and `0xBD444` (nibble-0 arm)** looks structured/meaningful
   but was not decoded into a data model this session — worth a follow-up dump+decode pass if the
   nibble-scan's role turns out to matter for future work.

## Cross-references
- `reference_accord_can_tx_trigger_path.md` (Segment 1) — independently found `FUN_0001d68e`'s own
  `0xFEDF68BC` ownership-ledger read/write and NEVER writes CTL/CSETR; explicitly asked the mailbox-index
  question this document partially answers. Read together with this document.
- `reference_accord_can_init_mid_pinmux_topology.md` (Segment 3) — CAN controller boot init; confirms only
  FCN0 is ever enabled; independently hit the same "invalid+unaligned" v850.gnu decode-gap symptom at a
  different address (`a2 07` family) and flagged it unresolved, same as this document did before resolving
  its own instance.
- `reference_accord_internal_id_lifecycle.md` (Segment 4) — found the outer coordinator `FUN_0001dcaa`, the
  7×/1× call pattern, `FUN_0001d82e`'s true (unrelated) role, and the STATUS[]/TABLE_1/2/3 read side in
  full; left the nibble-scan operand as the one explicit open item this document closes.
- `reference_accord_can_tx_segmentC_driver_hw_mailbox.md`, `reference_accord_can_tx_segmentD_known_frame_provenance.md`,
  `reference_accord_can_tx_fcn0_forward_verify.md`, `reference_accord_can_tx_segmentA_channel_topology.md`,
  `reference_accord_can_tx_synthesis_2026-07-07.md` — the prior swarm passes this segment builds on.
- `memory/reference_rizin_ghidra_v850_quirks.md` — the SIBLING (but distinct) V850E2 decode-gap document;
  this file's "r2 mis-decodes `ld.bu`-with-`ep`-as-`R1`" finding should probably be appended there in a
  future pass, flagged for the operator to confirm before merging.
