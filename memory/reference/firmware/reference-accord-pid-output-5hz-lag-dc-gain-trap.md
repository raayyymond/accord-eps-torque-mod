---
name: reference-accord-pid-output-5hz-lag-dc-gain-trap
description: FUN_00028ea6's PID-output lag (0xC63EC=992/0xC63EE=507) is a single-pole IIR y[n]=(992*y[n-1]+507*x[n])>>10 with DC gain 507/32=15.84 -- NOT unity -- so the pole coefficient `a` sets BOTH the corner frequency AND the forward gain simultaneously; moving the corner without moving the gain requires holding b/(1024-a) constant at 15.84375.
metadata:
  type: reference
---

# The LKAS PID-output lag: exact coefficients, corner, and the DC-gain trap

Freshly disassembled 2026-09-01 (GhidraMCP, stock `code.bin`, `0x2a172-0x2a1b4`), while adjudicating
the operator's driver-torque-feedback-loop hypothesis for V276/V277.

## The recursion, decoded instruction-by-instruction

```
0002a174  ld.hu  0x73ee, tp, r7      ; b = tp+0x73EE = 0xC63EE = 507
0002a178  ld.w   -0x3d3c, gp, r9     ; y_old = state (gp-0x3d3c, full word)
0002a180  mul    r7, r12, r0         ; r12 = x_new(=r12, the CLAMPED PID mixer sum gp-0x6b2e) * b
0002a184  ld.h   0x73ec, tp, r7      ; a = tp+0x73EC = 0xC63EC = 992  (sign-extended load, positive so no effect)
0002a194  mul    r9, r7, r0          ; r7 = y_old * a
0002a1a0  sar    0xa, r12            ; r12 = (x_new * b) >> 10
0002a1a6  sar    0xa, r7             ; r7  = (y_old * a) >> 10
0002a1a8  add    r12, r7             ; r7  = y_new = (x_new*b + y_old*a) >> 10   [note: split-shift, NOT (sum)>>10]
0002a1b0  st.w   r7, -0x3d3c, gp     ; state updated with y_new
```

**Exact form**: `y[n] = ((992*y[n-1])>>10) + ((507*x[n])>>10)` -- computed as two SEPARATE `>>10`
shifts then added, not `(992*y[n-1] + 507*x[n]) >> 10` as a single shift. For the coefficient values
in play here the two are numerically close but NOT bit-identical (the split form loses up to 1 LSB of
rounding relative to the combined form) -- **use the split form if reproducing this exactly in a
model.**

`r12` (the input `x[n]`) is the CLAMPED mixer sum `gp-0x6b2e` (clamp `0xC61BE`=15360) computed just
above this span from `(I>>7) + P + D`. The normal-path flow into this code is via `0x2a174`, reached
from the sum-clamp block at `0x2a13e-0x2a174`; `0x2a172` (`mov 0x0,r12`) is a FAULT/reset arm reached
only from the `0x2a164` block, not the normal path -- do not mistake it for the recursion's real input.

## Corner frequency

Pole = `a/1024` = `992/1024` = 0.96875. At the kit's established 1 kHz task rate for `FUN_00028ea6`
(🛑 **BELIEF — inherited kit convention for this function's task rate, not re-timed this session**):

```
tau = -Ts / ln(pole) = -0.001 / ln(0.96875) ≈ 0.0315 s
fc  = 1 / (2*pi*tau) ≈ 5.05 Hz
```

This independently reproduces the V276/V277 build scripts' inline comment "5 Hz output LPF" from the
raw coefficients alone -- EVIDENCE, cross-checked against an independent source.

## 🛑 THE DC-GAIN TRAP -- read before touching either cal

This filter's DC gain is **`b / (1024 - a)` = `507 / 32` = **15.84375**, NOT 1.** That means:

1. **`a` alone does not set the corner** -- `a` and `b` TOGETHER set both the corner AND the forward
   gain. Moving `a` to shift the corner frequency, without also moving `b` to hold `b/(1024-a)`
   constant, will silently change the gain of this stage by an arbitrary factor.
2. **This is a forward-gain multiplier sitting INSIDE the LKAS torque path**, between the PID mixer
   sum and the engagement-ramp multiply (`gp-0x6b30`). A future build that "just retunes the pole for
   a different corner" without preserving `507/32` will change delivered torque magnitude as a
   side-effect, not just filter dynamics -- exactly the kind of coupled-cal trap this kit has been
   burned by before (compare the sign-extension and clamp-pairing traps already on record in
   `docs/BUILD-LINEAGE.md`).
3. To move the corner while holding gain fixed: pick new `a'`, then solve
   `b' = round(15.84375 * (1024 - a'))`.

## Where it sits in the loop

This is the ONE real dynamic (memory-carrying) element the firmware puts inside the driver-torque
feedback loop the operator hypothesized for V276's 2-4 Hz oscillation -- everything upstream of it
(the raw sensor read, both driver-torque gates) is memoryless (see
[[reference-accord-gp4f60-no-producer-filter-raw-sensor]],
[[reference-accord-second-driver-torque-gate-cbae4-cbbc4]]). A single real pole at ~5 Hz contributes
only ≈22° phase lag at 2 Hz and ≈38° at 4 Hz -- not enough on its own to close 180° of loop phase for
sustained 2-4 Hz oscillation. The remaining phase almost certainly comes from the mechanical plant
(column/rack/tire inertia, torsion-bar stiffness+damping) -- unmeasurable from firmware, BELIEF only.

## Related
[[reference-accord-gp4f60-no-producer-filter-raw-sensor]]
[[reference-accord-second-driver-torque-gate-cbae4-cbbc4]]
