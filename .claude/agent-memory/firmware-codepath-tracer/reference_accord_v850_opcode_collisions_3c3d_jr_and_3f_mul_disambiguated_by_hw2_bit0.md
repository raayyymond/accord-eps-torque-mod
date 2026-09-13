---
name: reference_accord_v850_opcode_collisions_3c3d_jr_and_3f_mul_disambiguated_by_hw2_bit0
description: "Two V850E2 opcode-field collisions this kit's scanner memories do not record -- 0x3C/0x3D is shared by Format-V jr/jarl AND the 6-byte extended-disp23 load, and 0x3F is shared by ld.hu, mul and setfcc. BOTH are disambiguated by hw2 bit 0 (loads = 1, jr/mul/setf = 0). A DECODER without these rules reads jr as a load and mul as ld.hu, which is exactly how a phantom 'reader' gets invented."
metadata:
  type: reference
---

Found 2026-09-13 during the V291 adversarial pass (surface D, agent `advD`), by validating a
hand-written decoder against Ghidra's own 60-instruction listing of `0x28F12-0x28FC2`. The decoder
scored 56/60 on length before the fix and **60/60 after**. Every mismatch was one of these two.

## 1. Opcode field `0x3C`/`0x3D`: Format-V `jr`/`jarl` **collides with** the 6-byte extended load

Both have `hw1 = 0x0780 | reg1` with `hw1` bits[15:11] = 0. **The bit patterns are identical.**

| | `hw2` bit 0 | example |
|---|---|---|
| `jr` / `jarl` disp22 | **0** (branch targets are halfword-aligned) | `0x28F3C` = `80 07 74 01` -> `jr 0x290B0` |
| 6-byte extended-disp23 load | **1** (it is a sub-opcode field) | `0x59BFA` = `84 07 07 32 61 ff` -> `ld.h -0x4f60,gp,r6` |

⇒ **Disambiguate on `hw2 & 1`.** This is the same underlying fact as the kit's recorded
"`prepare` collides with jr/jarl -- filter on TARGET PARITY" trap
([[reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans]]), but stated from the
*load* side, which that memory does not cover.

## 2. Opcode field `0x3F`: `ld.hu` **collides with** `mul` and `setfcc`

| | `hw2` | example |
|---|---|---|
| `ld.hu disp16[reg1],reg2` | **bit 0 = 1** always | `0x28F86` = `e5 87 eb 73` -> `ld.hu 0x73ea,tp,r16` |
| `mul reg1,reg2,reg3` | `0x0220` | `0x28F8E` = `f0 3f 20 02` -> `mul r16,r7,r0` |
| `setfcc reg2` | `< 0x0020` (cond in low nibble) | `0x28F16` = `e9 ef 00 00` -> `setfnc r29` |

🛑 **The documented `disp|1` quirk is NOT optional decoration -- it is the opcode discriminator.**
[[reference_v850_gp_relative_opcode_field_map_validated]] and
[[reference_accord_v850_load_opcode_map_ldhu_0x3e]] both say "scan for both `disp` and `disp|1`",
which is right for a SCAN; neither says a bare `hw2` is not an `ld.hu` at all.

## 3. Why it matters, and the discipline that caught it

**Over-matching is SAFE for a null** (a scan that also matches `mul` still finds every real `ld.hu`,
so "zero readers" survives). **Under-matching and mis-DECODING are not.** A decoder without rule 2
renders `mul r16,r7,r0` as `ld.hu 0x220[r16],r7` -- a completely fictitious cal read at a
completely fictitious address. On the V291 pass my own over-matching scan produced 3 false
"overlapping accesses" on the edited cells (`0x29D9C`, `0x2AC8E` -> really `0xC63E6`; `0x3AB5E` ->
really `0xC6444`), all resolved by rule 2.

⭐ **The method that caught both: validate the decoder against a Ghidra listing you did not write,
counting LENGTH agreement instruction-for-instruction.** A mnemonic mismatch is easy to rationalise;
a length mismatch cannot be, because it desynchronises everything after it. Cheap control:
`disassemble_bytes(0x28F10, 0x28FC4, dry_run:true)` on `code.bin` gives 60 instructions with bytes,
and covers `ld.b`/`ld.h`/`ld.w`/`st.w`/`ld.bu`/`ld.hu`/`jr`/`mul`/`setf`/`sar`/`shl`/`movea`/`ori`/
`andi`/`addi` plus both 2- and 4-byte forms.

Related: [[reference_accord_fb_lag_filter_bytes_and_gate1_private]] (the same listing, decoded),
[[reference_accord_operand_text_search_false_positive_wrong_base_register]].
