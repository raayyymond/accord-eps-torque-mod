---
name: reference-accord-v22-float-monitor-2x-cave
description: V22 Accord build — doubles the integer NEGATIVE envelope (gp-0x3578) plus the float watchdog's upper/lower raw bounds via a verified code cave, so FUN_00043e44 stops throwing CAN fault 0x3f1b in the doubled-envelope regime
metadata:
  type: reference
---

# V22 — symmetric negative-envelope 2× + float-monitor 2× match (code cave)

Builder: `analysis-2020accord/builds/v18_v49/build_v22_tva.py` (copied from `builds/v18_v49/build_v21_tva.py`).
Output: `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V22-LKAS-2x-EMEfix-symNEGenv-floatmon2x-PNfix-0x13000-0x100000.rwd`.
BUILT + Ghidra-verified on the built image, **UNFLASHED** (study artifact; kit iron rule).

## Why V22 exists (the load-bearing chain)

The float watchdog `FUN_00043e44` (REPORT-ONLY; see [[reference-accord-override-snap-state-machines]])
**cross-checks the integer shaper's runtime outputs** `gp-0x6af6 / 6b00 / 6b0a / 6b98` — all
written by `s_motor_torque_rate_shaper` (FUN_00042af8) in two twin snapshot clusters at
`0x43a72–0x43b52` and `0x43dec–0x43e38`. Those signals now carry the **doubled** envelope
(V21 `shl 0x8→0x9` on `gp-0x3574`; V22 adds the same on `gp-0x3578`). Flags f1/f3/f6 compare
them against the float path's own recomputed envelope (tolerance `movhi 0x3ba0` = 5/1024 ≈
0.0049 @ `0x4463e`). If the float path stays stock while the integer envelope doubles, the
flags diverge → escalate → **fault 0x3f1b fires** in the high-torque regime the mod is for.
So the float monitor MUST double its own envelope to stay in lock-step. (The doc's earlier
"monitor stays stock = correct" was right only when command rides UNDER the envelope.)

No clean cal/in-place lever exists for the float side: the envelope base term shares the
universal `r1 = 1/1024` const (`movhi 0x3a80,r0,r1` @ `0x43efe`, reused for velocity, X-axis,
IIR alpha, AND the integer-ref scaling in the comparisons) and the runtime `gp-0x6444` table
(shared with the integer path, integrity-shadowed at `gp-0x4bf8`; built by FUN_00039702→
FUN_000389ec from live demand, additive cals `tp+0x7564`/`tp+0x7578` are ZERO, so it's a
guarded runtime filter state, not a scalable table). The only faithful 2× is to scale
`upper_raw`(r10) and `lower_raw`(r12) directly, after both are finalized and before any
consumption (IIR at `0x4427e`/`0x442b0`). That point is `0x44230`. Two `mulf.s` = 8 bytes,
can't fit in place → minimal single-instruction redirect into a code cave.

## The three V22 edits (on top of V21)

1. **Integer NEGATIVE envelope gp-0x3578 2×** — `0x42F16` `shl 0x8,r10 → shl 0x9,r10`
   (`c8 52 → c9 52`). ONE byte covers both IIR and bypass: the `shl` fires BEFORE the
   `be 0x42f40` branch chain (`0x42f1a/1e/22`), value rides in r9 → `ld.w -0x3578,gp,r9`
   @ `0x42f24`, consumed at `0x43142 sar 0x8,r9` (lower-bound twin of the upper bound's
   `0x43136`). Mirror of V21's `gp-0x3574` upper-bound pair at `0x42DAE`/`0x42DCA`.

2 & 3. **Float upper_raw + lower_raw 2× via redirect + cave.**
   - Redirect (4 B, in place, no shift): `0x44230` `ld.hu -0x6966,gp,r7 (e4 3f 9b 96)` →
     `jr 0xC4FC0 (88 07 90 0d)`.
   - Cave (20 B in free 0xFF padding at `0xC4FC0`, inside main CRC block, before block
     descriptor at `0xC4FF0`):
     ```
     0xC4FC0  movhi 0x4000,r0,r7    40 3e 00 40   ; r7 = 2.0f
     0xC4FC4  mulf.s r7,r10,r10     e7 57 64 54   ; upper_raw *= 2
     0xC4FC8  mulf.s r7,r12,r12     e7 67 64 64   ; lower_raw *= 2
     0xC4FCC  ld.hu -0x6966,gp,r7   e4 3f 9b 96   ; displaced original
     0xC4FD0  jr 0x44234            b7 07 64 f2   ; return to next instr
     ```
   - Control flow verified on the BUILT image: all THREE entry paths into `0x44230` reach the
     redirect — fall-through from `0x4422C addf.s r12,r8,r12`, plus `br 0x44230` at `0x441D4`
     (`e5 2d`) and `0x441F8` (`c5 1d`), both unchanged. r10/r12 live at `0x44230` on every
     path, not consumed until `0x4427e`/`0x442b0` (after the cave). r7 is the only scratch;
     the displaced `ld.hu` reloads it. Neighbors `0x4422C` and `0x44234` byte-identical (no shift).

## Verified V850 encodings (cross-checked against in-image instructions)

- `jr disp22`: hw0 = `0x0780 | disp[21:16]`, hw1 = `disp[15:0]` (LE halfwords). Refs:
  `0x40 jr 0x244 = 80 07 04 02`; `0x234 jr 0x1e0 = bf 07 ac ff` (neg). 0x44230→0xC4FC0
  (disp +0x80D90) = `88 07 90 0d`; 0xC4FD0→0x44234 (disp −0x80D9C) = `b7 07 64 f2`.
- `movhi 0x4000,r0,r7 = 40 3e 00 40` (vs `movhi 0x3f80,r0,r10 = 40 56 80 3f` @0x445f4).
- `mulf.s r7,r10,r10 = e7 57 64 54`; `mulf.s r7,r12,r12 = e7 67 64 64`
  (vs `mulf.s r17,r8,r10 = f1 47 64 54` @0x4317a; FP subop field preserved).
- `shl imm`: low byte `c8`(imm5=8)→`c9`(imm5=9); `[15:11]=reg2,[10:5]=0x16,[4:0]=imm5`.

## Build integrity (all green)

cipher round-trips (ECU-decode==patched); BOTH CRCs recomputed and bootloader CRC walk passes
all 49 blocks (incl. main `[0x13000,0xC4FFC)` covering the cave). Byte-diff = 42 B in 13 runs.
Ghidra disassembly of the imported built image (`../accord-firmware/analysis-2020accord/_v22_plain_image.bin`) confirms every edit
decodes correctly and the cave is defined code.

## Method note for next time

This is the FIRST Accord build to use a code cave (V11–V21 were cal-only or in-place byte flips).
`GHIDRA_MCP_ALLOW_SCRIPTS` was unset, so Ghidra could NOT assemble — encodings were hand-derived
and cross-checked against real in-image instructions, then verified by importing the built image
and disassembling. To assemble via Ghidra directly, restart the MCP server with
`GHIDRA_MCP_ALLOW_SCRIPTS=1`. Free `0xFF` cave space confirmed at `0xC4FC0–0xC4FEF`.

## See also

[[reference-accord-override-snap-state-machines]] (FUN_00043e44 REPORT-ONLY watchdog, fault 0x3f1b)
[[reference-accord-lerp3-gp3574-chain]] (upper-bound integer envelope chain; gp-0x3578 is its lower-bound twin)
[[project-accord-torque-mod-v0]] (V14 flashed/works → V18 ramp-only → V19 SM rescale → V21/V22 envelope 2×)
[[reference-accord-eme-lever-semantics]]
