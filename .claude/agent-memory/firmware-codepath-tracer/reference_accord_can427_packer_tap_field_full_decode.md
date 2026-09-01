---
name: accord-can427-packer-tap-field-full-decode
description: Full decode of the CAN 0x1AB (427) transmit packer FUN_00055d80 — the kit's telemetry tap field is 10 bits (max 1023) spanning frame byte0[1:0]+byte1, wire = clamp(( |src| *5)>>3, lo, 1023); plus the ld.h/ld.bu odd-displacement encoding rule that makes odd gp cells unreachable by ld.h.
metadata:
  type: reference
---

**The 427 tap field, decoded end to end (EVIDENCE — GhidraMCP decompile + byte-verified encodings on `code.bin`).**

Packer = `FUN_00055d80` (body `0x55D80-0x55F2D`). Builds the **CAN 0x1AB = 427 decimal**, DLC 3,
buffer base `gp-0x13CC`, handed to `FUN_00057b24(gp-0x13cc, 3, 0x1ab)` at `0x55F04`.

Frame layout: byte0 = `gp-0x13CC`, byte1 = `gp-0x13CB`, byte2 = `gp-0x13CA`
(byte2 low nibble = Honda checksum, bits5:4 = rolling counter).

**The tap field is 10 BITS, ceiling 1023** — not 8. `FUN_00021864` splits it:
byte1 = `wire & 0xFF`, byte0 bits[1:0] = `wire >> 8`. Values ≤ 255 therefore land entirely in byte1.

Stock arithmetic chain (each line with its address):
```
0x55DF0  ld.h -0x6c18[gp],r6      src = (int16) mem16[gp-0x6C18]
0x55DF4  jarl 0x49a5a             FUN_00049a5a = abs()          (saturating at INT_MIN)
0x55DFE  jarl 0x49a78             FUN_00049a78 = min UNSIGNED   (vs r7 = 0xFFFF)
0x55E02  andi 0xffff,r10,r6
0x55E06  mul 0x5,r6,r0            *5      imm9 low5 in hw1 bits0-4, high4 in hw2 bits0-3
0x55E0A  movea 0x3ff,r0,r8        clamp HIGH bound = 1023
0x55E0E  mov 0x0,r7               clamp LOW  bound = 0
0x55E10  sar 0x3,r6               >>3
0x55E12  jarl 0x49a90             FUN_00049a90 = clamp, SIGNED (cmovgt/cmovlt/cmovge), lo/hi order-normalised
0x55E1A  jarl 0x21864             writes the 10-bit field into the frame
```
Stock wire = `min(1023, (|src|*5)>>3)` = `|src| * 0.625`.
`gp-0x6C18` = a first-order lag of `gp-0x4F74`, state `gp-0x2F60`, coeff `tp+0x73C6` = **`0xC63C6`**
(NOT `0xC73C6` — the off-by-0x1000 trap), written at `0x56458` in `FUN_00056420`.

🛑 **ld.h CANNOT ADDRESS AN ODD gp DISPLACEMENT.** `ld.h` and `ld.w` share opcode `111001`; bit0 of
the displacement halfword selects them (0 = ld.h, 1 = ld.w). Verified on `0x55DF0` bytes `24 37 e8 93`.
So repointing this `ld.h` at an odd cell silently becomes a **word load**.

**`ld.bu` odd-displacement encoding (byte-verified, three independent instances):**
`hw1 = (reg2<<11) | (opcode<<5) | reg1`, where **opcode = 0x3C for an EVEN disp, 0x3D for ODD**,
and **`hw2 = disp | 1` always**. Confirmed at `0x55DB8` (`-0x685a`, even, op 0x3C, hw2 `0x97A7` = disp|1),
`0x55DD8` (`-0x685b`, odd, op 0x3D, hw2 `0x97A5`), `0x2DBD0` (`-0x674d`, odd, op 0x3D).
⚠ **A raw byte scan that reads hw2 literally MIS-LABELS every even-disp `ld.bu` by +1.** Correct for
the opcode-LSB parity or the census is wrong. `st.b` (op 0x3A) uses the full disp16 with no such trick.

`ld.bu -0x674b[gp],r6` = bytes **`A4 37 B5 98`** (hw1 `0x37A4`, byte-identical to the hw1 already
present at `0x55DD8`).

**`gp-0x674B` census (Ghidra + raw Python scan, set-differenced, agreeing): 2 WRITERS, 0 READERS.**
Writers `0x29D14` (`st.b r22`, `FUN_00028ea6` — the live LKAS rate PID) and `0x2AC0A` (`st.b r23`,
`FUN_0002a93a` — the dead twin). Nothing reads it: a free publish cell, same pattern as
[[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]].
`gp-0x674C` is a DIFFERENT, live, variant-coded config byte (written `0x42716` in `FUN_00042692`
alongside the selector `gp-0x674E`; read at `0x2B630`, `0x2C24E`, `0x2C3EC`).

See also [[reference_accord_variant_record_table_0xcd012_full_dump]],
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]].
