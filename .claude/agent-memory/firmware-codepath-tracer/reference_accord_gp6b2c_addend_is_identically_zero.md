---
name: accord-gp6b2c-addend-is-identically-zero
description: The addend r11 at 0x2A1FC in FUN_00028ea6 is (short)[gp-0x6b2c] on all 11 paths, and gp-0x6b2c is IDENTICALLY ZERO in stock and V282 (Y table 0xC673E-44 all zeros AND the r29 gate forces the above-range branch) - so gp-0x6b38 = clamp(-K6*r9>>15) with NO bar-torque feedthrough
metadata:
  type: reference
---

# `st.h r1,-0x6b38,gp` @0x2A23C: the addend is ZERO, not driver torque

**EVIDENCE, method: Ghidra `decompile_function`/`disassemble_function` on stock `code.bin`
(FUN_00028ea6, body 0x28EA6..0x2A30A — Ghidra ends it at the `dispose` at 0x2A30A, NOT 0x2A400),
plus raw little-endian byte reads of `code.bin` and the V282 plain image.**

## r11 at 0x2A1FC == `(short)[gp-0x6b2c]`, invariantly

Every path into 0x2A1FC passes the join at **0x29A48**. All 11 writers of r11 that dominate the
join leave r11 == the halfword cell `gp-0x6b2c`:

| addr | write | class |
|---|---|---|
| 0x297EA/EC | `sxh r11` then `st.h r11,-0x6b2c` | fresh 4-knot LERP |
| 0x2994A/4C | same | fresh LERP |
| 0x29A12/14 | same | fresh LERP |
| 0x29846, 0x2995C, 0x29A22 | `ld.h -0x6b2c,gp,r11` | reload of the cell |
| 0x29882 -> 0x2988A `subr r0,r11` -> 0x2988E st | negate-and-store | sign flip |
| 0x297FE, 0x29826, 0x298D6, 0x29986, 0x29A42 | `mov 0x0,r11` (paired with `st.h r0,-0x6b2c`) | zero |

Between 0x29A44 and 0x2A1FC there is **no r11 write and no `jarl`** (760 instructions) — r11
survives the whole rate-PID/lag block untouched. Only one branch enters [0x2A1EE,0x2A1FC]:
`0x2A1E4: br 0x0002a1ee`.

Branch selector for the block is `gp-0x3d37` (read 0x29734): 0 or >3 -> zero path 0x29A28;
1 -> 0x29752; 2 -> 0x29964; 3 -> 0x29808 (which re-dispatches on `gp-0x3d36` = 0/1/2).

## And `gp-0x6b2c` is identically ZERO — two independent reasons

1. **The LERP Y table is all zeros.** Base `movea 0x7734,tp` = **0xC6734**. X knots 0xC6736/38/3A/3C
   = `0, 31872, 31936, 32000`; Y values 0xC673E/40/42/44 = **`0, 0, 0, 0`** in BOTH stock and V282.
   Byte-read from the images. Interpolating a flat-zero table yields 0 on every branch, and the
   two out-of-range branches load 0xC673E and 0xC6744, also 0.
2. **The gate makes it moot anyway.** `r29` (0x28F0E-0x28F16: `ld.hu -0x6a5e,gp,r10` /
   `addi -0x7d01,r10,r0` / `setfnc r29`) = `[gp-0x6a5e] >= 32001`. The LERP is only reached when
   `r29 != 0` (tested at 0x2976A / 0x29810 / 0x29970), i.e. x >= 32001 > the top X knot 32000, so
   the above-range branch `ld.hu 0x7744[tp],r11` (= [0xC6744] = 0) always fires. r29 is written
   only at 0x28F16 / 0x28F1C, both before the block, and never again (grep of the full listing).

**=> `gp-0x6b38 = clamp(±[tp+0x71b4], (-K6 * r9) >> 15)`. The addend contributes nothing.**

## Not driver torque

`gp-0x4f60` (cached bar torque x1.024) is read **exactly twice** in the function:
- **0x28F26** `ld.h -0x4f60,gp,r15` -> a magnitude *band check* (`addi 0x6400,r15,r8`), into r15.
- **0x29A90** `ld.h -0x4f60,gp,r12` -> used ONLY as a **sign test** (`cmp r0,r12` + `blt`/`bge`) to
  pick between cal bank pairs {0xCBA74, 0xCB924} and {0xCBA04, 0xCB8B4}. Magnitude discarded.

Ghidra's `iVar28` conflates r15, an r10 return value and r11 into one decompiler variable — that is
what makes it *look* like `gp-0x4f60` reaches 0x2A1FC. On the machine, r11 never holds it.

## What the block actually is (BELIEF, mechanics are EVIDENCE)

A state machine (`gp-0x3d37` states 1/2/3, direction `gp-0x3d36`, cycle counter `gp-0x6756` vs
byte cal 0xC64DE, tick counter `gp-0x6a7e` vs 0xC6288=300 / 0xC628A=408) that emits a
sign-alternating amplitude from the 0xC6734 LERP, gated by `gp-0x6809 == 1` and r29. That shape —
amplitude table, period cals, repetition count, periodic negation — reads as a **haptic /
vibration-alert waveform generator** (LDW buzz). Calibrated OFF (zero amplitude) in this part number.

## Numbers (V282 vs stock)

`0xC646C` K6 = 891 both · `0xC6CD0` = **-1 stock / 5346 V282** (V282's only edit inside the function
is the 2 bytes at 0x2A1F0-F1, repointing `ld.h 0x746c,tp,r7` -> `ld.h 0x7cd0,tp,r7`) · `0xC61B4`
clamp = 512 stock / 3072 V282. **5346/891 = 6.000 and 3072/512 = 6.000 exactly**, so the clamp knee
referred to r9 is identical in both builds: it binds at |r9| > 18,830.

No overflow at 0x2A1FE: |r9| <= 32768 after `sxh` @0x2A1EC, so |-5346 * r9| <= 1.752e8, 12.3x under
INT32_MAX. Even a hypothetical full-scale r11 gives |r11+r9| <= 65535, 65535 * 32767 = 2.147e9,
still inside int32 — the multiply is structurally overflow-free for any 16-bit signed K6.

WARNING, latent: 0x2A204 compares against `ld.hu 0x71b4[tp]` (zero-extended) but 0x2A20C installs
`ld.h 0x71b4[tp]` (sign-extended). Harmless at 3072; a clamp cal > 32767 would install a NEGATIVE
positive limit. Same defect class as 0xC61BE in
[[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]].

See also [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]],
[[reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe]],
[[reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers]].
