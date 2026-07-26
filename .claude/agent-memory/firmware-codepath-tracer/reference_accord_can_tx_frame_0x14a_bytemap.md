---
name: reference-accord-can-tx-frame-0x14a-bytemap
description: 2020 Accord TVA-A160 (V850E2) — full per-byte/per-bit map of CAN frame 0x14A (330), the least-documented of the three car-facing EPS TX frames. Builder FUN_00055a98, buffer 0xFEDF6AE8 (gp-0x1518), DLC 8. Identifies 7 spare/never-written bits (byte4 bits7:3, byte7 bits7:6) as piggyback candidates, plus 3 unidentified 16-bit signal sources and 3 unidentified status-bit sources newly discovered this session.
metadata:
  type: reference
---

# Accord TVA-A160 CAN 0x14A (330) builder — full byte/bit map (2026-07-13, Ghidra `master.bin`)

Builder: `FUN_00055a98` (0x55a98-0x55c40, 129 instrs). Buffer `0xFEDF6AE8` = `gp-0x1518` (gp=0xFEDF8000).
DLC 8, CAN ID 0x14A confirmed at the checksum call site `0x55c14: movea 0x14a,r0,r8` /
`0x55c18: jarl 0x57b24,lp` (the shared Honda checksum/counter helper, see
`reference_accord_can_tx_segmentD_known_frame_provenance.md`). This closes Segment D's open item
("builder located via ID-load fingerprint, body not disassembled") for this specific message.

## Byte/bit map

| Byte | Bits | Content | Source (gp-relative) / const | Store instr (addr, bytes) |
|---|---|---|---|---|
| 0 | 7:0 | Signal-A hi byte (BE16) | `*(s16)(gp-0x69ec)` normal, `0x7FFF` sentinel if EPS-state==8 (hard shutdown, `gp-0x67fa`) | `0x21912 st.h r28,-0x1518,gp` (`64e7e8ea`) inside helper `FUN_000218fe`, called from `0x55b12`(normal)/`0x55b3c`(fault) |
| 1 | 7:0 | Signal-A lo byte (BE16) | same as byte0 | same instr (halfword store) |
| 2 | 7:0 | Signal-C hi byte (BE16) | `((s16)(gp-0x69ea))>>3` if `|raw*0.125| <= 1500.0` (float range check, own independent gate, NOT tied to EPS-state byte), else `0x7FFF` | `0x21932 st.h r28,-0x1516,gp` (`64e7eaea`) inside helper `FUN_0002191e`, called `0x55b76` |
| 3 | 7:0 | Signal-C lo byte (BE16) | same as byte2 | same instr |
| 4 | 7:3 | **NEVER WRITTEN — SPARE (5 bits, mask 0xF8)** | — | no store touches these bits anywhere in the builder (confirmed: masks used are `0xfb`/`0xfd`/`0xfe`, never touch bits 7:3) |
| 4 | 2 | status bit (always set, not fault-gated) | bit0 of `*(byte)(gp-0x6799)` | `0x55ac0 st.b r8,-0x1514,gp` (`4447ecea`) |
| 4 | 1 | status bit (fault-gated) | bit0 of `*(byte)(gp-0x679b)` normal; **forced 0** if EPS-state==8 | normal: `0x55ae8 st.b r6,-0x1514,gp` (`4437ecea`); fault: `0x55b20 clr1 1,0x6aec,r18` (`d28fec6a`, absolute-addressed form, independently confirms bit index 1) |
| 4 | 0 | status bit (fault-gated) | bit0 of `*(byte)(gp-0x679a)` normal; **forced 0** if EPS-state==8 | normal: `0x55b06 st.b r15,-0x1514,gp` (`447fecea`); fault: `0x55b30 clr1 0,0x6aec,r18` (`d287ec6a`) |
| 5 | 7:0 | Signal-B hi byte (BE16) | `*(s16)(gp-0x69ee)` normal, `0x7FFF` if EPS-state==8 | `0x21964 st.w r14,-0x1514,gp` (`6477edea`) inside helper `FUN_0002193e` (masked 32-bit RMW over buf+4..+7, only bytes 5/6 change — mask `0xff0000ff` preserves byte4 and byte7), called `0x55b44` |
| 6 | 7:0 | Signal-B lo byte (BE16) | same as byte5 | same instr |
| 7 | 7:6 | **NEVER WRITTEN — SPARE (2 bits, mask 0xC0)** | — | masks used on this byte are `0xcf` (preserve 7:6+3:0) and `0xf0` (preserve 7:4); bits 7:6 never cleared/set |
| 7 | 5:4 | 2-bit redundancy-voted rolling sub-counter | derived from shared external counter `gp-0xf47` (`(cnt&7)+1)&3`), cross-checked between `gp-0x4c4c`/`gp-0x685d` via fault comparator `FUN_0006b9fa` on mismatch | `0x55c02 st.b r8,-0x1511,gp` (`4447efea`) |
| 7 | 3:0 | checksum/rolling-counter nibble (Honda standard) | return value of `FUN_00057b24(buffer,8,0x14A)` | `0x55c2a st.b r6,-0x1511,gp` (`4437efea`) |

## SPARE BIT BUDGET
**7 total free bits, in two locations, both never written by any instruction in `FUN_00055a98`:**
- **Byte 4, bits 7:3** (mask `0xF8`) — 5 contiguous bits (upper nibble + bit3).
- **Byte 7, bits 7:6** (mask `0xC0`) — 2 contiguous bits (top 2 bits of the byte).

Not a single free byte — the widest contiguous run is 5 bits in byte4's top nibble. A piggyback needing
a full byte will not fit without touching a real signal/checksum bit; a piggyback needing ≤5 bits fits
cleanly in byte4 bits7:3 (equal-length in-place swap candidate: the `andi 0xfb/0xfd/0xfe` + `st.b` triplet
at `0x55aac-0x55b06`, or the `clr1`/`movhi` fault-path forms at `0x55b1c-0x55b34`, same shape as the V31T
0x660 piggyback's `st.b r0,disp[gp]` swap).

## Fault-gating mechanism (EPS-state == 8)
`cVar1 = *(char *)(gp-0x67fa); if (cVar1 == 8) { ...sentinel path... }` — `gp-0x67fa` is the
already-documented EPS state byte (`reference_accord_consistency_monitor_hardshutdown.md`: "Set to 8 for
hard shutdown"). When the EPS is in hard-shutdown state, this builder overrides Signal-A (byte0:1) and
Signal-B (byte5:6) to sentinel `0x7FFF`, and force-clears byte4 bits1:0. Signal-C (byte2:3) is NOT gated by
this flag — it has its own independent magnitude-based invalidation (`|raw*0.125| > 1500.0` -> `0x7FFF`).
Byte4 bit2 (source `gp-0x6799`) is also NOT fault-gated — set unconditionally before the branch.

## Open / unresolved (new this session, not found anywhere else in the repo — grepped, zero other hits)
- **`gp-0x69ea` / `gp-0x69ec` / `gp-0x69ee`** — three adjacent 16-bit signal sources (2 bytes apart,
  consecutive halfwords in RAM) feeding this message's three data signals. Sent out of source-address
  order (buffer layout is 69ec, 69ea, 69ee — not sequential), suggesting a deliberate CAN signal map
  rather than a raw struct copy. **Semantic identity (what physical signal each represents) is NOT
  resolved** — no other memory file or doc in this repo references these offsets. Given the neighborhood
  (gp-0x69xx/0x6bxx is otherwise SteerTorque/angle/rate territory per `reference_accord_gp6af8_fight_trigger.md`,
  `reference_accord_gp6b4c_lane_chain.md`), these are plausibly torque/angle-family signals, but this is
  INFERENCE, not evidence — flag for a future session to trace backward from these three addresses.
- **`gp-0x6799` / `gp-0x679a` / `gp-0x679b`** — three adjacent single-bit status sources, sitting 1-3
  bytes above the documented engage-state byte `gp-0x679c` (`reference_accord_telemetry_ram_hook_a160.md`).
  Plausibly companion sub-state/validity flags in the same struct as engage-state, but **not confirmed** —
  no direct writer trace was done this session (read-only per mission scope).
- **Whether byte4 bits7:3 / byte7 bits7:6 are truly dead, or written by some OTHER function via the same
  gp-relative displacement** (`-0x1514[gp]` / `-0x1511[gp]` resolve to the SAME absolute address
  0xFEDF6AEC/0xFEDF6AEF regardless of which function issues the store). This session verified (a) Ghidra's
  own xref DB shows zero writers to `DAT_fedf6aec` outside `FUN_00055a98` (only picks up the absolute
  `movhi+clr1` form, not gp-relative loads generally) and (b) prior Segment D's exhaustive 1-MiB
  buffer-pointer-array scan found this buffer belongs solely to table-A idx10 (this one message) — but did
  **not** do a fresh whole-image grep for the literal displacements `-0x1514`/`-0x1511` against `gp` this
  session. **Before using these bits as a live piggyback, run that grep** (same method as
  `reference_accord_can_tx_mailbox_index_map.md`'s disp22/literal-scan technique) to rule out a stray writer.

## Cross-references
- `reference_accord_can_tx_segmentD_known_frame_provenance.md` — located this builder/buffer via the
  `movea ID,r0,r8` fingerprint scan; did not disassemble the body. This document supersedes that gap for
  0x14A specifically.
- `reference_accord_consistency_monitor_hardshutdown.md` — source of the `gp-0x67fa==8` EPS-state
  identification used here.
- `reference_accord_can_tx_mailbox_index_map.md` — the "redundancy pair + `FUN_0006b9fa` voter" pattern
  seen at byte7 bits5:4 matches the same shape documented for other gp-relative pairs (`gp-0x6cc4`/shadow
  `gp-0x4d0c`, etc.) elsewhere in this codebase — a recurring idiom, not unique to this message.
