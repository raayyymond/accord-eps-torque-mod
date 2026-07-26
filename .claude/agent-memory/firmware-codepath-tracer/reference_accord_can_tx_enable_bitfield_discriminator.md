---
name: accord-can-tx-enable-bitfield-discriminator
description: 2020 Accord TVA-A160 V850E2 — CAN-TX map (one controller FCN0, one HW mailbox 6, one pending queue gp-0x170c). ⚠ CORRECTION 2026-07-08 the "0xFEDF693C enable bitfield is THE comma-visibility discriminator" claim is RETRACTED/WRONG: that bitfield gates an all-zero dead fn-ptr path, and 0x660 is active-from-ROM (0xB7D00[4]=1) + scheduled/transmitted at 5Hz exactly like 399 yet absent from the raw comma scan. No software gate discriminates; the split is almost certainly an EXTERNAL GATEWAY (outside code.bin) forwarding only {399,427,0x14A}. Empirically untested.
metadata:
  type: reference
---

# Accord TVA-A160 — CAN-TX map; the comma-visibility discriminator is NOT in the EPS software

> ⚠ **CORRECTION 2026-07-08 — read `## CORRECTION` below.** The original "bottom line" (enable bitfield
> `0xFEDF693C` is the discriminator) is WRONG. Kept for provenance, struck-through in intent by the correction.

Platform: 2020 Honda Accord 39990-TVA-A160, Renesas uPD70F3508 / V850E2. Stock `code.bin`.
Method THIS session: **Ghidra** (program `master.bin` == byte-identical stock `code.bin`, V850:LE:32, flat
base 0; verified `0x410c0`=`ld.bu -0x67fe,gp,r12` and `0x55c50`=399 torque packer against disk bytes). Ghidra's
decompiler resolves the gp-relative loads that r2's `v850.gnu` mis-decoded — this is what cracked the question
four r2 passes (see `reference_accord_why_car_facing_vs_internal_2026-07-07.md`) could not.

## CORRECTION (2026-07-08) — the enable-bitfield discriminator is RETRACTED

A follow-up activation trace + independent byte-verification overturned the "enable bit" conclusion below:
- `0xFEDF693C` (gp-0x16c4) gates a fn-ptr call whose table (`0xB7C40` = tp-0x73c0) is **all zeros** for all 11
  slots → DEAD path, not the TX trigger.
- Real TX arming = timer path: per-slot **active flag `gp-0x16a0[slot]&1`** (ROM seed `0xB7D00`: slots0-3=0,
  **slots4-10=1**) + interval `tp-0x7364`=`0xB7C9C` (399=1→100Hz, 427=2→50Hz, 0x14A=1→100Hz matches real rates;
  **0x660=20→5Hz, 0x19F=1→100Hz**). Suppression mask `0xB71CC` = uniform `0xC1` for all 11; `gp-0x1713`=0 driving
  → open for all. **Every software gate treats 0x660 identically to 399.**
- So the EPS **does schedule + transmit 0x660 on FCN0 at 5Hz** (buf-ptr `0xB7264[4]=0xFEDF6AF0`, builder
  `FUN_000561b0`, mailbox 6) — yet 0x660 (and 0x19F @100Hz) are absent from a raw comma scan (38409 frames/10s,
  no DBC filter). No in-software gate can explain that.

**Corrected conclusion:** there is NO software discriminator. The split is almost certainly an **external gateway
ECU** (outside `code.bin`) forwarding only {399,427,0x14A} to the comma-tapped bus — the ORIGINAL swarm's
"physical config outside code.bin" hypothesis (`reference_accord_why_car_facing_vs_internal_2026-07-07.md`), which
was right to leave open. **Decisive test is empirical:** flash `build_tier1_telem_tva.py`'s 0x660 telemetry RWD →
`comma4_can_inventory.py` → is 0x660 on bus1 @100Hz? Consequence: repurposing 0x660 / any new EPS TX ID is
probably invisible to the comma; only 399/427/0x14A are known-visible.

## ~~Bottom line~~ (RETRACTED — see CORRECTION above)

The car-facing/internal split is **NOT** a routing, bus, channel, or mailbox property. It is a **per-message
software enable bit**. A TX frame is built + queued + transmitted **iff its bit is set in the enable bitfield at
`0xFEDF693C` (gp-0x16c4)**. The three comma-visible EPS frames (399/427/0x14A) have their enable bits set during
normal driving; the four "internal" frames (0x660/0x19F/0x32E/0x64D and idx 0-3 = 0x720-0x723) do not — so they
never hit the single physical TX bus the comma taps. They are the same firmware, same controller, same mailbox,
same wire — just not requested. This DISFAVORS the "physical-layer / gateway / second transceiver" hypothesis:
there is no routing degree of freedom in the code for a requested frame to be diverted away from the comma.

## The transmit architecture (all Ghidra-decompiled this session)

- **One enabled controller: FCN0** (prior swarm; FCN1 dead). **One hardware TX mailbox: mailbox 6.** The only HW
  loader `FUN_0001d68e(mailbox_idx, logical_idx)` writes `FCN0M{mailbox_idx}` (`0xFF481000 + idx*0x40`) and is
  invoked ONLY with mailbox_idx=6 (from `FUN_0001db74` and the `FUN_0001d96e(6)` reload). It looks up CAN-ID
  (`0xB721C[idx]`), DLC (`0xB71B8[idx]`) and the builder fn-ptr (`0xB72AC[idx]`) by logical index and **calls the
  builder inline as part of loading** — so a message's builder (e.g. 399=`FUN_00055c42`, 0x660=`FUN_000561b0`)
  runs on demand only when that message is popped for TX. Table-B channel byte `0xB7208 == 6` for all entries
  corroborates the single-mailbox model.
- **One software pending queue: `gp-0x170c` (0xFEDF68F4)**, a 32-bit bitmask, one bit per logical Table-B index.
  Loader `FUN_0001db74` (and reload path in `FUN_0001d96e`): if mailbox-6 slot `regtable[6]` (`gp-0x1738`) is free
  AND pending != 0 → priority-encode the lowest set bit → clear it → register to `regtable[6]` → `FUN_0001d68e(6,
  idx)`. The registration table is `0xFEDF68BC + idx*2` (gp-0x1744, sentinel 0xFFFF) — this is the table the prior
  swarm localized but could not find the writer of; the writer is `FUN_0001d96e`/`FUN_0001db74`/`FUN_0001d68e`
  themselves (all gp-relative stores, invisible to r2 literal-immediate scans).
- **Periodic scheduler `FUN_0001e8ba`** (reached via `FUN_00045d9e` → `FUN_0001e286` and the message-task cluster
  `FUN_0001e9ec`=`FUN_0001e8ba`+`FUN_0001e942`): iterates 11 TX slots (descriptor table `0xB7C6C` = identity
  [0..10]). For each slot it tests the **enable bit** `enable[group(idx)] & mask(idx)` where
  `group = 0xB71E0[idx]` (idx0-7→0, 8-15→1, 16-17→2) and `mask = 0xB71F4[idx] = 1<<(idx&7)`, base
  `enable = gp-0x16c4 = 0xFEDF693C`. If set: consume the bit, load reload timer (`0xB7C90`), fire the action.
  `FUN_0001e942` runs the per-slot countdown timers and calls `FUN_0001e456(slot)` on expiry (re-request).
- **Enable-bit lifecycle:** `FUN_0001d5a6` (CAN-TX reset, called from CAN init `FUN_00057f22`) zeroes all three
  enable bytes `0xFEDF693C/D/E` → at init NOTHING transmits. `FUN_0001d96e` (TX-completion handler) does
  `enable[group] |= mask` to **re-arm** a message after it completes, sustaining periodic TX. `FUN_0001e38e(idx)`
  is the **disable** API (`enable[group] &= ~mask`); `FUN_0001ec76` is a caller. `FUN_0001e44e(idx,period)` sets a
  period byte (`gp-0x1711`). Xrefs to `0xFEDF693C`: writers = `FUN_0001d5a6`[W], `FUN_0001d96e`[|=],
  `FUN_0001e38e`[&=~].

Builders are structurally symmetric (399 and 0x660 both just fill a gp-relative buffer + call Honda
checksum `FUN_00057b24(buf,DLC,ID)`; neither self-registers) — confirming the discriminator is entirely in the
enable/dispatch layer, not the builder.

## What's still OPEN (honest)

1. **The initial-enable / mode gate.** Which condition first sets the internal IDs' enable bits (the re-arm in
   `FUN_0001d96e` only *sustains* an already-running message; something must seed it). Leading hypothesis
   (unchanged from the swarm, now with the exact mechanism located): the seed happens only under a
   diagnostic / bench / special mode (master mode gate `gp-0x1688`, tested `&3` in `FUN_0001e8ba` / `&2` in
   `FUN_0001e942`), so the internal IDs are enabled only then. Not yet traced to the seeding site.
2. **Dedicated mailboxes 0-5 vs overflow-6.** `FUN_0001dcaa` polls mailbox CTLs 0-6 (`0x203==0x201`) and calls
   `FUN_0001d96e(N)`; only N=6 reloads from the pending queue. Whether 0-5 are ever used as dedicated TX mailboxes
   (a separate load path not found) or are RX/unused was not fully resolved. Does NOT change the bottom line: all
   TX still goes out FCN0, and requires the enable bit.
3. Physical-layer config outside `code.bin` (bootloader pin-mux, gateway ECU) remains formally unexcludable from
   this binary — but is now strongly disfavored (no in-code routing DOF for a requested frame).

## How to confirm on the car (ties to the telemetry work)
Either dump `0xFEDF693C` (enable bitfield), `gp-0x170c` (pending), `gp-0x1688` (mode gate) live while driving, OR
simply set an internal frame's enable bit and see whether the comma then captures it. If it does, the whole
"a new/added telemetry frame might be invisible like 0x660" worry (from
`reference_accord_why_car_facing_vs_internal_2026-07-07.md` §"Practical consequence") DISSOLVES: 0x660 isn't
inherently invisible, it's just disabled.

## Cross-refs
- `reference_accord_why_car_facing_vs_internal_2026-07-07.md` (the open question this resolves)
- `reference_accord_can_tx_mailbox_index_map.md` (the 0xFEDF68BC registration table; now: writer = the
  dispatch functions themselves via gp-relative stores)
- `reference_accord_can_tx_synthesis_2026-07-07.md`, `_fcn0_forward_verify.md`
