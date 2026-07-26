---
name: reference-c6664-lerp-b-envelope
description: Cal 0xC6664 is LERP_B envelope modifier in FUN_00043e44, NOT a float corridor twin — instruction-verified
metadata:
  type: reference
---

## Verdict: Hypothesis B confirmed. 0xC6664 = LERP_B envelope term.

**[V] = instruction-verified** from Ghidra decompile of _v24_plain_image.bin.

### Table structure at 0xC6644/0xC6648/0xC6664

- N=7 at 0xC6644 (raw: `07000000`)
- X breakpoints at 0xC6648: [-7,-6,-5,0,5,6,7] f32 (confirmed from raw bytes)
- Y values at 0xC6664: all 1.0 f32 (stock) (`0000803f` × 7)
- tp=0xBF000 so `DAT_00007648+tp = 0xC6648`, `DAT_00007664+tp = 0xC6664`. Confirmed.

### What 0xC6664 feeds in FUN_00043e44 (0x43e44)

Decompile shows:
```c
fVar17 = *(float *)(&DAT_00007648 + unaff_tp);   // X base for LERP_B
pfVar20 = (float *)(&DAT_00007664 + unaff_tp);    // Y base for LERP_B
// ... LERP interpolation on fVar8 (clamped velocity) produces fVar17 = lerp_b_output
*(float *)(unaff_gp + -0x65a0) = (float)*(ushort *)(unaff_gp + -0x6444) * 0.0009765625 + fVar17 * fVar7;
// and inside the loop:
*(float *)(iVar11 + unaff_gp + -0x65a4) = (float)uVar4 * 0.0009765625 + fVar17 * fVar7;
```

`fVar17` = LERP_B output (from 0xC6664 table), `fVar7` = LERP_A output (from 0xC65D4/0xC65F0 table).
Product `fVar17 * fVar7` is ADDED into the float envelope Y-array at `gp-0x65a0` and `gp-0x65a4+offset`.

### What 0xC6664 does NOT feed

**[V]** The inline-check-A at 0x43172–0x431c0 in FUN_00042af8 reads `gp-0x6db0` and `gp-0x6db8` (NOT 0xC6664).
Exact instructions:
- `0x43172: ld.w -0x6db0[gp],r8`
- `0x43176: movhi 0x4480,r0,r17` (= 1024.0)
- `0x4317a: mulf.s r17,r8,r10`
- `0x4317e: trncf.sw r10,r12`
- `0x43182: ld.h -0x6af6[gp],r6`
- `0x4318c: sub r6,r12`  → diff = int(1024*float) - int_wall
- Decompiler renders: `== -0x10` (sentinel value -16, NOT ±5 tolerance)

FUN_00043e44 writes `gp-0x6db4` (NOT `gp-0x6db0` or `gp-0x6db8`).
FUN_00043e44 runs AFTER FUN_00042af8 in FUN_0002214a schedule (position 0x24 vs 0x23).

### Hypothesis A errors (instruction-by-instruction)

Hypothesis A claimed:
1. 0xC6664 LERP output is truncated to int and compared ±5 against gp-0x6af6/gp-0x6b00.
   **[V WRONG]**: The inline-check-A at 0x43172 reads `gp-0x6db0/gp-0x6db8` (DIFFERENT RAM slots),
   and the check is `== -0x10` (sentinel -16), not `|diff| <= 5`.
2. The ±5 check IS present in FUN_00042af8 at 0x43a48, but it compares `gp-0x6b04` vs corridor
   walls `gp-0x6af6 ± 5` and `gp-0x6b00 ± 5` — no float twin involved.
3. The cited `addi 0x5 / cmp 0xb` instructions exist at 0x4329e/0x432a2 but compare `gp-0x6dc0`
   vs `gp-0x6b0a`, a completely different pairing.

### What gp-0x6db0/gp-0x6db8 are

**[I]** These float slots are written by a sibling function upstream of FUN_00042af8.
FUN_00043e44 writes `gp-0x6db4` (4 bytes away) — a related slot (velocity clamp before LERP_B).
The `gp-0x6db0/gp-0x6db8` floats are the float corridor twins for the lockstep check,
but they come from a DIFFERENT source (not 0xC6664). Their writer was not resolved in this session
(searched FUN_00042af8, FUN_00043e44, FUN_00045a20, FUN_000456a4, FUN_0004595a, FUN_0004503c,
FUN_000428d4, FUN_00044cf0 — none write them).

**Why this matters for V26 edits:** Doubling 0xC6664 Y-values from 1.0→2.0 changes LERP_B output,
which scales the envelope product `fVar17*fVar7` added to gp-0x65a0/gp-0x65a4 array.
It does NOT directly change the float twin compared against gp-0x6af6/gp-0x6b00 at 0x43172.
