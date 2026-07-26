---
name: reference-v24-fault-monitor-validation
description: V24 build fault monitor validation at max 2x LKAS torque command — all bits pass, accumulator=0.0 vs EME threshold 128.0
metadata:
  type: reference
---

## V24 Fault Monitor Validation (2026-06-02)

**Program:** `_v24_plain_image.bin`, V850:LE:32, image_base 0  
**Scenario:** Maximum 2x LKAS torque command (output clamp=1024), steady state  
**Analysis method:** Static disassembly arithmetic (V850 FP multi-function emulation not feasible via GhidraMCP for this multi-function state scenario; arithmetic verified by Python script)

### Patch verification (STATIC, from memory reads)

| Address | Bytes | Description |
|---------|-------|-------------|
| 0x42DAE | c94ae557 | shl 0x9 (was 0x8) upper IIR doubling |
| 0x42DCA | c95a645f | shl 0x9 upper IIR (second site) |
| 0x42F16 | c952e0a1 | shl 0x9 lower IIR doubling |
| tp+0x71b2/b4 (0xC61b2) | 0x0400 | Output clamp = 1024 (2x V18 patch) |
| tp+0x746c (0xC646c) | 0x06f6 | LKAS gain = 1782 (1782/1024 = 1.7402x) |
| 0xC4E00 | addf.s lp,lp,lp | Cave: doubles FP upper envelope |
| 0xC4E0C | addf.s r20,r20,r20 | Cave: doubles FP lower envelope |
| 0x4463e | movhi 0x3c70 | Bit 1/2 threshold = +15/1024 (was 5/1024) |
| 0x44646/0x4466a | movhi 0xbc70 | Bit 1/2 threshold = -15/1024 |
| 0x43190 | addi 0xf | Inline check A neutralized (adds 15) |
| 0x43196 | cmp -0x1 | Inline check A always-pass condition |

### Bit-by-bit result at max 2x command, steady state

| Bit | Weight | Check type | Threshold | Fires? | Diff | Margin |
|-----|--------|-----------|-----------|--------|------|--------|
| 1 | 1.0 | Envelope FP upper (widened) | +-15/1024 | NO | 0.0 | 15/1024 (full window) |
| 2 | 2.0 | Envelope FP lower (widened) | +-15/1024 | NO | 0.0 | 15/1024 (full window) |
| 4 | 4.0 | Command-domain STOCK | +-5/1024 | NO | ~0 | INFERRED/V18 validated |
| 8 | 8.0 | Command-domain STOCK | +-5/1024 | NO | ~0 | INFERRED/V18 validated |
| 16 | 16.0 | Structural/speed | N/A | NO | N/A | INFERRED |
| 32 | 32.0 | Command-domain STOCK | ~1.5e-4 | NO | ~0 | INFERRED/V18 validated |
| 64 | 64.0 | Structural | N/A | NO | N/A | INFERRED |

### Accumulator and EME decision

- Accumulator r7 at 0x44a2e = 0.0
- EME threshold r12 at 0x44a26 = 128.0 (movhi 0x4300 = 0x43000000)
- Decision bgt at 0x44a34: 0.0 > 128.0 = FALSE, NO EME
- jarl 0x000462e6 at 0x44a4c is NOT reached

### Inline check A (0x43172-0x431c0)

- v24_diff_upper = trunc(gp-0x6db0 * 1024) - gp-0x6af6 = 0
- v24_diff_lower = trunc(gp-0x6db8 * 1024) - gp-0x6b00 = 0
- After addi 0xf patch: (0+15)=15; cmp -0x1 unsigned always passes
- sp+0x18 = 0, sp+0x30 = 0, NO fault from check A

### Why bits 1&2 diff = 0 by design (self-cancellation proof)

Cave at 0xC4E00 doubles lp (FP upper env); shl 0x9 doubles gp-0x3574 which doubles
gp-0x6af6 (after sar 0x8). At steady state with LERP3_out = L:
  lp_cave = 2*(L/1024) = L/512
  r2 = float(2L)/1024 = L/512
  diff = 0

The 5->15/1024 widening is conservative margin on top of this exact cancellation.

### Caveats

- Bits 4, 8, 32 are STATIC inferences backed by V18 empirical driving validation
- Transient ramp-up not analyzed here (worst-case for bits 4/8/32)
- Full GhidraMCP emulation of multi-function V850 FP state not available
