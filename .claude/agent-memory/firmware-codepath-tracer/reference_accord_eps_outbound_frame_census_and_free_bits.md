---
name: accord-eps-outbound-frame-census-and-free-bits
description: All 7 EPS outbound CAN frame builders (IDs, DLCs, buffers, dispatch table 0xB72BC-0xB72D4) with the exact free/unwritten bit map of each — only 0x14A/0x18F/0x1AB cross the car gateway, and NONE of the three has a free contiguous byte, so a second full-byte telemetry tap does not exist without a cave.
metadata:
  type: reference
---

**The EPS's complete outbound frame set (EVIDENCE — decompiled every caller of the CAN-TX
`FUN_00057b24`; dispatch is a function-pointer table at `0xB72AC-0xB72D4`).**

| builder | ID | dec | DLC | buffer base | ptr slot |
|---|---|---|---|---|---|
| `FUN_00055a98` | 0x14A | 330 | 8 | `gp-0x1518` | 0xB72D4 |
| `FUN_00055c42` | 0x18F | 399 | 7 | `gp-0x1420` | 0xB72D0 |
| `FUN_00055d80` | 0x1AB | 427 | 3 | `gp-0x13CC` | 0xB72C8 |
| `FUN_00055f2e` | 0x19F | 415 | 6 | `gp-0x1438` | 0xB72CC |
| `FUN_0005605c` | 0x64D | 1613 | 5 | `gp-0x13F8` | 0xB72C0 |
| `FUN_000561b0` | 0x660 | 1632 | 8 | `gp-0x1510` | 0xB72BC |
| `FUN_000562b8` | 0x32E | 814 | 4 | `gp-0x13D0` | 0xB72C4 |

🛑 **`FUN_000561b0` (0x660) writes SEVEN payload bytes to literal zero** — a perfect telemetry canvas,
and it is a TRAP. **0x660 is gateway-filtered and never reaches the comma tap.** The kit already built
this exact repurpose (`analysis-2020accord/builds/telemetry/build_tier1_telem_tva.py`, 2026-07-08, same
in-place equal-length swaps in the zero-store slots) AND flashed the 5 Hz→100 Hz rearm; 0x660 was still
absent on-car. Only **0x14A / 0x18F / 0x1AB** cross. See `memory/MEMORY.md` →
`reference_accord_can_single_fcn0_external_gateway`. **Do not propose a 0x660/0x19F/0x32E/0x64D tap.**

**Free-bit map of the three gateway-crossing frames** (bits the builder never writes, or writes to a
hard zero). Byte n = `base - n` counting down; the checksum `FUN_00057b24` runs LAST so it auto-covers
any spare-bit write.
- **0x14A (330)** b0:b1, b2:b3, b5:b6 = live 16-bit signals (helpers `FUN_000218fe`/`0002191e`/`0002193e`
  — note `0002193e` masks `0xff0000ff`, so it writes b5:b6 only). **b4 bits[7:3] free (5)**, b7 bits[7:6] free (2).
- **0x18F (399)** b0:b1 = driver torque (`FUN_000218be`), b2:b3 = column rate (`FUN_000218de`) — both
  openpilot-read. **b4 bits[2:0] free (3)**, b5 bits[3:0] hard-zeroed + bits[7:6] unwritten (6, but SPLIT
  by live bits[5:4] = `gp-0x6880`), b6 bit[6] free (1).
- **0x1AB (427)** b1 = the 10-bit tap field's low byte. **b0 bits[6],[5],[2] free (3)**, b2 bit[7] free (1).

⇒ **~21 scattered free bits, and NOT ONE free contiguous byte.** A faithful 8-bit publish on a
gateway-crossing frame is impossible without displacing a live signal or using a cave.

**The way out: the 427 tap chain has ~20 bytes of dead slack.** With an unsigned-byte source, `abs()`
(`0x55DF4`), `mov r10,r6`, `ori 0xffff` , `min()` (`0x55DFE`) and `andi 0xffff` are all no-ops — enough
to load a SECOND cell and bit-pack two signals into the existing 10-bit field. See
[[reference_accord_can427_packer_tap_field_full_decode]] for the field decode.

**V850 encoder forms, all positive-controlled against real image bytes** (Format II `(reg2<<11)|(op<<5)|imm5`;
Format I `(reg2<<11)|(op<<5)|reg1`; Format VI `hw1=(reg2<<11)|(op<<5)|reg1, hw2=imm16`):
`shl`=0x16 · `sar`=0x15 · `shr`=0x14 · **`or`=0x08 (NOT 0x04 — my first guess was wrong and the control
caught it)** · `mov reg,reg`=0x00 · `mov imm5`=0x10 · `andi`=0x36 · `ori`=0x34 · `st.b`=0x3A (full disp16,
no |1 trick) · `ld.bu`=0x3C even / 0x3D odd with `hw2 = disp|1`.
**`jarl` disp22: `hw1 = (reg2<<11)|(0x1E<<6)|disp[21:16]`, `hw2 = disp[15:0]`** — i.e. the displacement
splits 6/16, NOT the 16/6 the manual's field order suggests; verified on four sites in `FUN_000561b0`.

`FUN_0001fa42`/`FUN_0001fa72` are a **nested interrupt-disable counter** (depth `gp-0x163c`, saved PSW
`gp-0x1638`) — an unmatched `fa72` underflows the counter and re-enables IRQs early. **Any in-place edit
that consumes a `jarl` slot must keep the di/ei pairing balanced.**
