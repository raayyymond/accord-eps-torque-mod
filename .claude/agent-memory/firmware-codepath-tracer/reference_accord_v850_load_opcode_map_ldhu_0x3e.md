---
name: reference-accord-v850-load-opcode-map-ldhu-0x3e
description: Complete V850E2 disp16 load/store opcode map -- ld.hu is 0x3E/0x3F, not 0x3C/0x3D; a ld.bu-only decoder returns FALSE ZEROS on cal readers
metadata:
  type: reference
---

🛑★★★★★ **A hand-rolled disp16 scanner that knows `ld.bu` but not `ld.hu` returns a FALSE ZERO on
every halfword calibration cell.** Hit on 2026-09-01: my first census of `0xC62E6` (the LKAS
feedback clamp) reported **0 readers**; the true answer is **3**, all `ld.hu 0x72e6,tp,rN`
(`0x28F96`, `0x28F9C`, `0x28FB8`). Cal cells are halfwords, so `ld.hu` is the form that reads them.

THE COMPLETE MAP — hw1 bits [10:5] = opcode, [4:0] = reg1 (gp = r4, tp = r5), [15:11] = reg2:
| op | mnemonic | displacement |
|---|---|---|
| 0x38 | `ld.b`  | `hw2` (all 16 bits) |
| 0x39 | `ld.h` (hw2 bit0 = 0) / `ld.w` (bit0 = 1) | `hw2 & 0xFFFE` |
| 0x3A | `st.b`  | `hw2` |
| 0x3B | `st.h` / `st.w` (hw2 bit0) | `hw2 & 0xFFFE` |
| 0x3C / 0x3D | `ld.bu` | `(hw2 & 0xFFFE) | ((hw1 >> 5) & 1)` — **hw1 bit5 carries disp bit0** |
| 0x3E / 0x3F | `ld.hu` | `hw2 & 0xFFFE` |

So `ld.bu` at an odd displacement is opcode 0x3D; `ld.h` CANNOT reach an odd displacement at all.
Verified against real instances: `0x37BB4` = `a4 37 b9 98` -> gp-0x6747, `0x55DD8` = `a4 37 a5 97`
-> gp-0x685B, `0x28F96` = `e5 6f e7 72` -> `ld.hu tp+0x72E6,r13`.

Also worth keeping — the Format-V `jarl`/`jr` decoder, self-checked against `jarl 0x49A5A` at
`0x55DF4` (`bf ff 66 3c`): `(hw1 >> 6) & 0x1F == 0x1E`; `disp = ((hw1 & 0x3F) << 16) | (hw2 &
0xFFFE)`, sign-extended from 22 bits; target = site + disp; `reg2 != 0` means `jarl`, `0` means `jr`.
And the 48-bit `mov imm32, reg1` is hw1 op = 0x31 with **reg2 == 0**, imm32 following — this is the
register-indirect address-materialisation form that operand-text search is blind to, and it is how
every bank base (0xCBA04 etc.) is loaded.

THE 6-BYTE EXTENDED-DISPLACEMENT gp-relative FORM (disp16 scans miss it): hw1 bits0-4 = reg1,
bits5-10 in {0x3C,0x3D}, bits11-15 = 0; reg3 = hw2>>11; disp[6:0] = (hw2>>4)&0x7F; disp[22:7] = hw3;
sign-extend from 23 bits. **Positive-control every scanner on `ld.h -0x4f60,gp,r6` = `84 07 07 32 61
ff`** (present at 0x59BFA and 0x5A0BC) before trusting a null. There are ~4,934 such sites image-wide.

**Every "zero readers" null this kit recorded with a ld.bu-only or disp16-only decoder should be
re-run.** Still blind after both forms: a base built by arithmetic on an unrelated register, and
`ep`-relative `sld`/`sst`.

Related: [[reference_accord_can427_packer_tap_field_full_decode]] · [[feedback_rigorous_validation]]
