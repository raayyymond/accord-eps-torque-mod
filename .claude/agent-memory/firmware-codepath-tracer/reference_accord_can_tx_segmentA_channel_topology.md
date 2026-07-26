---
name: reference-accord-can-tx-segmentA-channel-topology
description: 2020 Accord TVA-A160 SEGMENT A — CAN controller (Renesas FCN) physical channel topology, register bases, message-buffer layout, and the software channel-selector chain from the TX scheduler down to the low-level mailbox function. Disasm-verified against code.bin + the device SVD (UPD70F3508_V850E2Px4).
metadata:
  type: reference
---

# Accord TVA-A160 CAN TX — Segment A: channel topology (2026-07-07 swarm)

Session scope: read-only study, `code.bin` (39990-TVA-A160), gp=0xFEDF8000, tp(r5)=0xBF000, radare2 5.5.0
`v850.gnu` plugin (default `v850` mis-decodes this silicon — see `memory/reference_rizin_ghidra_v850_quirks.md`).
Mission: locate a free TX mailbox/scheduler slot on the **car-facing** CAN channel for a new ~100Hz telemetry
frame (`docs/HANDOFF-2026-07-07-gating-map-and-telemetry-plan.md` §5 step 1).

## 0. Key resource found this session: the device SVD

`analysis-2020accord/svd_for_ghidra/UPD70F3508_V850E2Px4.svd` is a CMSIS-SVD register description for the
**exact MCU** (µPD70F3508, V850E2/Px4 core — confirmed by `PRDNAME` reset value `0x0DB40100` decoding to
product ID `0DB40h = uPD70F3508`, register at peripheral `SYSTEM`/`PRDNAME` offset 0x28). It documents:
- **`FCN0`** = "CAN Controller (FCN) instance 0", **`baseAddress = 0xFF480000`** (SVD line ~2513).
- **`FCN1`** = "CAN Controller (FCN) instance 1", **`baseAddress = 0xFF4A0000`**, `derivedFrom="FCN0"` (SVD
  line ~3475) — i.e. FCN1 is a structural clone of FCN0 at a different base.
- Register naming for FCN0 (63 named registers enumerated) confirms **per-message-buffer registers at
  offset `0x01000 + n*0x40`** for message buffer `n` (e.g. `FCN0M0DAT0B` "message buffer 0 data byte 0" at
  offset `0x01000`, description explicitly states "array step 0x40 for buffers 1-63" → **64 message buffers
  per controller instance**, buffer array spanning `0x1000`–`0x1FFF`).
- Global/mode/mask-control registers (`FCN0GMCSPRE`, `FCN0GMCLCTL`, `FCN0CMMKCTL01H..16H`, etc.) live in
  lower addressBlocks (`0x8`, `0x1000`, `0x8000`, `0x9000`, `0x100c0`, `0x11000` offsets per the SVD's
  `addressBlock` declarations — these declared sizes turned out to be incomplete/approximate; disasm shows
  live register traffic well past some of the declared block sizes, e.g. `0xff489e00..0xff489fc0`).

**This is the load-bearing artifact for the whole swarm**: it gives named ground truth for what would
otherwise be blind MMIO addresses.

## 1. CONFIRMED (disasm-verified): both channel bases exist in executed boot code, not just the SVD

**File offset `0xcf6`–`0xd08`** (early boot / peripheral-clear routine, called from the `0x900`-ish CAN0
init block — see §2):
```
0x00000cf6   400e48ff       movhi -184, r0, r1        ; r1 = 0xFF48 << 16 = 0xFF480000  (-184 == 0xFF48 as s16)
0x00000cfa   61070100       st.w r0, 0[r1]             ; *r1 = 0   <- zero-fill loop body
0x00000cfe   440a           add 4, r1                  ; r1 += 4
0x00000d00   300600204aff   mov 0xff4a2000, r16        ; r16 = 0xFF4A2000  (loop upper bound, imm32-mov form)
0x00000d06   f009           cmp r16, r1
0x00000d08   91fd           bl 0x00000cfa              ; loop while r1 < 0xFF4A2000
```
This is a straight-line `for (addr = 0xFF480000; addr < 0xFF4A2000; addr += 4) *addr = 0;` — it bulk-clears
**FCN0's entire register file plus FCN1's global-control + message-buffer block (offset 0–0x2000, i.e.
through FCN1's 64 buffers which end exactly at `0xFF4A1000 + 64*0x40 = 0xFF4A2000`)** in one sweep. This
independently confirms, from **executed code**, that:
- **FCN0 base = 0xFF480000**, **FCN1 base = 0xFF4A0000 = FCN0_base + 0x20000** (uniform 128KB channel
  stride) — matches the SVD exactly.
- FCN1's message-buffer array is `0xFF4A1000`–`0xFF4A1FFF` (mirrors FCN0's `0xFF481000`–`0xFF481FFF`),
  confirming the same `base+0x1000+n*0x40` layout applies to channel 1.

The `mov 0x<imm32>, rX` form seen above (`21 06 ...`/`30 06 ...`/`40 0e...` families, 6 bytes: opcode
halfword with `reg2` field forced to 0 + a raw 32-bit LE immediate) is a genuine V850E2 extended-ISA
instruction, not a movhi/movea pair fused by the disassembler — verified by reconstructing two independent
examples byte-for-byte (`mov 0xfffff, r10` @0x187a0 and `mov 0xffff5100, r1` @0x10c) and confirming the
trailing 4 bytes equal the printed immediate exactly. **r2's `v850.gnu` decodes this form correctly**; trust
it for `mov 0x<8-hex-digit>, rX` lines.

## 2. CONFIRMED: message-buffer stride, via multiple independent literal buffer addresses

A brute-force scan of the whole 1MB image for the 6-byte `mov 0x<imm32>,rX` form with immediate in
`[0xFF000000, 0xFFFFFFFF]` (script: raw byte scan, not r2 linear disasm, to avoid V850 alignment
mis-decode — see §5 caveat) found **234 literal MMIO-range immediates**. Two clusters are CAN0-specific:

**Cluster 1 — file offset `~0x900`–`0xd36`** (early boot CAN0 bring-up): `0xff488300`, `0xff488310`,
`0xff489028` (×3, inside a loop, buffer-control enable), `0xff481000` (×4, message-buffer base), and the
zero-loop above reaching into FCN1. Confirmed disasm (file offset 0x982-0xa4c) shows a loop indexed by
`r1` (`shl 5` → ep = 0xff488300 + r1*32, i.e. **32-byte-stride buffer-interrupt-enable table**) bounded by a
config-count byte read from `movhi -288,r0,r12; ld.bu -476[r12]` (a calibration/config byte — cal source not
resolved this session), and a second loop (`shl 6` → ep = 0xff489028 + r1*64) plus buffer-control writes at
`0xff481000 + r1*64` (`shl 6`, i.e. **64-byte message-buffer stride**, matching the SVD's stated `0x40` step
exactly).

**Cluster 2 — file offset `0x1ce72`–`0x1e34e`** (deeper CAN0 mask/filter/message-buffer setup, ~1.2KB of
code): contains **only `0xff48xxxx` literals** (buffer addresses `0xff4811c0`=buffer #7 `(0x11c0-0x1000)/0x40
=7`, `0xff481840`=buffer #33, `0xff481e00`=buffer #56 — each independently confirms the `0x1000+n*0x40`
formula), plus two arithmetic-progression register blocks stepping by `0x40` from `0xff489000` (7 entries)
and from `0xff489e00` (8 entries) — almost certainly the 16 `FCN0CMMKCTLnnH` mask-control register groups
named in the SVD, or acceptance-filter setup. **No `0xff4axxxx` literal appears anywhere in this cluster** —
see §4 open question.

## 3. CONFIRMED (structural call-chain trace): the software TX pipeline and where a "channel" value enters it

Traced top-down from the periodic scheduler (handoff-cited anchor `FUN_000520d0`) down through the TX driver
(`FUN_000541d8`) to the low-level mailbox function (`FUN_00016de6`):

| hop | address | what it does |
|---|---|---|
| ROM scheduler table | `0xBB544` = `tp - 15036` (`r5-0x3ABC`) | **19 slots × 32 bytes**, confirmed by the loop bound below. Full byte-decoded table in §3a. |
| `FUN_000521dc` (periodic tick handler, param = tick/mode byte) | `0x522a2`-`0x522d2` | `for (i=0; i<19; i++) { ep = table_base(0xBB544) + i*32; if (table[i].u32@8 == 1 [enabled] && (table[i].byte@24 & <phase-mask>) != 0) FUN_000520d0(i); }` — byte-verified: `sld.w 8[ep],r10; cmp 1,r10; bne skip; ld.bu 24[ep],r14; and r24,r14; be skip; mov r20,r6; jarl 0x520d0,lp; ... addi 32,r26,r26; add 1,r20; addi -19,r20,r0; blt loop`. The phase-mask register (`r24`) origin sits in a byte range (~`0x5221c`-`0x52224`) that r2 flags `invalid`/`unaligned` — **not fully resolved this session**, treat `f24`'s exact consumption as INFERRED (bitmask semantics), not fully verified. |
| `FUN_000520d0(slot)` | `0x520d0`-`0x521cc` | Re-derives `table_base+slot*32` (`shl 5`, confirming the 32-byte stride independently), reads `table[slot].u16@14` (r8) and `.u32@20` (r7, the RAM payload-buffer pointer), and if `u16@14 != 0` calls **`FUN_000541d8(slot, buffer_ptr)`** at `0x52148` — the TX driver. Then unconditionally reads `table[slot].u32@28` (builder function pointer) and tail-jumps into it (`jmp [r20]`) — **each scheduled slot owns a builder function**, confirmed via `ld.w 28[r26],r20; ... jmp [r20]`. |
| `FUN_000541d8(slot, buf_ptr)` [**TX driver**, handoff-cited anchor] | `0x541d8`-`0x542fa`+ | Calls `FUN_00053f32`, `FUN_00054052`, then `FUN_00057b24` (Honda counter/checksum, per handoff memory) with the `u16@14` value carried in `r27` as its 3rd arg. **Then, at `0x54200`: `mulhi 44, r22(slot), r28`** — computes `slot*44`, indexes a **second, RAM-resident, 44-byte-stride table at `gp-13004` (`0xFEDF4D34`)** — the **TX-object descriptor table**, ONE ENTRY PER SLOT (parallel to the 19-slot ROM scheduler table). At `0x5420c`: **`ld.hu 6[r28], r6`** — reads a `u16` field at object-offset `+6` — **this is the value passed as param1 ("channel") into `FUN_00016de6`** at `0x5421a` (`jarl 0x16de6,lp`, with r7=1,r8=0,r9=1 as the other 3 params). |
| `FUN_00016de6(channel, type=1, 0, 1)` [**HW mailbox writer**, handoff-cited anchor] | `0x16de6`-`0x16f5a`+ | First arg (`r26 = param1 & 0xFFFF`) indexes a **third RAM table at `gp-6348` (`0xFEDF6734`)**, 2-byte stride (`shl 1`) — a per-object 16-bit **status/flag word** (bit 11 gets set/cleared; other bits OR'd per a global mode byte `gp-6611`). State-dependent (`gp-6611` ∈ {0,1,2,3,4}) branches call further into `FUN_000162f4`, `FUN_0001611e`, `FUN_00018738`, and (via those) `FUN_00046efe`/`FUN_00046aea`/`FUN_0004786e`/`FUN_00047d06`/`FUN_00047d5e`/`FUN_0004781e` — this deeper stack is **priority/queue arbitration over software objects** (confirmed: `FUN_0004786e(1 or 2)` scans a 28-byte-stride, 8-16-entry priority table rooted at two RAM base pointers loaded from **flash-resident constant pointers at `0xB7034`/`0xB7038`** — `0xFEDFE02C`/`0xFEDFE1BC` — picking the highest-priority pending object). **No raw MMIO write into `0xFF48xxxx`/`0xFF4Axxxx` was reached in this call chain this session** — see §4. |

### 3a. ROM scheduler table, fully decoded (all 19 slots, `0xBB544`–`0xBB7A3`)

Byte layout per 32-byte slot (offsets in bytes): `+0` u32 slot index (0..18, sequential) · `+4` u32 (period?
values 3/5/6/7/8/10/11 — grouped) · `+8` u32 enabled-flag (=1 for all 19) · `+12` u16 (=1 for all except
slots 16,18 which are 0) · `+14` u16 (**semantics unresolved** — see below) · `+16` u32 (=1 for all except
slot 18=0) · `+20` u32 RAM payload-buffer pointer (`0xFEDF6Axx`-`0xFEDF6Cxx` range) · `+24` u32 low-byte-only
phase-bitmask (`0xF` or `0x8`) · `+28` u32 per-slot builder function pointer (all fall in `0x52200`-`0x53e00`
range).

```
slot  0: f4=10 f14=0x0158(344) buf=0xfedf6bf0 phase=0xf builder=0x522fe
slot  1: f4= 3 f14=0x013c(316) buf=0xfedf6b08 phase=0xf builder=0x52452
slot  2: f4= 3 f14=0x0130(304) buf=0xfedf6b10 phase=0xf builder=0x52414
slot  3: f4= 3 f14=0x017c(380) buf=0xfedf6be8 phase=0xf builder=0x524bc
slot  4: f4= 3 f14=0x01dc(476) buf=0xfedf6c00 phase=0xf builder=0x527da
slot  5: f4= 3 f14=0x0324(804) buf=0xfedf6ba0 phase=0x8 builder=0x525b8
slot  6: f4= 3 f14=0x0328(808) buf=0xfedf6b98 phase=0x8 builder=0x52608
slot  7: f4= 5 f14=0x00e4(228) buf=0xfedf6bd8 phase=0xf builder=0x52676
slot  8: f4= 6 f14=0x0326(806) buf=0xfedf6b00 phase=0x8 builder=0x52832
slot  9: f4= 6 f14=0x0374(884) buf=0xfedf6c18 phase=0x8 builder=0x528b8
slot 10: f4= 6 f14=0x03a1(929) buf=0xfedf6c10 phase=0x8 builder=0x52960
slot 11: f4= 7 f14=0x0198(408) buf=0xfedf6bd0 phase=0xf builder=0x52a14
slot 12: f4= 8 f14=0x0094(148) buf=0xfedf6bf8 phase=0xf builder=0x52ade
slot 13: f4= 8 f14=0x0305(773) buf=0xfedf6af8 phase=0x8 builder=0x52c28
slot 14: f4=11 f14=0x01a4(420) buf=0xfedf6bc0 phase=0xf builder=0x52c78
slot 15: f4=11 f14=0x01b0(432) buf=0xfedf6c28 phase=0xf builder=0x52e32
slot 16: f4=11 f14=0x01d0(464) buf=0xfedf6c20 phase=0xf builder=0x534da  (f12=0)
slot 17: f4=11 f14=0x01ea(490) buf=0xfedf6ba8 phase=0xf builder=0x53ccc
slot 18: f4=11 f14=0x078e(1934) buf=0xfedf6b88 phase=0x8 builder=0x53de0 (f12=0, f16=0 — the one outlier)
```
None of these fields is a clean 0/1 split matching "7 known IDs → 2 channel groups" — **the physical channel
selector does NOT live in this ROM table.** `f14` does not match any known CAN ID (399=0x18F, 427=0x1AB,
0x14A, 0x660, 0x19F, 0x32E=814≈slot9's 884 but not exact, 0x64D) closely enough to claim identity; it is
more likely a per-message checksum-seed or internal counter-slot index consumed by `FUN_00057b24`. **Belief,
not evidence** — flagging for whichever agent maps the checksum function.

## 4. OPEN QUESTION (the load-bearing one for the swarm): semantics of the RAM channel field

`FUN_000541d8` reads a `u16` at **TX-object-table (`gp-13004`=`0xFEDF4D34`) + slot*44 + 6** and passes it as
the "channel" argument into `FUN_00016de6`. This is the clearest **candidate** for the channel-selector
field the mission asked about — but:

- **The value's semantics are unconfirmed.** It could be (a) a raw `{0=FCN0, 1=FCN1}` physical-channel
  index, (b) a global mailbox index across a combined `0..127` space where a bit (e.g. bit 6, value `&0x40`)
  encodes channel + the rest encodes buffer number within that channel, or (c) something unrelated to
  physical routing (e.g. a logical queue/priority-class id, given `FUN_0004786e` deeper in the call chain
  is itself parameterized by "1 or 2" for what looks like priority-queue selection, not channel selection —
  **do not conflate these two different "1/2" and "channel" values**, they were found in different tables).
- **I could not find where this RAM table gets its initial channel values written.** An exhaustive
  byte-pattern scan for the `movea -13004,gp,rX` encoding (55 hits total) found every occurrence clustered
  in the TX driver/packer code range `0x53e00`–`0x5551c` — **all reads**, none are a plausible per-object
  initializer (no loop with a 19-iteration bound touches this specific gp-relative form anywhere else in the
  1MB image). The table is therefore either (a) populated via a *different* addressing form (e.g. an
  absolute-address `movhi`+`movea` pair targeting `0xFEDF4D34` directly rather than `gp`-relative — NOT yet
  searched for; my imm32-literal scan around the RAM range `0xFEDEC000-0xFEE00000` returned 708 hits and
  none matched `0xFEDF4D...`, but that scan only catches the 6-byte fused-immediate form, not a
  movhi/movea *pair*, which is the more common 2-instruction idiom and was NOT scanned for this session), or
  (b) populated by a generic loop that computes the destination via a parameter/pointer passed in from a
  caller (invisible to any literal-constant search).
- **No raw MMIO write into either `0xFF48xxxx` or `0xFF4Axxxx` was reached by hand-tracing the call chain**
  from `FUN_00016de6` through its ~6 callees this session. The actual hardware `TXREQ`/`CSETR` bit-poke
  (SVD: `FCN0M0CSETR` "Set/cancel transmit request", `FCN0M0SERY` "Set buffer ready") is presumably a few
  more calls deep (unexplored callees include `FUN_0001601e`, `FUN_00016dc0`, `FUN_00016634`,
  `FUN_00016b66`, `FUN_0001647c`, `FUN_00047d06`, `FUN_00047d5e`, `FUN_0004781e`).
- **Cluster 2's FCN0-only-ness (§2) is itself evidence, but weak evidence**, that FCN1's equivalent deep
  per-buffer/mask setup is either (a) done via a shared, base-parameterized subroutine (likely, and would
  explain why no `0xff4axxxx` literal shows up), or (b) FCN1 is configured much more sparsely than FCN0.
  **Not resolved.**

## 5. Tooling notes for the swarm

- **Raw-byte pattern scanning beat r2 linear disassembly for this task.** A full-image `pD` linear
  disassembly (`r2 -a v850.gnu -c 'pD 1048576 @ 0'`) did not complete in ~9 minutes and was killed — V850's
  mixed 16/32/48-bit instruction widths make full-image linear disasm slow and prone to realignment drift
  through data regions anyway. Hand-written Python byte-pattern scans (checking every 2-byte-aligned offset
  against a decoded bit-pattern for a specific instruction+operand, e.g. `movea -13004,gp,rX` or `mov
  0x<imm32>,rX` with reg2-field==0) were fast (seconds) and exhaustive, with the tradeoff that you must
  derive the exact bit encoding by hand from a couple of r2-confirmed examples first. Recommended technique
  for any address-hunting task on this binary.
- **Confirmed a V850E2 extended 6-byte `mov imm32, reg1` encoding** (distinct from movhi+movea): first
  halfword has `reg2` field forced to `0`, `reg1` = destination in bits[4:0], opcode bits give `0x31`-class
  (same numeric opcode field as MOVEA, disambiguated by the 48-bit total length + reg2==0); the following 4
  bytes are the raw 32-bit immediate, little-endian, printed directly by `v850.gnu` as `mov 0x<8-hex>, rX`.
  Verified against 2 independent known-value examples (`mov 0xfffff,r10` @0x187a0, `mov 0xffff5100,r1`
  @0x10c). Trust `v850.gnu`'s printed immediate for this form without further raw-byte verification.
- **r2 misalignment trap encountered and NOT fully resolved**: file offset `0x5221c`-`0x52224` inside
  `FUN_000521dc` decodes as `mov 1,r14` then `invalid`/`unaligned` bytes (`ec`, `77`) then recovers at
  `0x52220` with `satadd r2,r24`. This is almost certainly a real V850E2 instruction (likely another 6-byte
  extended form) that `v850.gnu` doesn't know, not a true misalignment — but I did not raw-byte-decode it.
  **Flag for whoever needs the exact scheduling phase-mask (`r24`) semantics.**

## 5b. ⚠ CROSS-AGENT CORRECTION — Segments B AND C's "second channel = 0xFF489000" is very likely wrong

(Both `reference_accord_can_tx_segmentB_scheduler_descriptor_table.md` and
`reference_accord_can_tx_segmentC_driver_hw_mailbox.md` independently converged on "`0xFF481000`=channel A,
`0xFF489000`=channel B, `+0x8000` apart, two full CAN module instances." Two independent agents agreeing
raises the bar for a correction — recorded in full below with the exact SVD text and two independent
exhaustive-scan results it rests on. This should be treated as a strong disagreement to actively reconcile,
not a settled overturn — flag for Segment D / operator adjudication.)

Segment C's memory (`reference_accord_can_tx_segmentC_driver_hw_mailbox.md`, same session/directory) found
the REAL hardware mailbox byte-scatter writer (`FUN_0001d68e`, confirmed genuine — 8 payload bytes written
to `mailbox_base + idx*64 + {0,4,8,...,0x1C}`, base `0xFF481000 + mailbox_idx*64`) and a second polling
region at `0xFF489000 + n*0x40` (n=0..6), which they labeled **"second CAN channel"** on the basis that it's
`0xFF489000 - 0xFF481000 = 0x8000` higher.

**This is very likely a misattribution — `0xFF489000` is FCN0's own internal sub-block, not a second
peripheral instance.** Evidence, directly from the SVD (§0): FCN0's `<peripheral>` entry (base `0xFF480000`)
declares its OWN `addressBlock` at **`offset 0x9000, size 0x3a`** — i.e. `0xFF480000 + 0x9000 = 0xFF489000`
is explicitly documented as *part of FCN0*, alongside FCN0's other sub-blocks at offsets `0x8`, `0x1000`,
`0x8000`, `0x100c0`, `0x11000` (→ `0xFF480008`, `0xFF481000`, `0xFF488000`, `0xFF4900C0`, `0xFF491000` — **all
of which Segment A independently found as live literal addresses in the SAME driver cluster Segment C was
reading**, §2 Cluster 2, file offset `0x1ce72`-`0x1e34e`, e.g. `0xff488240`, `0xff489000`, `0xff4890c0`,
`0xff489038`, `0xff491000`). The REAL second channel, FCN1, has base `0xFF4A0000` (`= FCN0_base + 0x20000`,
a full 128KB higher, not `0x8000`) — confirmed independently via the boot-code zero-init loop (§1) AND via
an exhaustive scan for both addressing idioms used to build 32-bit peripheral pointers in this binary:
- The 6-byte `mov 0x<imm32>,rX` form: only ONE `0xFF4Axxxx` literal exists in the **entire 1MB image**
  (`0xff4a2000` at file offset `0xd00`, the boot zero-loop's upper bound — not a distinct register access).
- The `movhi 0x<imm16>,r0,rX` form (opcode `0x32`, byte0 & 0xE0==0x40, byte1 & 0x07==0x06 — verified against
  a known example `movhi -288,r0,r17` @`0x9a0`): **`movhi 0xFF48,r0,rX` has 17 hits** (all `r0`-based, all
  building FCN0-space pointers, consistent with Cluster 1/2 above) and **`movhi 0xFF4A,r0,rX` has ZERO hits
  anywhere in the image.** `movhi 0xFF49,r0,rX` (10 hits) is also FCN0 — it builds `0xFF490000`-based
  pointers for FCN0's own `0x100c0`/`0x11000` sub-blocks.

**Conclusion (high confidence, two independent exhaustive literal-scans agree): FCN1 (`0xFF4A0000`, the
true second physical CAN channel) is bulk-cleared once at boot and is not otherwise referenced anywhere in
this firmware image via either common compile-time addressing idiom.** Either (a) FCN1 is driven entirely
through runtime-computed/parameterized addressing (a channel-base value loaded from RAM/a small config
table and added at runtime — genuinely possible and would explain why no literal shows up; consistent with
Segment A §4's "shared parameterized init function" hypothesis for why Cluster 2 is FCN0-only), or (b) FCN1
is initialized but genuinely unused in this firmware build, which would be a significant finding in itself
(it would mean the "≥2 physical channels" premise in the mission brief needs re-examination — the EPS may
have exactly ONE actively-used CAN channel at the hardware level, with the car-facing/internal split, if
real, implemented some other way — e.g. two logical buses multiplexed onto the same physical wire via ID
range, or a second transceiver driven by a completely different peripheral not yet considered).

**This directly affects Segment B/C's "channel A vs channel B" framing**: their "channel A" (`0xFF481000`)
and "channel B" (`0xFF489000`) are, on this evidence, the SAME physical channel (FCN0)'s message-buffer
array and status/mask-poll array respectively — not two channels. Segment B independently observed the SAME
mechanism I'd flag as the actual explanation: `FUN_0001d68e` reads/writes `<same index> * 64 + 0xFF481000`
(message data bytes) and, for the same or a related index, `<index>*64 + 0xFF489000` (a status/config
half-word, `ld.hu 56[...]`) — that is fully consistent with "one mailbox's data lives at `+0x1000+n*0x40`
and that SAME mailbox's status/config lives at `+0x9000+n*0x40`, both inside FCN0," with no need to posit a
second peripheral. Their open question #2 ("which channel is car-facing") may not have a meaningful answer
in the FCN0-vs-FCN1 framing at all if FCN1 turns out to be unused; it should be re-scoped to "is there a
genuinely separate TX path (possibly a wholly different peripheral, or FCN1 driven via a not-yet-found
parameterized function) for the internal-only IDs (0x660/0x64D/0x32E/0x19F), given they are never
comma-visible while 399/427/0x14A always are on the same physical harness the comma taps." Notably,
`FUN_0001d68e`'s own body **hardcodes the `0xFF481000` literal** (not parameterized by a channel argument —
its "channel/mailbox index" param only ever multiplies into the `+n*64` offset, never selects between two
base addresses) — so even if a channel-B twin of this function exists, `FUN_0001d68e` itself cannot be it;
one would need a structurally separate function using `0xFF4A1000` as its base, which no scan by any of A/B/C
has found. **Not resolved this session — flagging for Segment D / operator adjudication rather than
asserting a fix**, since this is a correction to two other agents' converging findings made without live
coordination.

## 5c. Reconciling my own "channel selector" claim (§3) against Segment C's independent trace of FUN_00016de6

Segment C traced `FUN_00016de6` far more thoroughly than I did this session (94 literal callers found via a
full-image scan, cross-checked against an independent prior memory
`reference_accord_consistency_monitor_hardshutdown.md`) and concludes it is a **DTC/fault-event logger**,
not a CAN-hardware or channel-routing primitive — the overwhelming majority of its call sites fit the
`FUN_00016de6(fault_idx, code, flag, flag)` shape used throughout the firmware for redundant-signal-pair
fault reporting. Segment B's independent trace of the SAME function (from Table A's dispatch path) reaches
the identical conclusion. **This means my §3 claim that "TX-object-table `+6` is the channel argument passed
into the HW mailbox writer" is very likely a mischaracterization of what `FUN_00016de6` actually is** — the
CALL and the ARGUMENT are byte-verified real (`FUN_000541d8` does read `+6[slot]` and pass it to
`FUN_00016de6` at `0x5421a`), but the DOWNSTREAM ROLE I assumed (hardware channel routing) is contradicted
by two independent, more thorough traces of the same callee. The `+6` field is more likely a **fault/log
identifier** for `FUN_000541d8`'s OWN checksum-retry state machine (matching Segment C's direct read of
`FUN_000541d8` as a "software TX descriptor checksum-validate/retry state machine", not a HW committer) than
a physical-channel selector. **I am retracting the "channel selector" framing of §3/§3a as my primary
finding** — the call-chain trace itself (ROM scheduler → `FUN_000521dc` → `FUN_000520d0` → `FUN_000541d8` →
`FUN_00016de6`) remains byte-verified and is left in this document for the record, but per Segment B's
independent, deeper analysis of the exact same table (`0xBB544`), **this entire pipeline is now believed to
be an RX-message-validity/consistency-check dispatcher, not the outbound CAN TX scheduler** the mission
brief assumed. The REAL outbound path (per Segments B+C, converging independently) is: **Table B**
(`0xB721C` CAN-ID / `0xB71B8` DLC / `0xB72AC` builder-ptr, 17 entries, sentinel-terminated, zero free) →
`FUN_0001d68e` → raw mailbox write at `0xFF481000+idx*64`. See those two memories for the authoritative
outbound-TX-path documentation; treat this file's §3/§3a as a corroborating-but-superseded side trace.

## 5d. Cross-check against Segment D (independent, exhaustive ground-truth trace of all 7 known IDs)

Segment D (`reference_accord_can_tx_segmentD_known_frame_provenance.md`) traced all 7 known car-facing +
internal CAN-TX builders end-to-end and found **no field anywhere splits car-facing from internal**: the
`0xb7208` per-message "channel byte" feeding `FUN_0001d68e` is uniformly `6` for all 11 checked entries
(both groups alike), and table-B's (`0xBB544`, the SAME table this document calls the ROM scheduler table in
§3a) phase-mask (+24) and "group" (+4) fields don't split cleanly along the car/internal line either. Segment
D explicitly asked segments A/C to cross-check "if your independent topology/driver traces also converge on
a single shared physical instance servicing both bus segments" — **this document's §5b/§1 independently
does exactly that** (SVD + boot-code zero-loop + exhaustive movhi/imm32 literal scan, arrived at without
seeing Segment D's request, converging on the same "FCN1 unreferenced" conclusion via a completely different
method). Per Segment D's own framing, this upgrades the finding from "ruled out at the `FUN_0001d68e` layer"
to **"there is likely only one physical CAN controller instance with confirmed software activity — car vs
internal, if it is a real distinction, is not implemented via dual-CAN-channel selection anywhere the swarm
has traced."**

Segment D also independently confirms the exact field this document's §3 identified (table-B RAM struct
`+6`/`+8`, `gp-13004+idx*44+6/+8`) as "the strongest still-open candidate" and could not extract its runtime
value (RAM-only, no writer found via the `movea -13004,gp` indexed-store form). **This document ran one more
independent check**: a direct brute-force scan for `st.h`/`st.b`/`st.w` instructions using **direct
`disp16[gp]` addressing** (not the `movea`+indexed-store form Segment D searched) with `reg1=gp` and
`imm16` matching `-13004+i*44+6` or `+8` for every `i` in `0..18` — **zero hits**, for any store width.
Between Segment D's search (indexed-store form) and this one (direct-disp16 form), the two most common
V850 store addressing idioms are now both exhaustively ruled out for this field. **The initializer is
either a generic memcpy/blob-copy (values live in ROM as an unstructured byte blob, never referenced by a
per-field store instruction) or uses a pointer parameter passed in from outside the module (invisible to any
literal-address scan)** — this is now a well-characterized dead end for static literal-scanning; the next
tool needed is different in kind (e.g. Ghidra's decompiler for better data-flow/pointer-parameter tracking,
or a live UDS memory read per Segment D's suggestion, out of this session's read-only-static scope anyway
since no CAN write was authorized).

## 6. What this means for the mission (telemetry TX-slot placement) — updated after reconciling with B/C/D

**Best current SWARM-WIDE understanding (mix of confirmed + inferred), stated explicitly:**
- CONFIRMED (this memory, §0-§2, SVD + boot-code zero-loop): the silicon has exactly 2 CAN controller
  instances, 64 message buffers each, register bases `0xFF480000` (FCN0) / `0xFF4A0000` (FCN1), buffer
  stride `0x40` from `+0x1000`, uniform `0x20000` (128KB) channel-to-channel stride.
- CONFIRMED (Segments B+C, independently converging): the true outbound CAN-TX path is **Table B**
  (`0xB721C` CAN-ID / `0xB71B8` DLC / `0xB72AC` builder-ptr, 17 entries incl. all 7 known car-facing +
  internal IDs, sentinel-terminated, **zero free logical slots**) → `FUN_0001d68e` (real HW mailbox
  byte-scatter writer) → `0xFF481000 + mailbox_idx*64`. My own §3 pipeline (ROM table `0xBB544` →
  `FUN_000521dc` → `FUN_000520d0` → `FUN_000541d8` → `FUN_00016de6`) is a REAL, byte-verified call chain but
  is now believed (per Segment B's deeper trace, corroborated by Segment C's independent read of
  `FUN_00016de6`) to be an **RX-message-validity/consistency-check dispatcher**, not part of the outbound TX
  path — treat it as superseded for TX-slot-placement purposes.
- **CORRECTED (this memory, §5b-§5c, high confidence): there is only ONE hardware CAN channel with
  confirmed software activity — FCN0 (`0xFF480000`).** `FUN_0001d68e` hardcodes `0xFF481000`; its
  "channel/mailbox index" parameter only ever computes `+n*64` within that fixed base, never selects a
  second base. FCN1 (`0xFF4A0000`) is bulk-cleared once at boot and is referenced NOWHERE else in the image
  via either addressing idiom exhaustively scanned this session. **This means: as of this swarm pass, NO
  agent has found a software mechanism that sends ANY CAN-TX frame — car-facing or internal — out through
  FCN1, and none of the known IDs' logical-table entries (`0xB721C`/`0xB72AC`) carry a channel field at
  all** (Segment C explicitly: "the logical table has no visible channel field"). The car-facing (399/427/
  0x14A) vs internal (0x660/0x64D/0x32E/0x19F) split that the operator observes on the comma bus is
  therefore **NOT yet explained by any SoC-level dual-CAN-channel mechanism found by this swarm** — it may
  be (a) a not-yet-found second HW writer targeting `0xFF4A1000`, (b) FCN1 driven via fully
  runtime-parameterized addressing invisible to literal scans, or (c) the split happens external to the
  SoC's CAN peripheral choice entirely (e.g. a single physical CAN0 bus that both groups share, with the
  "internal-only" appearance of 0x660 etc. explained by something in the vehicle wiring/gateway rather than
  EPS-side channel selection — genuinely open, do not assume either way).
- **Practical consequence for the mission**: since `FUN_0001d68e` and Table B are proven to be THE live
  outbound path for the confirmed car-facing IDs (399 at Table B slot matching `0x00055c42`, 427, `0x14A`
  are among the 17 decoded logical entries per Segment C), and since no second-channel TX path was found,
  the working hypothesis for the swarm should be: **a new telemetry frame added via Table B's extension
  path (per Segment C's `0xC4E00` code-cave plan) will go out the SAME physical wire as 399/427/0x14A** —
  i.e. **car-facing by construction**, PROVIDED it's wired through `FUN_0001d68e` the same way the 3 known
  car-facing builders are. This substantially DE-RISKS the "wrong channel" failure mode that motivated this
  Segment A investigation, IF the "only one channel is live" finding holds up under Segment D's cross-check.
  **Still explicitly unconfirmed — recommend Segment D verify by tracing one of the 3 known car-facing
  builders (`FUN_00055c42`/399, or the still-unidentified 427/`0x14A` builders from Segment B's 11-entry
  list) end-to-end through `FUN_0001d68e` and confirming the final mailbox write lands at `0xFF481000`-range,
  not `0xFF4A1000`-range, before committing to a build.**
