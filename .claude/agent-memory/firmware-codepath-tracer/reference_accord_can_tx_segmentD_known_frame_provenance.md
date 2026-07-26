---
name: accord-can-tx-segmentD-known-frame-provenance
description: 2020 Accord TVA-A160 V850E2 — ground-truth trace of all 7 known EPS CAN TX frame builders (399/427/0x14A car-facing; 0x660/0x19F/0x32E/0x64D internal) through the dispatch tables, scheduler, TX driver and HW-mailbox primitive. Establishes what is and is NOT the car-facing channel selector. Cross-validated against [[reference-accord-can-tx-segmentc-driver-hw-mailbox]] — both independently converge on FUN_0001d68e as the real HW writer and on "no per-message channel differentiator found."
metadata:
  type: reference
---

## ⚠ READ FIRST — reconciliation with Segment C (independent, already-completed trace)

Segment C (`reference_accord_can_tx_segmentC_driver_hw_mailbox.md`, same swarm) independently found and mapped
**the exact same function `FUN_0001d68e`** as the real HW mailbox writer, via a different route, with byte-level
disassembly that matches this document's exactly at every address checked in common (`0x1d692`, `0x1d6cc`,
`0x1d6d0`/`0x1d6d4`, `0x1d728`, `0x1d774`-`0x1d7b8`). This is strong independent cross-validation. Key
reconciliations:

1. **`FUN_00016de6` is NOT a HW mailbox primitive — it's the DTC/fault-event logger.** Segment C disassembled it
   fully and traced it to `FUN_0001611e`/`FUN_00018738`→`gp-0x685c` hard-shutdown latch, matching an independent
   prior trace (`reference_accord_consistency_monitor_hardshutdown.md`). **This document's section below that
   treats `FUN_00016de6`'s `r6` argument as a "mailbox/channel index" is WRONG and superseded — defer to Segment
   C.** The `ld.bu -6611[gp],r10` / `0x8000` early-return I also observed at `0x16dfa`-`0x16e08` (but didn't
   register the significance of) is exactly Segment C's "DTC logging enabled flag" gate. The 44-byte RAM table's
   offset+6/+8 fields that this document calls "the strongest remaining channel-selector candidate" are, per
   Segment C's independent read of the SAME `FUN_000541d8` body, **fault/retry bookkeeping fields for a
   SOFTWARE checksum-validate/retry state machine that touches no hardware at all** — not a channel selector.
   **This closes (with a negative result) the OPEN item this document originally left open in that section.**
2. **Table-A (`0xb72ac`) is not 11 entries — it's 17** (idx 0-16), sentinel-terminated at idx17
   (`0x800007FF`, which this document's raw dump also captured at `0xb7260` but did not decode). Segment C
   decoded the parallel CAN-ID table (`0xB721C`, format `ID<<18`) and DLC table (`0xB71B8`) that this document's
   "channel-byte array @ 0xb7208" sits directly next to — idx 11-16 are legitimate RX-only slots (builder
   pointer = 0, real ID+DLC) newly identifying CAN IDs `0x720-0x723`, `0x75B/0x753/0x752/0x72B/0x6FF/0x6FB`.
   **Defer to Segment C's fuller table characterization**; this document's 11-entry framing below is the
   subset that happens to include all 7 known IDs and remains accurate for those, but is incomplete as a
   description of the whole table.
3. **Convergent negative result on the channel question**, reached independently by two different methods:
   Segment C observed `FUN_0001d68e` hardcodes `0xFF481000` (channel A) at all 3 of its call sites with no
   channel-B twin found. This document independently found the `0xb7208` per-message byte lookup that feeds
   `FUN_0001d68e`'s `r6` argument is **uniformly `6` for every one of the 11 TX-capable table-A entries
   checked** (all 7 known IDs plus the other 4 in range 0-10) — i.e. not a channel selector but a **shared
   hardware TX-staging mailbox index within channel A** (consistent with Segment C's "mailbox index 0-63"
   framing: index 6 is simply the one shared staging mailbox this firmware's software scheduler round-robins
   through, since only one frame is ever being built+sent at a time). **Both segments therefore agree: within
   the `FUN_0001d68e` pipeline, car-facing and internal-only known messages are structurally
   indistinguishable — all funnel to channel A, mailbox 6.** If channel B (`0xFF489000`, confirmed to exist by
   Segment C via its status-polling loop) carries any of the internal-only traffic, it must be through a
   still-unfound sibling write-function — this is the single highest-value next step for whoever picks up
   Segment C's Open Question #2 / this document's original mission goal.

The rest of this document (below) is preserved as originally written for its address-level trace detail (all of
which remains independently useful and mostly still accurate), but its OWN "OPEN" section about the 44-byte RAM
table's offset+6/+8 should be read as **superseded/closed-negative** by point 1 above, not as still-open.

### Second reconciliation — Segment B: the `0xBB544`/`FUN_000520d0` chain is RX-validation, not TX

Segment B (`reference_accord_can_tx_segmentB_scheduler_descriptor_table.md`) independently disassembled the
SAME `0xBB544` table this document calls "table-B" (Segment B calls it "Table A" — naming collision, same
address) and found it is a **periodic RX-message-validity / dual-value lockstep-consistency dispatcher**, not
an outbound frame scheduler: entry7's callback is the confirmed CAN-0xE4 (STEERING_CONTROL) **RX** processor
`FUN_00052676`; entries 0/16 are redundant-signal-pair fault comparators (`FUN_0006b9fa`). They also
independently found `FUN_000520d0` has exactly one literal caller (`0x522c2`), matching this document exactly,
and identified the TRUE per-tick iterator as sibling function `FUN_000521dc` (phase-mask `r24` built from
bitfield extractions of `gp+0x6400`, a STATUS_WORD region) — richer detail than this document captured. **This
means the "scheduler → TX driver" framing used throughout the rest of this document (§ "Scheduler → TX driver
chain") is a mislabel inherited from the mission brief: `FUN_000520d0`→`FUN_000541d8` is a software RX-validity
/ retry-bookkeeping chain, not part of the outbound CAN hardware path.** This is now a THREE-WAY
cross-validated negative result (Segment B via RX-callback identity, Segment C via disassembly showing no HW
touch, this document via the same call-chain trace) — safe to treat as settled, not merely inferred.

Segment B's own Table-B (their name for the `0xb72ac`/`0xb7264` cluster this document calls "table-A") reached
**Open Question #2**: *"Resolve Table B's exact index-to-slot mapping and the param2 computation at each of
the 3 `FUN_0001d68e` call sites, to determine which slot(s) correspond to car-facing vs internal — REQUIRED
before claiming any free index is car-facing."* **This document's `0xb7208` channel-byte finding directly, if
partially, answers that**: at call site `0x1d904` (the one Segment B flagged as looking like "CAN controller
mailbox configuration"), the channel/param1 value is **uniformly 6 for every one of the 11 populated table-A
slots**, so that call site does not differentiate car-facing from internal by channel value. What remains
open (matching Segment B's framing) is whether car-facing vs internal messages are instead routed to
*different call sites* (`0x1d904` vs `0x1db32` vs `0x1dc8e`) rather than differing in the argument value at a
shared call site — this document did not fully resolve which messages reach which of the 3 call sites, only
that the value passed, where traced, is constant.

Segment B's **Open Question #7** ("resolve the 18-entry buffer-pointer array at `0xB7264-0xB72AB` — is it
index-aligned with the function-pointer array?") **is answered by this document's table-A section above**:
YES, confirmed index-aligned 1:1 for at least indices 0-10 (all 11 populated function-pointer slots), verified
by matching each known builder's own buffer-store address against the array entry at the SAME index (e.g.
`0x561b0` at idx4 pairs with buffer `0xfedf6af0` at idx4 — the exact buffer the 0x660 builder itself writes
into, confirmed by reading the builder's body).

---

# Segment D — known-frame CAN TX provenance (2020 Accord TVA-A160, V850E2, `code.bin`)

Produced as part of the 2026-07-07 4-agent CAN-TX swarm (`docs/HANDOFF-2026-07-07-gating-map-and-telemetry-plan.md`
§5 step 1). Goal: establish ground truth for the car-facing channel selector by tracing KNOWN frames (399/427/0x14A
comma-visible; 0x660/0x19F/0x32E/0x64D internal-only) from builder to hardware. Tool: raw byte-level JARL/pointer
scanning in Python cross-checked with `r2 -a v850.gnu` disasm (the `af`/`aa` auto-analysis DOES NOT WORK on this
plugin — `aa` found only 1 function/1 flag in the whole 1 MiB image; all xrefs in this doc were found by manually
decoding the JARL disp22 encoding and raw pointer-literal scanning in Python, then verified with `r2 pd` at each
hit). All addresses are flat file-offset == address, per project convention.

## Verified JARL disp22 encoding (used throughout this trace)
For `jarl target, lp` (4 bytes, base register field = lp/r31 fixed): word0 (bytes 0-1, LE) = `0xFF80 | ((disp>>16)&0x3F)`;
word1 (bytes 2-3, LE) = `disp & 0xFFFF`; `disp = (target - pc) & 0x3FFFFF` (22-bit signed, sign bit 21). Confirmed
against 7 known jarl instances (`0x55c5e→0x218be`, `0x55d5a→0x57b24`, etc.) — all matched exactly. This lets you
find ALL static callers of a function even though `aa`/`axt` produce nothing under `v850.gnu`.

## CONFIRMED — the shared checksum/ID-stamp helper
`FUN_00057b24(r6=buffer_ptr, r7=DLC, r8=CAN_ID)` — Honda 4-bit rolling checksum/counter (nibble-sum over `buffer[0..DLC-1]`
seeded by `r8`, returns nibble in r10; ends `0x57bee jmp [lp]`). This is NOT a mailbox/channel binder — verified by
full disassembly (`0x57b24`-`0x57bee`), it is pure arithmetic over the ID literal as checksum seed. Every builder
calls it once near its end, which makes the `movea ID, r0, r8` immediately before each such call a **reliable,
unique fingerprint for locating every builder function** — used below.

## CONFIRMED — all 7 known-ID builders located and mapped to table-A/table-B index
Found via exhaustive scan for `bytes(0x20,0x46) + LE16(ID)` (the `movea ID, r0, r8` encoding) across the whole 1 MiB
image — each ID occurs **exactly once**, immediately before the `jarl 0x57b24` checksum call inside that message's
builder.

| CAN ID | ID-load addr | builder (enclosing fn) | table-A idx | table-A buffer | DLC (r7 at ID-load site) |
|---|---|---|---|---|---|
| 399 / 0x18F STEER_STATUS (car-facing) | `0x55d56` | `FUN_00055c42` | 9 | `0xfedf6be0` | 7 (`0x55d54 mov 7,r7`) |
| 427 / 0x1AB MOTOR_TORQUE (car-facing) | `0x55f00` | `FUN_00055d80` | 7 | `0xfedf6c34` | — |
| 0x14A (car-facing) | `0x55c14` | `FUN_00055a98` | 10 | `0xfedf6ae8` | — |
| 0x660 (internal-only) | `0x5628e` | `FUN_000561b0` | 4 | `0xfedf6af0` | 8 (`0x5628c mov 8,r7`) |
| 0x19F (internal-only) | `0x5602e` | `FUN_00055f2e` | 8 | `0xfedf6bc8` | — |
| 0x32E (internal-only) | `0x563f2` | `FUN_000562b8` | 6 | `0xfedf6c30` | — |
| 0x64D (internal-only) | `0x56180` | `FUN_0005605c` | 5 | `0xfedf6c08` | — |

DLC cross-check: 399 (DLC7) and 0x660 (DLC8) match the handoff's live-capture ground truth exactly (§3a of the
2026-07-07 handoff) — strong confirmation these are the correct builder functions, not lookalikes.

Both `FUN_00055c42` and `FUN_000561b0` have **zero direct JARL callers** in the whole image (confirmed by the
disp22 scan above) — i.e. neither builder is called by a fixed PC-relative call anywhere. They are reached **only**
via an indirect function-pointer table.

## CONFIRMED — table-A: the message registry (ROM, indirect-call dispatch)
Two parallel ROM arrays, 4-byte stride, SAME index space, found via raw-pointer literal search (`struct.pack('<I',
addr)` occurring in the file):
- **Function-pointer array** @ `0xb72ac`..`0xb72d4` (11 entries, idx 0-10) — `0x561b0` (0x660 builder) at
  `0xb72ac+4*4=0xb72bc` (idx4); `0x55c42` (399 builder) at `0xb72ac+9*4=0xb72d0` (idx9).
- **Buffer-pointer array** @ `0xb7264`..`0xb72a8` (18 entries, idx 0-17, only first 11 slots are consumed by
  table-A's builders) — `0xfedf6af0` (0x660 buffer) at idx4; `0xfedf6be0` (399 buffer) at idx9. Same index as the
  function-pointer array, confirmed by exact index match.
- **Channel-byte array** @ `0xb7208`..`0xb7212` (byte per idx, SAME idx space) — see "ruled out" section below.

### Dispatcher: `FUN_0001d68e(r6=peripheral_channel, r7=table-A_msg_idx)` [`0x1d68e`–`0x1d82a`, `dispose` at `0x1d82a`]
This is where the indirect call to the builder actually happens (`0x1d728: mov 0xb72ac,ep; add r22,ep [r22=r7<<2];
sld.w 0[ep],r25; ... jmp [r25]` at `0x1d744`, with args `r6=buffer_addr(0xfedf6904+r27*8)`, `r7`, `r8` staged from
the stack — matches both builders' prologues, which save incoming r6/r7/r8 to `4[ep]`/`8[ep]`/`12[ep]`). Before/
after the dispatch it computes an MMIO base `= r27(channel)*64 + 0xFF481000` (`0x1d7e4 shl 6,r27; 0x1d7e6 mov
0xff481000,r9; 0x1d7ec add r9,r27`) and pokes the checksum byte there (`0x1d778 di; ...; 0x1d78c sst.b r6,0[ep]`
where `ep = channel*64 + 0xFF481000`). This proves the SoC has multiple (≥7, given values 0-6 observed) physical
CAN-adjacent MMIO instances at stride `0x40` from base `0xFF481000` (and a sibling family at `0xFF489000`, seen in
neighbouring functions `FUN_0001d82e`/`FUN_0001d96e`).

Exhaustive JARL-scan found only **3 static callers** of `FUN_0001d68e`: `0x1d904`, `0x1db32`, `0x1dc8e`.

## RULED OUT — `FUN_0001d68e`'s "channel" param is NOT the car/internal selector
The byte table @ `0xb7208` (indexed by table-A's own msg_idx, 0-10 — confirmed, since the caller
`FUN_0001d82e(r6→r24=msg_idx)` passes `r24` straight through as `FUN_0001d68e`'s `r7` at call site `0x1d904`) was
dumped for all 11 slots:

```
idx 0..10 (incl. 399=idx9, 427=idx7, 0x14A=idx10, 0x660=idx4, 0x19F=idx8, 0x32E=idx6, 0x64D=idx5)
byte value: 0x06  0x06  0x06  0x06  0x06  0x06  0x06  0x06  0x06  0x06  0x06   <- ALL ELEVEN = 6
```

The code explicitly special-cases this: `0x1d88c cmp 6,r26; bne 0x1d8b8` — when the looked-up channel equals 6,
`FUN_0001d82e` takes an EARLY-RETURN path and never calls `FUN_0001d68e` at all (`0x1d8b4 mov 1,r10; br 0x1d90e`).
Since **every single table-A message — the 3 known car-facing IDs and the 4 known internal-only IDs alike — has
channel byte 6**, call site `0x1d904` is a structural no-op for all of them; call site `0x1dc8e` (in a twin code
block) hardcodes `mov 6, r6` literally right before the call, i.e. it's the real path, and it is **the same
literal 6 for the whole registry, with no per-message variation observed**.

**Conclusion: the `FUN_0001d68e` / `0xFF481000+channel*0x40` MMIO family is NOT where car-facing vs internal
routing is decided.** All known messages share one value here. This is a genuine negative result, not an
incomplete trace — the table was fully dumped and the branch condition fully read. Flag for Agents A/C: if your
independent topology/driver traces also converge on a single shared physical instance servicing both bus
segments, that would upgrade this from "ruled out at this layer" to "there may only be one physical CAN
controller instance, with car/internal being a logical distinction elsewhere" — worth cross-checking.

## CONFIRMED — the periodic scheduler path (table-B, separate from table-A)
**Table-B**: ROM descriptor array @ `0xBB544` (= `tp(0xBF000) - 15036`), 32-byte stride, 19 entries (idx 0-18).
Index space is DIFFERENT from table-A's — correlated by observing table-B's offset+20 (word[5], a buffer pointer)
equals table-A's buffer pointer **+8 bytes**, for the entries where a match exists:

| known ID | table-A idx | table-A buf | table-B idx (via buf+8 match) | table-B buf |
|---|---|---|---|---|
| 399 (car) | 9 | `0xfedf6be0` | **3** | `0xfedf6be8` |
| 0x660 (internal) | 4 | `0xfedf6af0` | **13** | `0xfedf6af8` |
| 0x19F (internal) | 8 | `0xfedf6bc8` | **11** | `0xfedf6bd0` |
| 0x64D (internal) | 5 | `0xfedf6c08` | **10** | `0xfedf6c10` |
| 427 (car) | 7 | `0xfedf6c34` | *no exact +8 match* | — |
| 0x14A (car) | 10 | `0xfedf6ae8` | *no exact +8 match* | — |
| 0x32E (internal) | 6 | `0xfedf6c30` | *no exact +8 match* | — |

Only 4 of 7 known IDs are present in table-B, and the split does **not** track car-facing/internal (399 is
present WITH the internal trio; 427/0x14A car-facing AND 0x32E internal are all absent). Table-B is therefore a
**scheduling-mechanism-type split** (e.g. "needs periodic retry/ack tracking" vs not), not a channel selector —
noted as a caution against over-reading table membership as topology.

### Scheduler → TX driver chain (table-B-indexed messages only)
`FUN_000520d0(r6=tableB_idx)` [`0x520d0`] — reads `table-B[idx]`; if descriptor `+14`(halfword, enable) != 0, calls
`FUN_000541d8(r6=tableB_idx, r7=descriptor[+20])` at **the sole static call site `0x52148`** (confirmed via
disp22 scan — `FUN_000541d8` has exactly one caller in the whole image). `FUN_000520d0` itself has exactly one
static caller too: `0x522c2`, inside a loop (`0x522ac`..`0x522d0`) that sweeps `idx=0..18` gated by descriptor
`+24` (byte, AND'd against a phase counter — see "ruled out" note below).

`FUN_000541d8` (TX driver) [`0x541d8`] — on entry `r22=tableB_idx`. Reads a **44-byte-stride RAM table** at
`gp(0xFEDF8000) - 13004 (0x32CC) + idx*44` = `0xFEDF4D34 + idx*44`. Confirmed via 55 occurrences of the
`movea -13004, gp, rX` encoding, ALL confined to one module `0x53e00`-`~0x5560`. Two fields of this per-message
struct — **halfword @ offset+6** (primary/steady-state path, `0x5420c ld.hu 6[r28],r6`) and **halfword @
offset+8** (secondary/registration path, `0x54256`/`0x54294 ld.hu 8[r28],r7`) — are read and passed as the
**FIRST ARGUMENT** to `FUN_00016de6` (`0x5421a`, `0x54272`, `0x5429c` — three call sites inside the TX driver,
all `jarl 0x16de6,lp` with r6 set from one of these two table fields).

### `FUN_00016de6` — confirmed generic HW-mailbox primitive
96 direct static callers across the whole image (by far the most-called low-level routine found this session) —
consistent with being the shared "poke a hardware CAN-mailbox-adjacent register" primitive. Its own `r6` argument
(our "channel/mailbox index" candidate) is itself used to index **two further per-mailbox config structures**:
a halfword array @ `gp-6348` (`0x16e0c`-`0x16e18`, stride 2, `r26<<1`) and a 28-byte-stride array @ `tp-29352`
(`0x16e56`-`0x16e66`, `mul 28,r26/r12,r0`). This shape (index feeding two more per-slot config tables) is
exactly what you'd expect for a genuine hardware mailbox-slot number.

**This 44-byte RAM table's offset+6/+8 field is structurally the strongest remaining candidate for "the channel
selector"** — it sits directly between the TX driver and the confirmed generic HW-register primitive, on the ONE
sole call path from the scheduler. But:

## OPEN — could not extract the actual numeric value
The 44-byte table lives in **RAM** (`0xFEDF4D34+`), not flash, so it cannot be read from the static `code.bin`
image directly — it must be populated at runtime by a one-time init/registration write. An exhaustive search for
STORE instructions (`st.h`/`sst.h`/`st.b`/`sst.b`) to offset+6 or +8 of any register holding this table's base,
across the full 0x53e00-0x557xx module, found **zero writers** (only one unrelated store at offset+33 was found).
The zero-init loop at `0x53e9e` (which clears offsets 10/12/14/20/28/34/36 for all ~19 entries at boot) explicitly
**does not touch offset+6/+8**, confirming they are meant to hold a value set once elsewhere, outside this module,
that survives the zero-init sweep.

**What would close this:**
1. Grep the WHOLE 1 MiB image (not just the 0x53e00-0x557xx module) for STORE-form accesses to `gp-13004+K` for
   `K` = each field offset (try disp = `-13004+6=-12998`, `-13004+8=-12996`, and the same +44,+88,... for idx=3/13
   specifically: `-13004+3*44+6=-12866`, `-13004+13*44+6=-12432`, etc.) — the compiler may fold a per-entry
   constant offset directly into a `movea`/`st.h` displacement rather than doing base+idx*44 arithmetic, especially
   for a one-time unrolled boot-time initializer (the zero-init loop at `0x53e9e` itself is unrolled 4-wide with
   exactly this folded-constant style, so the writer for +6/+8 likely follows the same idiom and was missed by the
   base-literal (`-13004`) scan because it uses a *different* per-entry literal).
2. Alternatively, a live RAM read at `0xFEDF4D34 + 3*44 + 6` (399) and `0xFEDF4D34 + 13*44 + 6` (0x660) — and the
   +8 variants — via a SAFE read-only debug/UDS memory-read (if the ECU exposes one) would settle this empirically
   without further static work. NOT attempted this session (read-only static study only, per mission scope).

## RULED OUT — table-B offset+24 bitmask (schedule-phase, not channel)
`0x522b8: ld.bu 24[ep],r14; and r24,r14` inside the OUTER scheduler sweep (`r24` = sweeping tick-phase counter
0-18) — table-B offset+24 (word[6]) differs 399=`0xF` vs 0x660=`0x8`, but this is confirmed by its read-site to be
a **tick-phase membership bitmask** (gates which sweep passes re-arm the message), not a channel/bus selector.
Noted so a future agent doesn't re-discover this and misattribute it as the channel field.

## INFERRED, NOT CONFIRMED — table-B offset+4 "group" field
Word[1] (byte offset+4) of table-B clusters into contiguous idx ranges sharing a value: idx1-6→3, idx7→5,
idx8-10→6, idx11→7, idx12-13→8, idx14-18→11, idx0→10. 399(idx3)=3, 0x660(idx13)=8 — genuinely different, and the
clustering-by-contiguous-idx-range pattern is consistent with a compiler-assigned "owning source
file/subsystem" tag (typical of auto-generated CAN message tables grouped by feature). **No read-site for this
field was located this session** — flagged as a lead for a follow-up, not a conclusion. Do not treat as confirmed
channel evidence without finding where it's consumed.

## Summary table (ground truth as established this session)

| CAN ID | car-facing? | table-A idx | table-A buffer | table-B idx | table-B buf+24 (phase bitmask) | table-B buf+4 ("group", unconfirmed use) | `0xb7208` channel byte (ruled out as selector) |
|---|---|---|---|---|---|---|---|
| 399/0x18F | YES | 9 | `0xfedf6be0` | 3 | `0xF` | 3 | 6 |
| 427/0x1AB | YES | 7 | `0xfedf6c34` | — (not in table-B) | — | — | 6 |
| 0x14A | YES | 10 | `0xfedf6ae8` | — (not in table-B) | — | — | 6 |
| 0x660 | no | 4 | `0xfedf6af0` | 13 | `0x8` | 8 | 6 |
| 0x19F | no | 8 | `0xfedf6bc8` | 11 | `0xF` | 7 | 6 |
| 0x32E | no | 6 | `0xfedf6c30` | — (not in table-B) | — | — | 6 |
| 0x64D | no | 5 | `0xfedf6c08` | 10 | `0x8` | 6 | 6 |

**No field enumerated above splits cleanly along the car-facing/internal-only line across all 7 known IDs.** The
strongest still-open candidate (44-byte RAM table offset+6/+8, feeding `FUN_00016de6`'s mailbox-index argument) is
structurally right but its value is unresolved. This is a considered, evidence-backed negative/open result, not an
incomplete search — every table this session found containing per-message data for all 7 known IDs has been
dumped and checked.

## Tool notes for future agents on this binary
- `r2 -a v850.gnu -c 'aa'` produces almost nothing (1 function, 1 flag) on this image — **do not rely on `axt`/
  `afl`/`aa`-based xrefs**. Use the JARL disp22 decode + raw pointer-literal scan technique documented above
  instead; it is exhaustive and fast (<5s for the whole 1 MiB image in Python).
- `movea IMM, r0, rX` (bytes `20 46 <imm_lo> <imm_hi>`) is a reliable fingerprint for "load an immediate 16-bit
  CAN ID into a register" and can be grepped directly for any known ID to find its builder.
- Two DIFFERENT per-message ROM tables exist with DIFFERENT index spaces (table-A @ `0xb72ac`/`0xb7264`/`0xb7208`,
  11-18 entries; table-B @ `0xBB544`, 19 entries) — do not assume one index numbering applies to both; correlate
  via shared buffer pointers (table-B's buffer field = table-A's buffer field **+8 bytes**, empirically).
