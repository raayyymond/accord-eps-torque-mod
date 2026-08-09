---
name: reference_v850_gp_relative_opcode_field_map_validated
description: Validated V850E2 opcode-field map for 4-byte gp-relative load/store byte scans — ld.hu is field 0x3F and ld.w/st.w 0x3E; omitting them silently drops most reads (gp-0x6a5e went 2 readers -> 47 when fixed). Includes the ground-truth byte examples to re-validate any scan against
metadata:
  type: reference
---

Derived 2026-08-09 (`EXCITATION-TRACER`) after my own scan under-reported and I caught it by
cross-checking a Ghidra decompile that plainly showed a read my scan had missed.

## The decode

For a 4-byte gp-relative load/store, `hw1` (little-endian u16 at the instruction address):
```python
reg1 = hw1 & 0x1F          # base register; 4 = gp, 5 = tp
op   = (hw1 >> 5) & 0x3F   # opcode field
reg2 = (hw1 >> 11) & 0x1F  # data register
disp = struct.unpack_from('<h', b, addr+2)[0]   # signed 16-bit displacement in hw2
```

| op | mnemonic | notes |
|---|---|---|
| 0x38 | `ld.b` | |
| 0x39 | `ld.h` | |
| 0x3A | `st.b` | |
| 0x3B | `st.h` | |
| 0x3C | `ld.bu` (even disp) | disp bit 0 lives in **hw1 bit 5**, not hw2 |
| 0x3D | `ld.bu` (odd disp) | ⇒ two cells one apart sit on **opposite parities** |
| 0x3E | `ld.w` / `st.w` | |
| **0x3F** | **`ld.hu`** | **the one that gets forgotten** |

`ld.hu` / `ld.w` also carry the **`hw2 = disp | 1`** quirk — scan for **both** `disp` and `disp|1`.

## Ground truth to re-validate any scan against (stock `code.bin`)

```
0x431C4  244f3495   ld.h   -0x6acc, gp, r9     op=0x39
0x45932  64473495   st.h   r8, -0x6acc, gp     op=0x3B
0x3AD76  84570d98   ld.bu  -0x67f4, gp, r10    op=0x3C (even)
0x3AD88  a487fd63   ld.bu  0x63fd, gp, r16     op=0x3D (odd)
0x3AD7E  e40fa395   ld.hu  -0x6a5e, gp, r1     op=0x3F, disp 0x95A3 = (-0x6a5e & 0xFFFF) | 1
```

## Why it matters

Scanning with only `{0x38..0x3D}` reported **`gp-0x6a5e` (voted vehicle speed) as having 2 readers.**
With the full `{0x38..0x3F}` set it has **47** — including `FUN_00034a72` (boost), `FUN_0003a382` (PID)
and `FUN_0003ad74`, all of which materially changed a speed-gating conclusion. **Honda's code reads
u16 sensor cells with `ld.hu` far more often than `ld.h`**, so the missing entry is not a corner case.

⚠ Still not covered by this map: the **6-byte extended-disp23** form. A scan using this map is
"corroborated 2 ways", not certified.

## Related
[[reference_v850e2_extended_disp23_encoding_solved]] — the 6-byte form this map does NOT cover.
[[reference_accord_gp6b08_choke_point_and_shaper_consistency_monitor]] — census built with the full set.
