---
name: accord-feedback-operand-is-a-two-sample-sum-dc-30-89
description: The LKAS rate PID's feedback operand r26 at 0x29d78 is s_old + s_new of the lag filter (add r9,r26 @0x28FA4), DC gain 2*1560/101 = 30.89 per raw count of gp-0x6a56 -- NOT 15.45. This reconciles the two inherited figures (8 counts/deg/s on 0x18F, 22.3 deg/s stock reference ceiling) that a single-state reading made contradict each other. Two agents in one session misread the add as an increment.
metadata:
  type: reference
---

# The feedback operand is a TWO-SAMPLE SUM, DC gain 30.89 -- 2026-09-01 [EVIDENCE, orchestrator-verified]

```
0x28f7c  ld.w -0x3d30,gp,r26     ; r26 = s_old
0x28fa2  add  r7,r9              ; r9  = s_new = (923*s_old>>10) + (1560*x>>10)
0x28fa4  add  r9,r26             ; r26 = s_old + s_new        <-- the sum
0x28fa8  st.w r9,-0x3d30,gp      ; state = s_new
0x28fa6..fbc  clamp r26 to +-0xC62E6 (stored x256: 7680 = 30x256)
0x29d78  sub  r26,r16            ; E = 32*setpoint - r26
```
DC gain of r26 = 2 x 1560/(1024-923) = **30.89** per raw count of `gp-0x6a56`. The 0x18F wire is `-gp-0x6a56` at 1:1
(no scale in FUN_000218de), and the wire is 8 counts/deg/s (measured, corr 0.997), so **stock's ceiling crossover is
5504/30.89 = 178 wire = 22.3 deg/s** -- exactly the inherited stock reference ceiling. Both inherited figures were right.

**Why:** `osc-units` and `adv278a` both traced this block and both reported 15.45, reading `add r9,r26` as
"state_old + delta" -- but r9 IS the new state (it is what gets stored), so r26 is old+new. One instruction,
factor of two, and every K-sizing threshold moved with it. The orchestrator verified it by disassembly.

**How to apply:** any threshold expressed in "operand counts" converts to the 0x18F wire at /30.89, and to deg/s
at a further /8. The crossover at the map ceiling for scale K is 178*K wire = 22.3*K deg/s. See
[[accord-v276-mechanism-is-a-matter-of-degree]] and [[accord-sign-e-alone-cannot-measure-damping]].
