---
name: reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget
description: Accord TVA-A160 CAN TX — fresh disasm of FUN_00055c42 (399) and FUN_00055d80 (427) finds the SAME pre-checksum hook shape as 330's proven V31P/V49P site, exact stock bytes given. Combined spare-bit budget across all 3 gateway-crossing frames is 20 bits (330:7 + 399:10 + 427:3), not the 5-7 previously catalogued -- 399/427 have NEVER been claimed by any build. Corrects a "0x18F byte5 fully free" overstatement by 2 live bits.
metadata:
  type: reference
---

# 399/427 hook sites + full-corpus telemetry budget re-audit (2026-08-07)

Session task: CAN-TX telemetry channel widening for V83 (team-lead brief). Verified fresh via
`disassemble_function`/`read_memory` on `code.bin` (program="code.bin"), cross-checked against the
existing CAN-TX memory corpus (`reference_accord_can_tx_399_427_bitmap.md`,
`reference-accord-can-tx-frame-0x14a-bytemap.md`, `reference-accord-piggyback-channel-audit-dbc-panda.md`)
which this entry reconfirms byte-for-byte and extends. gp=0xFEDF8000.

## NEW: 399 and 427 have the IDENTICAL pre-checksum hook shape as 330's proven V31P/V49P site

All three builders end with the same compiler idiom — a critical-section-enter `jarl` (which clobbers
`lp` anyway) immediately followed by the buffer-base `movea`, then DLC/ID setup, then the checksum call.
Because `lp` is about to be re-clobbered by the checksum `jarl` regardless, the `movea` is safe to replace
with a `jarl <cave>,lp` (cave re-executes the displaced `movea` before returning) — this is exactly
`build_v49p_tva.py`'s proven `pack_polarity` mechanism, now confirmed to generalize:

| frame | builder | hook addr | stock bytes (LE) | decode | checksum call |
|---|---|---|---|---|---|
| 0x14A/330 | `FUN_00055a98`@0x55A98 | 0x55C0E | `2436e8ea` | `movea -0x1518,gp,r6` | 0x55C18 |
| 0x18F/399 | `FUN_00055c42`@0x55C42 | 0x55D50 | `2436e0eb` | `movea -0x1420,gp,r6` | 0x55D5A |
| 0x1AB/427 | `FUN_00055d80`@0x55D80 | 0x55EFA | `243634ec` | `movea -0x13cc,gp,r6` | 0x55F04 |

Byte pattern `2436` is identical across all three (same opcode/register fields); only the 2-byte
displacement differs and matches each buffer base exactly (`-0x1518`→`e8ea`, `-0x1420`→`e0eb`,
`-0x13cc`→`34ec`, all LE halfword2 of the `movea`). Checksum helper `FUN_00057b24(buf=r6,dlc=r7,id=r8)`
runs immediately after in program order in all three, so a write inside the cave is automatically covered
by the checksum — no separate recompute needed (already proven on-car 4x for 330).

## Full-corpus spare-bit re-verification (fresh disasm, not re-quoted from memory)

Independently re-derived every read-modify-write on all three builders' payload bytes this session
(`disassemble_function` 0x55A98/0x55C42/0x55D80 in full) and it matches the existing bitmap memories
exactly. Total structural spare-bit budget, only counting bits confirmed **never written by any
instruction** in the builder (excludes bits that are explicitly re-cleared each cycle — those need a
mask-constant edit, a different/riskier edit class):

| frame | clean spare bits | location | +mask-edit tier | rate | claimed by any build? |
|---|---|---|---|---|---|
| 0x14A/330 | 5 | byte4[7:3] | +2 (byte7[7:6], also clean not mask-edit) | 100 Hz | V31P-family uses 5b; V49P (diff. baseline) used 5+2=7b |
| 0x18F/399 | 6 | byte4[2:0](3)+byte5[7:6](2)+byte6[6](1) | +4 (byte5[3:0], explicit `andi 0xf0` clear/cycle @0x55CD2) | 100 Hz | **nobody, ever** — grepped all `build_v*_tva.py`, zero hits for 0x55D50/0x55D4C/gp-0x141x/FUN_00055c42 |
| 0x1AB/427 | 3 | byte0[6:5](2)+byte2[7](1) | 0 | 50 Hz (cadence 2 @ 100Hz base tick) | **nobody, ever** — same grep, zero hits |

**Combined clean-tier total: 5+2+6+3 = 16 bits** (or 14 if byte7 of 330 turns out already claimed by a
live V49P-lineage cave — unconfirmed which cave is currently flashed, see Open below), **20 with the
mask-edit tier**, all inside frames independently proven to cross the gateway to the comma tap
(`reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null.md`: 0x14A/0x18F/0x1AB present at
97.3/97.4/48.7 Hz on route 1a). This is 3-4x the previously-recorded 5-7 bit budget, purely because
399/427 had never been bit-mapped for hook-site purposes before (only 330 had a build against it).

## CORRECTION to a claim on file

`reference-accord-can-tx-100hz-base-tick-and-gateway-evidence.md` states "0x18F byte5 = CONSTANT ZERO in
100% of 22,409 frames — a fully free byte". **This overstates the safe budget by 2 bits.** Byte5 bits[5:4]
are a REAL live write (`gp-0x6880 & 3`, packer instructions 0x55CAE-0x55CC2) that merely read 0 throughout
the captured route — not a structurally-unwritten field. Only byte5 bits[7:6]+[3:0] (6 of 8) are
genuinely free, matching `reference_accord_can_tx_399_427_bitmap.md`'s original (correct) count. Do not
use byte5[5:4] as a telemetry field — it will silently corrupt a real (if usually-zero) EPS signal.
General lesson: a wire-level "byte reads constant across N frames" observation is not equivalent to a
firmware-level "byte is structurally unwritten" claim — always cross-check against the builder disasm.

## New-ID/new-mailbox channels are a confirmed dead end for reaching openpilot

Re-confirming from memory, not new this session, but worth restating as the governing constraint on any
future CAN-TX telemetry work: V53 flew FOURFRAME2 (4 new IDs, mechanically correct TX, STRB defect fixed)
and got zero frames at the comma tap, while stock-firmware IDs that are ALSO actively fired but not in
openpilot's DBC (0x660/0x64D/0x32E/0x19F/0x720-3) are equally absent — a downstream gateway per-ID
whitelist admitting only {0x14A, 0x18F, 0x1AB}. Any new mailbox/new ID recipe
(`reference_accord_can_tx_mailbox16_freecheck...md`, `reference_accord_can_mailbox_boot_init_fun1cf30...md`)
is real and buildable but **cannot deliver telemetry to openpilot** — only piggybacking on the 3
whitelisted frames can. Do not spend further build effort on the mailbox-16/new-ID path for this purpose.

## Open / unresolved
- **Which cave is actually flashed on the car for 330 right now** — V31P-family (byte4 only, 5b) or a
  V49P-lineage build (byte4+byte7, 7b)? Determines whether byte7[7:6] is free to claim in a new design.
  Not checked this session (STATE.md's domain).
- 399 byte5[3:0]'s "explicit clear every cycle" — whether this is a deliberate reserved field or just
  unused-but-defensively-zeroed compiler output is genuinely unresolved (flagged in the original bitmap
  memory too). Treat as elevated risk; ship the clean-tier bits first.

## Related
[[reference_accord_can_tx_399_427_bitmap]], [[reference-accord-can-tx-frame-0x14a-bytemap]] — the
byte-level maps this entry re-verifies and extends with hook-site addresses.
[[reference-accord-piggyback-channel-audit-dbc-panda]] — 330-only version of this audit; this entry
generalizes it to 399/427 and finds they were never audited for hook-site purposes.
[[reference-accord-can-tx-100hz-base-tick-and-gateway-evidence]] — source of the corrected "byte5 free"
claim.
[[reference-accord-fourframe-strb-ssam-defect]], [[reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null]]
— the on-car evidence that new-ID channels don't cross the gateway.
