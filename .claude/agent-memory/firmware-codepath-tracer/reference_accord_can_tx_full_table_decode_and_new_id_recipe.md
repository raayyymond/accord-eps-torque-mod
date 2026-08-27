---
name: reference_accord_can_tx_full_table_decode_and_new_id_recipe
description: Accord TVA-A160 CAN TX — full 18-slot table decode with a validated ID-encoding formula (ID = table_entry >> 18), the FUN_0001d68e/0001d82e emitter mechanics disasm-verified against the SVD, the cadence chain to the confirmed 1kHz control task (base tick 62.5Hz), and a concrete recipe for adding a brand-new dedicated-mailbox TX ID. Corrects CAN330's "unresolved" TX rate and partially reopens the mailbox-6 arm mechanism.
metadata:
  type: reference
---

# CAN TX: full table decode, emitter mechanics, cadence, new-ID recipe (2026-07-23)

Traced on stock `code.bin` via GhidraMCP (disassembly, not just decompiler C — the decompiler mistyped a
32-bit `st.w` as a 16-bit short-store on the ID-register write; always cross-check against `disassemble_function`
for anything load-bearing here).

## Table layout (corrects "one table at 0xB721C" framing used elsewhere)

Four abutting 18-entry (slots 0-17) tables, immediately following each other in flash:
- `0xB7208` (20B, last 2 padding): routing, 1B/slot = HW mailbox index (0-6)
- `0xB721C`-`0xB7264` (18x4B): **ID table**, `entry = CAN_ID << 18` (11-bit std ID, left-justified — matches
  `FCN0M0MID0W`'s bits[28:0]+IDE(29) layout for a standard, non-extended frame)
- `0xB7264`-`0xB72AC` (18x4B): static-default-payload pointers, all `0xFEDF6Axx/6Bxx/6Cxx` RAM addresses
- `0xB72AC`+ (18x4B, 11 non-null): per-slot **dynamic-payload callback function pointers**

**ID formula validated two independent ways** (not guessed): slot 9's callback ptr == `FUN_00055c42`
(known CAN-399 STEER_TORQUE_SENSOR packer) and its ID entry `0x063C0000>>18 = 0x18F = 399` exact.
Slot 10's callback == `FUN_00055a98` (known CAN-330 packer), entry `0x05280000>>18 = 0x14A = 330` exact.

Full decoded map — routing table confirms slots 0-10 ALL share mailbox 6:

| slot | mbx | ID | note |
|---|---|---|---|
| 0-3 | 6 | 0x723,0x722,0x721,0x720 | unidentified, sequential |
| 4 | 6 | **0x660** | comma-ABSENT |
| 5 | 6 | **0x64D** | comma-ABSENT |
| 6 | 6 | **0x32E** | comma-ABSENT |
| 7 | 6 | **0x1AB**(427) | comma-VISIBLE |
| 8 | 6 | **0x19F** | comma-ABSENT |
| 9 | 6 | **0x18F**(399) | comma-VISIBLE, callback=FUN_00055c42 |
| 10 | 6 | **0x14A**(330) | comma-VISIBLE, callback=FUN_00055a98 |
| 11-14,16 | 5,4,3,2,0 | 0x75B,0x753,0x752,0x72B,0x6FB | dedicated mailboxes |
| 15 | 1 | anomalous entry `0x9BFC9203` (nonzero low bits, doesn't fit `ID<<18`) — NOT resolved |
| 17 | 6 | N/A — bypass, dynamic ID from live RAM `gp-0x1700` (likely UDS diag-response slot) |

All 7 previously-tracked EPS CAN IDs (visible + absent) are slots 4-10, **all with byte-identical routing** (mailbox 6).

## Emitter mechanics (disasm-verified)

`FUN_0001d82e(slot)`: reads `0xB7208[slot]`(routing). Mailbox==6 → ORs a pending bit into `gp-0x170c`
(bit values from `tp-0x7fac`), returns (deferred to ISR). Mailbox 0-5 (dedicated) → if
`gp-0x1744[mbx*2]`(owner-slot sentinel, `-1`=free) is free AND `FCN0M{mbx}CTL` bits[1:0] idle, claims it
(`gp-0x1744[mbx]=slot`) and calls `FUN_0001d68e(mbx,slot)` immediately.

`FUN_0001d68e(mailbox,slot)`: `sld.w` the full 32-bit ID-table entry → `st.w` into `FCN0M{mbx}MID0W`
(SVD offset `0x11028`, step `0x40`); DLC byte from `0xB71B8[slot]` (byte-indexed, NOT the ID table's `*4`
stride) → `FCN0M{mbx}DTLGB`(`0x01020`). Invokes callback `0xB72AC[slot]` for dynamic payload, else static
default via `tp-0x7d9c`=`0xB7264[slot]`, copied byte-wise into `FCN0M{mbx}DAT0..7B`(`0x01000`) under
IRQ-disable. **Before firing**, re-checks `0xFEDF68BC[mbx*2]` (== `gp-0x1744`, same table, just accessed via
absolute-immediate addressing here instead of gp-relative displacement — these are NOT two different tables,
confirmed by address arithmetic: `gp-0x1744 = 0xFEDF8000-0x1744 = 0xFEDF68BC` exactly) against the slot being
serviced; on match + global-TX-enabled (`gp-0x1712` bit0) → arms via two writes to `FCN0M{mbx}CTL`(`0x09038`,
`0x0100` then `0x0200`, SVD strobe names `SERY`/`CSETR`) and returns 1 (leaves claim in place — freed later by
the TX-complete handler `FUN_0001d96e`/`FUN_0001db74`, which explicitly clear `gp-0x1744[mbx]=0xFFFF`); on
mismatch → clears the entry and returns 0 or the special code 5.

Registers cited from `reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`: `FCN0M0DAT0..7B`(+0x01000),
`FCN0M0DTLGB`(+0x01020, DLC), `FCN0M0STRB`(+0x01024, `SSOW` bit7=dir 0RX/1TX), `FCN0M0CTL`(+0x09038,
bit-set/clear, strobes `SERY`(0)/`TCPF`(1,RO)/`CSETR`(2)/`SEIE`(3)/`SENH`(6)/`RDYF`(8,RO)/`TRQF`(9,RO)),
`FCN0M0MID0W`(+0x11028, ID[28:0]+IDE[29]), `FCN0M0DAT0W`(+0x11000). All step 0x40/mailbox.

**FCN1 (base `0xFF4A0000`) re-confirmed dead, 2 ways:** zero real xrefs in ~186k scanned instructions
(`search_instructions operand_pattern="ff4a"/"4a0000"`); the only 2 substring hits are a false positive —
`FUN_00000c76`, a boot-time **bulk zero-clear loop** `for(p=&DAT_ff480000; p<0xff4a2000; p++) *p=0;` that
incidentally clears FCN1's first 0x2000 bytes as part of clearing FCN0+padding, never subsequently configures
it — and an unrelated code address (`br 0x0006ff4a`).

## Cadence (fully traced to the confirmed ~1kHz control task)

`FUN_0002214a`(the confirmed 1000Hz control task) → `FUN_00045d9e(0x25)` (called inside an always-true
state-gated block) → `FUN_0001e9ec` → `FUN_0001e942`(scheduler) → `FUN_0001e456` → `FUN_0001d82e` → `FUN_0001d68e`.

`FUN_00045d9e` gates `FUN_0001e9ec()` behind a self-wrapping 4-bit nibble counter at `gp-0x3518` (decrements
every call, wraps 0xF→0 automatically, no explicit reload needed) → fires once per 16 control-task cycles →
**base scheduler tick = 1000/16 = 62.5 Hz**. `FUN_0001e942` iterates slots 0-10 each base tick, reloading a
per-slot countdown from cadence table `tp-0x7364`=`0xB7C9C` (1B/slot=period in base-tick units) on expiry:

| slot 0-3 | 4(0x660) | 5(0x64D) | 6(0x32E) | 7(0x1AB) | 8(0x19F) | 9(0x18F/399) | 10(0x14A/330) |
|---|---|---|---|---|---|---|---|
| period 1 → 62.5Hz | 20 → 3.125Hz | 100 → 0.625Hz | 10 → 6.25Hz | 2 → 31.25Hz | 1 → 62.5Hz | 1 → 62.5Hz | 1 → 62.5Hz |

**⚠ CORRECTS `reference_accord_can330_tx_rate_unresolved.md`:** that memory found `FUN_00055a98` had zero
static callers and called 330's TX rate genuinely unresolved, "not in phase-scheduled Table B", and flagged
the build script's "100Hz" as an unverified assumption. This session found `FUN_00055a98` is a **callback**,
invoked indirectly via the function-pointer table at `0xB72AC[10]`, not via a direct `jarl` — which is exactly
why the disp22 scan found nothing (it's a computed call, `jmp [r25]` in `FUN_0001d68e`). 330 **is** slot 10 of
the same scheduled table the other 6 known IDs use; its real rate is **62.5 Hz**, not the assumed 100Hz and not
unresolved. Flagging for the operator to review/retire that older memory rather than deleting it myself.

## Gateway-visibility verdict — strengthens but does not fully close the 2026-07-07 synthesis

`reference_accord_why_car_facing_vs_internal_2026-07-07.md` (prior swarm) already ruled out a 2nd controller,
a static per-message channel field, ID-keyed CSETR gating, and per-builder cadence differences — leaving "the
discriminator lives in unlocated dynamic-RAM producers (0xFEDF68BC registration table + STATUS[idx] pending
table) or physical-layer config outside code.bin" as the open leading hypothesis.

This session's cadence-table find is **new, corroborating evidence for the same "no firmware discriminator"
conclusion**, one level stronger: all 7 known IDs are not just statically identical in routing/mailbox/enable-mask,
they are **actively, continuously scheduled and fired** at explicit (non-zero, non-diagnostic-gated) periods —
including the 4 "absent" ones (0x660 @3.125Hz, 0x64D @0.625Hz, 0x32E @6.25Hz, 0x19F @62.5Hz, the last one at
the SAME rate as visible 399/330). This undercuts the prior memory's "maybe internal IDs only fire in a
diagnostic/bench mode" framing — there's no cadence/enable-mask evidence of conditional firing; they run in
normal operation identically to the visible set.

**⚠ NOT fully closed — `0xFEDF68BC`/`gp-0x1744` IS the "mailbox-registration table" the prior memory flagged
as unresolved, and I only closed HALF of it this session:** for DEDICATED mailboxes (0-5) the claim/free cycle
is fully traced (`FUN_0001d82e` claims, `FUN_0001d68e`'s registration-check fires, `FUN_0001d96e`/`FUN_0001db74`
free). For the SHARED mailbox 6 (which is what ALL 7 known IDs, visible and absent, actually use) I could NOT
locate where `gp-0x1744[6]` gets claimed before `FUN_0001d96e`/`FUN_0001db74` call `FUN_0001d68e(6,next_slot)`
— neither function writes it in the decompiled code I read, and `FUN_0001d82e`'s shared-mailbox branch only
ORs a pending bit into `gp-0x170c`, never touches `gp-0x1744[6]`. If the registration check inside
`FUN_0001d68e` genuinely gates on this for mailbox 6 too, there must be a write I haven't found (plausibly at
boot/init, seeding the first slot). This is a real residual gap, not a hand-wave — it's the one piece of the
mailbox-6 path this session did not close, and it's the piece that would matter if the actual discriminator
turns out to be dynamic rather than static. Next step: full `disassemble_function` (not decompiler C) of
`FUN_0001d96e` end-to-end, and a search for any OTHER writer of `gp-0x1744+0xc` (mailbox 6's slot, offset
`6*2=0xc`) or absolute `0xFEDF68C8`, especially in boot/init code.

## New-ID build recipe (recommended, not yet built)

**Do not extend the 4 packed tables** (zero slack — a 19th slot physically collides with the next table, would
require relocating all 4 tables and every hardcoded `0xb721c`/`0xb7264`/`0xb72ac`/`tp-0x7fac`/`tp-0x7d9c`
immediate across 3 functions). **Recommended: a standalone dedicated mailbox, driven by a small new cave that
bypasses the round-robin/table machinery entirely.**

- FCN0 supports mailboxes 0-63 (SVD: `FCN0M0DAT0B` "array step 0x40 for buffers 1-63"; `DNBMRX0`/`RX1` cover
  buffers 0-31/32-63). Only 0-6 confirmed in TX use. **Not yet checked: whether any of 7-63 are RX-configured
  elsewhere** — needed before naming a specific free buffer number.
- Once a free mailbox N is confirmed: one-time init `FCN0M{N}STRB`=0x80(TX), `DTLGB`=8, `MID0W`=`new_id<<18`.
  Each cycle: write 8 payload bytes to `DAT0..7B`(or the 32-bit alias `+0x11000`), then `CTL`=0x0100 then
  0x0200 (mirrors `FUN_0001d68e`'s trigger sequence) — hook this into the existing ~1kHz `FUN_0002214a` task
  with your own local cadence divider.

## Related
[[reference_accord_can330_tx_rate_unresolved]] — corrected by this entry (330's rate is 62.5Hz, not unresolved).
[[reference_accord_why_car_facing_vs_internal_2026-07-07]] — the prior, more-hedged investigation of the same
gateway-visibility question; this entry corroborates its "no static discriminator" conclusion and adds the
cadence-table evidence, but does not close its `0xFEDF68BC` producer open item for mailbox 6.
[[reference_accord_can_tx_synthesis_2026-07-07]] — prior "Table B" naming for what this entry calls the
routing/ID/payload-ptr/callback 4-table stack; addresses match (0xB7208 etc.), naming differs.
