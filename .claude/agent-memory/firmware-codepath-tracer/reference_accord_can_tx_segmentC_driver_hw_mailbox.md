---
name: reference-accord-can-tx-segmentc-driver-hw-mailbox
description: 2020 Accord TVA-A160 (V850E2) CAN TX driver + hardware mailbox layer, byte-verified on stock code.bin. Corrects the mission brief's premise that FUN_00016de6 is the HW mailbox writer (it is not — it's DTC/fault logging). Finds the real HW mailbox writer (FUN_0001d68e, base 0xFF481000/0xFF489000, 64B stride) and the real logical CAN-ID/DLC/builder table triplet (17 entries, exactly sized, sentinel-terminated — no free logical slot).
metadata:
  type: reference
---

# Accord TVA-A160 CAN TX driver + HW mailbox layer (Segment C, 2020-07-07 swarm)

Platform: 2020 Honda Accord 39990-TVA-A160, V850E2. All addresses verified on
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (flat base 0, offset==address) with
`r2 -a v850.gnu -b 32 -m 0 -s <addr> -c 'pd N' code.bin`. gp=0xFEDF8000, tp=0xBF000.

## ⚠ CORRECTION to the swarm task brief — read first

The task brief (inherited from `docs/handoffs/2026-06/HANDOFF-2026-06-30-v31t-telemetry.md` line 31) asserted
**`FUN_00016de6` = "HW mailbox write... pokes V850E2 CAN controller mailbox regs (TX request/abort)"**.
**This is WRONG.** Direct disassembly of `FUN_00016de6` at `0x16de6` shows:
- Args masked `andi 0xFFFF,r6,r26` / `andi 0xFFFF,r7,r21` / `andi 0xFF,r8,r20` / `andi 0xFF,r9,r23`
  (the masking pattern IS real — 16/16/8/8 — but that doesn't make it a HW mailbox call).
- Reads `ld.bu -6611[gp],r10` — a "DTC logging enabled" flag; early-returns with `0x8000` if clear.
- Indexes a `u16`-stride (`shl 1`) fault-status bitmask table at `gp-0x1954`ish (`movea -6348,gp,r8`),
  sets/clears bit `0x800`(2048) based on arg2 (code) vs 1/4.
- Calls `FUN_0001611e` (hard-fault-eligible check) and conditionally `FUN_00018738` (DTC trip-counter →
  `gp-0x685c` latch → `FUN_00019f7c` hard shutdown).

This is **byte-for-byte identical in structure** to the DTC/fault-log chain independently mapped in
[[reference-accord-consistency-monitor-hardshutdown]] (`FUN_00016de6→FUN_00018738→gp-0x685c/gp-0x3ef8→
FUN_00019f7c→FUN_0001a16a→FUN_00045608`), confirmed from a **completely separate investigation**. Two
independent traces agree: **`FUN_00016de6` is the DTC/fault-event logger, not a CAN peripheral write.**

`FUN_000541d8` calls `FUN_00016de6` three times (`0x5421a`, `0x54272`/`0x54196`/`0x541be` via callee
`FUN_0005413a`), always as `(u16_field, code, flag3, flag4)` — logging checksum-mismatch / retry faults
on its own TX descriptor bookkeeping, not committing anything to hardware.

## FUN_000541d8 — real role: SOFTWARE TX descriptor checksum-validate/retry state machine

`FUN_000541d8(arg1=slot, arg2=buf_ptr_or_similar, arg3, arg4)`, confirmed body `0x541d8-0x542a2`:
- `andi 0xFFFF,r8,r27` — masks arg3 to 16 bits (NOT arg1; the "masks arg to 16 bits" note in the task
  brief refers to arg3, not a CAN ID field on this function).
- Calls `FUN_00053f32` (a 20-case `switch r6` field/bit-test dispatcher, orig arg1), then `FUN_00054052`,
  then `FUN_00057b24` (Honda 4-bit rolling counter/checksum, confirmed elsewhere as the same function
  used by all known CAN-TX content builders).
- Indexes a **44-byte-stride RAM descriptor table at `gp-0x32CC`** (`movea -13004,gp,rX`; -13004 = -0x32CC),
  slot = arg1 (`mulhi 44,r7,r28`). Confirms the handoff's "44-byte descriptor table at gp-0x32cc (RAM)"
  claim exactly.
- On checksum match: clears descriptor fields `+0x14`(u32) and `+0xE`(u16), logs success via
  `FUN_00016de6(field+6, 1, 0, 1)`.
- On mismatch: sets `+0x14=2`, calls `FUN_000540d0` (retry-counter bump, compares against 4, timestamps
  at `+0xC`/`+0xE`), then state-machine branches (status codes 2/6/7) each logging via `FUN_00016de6`.
- Sibling functions in the SAME cluster, all operating on the SAME 44-byte RAM table (no HW touch):
  `FUN_0005413a` (type-field `+0x18` state-transition dispatcher, called right after `FUN_000541d8` from
  the scheduler), `FUN_00054052`/`FUN_000540d0` (retry/timeout accessors), `FUN_00054520` (called
  BEFORE `FUN_000541d8` in the scheduler at `0x5211c`; clears fields, does lockstep lo/hi consistency
  checks against `0x6b9fa`, logs `FUN_00016de6(field6,4,0,1)` on mismatch).
- **None of these touch a hardware address.** All I/O is RAM read/write on the `gp-0x32CC` table.

Scheduler caller confirmed at `0x52148` inside `FUN_000520d0` (the sole `jarl` xref to `0x541d8` in the
whole binary, verified by disp22 brute-force scan): `mov r25,r6` (slot); `ld.w 20[r26],r7` (buf ptr from a
**separate 32-byte ROM record table at `~0xBB544`**, per-slot fields period(+0xE)/bufptr(+0x14)/
callback(+0x1C) — this ROM table is CONFIRMED by direct byte dump: **exactly 19 records (idx 0-18,
little-endian index as first u32 of each record), terminated by an all-zero sentinel record at idx19**
(`0xBB7A4`). No spare capacity in this generic 19-slot periodic-task scheduler table either — it's
exactly sized, same pattern as the CAN-ID table below.

## THE REAL hardware mailbox writer: FUN_0001d68e

Found via raw-pointer literal scan (not jarl xref — this function is invoked indirectly through data
tables), then confirmed via disassembly. Function boundary `0x1d68e` (`prepare {r20,r22-23,r25-28,lp},4`).

```
0x1d692: andi 0xFFFF,r6,r27      ; arg1 masked 16-bit -> r27 = HARDWARE MAILBOX INDEX
0x1d696: andi 0xFFFF,r7,r23      ; arg2 masked 16-bit -> r23 = LOGICAL MESSAGE-SLOT INDEX (0-16, see below)
0x1d69e: addi -17,r23,r0 ; bnl 0x1d6aa   ; bound check: r23 vs 17 -- MATCHES the 17-entry table found below
0x1d6cc: mov r23,r22 ; shl 2,r22          ; r22 = logical_idx * 4  (stride-4 index into the ID/builder tables)
0x1d6d0: mov r27,r28 ; shl 6,r28          ; r28 = mailbox_idx * 64
0x1d6d4: mov 0xff481000,r6 ; add r6,r28   ; r28 = 0xFF481000 + mailbox_idx*64   <-- HW MAILBOX BASE (channel A)
0x1d6dc: cmp r0,r15 ; bne 0x1d6f4          ; branch on a flag computed from the bound check above
0x1d6f4 (r15!=0 path): mov 0xb721c,ep; add r22,ep; ld.w 0[ep],r13   ; load CAN-ID-table entry (see below)
         mov 0xb71b8,ep; ...                                          ; load DLC-table entry
0x1d728: mov 0xb72ac,ep; add r22,ep; sld.w 0[ep],r25 ; cmp r0,r25; be [skip]  ; NULL-checked load of
         the TX content-builder function pointer for this logical slot
0x1d744: jmp [r25]                                                     ; INDIRECT CALL to content builder
0x1d768 (after builder returns): [content ptr r26 from builder, non-null check]
0x1d774: jarl 0x1f98e,lp ; di                                          ; lock (di/ei wrapped, matches
                                                                          the known di/ei idiom FUN_0001fa42/
                                                                          FUN_0001fa72 elsewhere)
0x1d77c-0x1d7b8: mov r27,ep; shl 6,ep; mov 0xff481000,r8; add r8,ep    ; ep = HW mailbox base + idx*64
    ld.bu 0[r26],r6  -> sst.b r6, 0[ep]     ; data byte 0 -> mailbox+0x00
    ld.bu 1[r26],r15 -> sst.b r15,4[ep]     ; data byte 1 -> mailbox+0x04
    ld.bu 2[r26],r13 -> sst.b r13,8[ep]     ; data byte 2 -> mailbox+0x08
    ld.bu 3[r26],r11 -> sst.b r11,12[ep]    ; data byte 3 -> mailbox+0x0C
    ld.bu 4[r26],r8  -> sst.b r8,16[ep]     ; data byte 4 -> mailbox+0x10
    ld.bu 5[r26],r6  -> sst.b r6,20[ep]     ; data byte 5 -> mailbox+0x14
    ld.bu 6[r26],r15 -> sst.b r15,24[ep]    ; data byte 6 -> mailbox+0x18
    ld.bu 7[r26],r13 -> sst.b r13,28[ep]    ; data byte 7 -> mailbox+0x1C
0x1d7ba: bl 0x1d7c0 ; ei                                                ; unlock
```

**CONFIRMED: this IS the genuine raw hardware CAN TX mailbox write** — the 8 CAN payload bytes are
scattered one-per-4-byte-aligned-register across the low 32 bytes of a 64-byte-stride mailbox block, a
classic Renesas CAN-peripheral register layout (one byte-lane per word-aligned SFR). Base address
`0xFF481000` is far outside both flash (`0x0-0xFFFFF`) and RAM (`gp`=`0xFEDF8000` region) — consistent
with V850E2 peripheral I/O (SFR) space.

**3 callers of `FUN_0001d68e`** (verified via disp22 jarl brute-force scan, the only ones in the binary):
`0x1d904`, `0x1db32`, `0x1dc8e` — all within a tight low-level driver cluster `0x1d68e-0x1de00`. These
callers pass a mailbox index (`r26`/`r10` origin) and a logical-type index (`r24`) as **separate
registers**, i.e. **mailbox index ≠ logical index is the observed calling convention** — the mapping
between them is NOT confirmed 1:1 in this session (see Open Questions).

## The REAL logical message table: 3 parallel arrays, EXACTLY 17 entries, NO free slot

Byte-dumped and decoded directly from ROM. All three tables share the same index `i` = 0..16:

| Table | Base | Stride | Format | Verified |
|---|---|---|---|---|
| DLC | `0xB71B8` | 1 byte | raw DLC value | byte-exact match to all 7 known DLCs |
| CAN ID | `0xB721C` | 4 bytes | `(ID << 18) & (0x7FF<<18)` in top bits of a 32-bit word | exact match to all 7 known IDs |
| TX content-builder ptr | `0xB72AC` | 4 bytes | function pointer, `0` = no TX builder (RX-only slot) | exact match to all 7 known builder addrs |

Decoded (id_raw>>18 & 0x7FF = CAN ID; verified against `docs/handoffs/2026-06/HANDOFF-2026-06-30-v31t-telemetry.md`'s
known-builder list for idx4-10):

```
idx  CAN ID   DLC  builder        role
 0   0x720    8    0x000558a6     TX-capable, ID NEWLY IDENTIFIED this session (not in prior known-frame list)
 1   0x721    8    0x00055840     TX-capable, NEWLY IDENTIFIED
 2   0x722    8    0x000557c8     TX-capable, NEWLY IDENTIFIED
 3   0x723    8    0x00055616     TX-capable, NEWLY IDENTIFIED
 4   0x660    8    0x000561b0     TX, internal-only (known: heartbeat/piggyback target)
 5   0x64D    5    0x0005605c     TX, internal-only (known)
 6   0x32E    4    0x000562b8     TX, internal-only (known)
 7   0x1AB    3    0x00055d80     TX, CAR-FACING (427 MOTOR_TORQUE, known)
 8   0x19F    6    0x00055f2e     TX, internal-only (known)
 9   0x18F    7    0x00055c42     TX, CAR-FACING (399 STEER_STATUS, known)
10   0x14A    8    0x00055a98     TX, CAR-FACING (0x14A, known)
11   0x75B    8    0x00000000     RX-only (no TX builder) — NEWLY IDENTIFIED
12   0x753    8    0x00000000     RX-only — NEWLY IDENTIFIED
13   0x752    8    0x00000000     RX-only — NEWLY IDENTIFIED
14   0x72B    8    0x00000000     RX-only — NEWLY IDENTIFIED
15   0x6FF    8(?) 0x00000000     RX-only — NEWLY IDENTIFIED (idx15 ID-table raw value was less clean;
                                   moderate confidence, re-verify)
16   0x6FB    8    0x00000000     RX-only — NEWLY IDENTIFIED
17   —        —    —              **SENTINEL: ID-table raw = 0x800007FF (MSB set, low 11 bits = ID mask
                                   0x7FF) — classic end-of-table marker. Builder-table idx17 = 0.**
```

The `0x720-0x723`/`0x72B`/`0x752`/`0x753`/`0x75B`/`0x6FF`/`0x6FB` IDs are all in the `0x6xx-0x7xx` range
consistent with UDS/diagnostic request-response traffic (functional/physical request IDs), not
consumer-visible signal frames — plausible but **NOT independently confirmed** against opendbc/DBC
reference in this session.

**This table is EXACTLY sized to today's 17 known messages and sentinel-terminated.** This directly
explains the `addi -17,r23,r0 ; bnl` bound check seen in `FUN_0001d68e`'s prologue (r23 = arg2 = logical
index, checked against 17). **There is no unused/NULL entry inside the valid range (idx 0-16) — the
table simply ends.** My first-pass read of the *builder-pointer table alone* (idx11-32 all zero) is
**WRONG as a "22 spare slots" claim** — idx11-16 are legitimate RX-only entries (real ID + DLC, builder=0
because RX doesn't need one), and idx17+ is past the table's declared end (garbage/unrelated adjacent
data, confirmed by ID-table values becoming non-sensical — RAM buffer-pool pointers, not IDs — from
idx18 onward).

## Second CAN channel confirmed: 0xFF489000

An unrolled per-mailbox status-polling loop at `0x1dcd0-0x1ddb0` (part of the same driver cluster) reads
`ld.hu 0x38[mailbox_base], status` for **7 explicit unrolled mailbox indices** at hardcoded addresses
`0xFF489000, 0xFF489040, 0xFF489080, 0xFF4890C0, 0xFF489100, 0xFF489140, 0xFF489180` (indices 0-6, exact
`0x40`=64-byte stride match), masks `andi 0x203,status,tmp; addi -0x201,tmp,r0; bne` (checks specific
status bits), then dispatches `FUN_0001d46c`/`FUN_0001d96e`/`FUN_0001d49e` with the literal mailbox index
(`mov N,r6` for N=0..6) — clearly a **second physical CAN channel/controller instance**, exactly
`0xFF489000 - 0xFF481000 = 0x8000` (32KB) higher, same mailbox layout. A parallel control-block read
exists at `0xFF480240`(channel A, seen at `0x1d912`) vs `0xFF488240`(channel B, seen at `0x1dcbc`,
`ld.hu 32[ep],r16` = reads `0xFF488260`) — also `+0x8000` apart, consistent with two full CAN module
instances at that spacing.

**`FUN_0001d68e` (the byte-scatter TX write) only ever hardcodes `0xFF481000` (channel A) at its 3 call
sites.** No channel-A-vs-B twin of `FUN_0001d68e` was located this session — if channel B also transmits
via byte-scatter writes, that function is still unfound (see Open Questions).

## Mailbox count (INFERRED, not exhaustively confirmed)

Literal-address high-water-mark scan (`base + idx*0x40` as a raw 32-bit pointer constant appearing
anywhere in `code.bin`) found:
- Channel A (`0xFF481000`): highest referenced index = **56** (indices 0,7,25,33,56 found as literals;
  sparse coverage — most code computes the address arithmetically via `shl 6` rather than embedding a
  literal per-mailbox, so this undercounts).
- Channel B (`0xFF489000`): highest referenced index = **63** (indices 0-6,25,33,56-63 found), consistent
  with a full 64-mailbox array (0-63).

**Working estimate: up to 64 hardware mailboxes per channel** (INFERRED from the channel-B high-water
mark of 63, not from an explicit "NUM_MAILBOXES=64" bound-check instruction — genuinely open). If
correct, **hardware mailbox RAM is NOT the scarce resource** — only ~11 TX-active + ~6 RX logical slots
are wired today out of up to 64 physical mailboxes per channel. The scarce resource is the **exactly-sized
17-entry software ID/DLC/builder table triplet**, not hardware mailbox count.

## Deliverable: occupancy map / spare candidates (CORRECTED framing)

- **Logical (software) slots: 17/17 used, sentinel-terminated. Zero free logical slots exist today.**
  Adding a new CAN-TX frame requires **extending** the 3 parallel tables (`0xB71B8` DLC,
  `0xB721C` ID, `0xB72AC` builder-ptr) by one entry each — a genuine relocate+resize patch, not a
  drop-into-an-existing-NULL-entry patch. The known code cave `0xC4E00-0xC4FEF` (~528 bytes, per
  `docs/handoffs/2026-07/HANDOFF-2026-07-07-gating-map-and-telemetry-plan.md` §4) is comfortably large enough to host an
  18-entry version of all three tables (18×4 + 18×4 + 18×1 = 162 bytes) plus a small new content-builder
  function, if every code reference to the 3 table bases is found and repointed (multiple xrefs exist —
  not yet fully enumerated this session, see Open Questions).
- **Hardware (physical) mailboxes: plentiful headroom.** Only a fraction of the up-to-64-per-channel
  mailbox array is wired to the 17 logical messages. Once a logical slot is added, a spare **hardware
  mailbox index** (e.g. anything above the currently-observed highest wired indices, or any index not
  referenced by the polling/TX code) is very likely available on **either** channel — but WHICH indices
  are actually wired-vs-free was not exhaustively enumerated (only high-water-mark literals were found,
  not a full occupancy bitmap).
- **Which physical channel (A=`0xFF481000` vs B=`0xFF489000`) is car-facing vs internal: NOT
  RESOLVED this session.** All 11 TX-capable logical slots share the SAME software ID/DLC/builder
  tables regardless of car-facing (399/427/0x14A) vs internal (0x660/0x64D/0x32E/0x19F) status — the
  logical table has no visible "channel" field. Channel selection must happen either (a) inside each
  content-builder function itself, or (b) via the mailbox-index-to-channel mapping at a layer above
  `FUN_0001d68e` that wasn't traced back to specific CAN IDs this session.

## Open questions / next verification steps

1. **Logical-slot-idx → physical-mailbox-idx mapping.** `FUN_0001d68e`'s 3 call sites pass mailbox index
   and logical index in different registers (`r26` vs `r24`) — confirmed NOT the same variable at the
   call site, but the actual value relationship (identity, offset, or lookup) is unconfirmed. **Next
   step:** trace backward from each of the 3 call sites (`0x1d8e0-0x1d90e`, `0x1db10-0x1db42`,
   `0x1dc70-0x1dca6`) to find where `r26`(mailbox idx) is computed relative to the logical index, likely
   in the enclosing function's own parameter or a lookup a few instructions earlier (truncated in this
   session's disasm windows).
2. **Car-facing vs internal channel identity (0xFF481000 vs 0xFF489000).** **Next step:** disassemble
   content-builder `FUN_00055c42` (399/STEER_STATUS, known car-facing) end-to-end through its
   commit/checksum call chain to see whether it (directly or via the software descriptor at `gp-0x32CC`)
   ultimately drives a mailbox index that resolves to channel A or channel B hardware. Cross-check
   against agent A's channel-topology findings (this segment did not coordinate live with agent A).
3. **Exhaustive hardware mailbox occupancy bitmap.** The literal-address high-water-mark method
   (Python scan in this session) is a coarse lower bound, not an exhaustive occupancy map — many
   mailbox-index computations are arithmetic (`shl 6`) rather than literal, so a full occupancy answer
   needs either (a) a live register-trace/data-flow tool run over `FUN_0001d68e`'s full caller graph and
   the polling-loop dispatch tables (`FUN_0001d46c`/`FUN_0001d96e`/`FUN_0001d49e`), or (b) locating a
   central mailbox-configuration/init table (likely written once at startup, listing ID+mailbox-index
   pairs for HW acceptance-filter setup) — not found this session; **search hint:** look near CAN
   peripheral init code (likely early boot, before the main scheduler loop) for a loop writing the
   `0xFF481xxx`/`0xFF489xxx` ID-field sub-registers (offset within the 64-byte block not yet identified
   — only the 8 data-byte offsets `0x00,0x04,...,0x1C` were directly observed; ID/DLC/control register
   offsets within the 64-byte mailbox block are still unknown).
4. **idx15 ID value (`0x6FF`) had a less clean raw hex pattern than its neighbors** — worth a second
   look/byte-recheck before treating it as fully confirmed (moderate, not full, confidence).
5. **All code references to the 3 table bases (`0xB71B8`/`0xB721C`/`0xB72AC`) were not exhaustively
   enumerated** — only the ones inside `FUN_0001d68e` were found. Before attempting a table-extension
   patch, a full xref sweep for these 3 literals is required (some may be baked into other functions via
   `movea`/`mov` absolute-address idioms not yet searched for elsewhere in the binary).

## Cross-references
- [[reference-accord-consistency-monitor-hardshutdown]] — the independent trace that first mapped
  `FUN_00016de6`'s real role (DTC/fault latch chain), confirming this session's finding from a different
  angle.
- `docs/handoffs/2026-07/HANDOFF-2026-07-07-gating-map-and-telemetry-plan.md` §5 — the mission context (find a free TX
  mailbox on the car-facing channel for a new telemetry frame); this memory materially revises that
  mission's premise (no free *logical* slot exists; the real feasibility path is table extension into the
  known code cave, with abundant *hardware* mailbox headroom once extended).
