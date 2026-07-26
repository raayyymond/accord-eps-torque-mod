---
name: reference-accord-can-tx-segmentb-scheduler-descriptor-table
description: 2020 Accord TVA-A160 Segment B (2026-07-07 telemetry-slot swarm) — FUN_000520d0/table@0xBB544 is proven an RX-validator dispatcher (NOT the TX scheduler the handoff assumed), all 19 slots used, zero free. Independently rediscovered Segment C's 0xB721C/0xB72AC logical-slot table from a different angle; my initial "20 free slots" read of that table is WRONG/RETRACTED — see the correction block: Segment C's byte-exact reconstruction (17 entries, sentinel-terminated, zero free logical slots) supersedes it.
metadata:
  type: reference
---

2020 Accord 39990-TVA-A160, V850E2. STOCK `code.bin` (flat base 0 → file offset == address).
gp=0xFEDF8000, tp=0xBF000. r2 5.5.0 `-a v850.gnu` (verified against self-check 0x410c0).
[V] = disasm-verified this session (2026-07-07). [I] = inferred/structural. Belief vs evidence kept separate throughout.

## ⚠ HEADLINE CORRECTION to the swarm's mission framing
The handoff's mission brief assumed `FUN_000520d0` + a `~0xBB544` table is "the periodic TX scheduler...
dispatches each due frame to the TX driver FUN_000541d8". **This is only half right, and the "TX scheduler"
half is WRONG.** Two structurally distinct tables exist:

1. **Table A** (`FUN_000520d0`, table at `0xBB544`, exactly as the handoff described its address) — proven
   by full disasm to be a **periodic RX-message-validity / dual-value CONSISTENCY-CHECK dispatcher**, not
   an outbound CAN frame scheduler. Confirms and extends Segment A's finding
   (`reference_accord_can_e4_intake_gates.md`) that this is the "generic CAN-message validator" table.
2. **Table B** (`0xB7260` mask + `0xB72AC` function-pointer array, NEWLY FOUND this session, ~0xB7000
   region, NOT the address the handoff estimated) — this is what actually holds the pointers to the
   confirmed outbound frame builders (`FUN_00055c42`=399 packer, `FUN_000561b0`=0x660 builder), and it has
   **genuine, large free capacity** (20 of 32 slots unpopulated). **This is the far stronger candidate for
   "where to register a new telemetry TX builder."**

Both tables are documented fully below with all disasm evidence.

---

## ⚠⚠ SECOND CORRECTION (post-hoc reconciliation with Segment C) — my Table-B "free slot" claim is WRONG

After writing the Table-B section below, I found `reference_accord_can_tx_segmentC_driver_hw_mailbox.md`
already in memory (written by a parallel agent this same session). Segment C independently found the exact
same table cluster from the HW-mailbox-writer side and did the deeper, more precise job:

- **My `0xB7260` = `0x800007ff`, which I called an "enable bitmask", is actually the SENTINEL ENTRY (index
  17) of a DIFFERENT, adjacent parallel array: the CAN-ID table at `0xB721C` (4-byte stride).**
  `0xB721C + 17*4 = 0xB7260` — exact match. `0x800007FF` = MSB-set-as-terminator + `0x7FF` (an 11-bit
  ID-mask artifact), a classic end-of-table marker, NOT a per-slot bitmap. My bit-counting coincidence
  (11 bits happened to match 11 populated builder-table entries) was exactly that — a coincidence.
- **Segment C found THREE parallel arrays, not the two I found**, all indexed 0-16 (17 real entries) +
  sentinel at 17: `DLC@0xB71B8`(1B stride), `CAN-ID@0xB721C`(4B stride), `TX-builder-ptr@0xB72AC`(4B
  stride, exactly the table I found). **Entries 11-16 in the builder table are legitimately RX-only
  slots (real ID + DLC, builder=0 because RX doesn't need a TX builder) — NOT free/unused capacity.**
  Segment C decoded real CAN IDs for all 17: `0x720,0x721,0x722,0x723,0x660,0x64D,0x32E,0x1AB(427),
  0x19F,0x18F(399),0x14A,0x75B,0x753,0x752,0x72B,0x6FF,0x6FB`.
- **The zero-fill I observed from `0xB72D8` through `0xB7328` is a mix of: (a) 6 legitimate RX-only
  zero-builder entries (idx11-16, `0xB72D8-0xB72EC`), (b) the table's own sentinel (idx17, `0xB72F0`),
  and (c) genuinely unrelated/unmapped flash past the table's declared end (`0xB72F4` onward) — NOT
  "20 free registration slots" as I claimed below. My "20 free Table-B slots" claim is RETRACTED.**
- Segment C also went one step further than I did on `FUN_0001d68e`: they disassembled past where I
  stopped (`0x1d77c-0x1d7b8`) and found the actual 8-byte CAN-payload scatter-write into
  `0xFF481000+mailbox_idx*64` — i.e. **`FUN_0001d68e` (or its post-builder-return continuation) IS the
  real hardware CAN TX mailbox write**, resolving what I had left as "genuinely uncertain" below. They also
  independently confirmed `FUN_00016de6` = DTC/fault logging, NOT a HW mailbox commit — matching what I
  found for Table A's use of the same function (94 callers, overwhelmingly fault/DTC-shaped).
- **Corrected bottom line: BOTH Table A (19/19 used) and the real logical-slot table (17/17 used,
  sentinel-terminated) have ZERO free slots today.** Segment C's recommended path — extend the 3 parallel
  tables by one entry each into the `0xC4E00` code cave — is the right next step, not "write into an
  existing NULL entry." Everything else in my Table-B section below (the raw-pointer-search method, the
  builder-family prologue signatures for all 11 TX-capable entries, `FUN_0001d68e`'s HW-register-poke
  discovery, the JARL scanner method) remains independently corroborating evidence and is left as-is for
  the record, but its "free slot" CONCLUSION is superseded by this correction.

---

## TABLE A — `FUN_000520d0` / `0xBB544` (as named in the handoff)

### Structure [V, byte-verified]
- **Base**: `0xBB544` = `tp + (-15036)` = `tp - 0x3ABC`, confirmed independently TWO ways: (a) directly in
  `FUN_000520d0` at `0x5212c`/`0x52134` (`movea -15036,r5,r15`/`r13`), (b) in the iteration loop at `0x522a6`
  (`movea -15036,r5,ep`). `r5` = tp = `0xBF000` confirmed in prior sessions.
- **Stride**: 32 bytes (`shl 5` on the slot index at `0x52126`).
- **Entry count**: **19** (indices 0-18). Bound proven at `0x51d92` (`FUN_00051d92`, called from
  `FUN_000520d0`'s own entry with the same param): `addi -19,r6,r0` / `bnl 0x51d9c` gates a `switch r6`
  (19-way jump table) vs a default/reject path at `0x51fb8`. Independently confirmed by the iteration loop
  at `0x522cc`: `addi -19,r20,r0` / `blt 0x522ac` — loop runs while `r20 < 19`.
- **Entry 19** (`0xBB7A4`, immediately past the valid range) is an all-zero **sentinel/terminator**: `word0
  (self-index) = 0x13(19)`, `word2 (enable) = 0`, all remaining fields `0`. NOT reachable through the normal
  bounds-checked call path (`FUN_00051d92` rejects `r6>=19`). Sentinel byte-dump: `0x000bb7a4: 00000013
  0000000c 00000000 00000000` / `0x000bb7b4: 00000000 00000000 0000000f 00000000`.

### Per-entry field layout (32 bytes, decoded from disasm of `FUN_000520d0` @ `0x52120-0x52176`) [V]
| offset | size | role | evidence |
|---|---|---|---|
| +0x00 | u32 | **self-index** (0..18, sentinel=19) — data-verified, not read by the dispatcher code itself | raw table dump |
| +0x04 | u32 | "class"/group value (10, 3×6, 5, 6×3, 7, 8×2, 11×5) — role INFERRED (priority/rate-class), NOT the actual scheduling gate | raw table dump; not read by `FUN_000520d0`'s traced path |
| +0x08 | u32 | enable flag, `=1` for all 19 real entries, `=0` for sentinel | `0x52134`/`0x5213a` region reads offset via `+8[r26]` implicitly through the `sld.w 8[ep]` in the iteration loop at `0x522b2`; `cmp 1,r10;bne skip` |
| +0x0C | u8 | "retry-enabled" flag: `1` for 17/19 entries, `0` for entries **16 and 18** | `ld.bu 12[r26],r11` @ `0x5214e`; gates whether the `FUN_00051fbc`/`FUN_0005413a` retry pair runs |
| +0x0E | u16 | per-entry value (228–1934 range; entry7=**0x00E4=228, exactly matches CAN ID 0xE4**) — used as a simple **nonzero-gate**, NOT literally passed as an argument to the TX-driver call | `ld.hu 14[r26],r8` @ `0x5213a`; `cmp r0,r8;be skip` |
| +0x10 | u32 | `=1` for 18/19 entries, `=0` only for **entry 18** | raw table dump (row2 word0) |
| +0x14 | u32 | RAM buffer pointer (`0xFEDF6Axx-0xFEDF6Cxx` family — the SAME address family as the CAN-RX routed-buffer table `0xB739C` documented in `TORQUE_PATH_AND_TABLE.md` §0.5) | `ld.w 20[r26],r7` @ `0x52142`, passed as arg2 to `FUN_000541d8` |
| +0x18 | u8/u32 | bitmask value: `0xF`(15, 12 entries) or `0x8`(8, 7 entries) — **CONFIRMED this is a tick-phase selector**, ANDed against a live phase-mask `r24` built from bitfield extractions of STATUS_WORD-adjacent word `gp+0x6400`-ish region (see iteration loop below), NOT a DLC | `ld.bu 24[ep],r14` @ `0x522b8`; `and r24,r14;be skip-call` in the OUTER iteration loop |
| +0x1C | u32 | callback/handler function pointer, tail-jumped via `jmp [r20]` at merge point `0x5216a`-`0x52176` with `r6`=accumulated small-int result | confirmed entry7 = `0x00052676` = the CAN-0xE4 RX processor `FUN_00052676` (byte-identical to Segment A's `reference_accord_can_e4_intake_gates.md` finding that `0x52676` appears as a raw pointer at file offset `0xbb640` = entry7's `+0x1C` = `0xBB624+0x1C`= `0xBB640` ✓ EXACT MATCH) |

### The TRUE iteration/dispatch loop — a SIBLING function, not `FUN_000520d0` itself [V]
`FUN_000520d0` only services ONE slot per call. The actual per-tick iterator is a separate function starting
at `0x521dc` (share the same code cluster, immediately after `FUN_000520d0`'s `dispose` at `0x521cc`):
```
0x521dc  prepare {r20,r24,r26,lp},0        ; FUN_000521dc(param1) — the REAL per-tick loop
...
0x52228  ld.w 25600[gp],r11  ; word at gp+0x6400 = 0xFEDFE400  (STATUS_WORD family, positive gp offset)
0x52234  shr 4,r11 / mov 7,r7 / setf nc/nl,r6 / jarl 0x521d0,lp     ; 6 more of these with mov N,r7 for
0x52246  shr 1,r9  / mov 12,r7 ...                                  ; N = 7,12,11,8,13,10,9 — each call
0x52256  shr 7,r7  / mov 11,r7 ...                                  ; to FUN_000521d0 extracts a different
0x52266  shr 24,r16/ mov 8,r7 ...                                   ; bitfield of gp+0x6400 and folds it
0x52276  shr 24,r14/ mov 13,r7 ...                                  ; (via satadd r2,r24 @0x52220) into
0x52286  shr 24,r12/ mov 10,r7 ...                                  ; r24 = the CURRENT tick-phase mask
0x52296  shr 24,r10/ mov 9,r7 ...
0x522a6  movea -15036,r5,ep   ; ep = table base 0xBB544  (2nd independent confirm of the base)
0x522ac  add r26,ep ; sld.w 8[ep],r10 ; cmp 1,r10 ; bne skip     ; entry+8 must be enabled(1)
0x522b8  ld.bu 24[ep],r14 ; and r24,r14 ; be skip                ; entry+0x18 phase-mask AND current phase
0x522c0  mov r20,r6 ; jarl 0x520d0,lp    ; <-- FUN_000520d0(slot=r20) — THE ONLY LITERAL CALLER**
0x522c6  addi 32,r26,r26 ; add 1,r20 ; addi -19,r20,r0 ; blt 0x522ac  ; r20: 0..18, r26 += 32/iter
```
**`FUN_000520d0` has exactly ONE literal `jarl` caller in the whole image: `0x522c2`, inside this loop.**
(Verified with a manual V850 JARL22 byte-level scanner over `0x0-0xC4000` — see Method box below.)
`FUN_000521dc` itself has exactly ONE literal caller: `0x22b7e` (not walked further this session — see Open
Questions).

### What Table A's entries actually DO — proven NOT a TX-frame-build table [V]
- **Entry 7** (`0xBB624-0xBB643`): `+0x14`(buf)=`0xFEDF6BD8`, `+0x1C`(callback)=`FUN_00052676`. This is
  **EXACTLY the confirmed CAN-0xE4 (STEERING_CONTROL) RX destination buffer and its RX-side processor**
  (`s_lkas_process_steer_cmd`, per `TORQUE_PATH_AND_TABLE.md` §0.5 and Segment A's memory). This is an
  **inbound** message slot, not outbound.
- **Entries 0 and 16** (callbacks `0x522fe` and `0x534da`, disassembled in full): both are **dual-value
  lockstep/consistency comparators** — they load a PAIR of gp-relative int16 shadow values, compare them,
  and on mismatch call `FUN_0006b9fa` (the SAME generic "record mismatching address's error code" fault
  reporter documented across many OTHER subsystems in this codebase — see
  `reference_accord_engage_sm_caller_enumeration_v34.md`, `reference_accord_gp6cc4_tracking_pipeline.md`,
  `reference_accord_post_governor_comp_add.md`, `reference_accord_shaper_fun42af8.md` — all use the identical
  `FUN_0006b9fa` idiom for redundant-signal-pair safety checks). This has nothing to do with building or
  sending a CAN frame.
- **`FUN_00016de6`** (the "TX driver commits mailbox" call inside `FUN_000541d8`, called conditionally from
  Table A's dispatch when `+0xE != 0`) has **94 literal callers across the whole image**, the overwhelming
  majority of which are unambiguous **fault/DTC logging calls** (`FUN_00016de6(fault_idx, code, 1, 1)`
  pattern, e.g. `FUN_0004613e`'s `FUN_00016de6(0x1c,...)`, `FUN_000462e6`'s `FUN_00016de6(0x1d,...)`, per
  `reference_accord_consistency_monitor_hardshutdown.md`). It is a low-level, multi-purpose IPC/mailbox
  primitive shared by DTC logging, CSIG0 inter-chip serial messaging (`TORQUE_PATH_GUIDE.md` Hop 10), AND
  (per the shared swarm context) actual HW CAN mailbox commits. Its role inside `FUN_000541d8`'s specific
  call is NOT independently disambiguated this session — see Open Questions.

**Verdict on Table A: this is a periodic redundancy/plausibility-check + RX-message-revalidation dispatcher.
All 19 valid slots (0-18) are populated with real, non-null buffer pointers and callback pointers — there is
NO free/unused slot inside the valid range.** The only "empty" table space is entry 19 (the sentinel just
past the bounds-checked range), which is not reachable by the normal call path without ALSO widening the
`19` bound constant at `0x51d92` and the `19` loop bound at `0x522cc` — i.e. it is not usable without a code
edit, not just a data edit.

---

## TABLE B — `0xB7260` (enable mask) / `0xB72AC` (function-pointer array) — NEWLY FOUND, the real lead

### How it was found [V]
A manual V850 JARL22 caller-scanner (see Method box) found **zero literal `jarl` callers** for
`FUN_00055c42` (399/`0x18F` STEER_STATUS packer, entry point confirmed at `0x55c42`, prologue ends and body
starts at `0x55c50` matching the handoff's "@0x55c50" annotation) and for `FUN_000561b0` (0x660 builder) —
exactly analogous to Segment A's finding that `FUN_00052676` has zero literal callers (it's reached only via
Table A). This means the 399/0x660 builders are ALSO reached only via an indirect (function-pointer) table.
A raw-byte pointer search (Segment A's technique) for the LE bytes of `0x00055c42` and `0x000561b0` found:
```
r2 /x 425c0500   -> hit at file offset 0x000b72d0   (= &FUN_00055c42, the 399 packer)
r2 /x b0610500   -> hit at file offset 0x000b72bc   (= &FUN_000561b0, the 0x660 builder)
r2 /x 76260500   -> hit at file offset 0x000bb640    (sanity check — reproduces Segment A's Table-A finding)
```

### Table B layout [V, byte-verified from `pxw` dump 0xB7000-0xB7400]
```
0x000b7260: 0x800007ff                          <- ENABLE BITMASK (32-bit)
0x000b7264..0x000b72ab: 18x u32 RAM pointers      <- 0xFEDF6Axx/6Bxx/6Cxx family (same family as the
                                                     confirmed CAN-RX routed-buffer table 0xB739C);
                                                     exact 1:1 relationship to the fn-ptr array below
                                                     NOT fully resolved this session (18 entries vs
                                                     32-slot fn-ptr capacity — see Open Questions)
0x000b72ac..0x000b72d7: 11x u32 function pointers <- POPULATED slots (indices 0-10), ALL confirmed to be
                                                     CAN-frame-builder-family functions (see below)
0x000b72d8..0x000b7328: zero (slots 11-30)         <- FREE / UNPOPULATED — 20 slots
0x000b7328 (slot 31):    0x00000000                <- ANOMALY: mask bit 31 is SET but pointer is NULL
                                                     (see Open Questions)
```
Mask `0x800007FF` = `1000 0000 0000 0000 0000 0111 1111 1111`b = bits 0-10 set (11 bits, matches the 11
populated pointers exactly) **+ bit 31 set** (does not correspond to a populated pointer — see below).

### The 11 populated entries — ALL confirmed to be builder/packer-family functions [V]
Disassembled the prologue of every populated entry. **All 11 share the identical calling-convention
signature** as the two confirmed builders (`addi -N,sp,sp` frame alloc; `mov sp,ep`; then `sst.w` storing
3-4 incoming params `r6/r7/r8`(/`r26`/`r28`) into the local frame) — this is a strong structural family
match, not a coincidence:
| index | addr | identity |
|---|---|---|
| — | `0x000558a6` | unidentified builder-family fn |
| — | `0x00055840` | unidentified builder-family fn |
| — | `0x000557c8` | unidentified builder-family fn |
| — | `0x00055616` | unidentified builder-family fn |
| — | `0x000561b0` | **CONFIRMED = `FUN_000561b0`, the 0x660 internal-only telemetry-cave builder** (per `docs/HANDOFF-2026-07-07`) |
| — | `0x0005605c` | unidentified builder-family fn |
| — | `0x000562b8` | unidentified builder-family fn |
| — | `0x00055d80` | unidentified builder-family fn |
| — | `0x00055f2e` | unidentified builder-family fn |
| — | `0x00055c42` | **CONFIRMED = `FUN_00055c42`, the CAN 399/`0x18F` STEER_STATUS packer** (`@0x55c50` = its body start, matches handoff annotation) |
| — | `0x00055a98` | unidentified builder-family fn |

**I could NOT, within this session's budget, map each of the other 9 addresses to a specific known CAN ID
(427/`0x1AB` MOTOR_TORQUE, `0x14A`, `0x19F`, `0x32E`, `0x64D` are all still unidentified by address) or
determine each entry's exact array INDEX (0-10) — only that exactly 11 non-null pointers occupy the first 11
slots contiguously with no gaps.** This is the single most valuable next step (see Open Questions).

### Invocation context — genuinely uncertain, flagged explicitly [V mechanism, I semantics]
The table is read from `FUN_0001d68e(param1, param2)` at `0x1d728`:
```
0x1d728  mov 0xb72ac,ep ; add r22,ep ; sld.w 0[ep],r25   ; r25 = table[param2]  (r22 = param2<<2 @0x1d6ce)
0x1d732  cmp r0,r25 ; be 0x1d768                          ; NULL-CHECK — skip if unpopulated (the "free slot"
                                                             semantics: index 11-30 would hit exactly this)
0x1d736  mov sp,ep ; sld.w 4[ep],r7 ; sld.w 8[ep],r8       ; load 2 more params from the local frame
0x1d742  sld.w 0[ep],r6 ; jmp [r25]                        ; 3-argument tail-call into the builder — matches
                                                              FUN_00055c42/FUN_000561b0's own 3-param prologues
```
`FUN_0001d68e`'s own prologue: `param1(r6)&0xffff -> r27`, `param2(r7)&0xffff -> r23`; `r22 = r23<<2` (table
index), `r28 = r27<<6 + 0xFF481000` (a **hardware register block**, 64 bytes/channel — `st.b r13,32[r28]`
pokes a byte into it) and a second HW base `0xFF489000` (`ld.hu 56[r14]` where `r14=r26<<6+0xFF489000`).
This means **param1 is a CAN-controller channel/mailbox index used for raw HW register access**, and
**param2 is the message-type index into Table B**.

`FUN_0001d68e` has exactly **3 literal callers**: `0x1d904`, `0x1db32`, `0x1dc8e`. At `0x1dc8e` the channel
arg is a **literal `mov 6,r6`** (channel = 6, fixed). At `0x1d904` BOTH args (`r26`→param1,
`r24`→param2) are **loop variables**, not literals — this call site sits inside a nested loop (di/ei-guarded,
touching the same `0xFF481000`/`0xFF489000` HW register family) that looks structurally like **CAN
controller mailbox configuration** (bit tests, `st.b`/`ld.hu` register pokes, critical sections) rather than
an obvious once-per-tick software scheduler.

**I did NOT resolve within budget whether this is (a) one-time startup mailbox-registration [most likely
per the `di`/`ei` HW-register-poke pattern] whose registered pointer is later invoked by a TX-mailbox-empty
ISR, or (b) directly re-entered on a periodic/interrupt cadence at runtime.** Either way, Table B is
DEFINITELY the correct place to look — it is the actual container of the 399/0x660 builder pointers, with
real free capacity — but the mechanism that ARMS a new registration (what to write into the HW registers at
`0xFF481000+channel*64` matching the CAN-controller's actual TX-mailbox setup, per `UPD70F3508` docs) still
needs the register-level manual to complete a build.

### Free-slot answer for Table B [V structural / I usability]
- **20 fully free (all-zero) function-pointer slots: indices 11-30** (`0xB72D8` through `0xB7324`), no
  registered builder, mask bits 11-30 all clear.
- **1 anomalous slot: index 31** (`0xB7328`) — mask bit 31 IS set but the pointer is NULL. Semantics
  unresolved — could be a "table valid" flag mis-aliased onto the last bit rather than a genuine per-slot
  enable (see Open Questions).
- The companion 18-entry RAM buffer-pointer array at `0xB7264-0xB72AB` is a SEPARATE list (different size
  than the 32-slot fn-ptr array) whose 1:1 relationship to Table B's indices was not established this
  session — flagged OPEN, not assumed.

---

## Free-slot verdict for the mission (car-facing ~100 Hz telemetry frame) — CORRECTED

| Candidate | Free capacity | Confidence it's the right place |
|---|---|---|
| Table A (`FUN_000520d0`/`0xBB544`, the handoff's literal target) | **NONE** — all 19 slots populated; only the past-bounds sentinel (needs a code-constant edit, not just data) | **LOW** — proven to be an RX-validator/consistency-check dispatcher, structurally unrelated to outbound CAN framing |
| Table B / Segment C's logical-slot triplet (`0xB71B8` DLC / `0xB721C` ID / `0xB72AC` builder-ptr) | **NONE** — exactly 17 entries (11 TX-capable + 6 RX-only), sentinel-terminated at idx17. My earlier "20 free slots" read was wrong (see correction block above) | **HIGH** — this IS the right tree (proven to hold the 399/0x660/427/0x14A builders and real CAN IDs), it is just fully occupied, not spare |

**Corrected bottom line: no existing free slot exists in either table.** Per Segment C's analysis, the
viable path is **extending** the 3 parallel tables (`0xB71B8`/`0xB721C`/`0xB72AC`) by one entry each,
relocated into the `0xC4E00` code cave (528 bytes, comfortably large enough — 18×(1+4+4)=162 bytes plus a
new builder function), with every existing xref to the 3 table bases repointed. This is a genuine
code+data patch, not a data-only "flip a NULL entry" patch. See Segment C's memory for the fuller
feasibility writeup and open questions (channel A vs B identity, logical→physical mailbox mapping,
exhaustive xref sweep for the 3 table bases).

---

## Method box — the two techniques that broke this open (reusable)

1. **Manual V850 JARL22 byte-level caller scanner** (r2's `aa`/`axt` are unreliable on this cluster, per
   Segment A — confirmed again this session: `aaa; axt <addr>` returned ZERO hits for `FUN_000520d0`,
   `FUN_00052676`, `FUN_00055c42`, `FUN_000561b0`, `FUN_000541d8` even though `FUN_000520d0` and
   `FUN_000541d8` DO have real callers findable by other means). Encoding (derived + cross-verified against
   the known-good `0x520da -> jarl 0x51d92,lp`):
   ```
   word0 (LE16) = 0xFF80 | ((disp>>16)&0x3F)
   word1 (LE16) = disp & 0xFFFF
   disp = 22-bit signed, pc = address of the jarl instruction ITSELF (not +4)
   target = (pc + disp) & 0xFFFFFFFF
   ```
   Byte-level filter: at address `a`, `data[a+1]==0xFF and 0x80<=data[a]<=0xBF` flags a candidate; decode
   `disp` from the next 2 bytes and compute target. Script written this session:
   `/tmp/claude-0/.../scratchpad/find_jarl_callers.py <target_hex...>` (scans `0x0-0xC4000` in well under a
   second, vs. 2+ minutes for full-range `r2 pD` which timed out).
2. **Raw pointer search** (Segment A's technique, reused): `r2 /x <LE-hex-of-target-address>` finds a
   function's address stored as DATA (a table entry) anywhere in the image — the only way to locate
   indirect-dispatch tables when `aa`-based analysis can't see them.

---

## Open questions / next verification steps
1. **Identify the other 9 populated Table-B function pointers** against known CAN IDs (427/`0x1AB`, `0x14A`,
   `0x19F`, `0x32E`, `0x64D`). Next step: disassemble each fully (not just the prologue) looking for the
   `sxh`/`shl`/`subr r0` scale-and-negate idiom (matches `FUN_00055c42`'s body at `0x55c50`) or a checksum
   call to `FUN_00057b24`, and correlate against the DLC/rate table at `0xB7120-0xB7139` (already documented
   in `TORQUE_PATH_AND_TABLE.md`, "copy length 0xB7124").
2. **Resolve Table B's exact index-to-slot mapping and the `param2` computation** at each of the 3
   `FUN_0001d68e` call sites, to determine which slot(s) correspond to the confirmed car-facing IDs (399,
   427, `0x14A`) vs internal-only (`0x660`, `0x19F`, `0x32E`, `0x64D`) — this is REQUIRED before claiming any
   free Table-B index is "on the car-facing channel" specifically.
3. **Resolve whether `FUN_0001d68e` runs once at init or is re-entered periodically/on interrupt.** Walk its
   enclosing caller (`0x1d904`'s enclosing function; find via its `dispose` at `0x1d90e` and its own callers)
   up to the true root (ideally reaching the "1ms scheduler `FUN_0002214a`" already documented in
   `TORQUE_PATH_AND_TABLE.md` §0.3, or an interrupt vector).
4. **Get the V850E2/UPD70F3508 CAN-controller register manual** for the `0xFF481000`/`0xFF489000` blocks
   (64 bytes/channel stride) to understand what `FUN_0001d68e` is actually configuring — this is required to
   know what register writes a new Table-B registration needs beyond just the pointer+mask.
5. **Resolve mask bit 31 / slot 31's anomaly** (bit set, pointer null) — check if it's a "table-initialized"
   global flag rather than a per-slot enable, by finding the code that TESTS individual mask bits (not yet
   located this session).
6. **Resolve `FUN_00016de6`'s exact role inside `FUN_000541d8`** (Table A's TX-driver call) — is it a genuine
   HW mailbox commit for at least SOME of its 94 call sites, or exclusively DTC/CSIG0 as the concrete
   evidence gathered this session suggests for the handful of sites actually walked? This affects whether
   Table A is TRULY irrelevant to CAN TX or only mostly so.
7. **Resolve the 18-entry buffer-pointer array at `0xB7264-0xB72AB`** — same family of RAM addresses as the
   confirmed RX routed-buffer table `0xB739C`, but a different size (18 vs 24) and different order. Is it a
   TX-source-buffer array paired with Table B, or an unrelated table that happens to be adjacent?

[[reference-accord-can-e4-intake-gates]] [[reference-accord-consistency-monitor-hardshutdown]]
[[reference-accord-engage-sm-caller-enumeration-v34]]
