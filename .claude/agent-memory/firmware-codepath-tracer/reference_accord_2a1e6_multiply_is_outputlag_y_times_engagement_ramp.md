---
name: reference_accord_2a1e6_multiply_is_outputlag_y_times_engagement_ramp
description: The multiply at 0x2A1E6 in FUN_00028ea6 (mul r14,r9,r0 ; sar 0xf ; sxh) is y (the output-lag filter's own result, r9, last written at 0x2A1AC sar 0x5,r9) TIMES gp-0x69b0 (the engagement ramp, r14, Q15). It is NOT the rectified/quantized |fb| magnitude computed earlier at 0x28FC0-0x28FC6 (that feeds a DIFFERENT consumer, gp-0x6a34 -- see the sibling memory on that). Corrects GRIND1-LOOP-SHAPE-V287-2026-09-06.md's |q32(H_fb*rate)| reading for this site; confirms (for r14 only) five prior tracer memories calling it "the ramp".
metadata:
  type: reference
---

# `0x2A1E6` multiply = `y (output-lag result) × gp-0x69b0 (engagement ramp)` — settled by decompile

2026-09-08, subagent `tracer`, stock `code.bin`, `decompile_function` on `FUN_00028ea6` (lines 1224-1245
of the decompile) cross-checked against `search_instructions function:FUN_00028ea6 operand_pattern:"r9"`
(183 hits) and `operand_pattern:"r14"` (117 hits) to find the last write to each register before the
site. Produced settling a disagreement `loopshape` raised between `GRIND1-LOOP-SHAPE-V287-2026-09-06.md`
(headline 10 / A2 / B4, reading the site as `|q32(H_fb·rate)|` and striking the feedback pole as a gain
lever on that basis) and five tracer memories calling it "the engagement ramp".

## The decompile, verbatim (lines 1224-1245)

```c
iVar23 = ((int)sVar27 * *(int*)(gp-0x3d3c) >> 10) + ((int)(iVar23*(uint)uVar25) >> 10);  // output-lag s_new
iVar31 = *(int*)(gp-0x3d3c) + iVar23;   // s_old + s_new
iVar34 = iVar31 >> 5;                    // y  <-- r9's value at the multiply
*(int*)(gp-0x3d3c) = iVar23;             // state := s_new
if ((cVar15=='\x01') && (gp-0x6806=='\0')) {   // DISENGAGED-ONLY branch
    ... a deadband/sign test on y using gp-0x6b30 ...
    if (<condition>) { iVar23 = 0; goto LAB_0002a1ee; }   // skips the multiply, matches asm 0x2A1E2/0x2A1E4
}
iVar23 = (int)(short)((int)(iVar34 * uVar18) >> 0xf);   // 0x2A1E6: y * ramp, >>15, sign-extended
```

`uVar18` is the SAME variable reloaded from `gp-0x69b0` throughout the function's long engagement-ramp
state machine (41 `ld.hu`/`st.h` hits on that exact cell in this function, `0x2936A`-`0x29714`). `iVar34`
is confirmed `y`: `0x2A1AC sar 0x5,r9` (the output-lag filter's own final shift) is the LAST write to `r9`
before `0x2A1E6` on the engaged path — the disengaged-only deadband branch, when it fires, sets `r9→0`
and branches AROUND `0x2A1E6` entirely (`0x2A1E2 mov 0x0,r9 ; 0x2A1E4 br 0x2A1EE`).

## Why the V287 doc's reading was wrong

The rectified/quantized `|floor32(fb)|` value (computed at `0x28FC0`-`0x28FC6`: `sar 0x5,r16 ; shl
0x5,r16 ; bp ; subr r0,r16`) is a COMPLETELY DIFFERENT, EARLIER computation in the same function. It does
NOT feed this multiply. Its actual consumer is `gp-0x6a34` — see
[[reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane]]. The two computations happen to be
close together in the disassembly (within ~0x28FC0-0x28FDE) and both derive from the feedback filter's
clamped sum, which likely caused the conflation.

## Decision-bearing consequence

Moving the output-lag pole (`0xC63EC`/`0xC63EE`) changes `y` directly, which changes what the
engagement ramp scales at this site. **The output-lag pole and this multiply are coupled on the engaged
path** — a pole move is not isolable from this stage. See [[reference_accord_lkas_pid_filter_form_two_sample_sum_and_oscillation_detector]]
for the pole's own arithmetic and DC/phase figures.

Full trace: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`, ADDENDUM Q0.
