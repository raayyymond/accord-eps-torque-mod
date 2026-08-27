---
name: accord-internal-id-lifecycle
description: 2020 Accord TVA-A160 V850E2 — Segment 4 of the 2026-07-07 car-facing-vs-internal CAN TX swarm. Traces the SOFTWARE invocation-gating, pending-status-word, and RX-consumer side for the 4 internal-only builders (0x660/0x19F/0x32E/0x64D) vs the 3 car-facing builders (399/427/0x14A). Finds every gate in the mailbox-6 dispatch chain operates on mailbox index / hardware TX-request state, never on message identity — REFUTED for a software-side car/internal gating difference, with one open seam (the STATUS[] pending-table producer is not located).
metadata:
  type: reference
---

# Segment 4 — internal-ID software lifecycle (invocation gating, pending word, RX consumer)

2020 Accord `39990-TVA-A160`, Renesas uPD70F3508/V850E2. STOCK `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`
(flat, file offset == address). `r2 -a v850.gnu -b 32 -m 0`. gp=`0xFEDF8000`, tp=`0xBF000`. SVD:
`analysis-2020accord/reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`. Self-check `0x410c0` re-verified this session
(`ld.bu -26622[gp],r12 ; cmp 2,r12`).

**Read first**: `reference_accord_can_tx_synthesis_2026-07-07.md` (rollup),
`reference_accord_can_tx_segmentC_driver_hw_mailbox.md`, `reference_accord_can_tx_segmentD_known_frame_provenance.md`,
`reference_accord_can_tx_fcn0_forward_verify.md` (this document extends its Open Items #1-#3 one layer deeper —
does not fully close them). Baseline facts inherited without re-deriving: all 7 known builders are reached ONLY
via indirect fn-ptr table-A (`0xB72AC`, 17 entries), table-A's channel byte (`0xB7208`) is `6` for all 11
TX-capable slots, and the one live `FUN_0001d68e` call site hardcodes mailbox index `6` — i.e. **all 7 known
messages (car-facing and internal alike) share one hardware mailbox and one dispatch table.**

## Index map (unchanged from prior segments)
| CAN ID | role | table-A idx | builder |
|---|---|---|---|
| 0x660 | internal | 4 | `FUN_000561b0` |
| 0x64D | internal | 5 | `FUN_0005605c` |
| 0x32E | internal | 6 | `FUN_000562b8` |
| 427/0x1AB | car-facing | 7 | `FUN_00055d80` |
| 0x19F | internal | 8 | `FUN_00055f2e` |
| 399/0x18F | car-facing | 9 | `FUN_00055c42` |
| 0x14A | car-facing | 10 | `FUN_00055a98` |

---

## CONFIRMED (byte-verified this session, `r2 -a v850.gnu`)

### 1. Function boundaries in the mailbox-6 dispatch cluster (forward disasm from `FUN_0001d68e`=`0x1d68e`, a known-good instruction boundary — backward `pd -N` is unreliable on this ISA and was NOT used for boundaries)
```
0x1d68e  FUN_0001d68e   (HW mailbox byte-scatter writer, per Segment C/D)
0x1d82e  FUN_0001d82e   (dead TX dispatcher — call site 1; see §5 below, NEW finding on its real role)
0x1d942  FUN_0001d942
0x1d96e  FUN_0001d96e   (per-mailbox dispatcher — call site 2, 0x1db32)
0x1db74  FUN_0001db74   (the LIVE dispatcher — call site 3, 0x1dc8e, literal mailbox=6)
0x1dcaa  FUN_0001dcaa   (outer per-tick mailbox-0..6 coordinator)
0x1ddd0  FUN_0001ddd0
0x1debc  FUN_0001debc
```

### 2. The outer coordinator `FUN_0001dcaa` — every gate is mailbox-index / HW-state, not message-identity
Full body disassembled `0x1dcaa`-`0x1ddc6`:
```
0x1dcaa prepare {lp},0
0x1dcb0 andi 65489,r5,r11 ; cmp r0,r11 ; be 0x1dcbc [else] jr 0x1ddcc   ; TOP-LEVEL EARLY-EXIT gate #1
0x1dcbc mov 0xff488240,ep ; ld.hu 32[ep],r16 ; ...                      ; channel-B control-block status read
0x1dccc andi 65489,r13,r9 ; bnl 0x1ddc2                                 ; EARLY-EXIT gate #2 (skips to near end)
0x1dcd2 sst.h r9,32[ep]                                                  ; ack/clear the control-block status
```
Then, UNROLLED for mailbox_idx = 0,1,2,3,4,5,6 (7 blocks, each 0x1c bytes, verified byte-identical shape):
```
mov 0xff489000+idx*0x40, rX
ld.hu 56[rX], rX                 ; = FCN0M{idx}CTL  (SVD addressOffset 0x09038 + idx*0x40)
andi 515(0x203), rX, rY          ; mask bits {FCN0M{idx}TRQF(bit9), FCN0M{idx}TCPF(bit1), bit0}
addi -513(0x201), rY, r0         ; compare masked value to 0x201 (bit9=1,bit1=0,bit0=1)
bne [skip this idx entirely]
jarl 0x1d46c,lp                  ; generic per-mailbox helper (23 total static callers image-wide)
mov idx, r6
jarl 0x1d96e,lp                  ; FUN_0001d96e(mailbox_idx=idx)  <-- the per-mailbox dispatcher
jarl 0x1d49e,lp                  ; generic per-mailbox post-processing helper
```
**SVD-grounded**: `FCN0M0CTL` (`0xFF489038`, "message buffer 0 control register, bit-set/clear mechanism"):
bit9 = `FCN0M0TRQF` "Transmit request pending flag" (read); bit1 = `FCN0M0TCPF` "Transmit cancel pending flag"
(read); bit0 = `FCN0M0SERY` "Set buffer ready" (documented write-only, reused read position). The `0x203→0x201`
test is a **hardware TX-request-pending / not-cancelled check per mailbox** — a generic CAN-peripheral
flow-control gate, structurally identical for every one of mailbox 0-6, with **no message-type or car/internal
distinction anywhere in this test**. Since all 7 known messages share mailbox 6, they are subject to the exact
same instance of this gate — there is no way for this mechanism to distinguish 399 from 0x660.

`FUN_0001dcaa` itself has exactly 2 static callers (JARL disp22 scan): `0x1ce56` and `0x1e28e`.
- `0x1ce52: cmp 1,r10 ; bne 0x1ce5c [else] 0x1ce56: jarl 0x1dcaa,lp` — gated on `r10==1`, a value produced
  earlier in the same function by a byte-copy loop (`0x1ce3e-0x1ce4a`) whose origin was not traced further this
  session — plausibly a CAN-controller-state result (e.g. "normal operating mode"), not message-specific.
- `0x1e28e: jarl 0x1d942,lp ; jarl 0x1dcaa,lp ; jarl 0x1df5c,lp ; jarl 0x1e0f4,lp` — **UNCONDITIONAL,
  straight-line sequence of 4 sub-task calls, no branches between them.** This is inside a small wrapper
  `FUN_0001e286` (`0x1e286`-`0x1e29e`) with exactly ONE static caller: `0x45de2`.

### 3. `FUN_0001e286`'s single caller (`0x45de2`) sits behind a rate-limited SCHEDULER-TASK admission idiom
```
0x45db0 movea -16000,gp,ep ; cmov h,7,r6,r6 ; add r6,ep ; sld.bu 0[ep],r13 ; add 1,r13 ; sst.b r13,0[ep]
        zxb r13 ; cmp r15,r13 ; be [skip 0x1cba6 call]     ; increment-and-compare-to-period counter
0x45dd6 ld.w -28024[gp],r11 ; shr 14,r11 ; bl 0x45de2 [else] jr 0x45eec
0x45de2 jarl 0x1e286,lp                                     ; the whole mailbox-0..6 CAN-service task
```
The `movea -16000,gp,ep / cmov h,7,r6,r6 / add r6,ep / sld.bu.../add 1/sst.b.../cmp rN,r13/be` shape is
**byte-identical in structure** to the task-admission prologue independently found at `0x55544-0x55566` (start
of `FUN_00055540`, one of `FUN_0001d82e`'s callers, §5 below) — this is a **generic rate-gated task-scheduler
slot entry idiom** used repeatedly in this firmware, not a message-specific check. **Conclusion: the entire
mailbox-6 dispatch pipeline (`FUN_0001dcaa`→7×`FUN_0001d96e`+1×`FUN_0001db74`→`FUN_0001d68e`) is admitted into
execution as ONE scheduler task on a fixed periodic cadence — car-facing and internal messages that share
mailbox 6 are serviced on the identical cadence, because they are the identical code path.**

### 4. `FUN_0001d96e(mailbox_idx)` and `FUN_0001db74()` — the "pending word" scan, both structurally identical
`FUN_0001d96e` (call site 2, 7 callers `0x1dcee/0x1dd10/0x1dd32/0x1dd54/0x1dd76/0x1dd98/0x1ddba` — matches the
7 unrolled mailbox-idx blocks in §2 exactly, one call per idx=0..6):
```
0x1d972 zxh r6 ; mov r6,r10 ; shl 1,r10             ; r10 = mailbox_idx * 2
0x1d978 mov 0xfedf68bc,ep ; add r10,ep               ; ep = 0xFEDF68BC + idx*2   (= gp - 0x1744)
0x1d980 sld.hu 0[ep],r26                              ; r26 = STATUS[idx]   <-- the per-mailbox pending word
0x1d982 mov r6,r24                                    ; r24 = idx (saved)
0x1d984-0x1d992  [channel-B CTL handshake: write 1 to FF489000+idx*64+0x38, spin-poll until bit clears]
0x1d99c xori 65535,r26,r0 ; bne 0x1d9a6 [else] jr 0x1db70(=return)   ; STATUS[idx]==0xFFFF -> early return
0x1d9a6 cmp 6,r24 ; be 0x1d9b6 [else: a second, less-traveled branch not needed for idx==6, not fully re-walked]
0x1d9b6 xori 65534,r26,r0 ; be 0x1da12 [i.e. STATUS[idx]==0xFFFE -> skip straight to the tail below]
0x1d9bc jarl 0x1f98e,lp ; di                          ; critical section
0x1d9c4 mov 0xb71e0,ep ; add r26,ep ; sld.bu 0[ep],ep  ; byte lookup: TABLE_1[STATUS[idx]]   (0xB71E0)
0x1d9ce mov r26,r15 ; add r5,r15 ; mov 0xfedf693c,r14 ; add r14,ep ; sld.bu 0[ep],r13          ; TABLE_2 lookup
0x1d9e2 mov 0xb71f4,r8 ; or r11,r13 ; andi 32,r10,r9 ; sst.b r13,0[ep] ; [bne-gated] ei         ; write-back a flag byte
0x1d9f6 mov r26,ep ; shl 2,ep ; mov 0xb72f4,r7 ; add r7,ep ; sld.w 0[ep],r22                   ; TABLE_3[STATUS[idx]]
0x1da04 cmp r0,r22 ; be 0x1da12 [else jmp [r22] with r6=STATUS[idx], return addr = 0x1da12]     ; callback dispatch
0x1da12 cmp 6,r24 ; be 0x1da1a [else jr 0x1db70]                                                ; only idx==6 continues
0x1da1a jarl 0x1f98e,lp ; di ; [nibble-decode tree over `ep`, see §note below] ; ei ; return
```
`FUN_0001db74` (call site 3, ONE caller `0x1ddc2`, the sole live path per `fcn0_forward_verify`) has the
**structurally identical** nibble-decode tail starting at its own entry (`0x1db74`), ending — per prior
segment's already-confirmed trace — at `0x1dc40: andi 0xffff,r28,r26 ; mov r26,r7 ; mov 6,r6(literal) ;
jarl 0x1d68e,lp`, the ONE live dispatch into the shared HW mailbox writer.

**Table-3 (`0xB72F4`) dump, byte-verified** (`px 0xA0 @ 0xb72f4`): indices 0-32 (relative, 4-byte stride
continuing table-A's own numbering — `0xB72F4 = 0xB72AC + 18*4`) are **ALL ZERO**. The first non-zero entries
appear only at index 34+ (`0xB7334` = `0x0001FAF6`, `0xB7338`=`0x0001EE3C`), and the pattern immediately breaks
into a DIFFERENT, unrelated-looking data shape from index 36 onward (values like `0x1e380000`, `0x1d680000` that
do not parse as plausible absolute code pointers) — **corroborating, from fresh byte-level inspection, Segment
C's original read that flash past the table's declared end is unrelated data, not a spare capacity region.**
Since STATUS[idx] must be in table-A's valid range (0-16, bounds-checked <18 elsewhere — see §6) to represent a
real message, **the Table-3 callback dispatch at `0x1d9f6-0x1da10` is a structural no-op for the ENTIRE real
message-index range** — it never fires for any of the 17 known logical slots, car-facing or internal.

**Note on the nibble-decode tree** (`0x1da3c` in `FUN_0001d96e`, `0x1db96` in `FUN_0001db74`): both instances
open with `movhi -1,r0,rX ; and ep,rX ; be [skip]`, then progressively narrower masks (`0xFF000000`,
`0x00FF0000`, `0x00000FF0`...) each feeding a `shr N,ep ; add r5,ep ; sld.h 138[ep]`-style lookup into a
tp-relative table region (`0xb71cc`/nearby). This is a **generic "which byte/nibble is nonzero" classifier**,
structurally suited to a LARGE-range value (not the small 0-16 STATUS[idx] value) — the value it operates on
(`ep`) is loaded at each function's own entry via 2 bytes that `r2`'s `v850.gnu` plugin flags `invalid`/
`unaligned` at an IDENTICAL relative offset (+4 bytes from `prepare`) in BOTH `FUN_0001d96e` and `FUN_0001db74`
— strong circumstantial evidence this is a genuine **decoder gap in the plugin**, not a real code-alignment
issue (flow into both sites is straight-line from a verified `prepare` boundary). **What this classifier
actually operates on was NOT resolved this session** — flagged OPEN (§ below), but note it gates on `cmp
r0,ep; bne` first (null = skip everything), consistent with "nothing pending → do nothing."

### 5. `FUN_0001d82e` is a SEPARATE, structurally-dead CAN-driver EVENT dispatcher — NOT our message-content gate
Re-confirmed (matches `fcn0_forward_verify` finding #4 exactly, independently re-derived): `FUN_0001d82e`'s
central test `0x1d88c: cmp 6,r26 ; bne 0x1d8b8` where `r26 = 0xB7208[arg1]` (channel byte, `=6` for all 17
table-A slots) means execution **ALWAYS falls into the early-return** (`mov 1,r10 ; br 0x1d90e`) — this
function structurally never reaches `FUN_0001d68e` for ANY argument value, car-facing or internal.

New this session — its callers and argument values. 12 static callers found (JARL disp22 scan):
`0x1ce4e/0x1ce5e`, `0x1e486`, `0x1ece2/0x1ed70`, `0x1f6a6/0x1f6fc`, `0x1fb34`, `0x55584/0x5558a/0x55590/0x55596`.
Disassembled the surrounding context of every cluster:
- `0x55578-0x55596` (inside `FUN_00055540`): gated by `STATUS_WORD(gp+0x6400) bit4 == 0`
  (`ld.w 25600[gp],r15 ; andi 16,r15,r0 ; bne [skip]`) — calls `FUN_0001d82e` with **literal** `r6=3,2,1,0`
  in sequence. `gp+0x6400` is the SAME status word Segment B/D's `FUN_000521dc` reads for table-A's OWN
  19-entry scheduler phase mask — corroborating cross-reference, but the literal args here (0,1,2,3) are
  table-A indices `0x720/0x721/0x722/0x723` (the newly-identified TX-capable messages, NOT our 7 known IDs).
- `0x1ece2`, `0x1f6a6`/`0x1f6fc`: literal `r6=17` (`0x11`), each gated behind a DIFFERENT `tst1`/`clr1`/`set1`
  bit-flag test on `movhi -289,r0,r18`-based gp-relative flag bytes (classic CAN bus-off/error-state latches)
  plus a `ld.w -5744[gp],r10 ; shr N ; bnl [skip]` counter-threshold check.
- `0x1fb34`: literal `r6=16` (`0x10`), reached after an unrolled 8-byte `sld.bu`-copy sequence (looks like
  copying a received CAN payload out of a buffer) — this is the only site resembling RX-content handling, but
  the `FUN_0001d82e(16)` call itself is still structurally dead per the channel==6 rule.
- `0x1ce4e/0x1ce5e`, `0x1e486`: **computed** `r6` (from `r28`/`r10`/`ld.hu -29588[ep],r6`), not literal.

**None of the 12 call sites pass a literal argument in table-A's 4-10 range (our 7 known messages' indices).**
The literal values actually observed (0,1,2,3,16,17) plus computed values from clearly CAN-driver-error/init
contexts (bus-off flags, error counters, RX-payload copies) indicate `FUN_0001d82e` occupies a **separate index
space tied to CAN-controller DRIVER EVENTS** (mode/error/init notifications), not the message-content index
space table-A uses for TX framing. This is well-supported negative evidence that `FUN_0001d82e` is NOT where
car-facing-vs-internal gating would live, even though it superficially looks like "the" TX dispatcher (it
shares table-A's channel-byte lookup and argument-bound-check shape).

### 6. `FUN_0001cf30` — a separate STATUS[] validate/reset sweep, uniform across indices
2 static callers: `0x1d5fa`, `0x1fb5c`. Body (`0x1d000-0x1d15x`, three explicitly seen unrolled instances,
consistent with a larger unrolled or counted loop `0x1d040-0x1d10a`, `bne 0x1d040`) repeats, per processed
index:
```
mov 0xfedf68bc,ep ; add idx*2,ep ; sld.hu 0[ep],r6      ; r6 = STATUS[idx]   (READ)
addi -18,r6,r0 ; bl [skip] ; jarl 0x1e9fc,lp             ; if STATUS[idx] >= 18 (unsigned) -> FAULT call
[then: recombine idx via 'add gp,r26' and a store-shaped instruction sequence toward the same slot —
 consistent with resetting/clearing the entry, exact byte semantics not fully pinned, see Open Items]
```
`FUN_0001e9fc` (the bounds-fault handler) has **15 total static callers**: the majority (`0x1d05e,0x1d0b8,
0x1d12a,0x1d4fe,0x1d510,0x1d522,0x1d534,0x1d546,0x1d558,0x1d56a,0x1d582,0x1d654,0x1d67e` — 13 sites) are inside
`FUN_0001cf30`'s module, consistent with it validating a run of MANY mailbox indices (more than the 7 serviced
by `FUN_0001dcaa`'s channel-B polling loop) — plus 2 more (`0x1db3c`, `0x1dc98`) sitting immediately after the
two LIVE `FUN_0001d68e` call sites in `FUN_0001d96e`/`FUN_0001db74` themselves (an additional bounds-check right
after dispatch). **This is a generic housekeeping/validation sweep — every index is checked the same way; no
message-identity branch exists in it.**

### 7. RX/MID acceptance-filter search — no match found for any internal ID outside the known TX table
Per the SVD, `FCN0M0MID0W` (`0x11028`) documents "ID bits [28:0] + IDE bit", and the previously-confirmed
table-A CAN-ID array (`0xB721C`) uses the encoding `(ID<<18) & (0x7FF<<18)`. Whole-image byte search (Python,
exhaustive) for each of the 7 known IDs in that exact `raw_id<<18` 32-bit encoding found **exactly one hit per
ID for 0x660, 0x19F, 0x64D, and 0x14A — each landing precisely inside the known table-A CAN-ID array
(`0xB7230-0xB7248`)**. No second occurrence anywhere else in the 1 MiB image. (0x32E, 399, 427 additionally
matched a handful of 16-bit half-values elsewhere; each was individually checked: values are either extremely
common (399's `0x063c` — 113 hits, meaningless), non-clustered singletons in code regions unrelated to CAN init
(`0x32E`'s `0x28fcf/0x29beb/0x2aae1`), or plausible coincidence next to the known table (`0x32E`'s `0xb7792` is
`0x55E` bytes past the table's declared end, in the same "unrelated data" region flagged in §4's Table-3 dump —
not a second table). **No credible second (RX-shaped) ID table was found for any of the 4 internal-only IDs.**
This is a static-literal search only — see Open Items for its limits.

---

## INFERRED (structurally well-supported, not byte-exhaustively proven)

- **`STATUS[idx]` (`gp-0x1744`, i.e. `0xFEDF68BC` + `idx*2`) is very likely the actual per-mailbox
  "message-type pending" word** the mission brief calls the pending status word: it is bounds-checked against
  17/18 (matching table-A's exact entry count), carries two observed sentinels (`0xFFFF`="empty",
  `0xFFFE`="alternate skip"), and — when neither sentinel — is the SAME value indexed into Table-3 (`0xB72F4`,
  §4) which is table-A-shaped (4-byte stride starting right after table-A's own sentinel). This is inference
  from consumer-side structure; the producer (who writes a real 0-16 value into it) was not located this
  session (Open Item #1).
- **The mailbox-6 dispatch pipeline runs on one fixed scheduler cadence, uniform for every message that shares
  mailbox 6** (§3) — i.e. if car-facing and internal messages differ in effective TX rate, that difference (if
  real) must come from elsewhere (e.g. the STATUS[] producer's own cadence, or table-A idx9/idx4's respective
  builder content/counter logic) — not from this dispatch layer.

## OPEN — flagged rather than guessed

1. **Producer of `STATUS[idx]`** (who writes a real 0-16 logical-index value into `gp-0x1744`+`idx*2`) — NOT
   found. My literal-address scan (searching for the raw 32-bit `0xfedf68bc` pointer, which found all 8
   existing consumer-side references, all confined to `0x1d000-0x1d97a`) cannot see a compiler-emitted
   `st.h rX, DISP16[gp]` write that bakes a small negative displacement directly (no absolute-address literal
   needed for a compile-time-constant index). **Next step:** write a proper V850 format-VI byte decoder for
   `st.h`/`sst.h` with base register `gp`(r4) and displacement in `[-5956, -5830]` (the table's ~64-entry span,
   i.e. `-0x1744` to `-0x16C6`), scan the whole image for it. This is THE single highest-value remaining gap —
   it is the one place a car-facing-vs-internal difference could still hide, since everything downstream of
   this write (§2-§6 above) is confirmed uniform.
2. **Source of `ep` feeding the nibble-decode tree** in `FUN_0001d96e`/`FUN_0001db74` (§4's "note") — 2-byte
   region flagged `invalid`/`unaligned` by `r2 -a v850.gnu` at an identical offset in both functions, likely a
   plugin decoder gap. **Next step:** raw `px` byte inspection cross-referenced against the V850E2 architecture
   manual, or fall back to Ghidra's SLEIGH decoder (may have fuller V850E2 coverage) per the standard tool
   order.
3. `FUN_0001cf30`'s loop bound (how many mailbox indices it validates) and its exact reset/clear semantics for
   `STATUS[idx]` after a bounds-check pass were not fully pinned (parallels `fcn0_forward_verify`'s open item #4
   about the boot-loop's `r12` bound — another runtime-RAM-value gap).
4. RX/MID search (§7) is static-literal only — cannot rule out a **dynamically computed** RX acceptance filter.
   `fcn0_forward_verify` already flagged the boot-time `MID0H`/`MID1H` source table as unresolved (their `r13`
   reassignment between `0x970`-`0xa06` not fully traced). This document does not close that gap either.
   **Next step:** fully disassemble `0x970-0xa06` linearly (forward, from a verified boundary) to find the true
   MID-source table/computation.

---

## VERDICT

**Invocation gating**: at every layer of the mailbox-6 dispatch chain actually traced this session — the
periodic scheduler-task admission (§3, rate-gated but message-agnostic), the outer coordinator's per-mailbox
hardware TRQF/TCPF check (§2, SVD-grounded, mailbox-index-keyed not message-keyed), the STATUS[]-sentinel check
and Table-3 callback dispatch (§4, empty/no-op for the entire real message range), and the separate
`FUN_0001d82e` event-dispatcher family (§5, a different index space tied to CAN-driver bus/error events, not
message content) — **no differential software gate (mode flag, diagnostic-session check, or RAM flag) was found
that treats internal-only builders (0x660/0x19F/0x32E/0x64D) differently from car-facing builders
(399/427/0x14A).** All 7 share one hardware mailbox (6) and one generic dispatch code path with no per-ID
branch anywhere in it. **This is REFUTED, but with one open seam**: the actual producer of the STATUS[]
per-mailbox pending value (Open Item #1) was not located, and it is the one place upstream of everything
confirmed-uniform where a real distinction could still exist. Calibration: "gated off in normal driving" is
supported by evidence for every layer downstream of STATUS[]; "could still be gated upstream of STATUS[]" is a
belief, not yet evidence either way.

**Dispatch status word / pending-bit producers**: `STATUS[idx]` at `gp-0x1744` is the strongest identified
candidate for "the pending status word," fully mapped on the consumer (read/validate/reset) side; its producer
is unresolved (Open #1). No evidence found that internal IDs' pending bits are set on a different cadence than
car-facing ones — but this is an absence-of-evidence result (the producer wasn't found), not a proof of
sameness.

**Internal consumers / RX side**: REFUTED (static evidence) that any of the 4 internal-only IDs are matched by
an on-chip RX acceptance filter — each appears exactly once in the image, inside the known outbound
CAN-ID/DLC/builder table, and nowhere else. No self-reception / internal-peer RX match was found. This does not
rule out a dynamically-computed RX filter (Open #4).

## ⚠ Reconciliation with Segment 1 (`reference_accord_can_tx_trigger_path.md`, same swarm, concurrent)

Segment 1 independently traced the SAME `gp-0x1744`(`0xFEDF68BC`)+`idx*2` RAM table from the opposite direction
(inside `FUN_0001d68e`'s own body, `0x1d7c0-0x1d828`, a critical section this document did not examine) and
reaches the **same top-level verdict** (REFUTED for a car/internal gate, with the identical residual caveat
about mailbox-index ASSIGNMENT via call site 2/`0x1db32` = this document's `FUN_0001d96e`). Two points of their
trace usefully REFINE this document's §4/OPEN-1:

1. **The RAM table's role is "mailbox ownership," not just "pending."** Segment 1 shows
   `FUN_0001d68e` reads `RAM_table[mailbox_idx]` and compares it against `r23`=the just-dispatched
   `logical_idx`; on mismatch it writes the table's `0xFFFF` sentinel back into that slot. This means
   `STATUS[idx]`(this doc's name)/`RAM_table[idx]`(Segment 1's name) records **which logical message currently
   owns mailbox `idx`**, and `FUN_0001d68e` itself is (partially) a WRITER of it (the `0xFFFF`-clear path on
   mismatch) — not purely a downstream reader as this document's §4/§6 treats it. This still does not locate
   the writer of a REAL (non-sentinel) 0-16 value — Open Item #1 stands — but the record's semantics are now
   better understood.
2. **This document's "`FUN_0001e9fc` = bounds-fault handler" label (§6) is a weaker inference than Segment 1's
   direct read and should be treated with reduced confidence.** This document inferred the role only from the
   calling pattern at `FUN_0001cf30`'s sites (`addi -18,r6,r0 ; bl [skip] ; jarl 0x1e9fc,lp` — i.e., "called
   when `r6>=18`"), without disassembling `FUN_0001e9fc`'s own body. Segment 1 DID disassemble it (at its OWN
   call site, `0x1dc98`, gated on `FUN_0001d68e`'s return value `==5`, not on an out-of-range check) and found
   it is an **unconditional, branch-free sequence of 11 `cmp`/`st.b` pairs** comparing `r6` against 11 specific
   ROM constants at `tp-29588..tp-29568` (matching table-A's 11 TX-capable slots) and clearing a corresponding
   byte in an 11-entry flag array at `gp-5780..gp-5770` on match — i.e. a **"clear this logical message's
   pending flag" utility**, not a fault/assert handler. Given `FUN_0001cf30`'s call convention was inferred by
   this document from the branch structure only (not from reading `FUN_0001e9fc`'s body), it is plausible
   `FUN_0001e9fc` is genuinely dual-natured (both an out-of-range path AND a normal-match clear path use the
   same shared utility, called from different sites with different arguments) — or that this document's
   ">=18 = fault" framing is simply wrong and `FUN_0001cf30`'s call is actually a normal "clear the flag for
   whatever message this identifies" step gated by something this document mis-read. **Flagged for a follow-up:
   directly disassemble `FUN_0001e9fc`'s body (should be ~`0x1e9fc-0x1ea82` per Segment 1) to settle which
   framing is correct** — not done in this document since Segment 1's independent read already covers it more
   authoritatively for the `0x1dc98` call site; this document's own `FUN_0001cf30` call sites (`0x1d05e`,
   `0x1d0b8`, `0x1d12a`, etc.) were NOT re-examined against Segment 1's finding and their exact semantics remain
   as originally described in §6, now with reduced confidence on the "fault" label specifically (the
   ">=18 triggers a call" structural fact itself is still directly byte-verified and stands).

## Cross-references
- `reference_accord_can_tx_synthesis_2026-07-07.md`, `reference_accord_can_tx_segmentC_driver_hw_mailbox.md`,
  `reference_accord_can_tx_segmentD_known_frame_provenance.md`, `reference_accord_can_tx_fcn0_forward_verify.md`
  — this document extends but does not fully close their shared Open Item ("what selects the logical index at
  the live `FUN_0001d68e` call sites").
- `reference_accord_can_tx_trigger_path.md` (Segment 1, concurrent) — independently reaches the same top-level
  verdict via the CSETR/hardware-trigger angle; see reconciliation note above. Their Open Item #4 ("call site 2
  / `0x1db32`'s mailbox-index provenance") is the SAME open seam as this document's Open Item #1 — both
  segments converge on "mailbox/logical-index assignment inside `FUN_0001d96e`/`FUN_0001db74`" as the single
  highest-value remaining unknown for the whole car-facing-vs-internal question.
