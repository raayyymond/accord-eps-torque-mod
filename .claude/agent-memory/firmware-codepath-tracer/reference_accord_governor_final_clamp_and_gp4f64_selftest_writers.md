---
name: reference_accord_governor_final_clamp_and_gp4f64_selftest_writers
description: "Governor FUN_0004503c fully re-derived at instruction level (0x453e0-0x45604): a SECOND Q15 scale + a THIRD Q15 step-authority beyond the previously-documented bound clamp, and the precise asymmetric-slew rule (step-limited only moving AWAY from zero in target's sign; toward-zero/sign-crossing snaps instantly). The final summation site is FUN_00042af8:0x43ae0-0x43b34 (gp-0x6afe + shaper output, re-clamped against the SAME gp-0x4f64 a second time, then hard +/-0x2000, -> gp-0x6b98). CRITICAL NEW: gp-0x4f64 has two more external readers, FUN_0006e09a/FUN_0006e140 (dispatch-table-invoked, 0xbcb14/0xbcb18), a self-test/BIT state-machine pair that writes gp-0x6b98 DIRECTLY (bypassing the whole aggregator/governor/shaper chain), scaled by gp-0x4f64 * cal(0xC7C3C=168), gated by cal(0xC7C22)=14 ticks. Trigger conditions NOT resolved -- top safety open item for any 0xC520C/gp-0x4f64 lever."
metadata:
  type: reference
---

# Governor final form + the final-summation clamp site + gp-0x4f64's self-test writers

Traced 2026-08-26 (`ratecap` task, "what caps max steering rate"), decompile+disasm of `FUN_0004503c`
and `FUN_00042af8` on `code.bin`, cross-checked against `reference_accord_gp6ac0_rectify_after_iir_and_governor_bound_census`
and `reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale` (both confirmed, this entry
EXTENDS them, does not replace them).

## 1. [EVIDENCE] Governor `FUN_0004503c` has THREE Q15 authority lanes, not one

Raw disasm 0x453e0-0x45604 (full listing quoted in the 2026-08-26 session transcript):

```python
bound   = (auth_bound  * gp_4f64) >> 15     # 0x453f4/f8; jarl FUN_00049a90 @0x453fe is a 3-ARG clamp
clamped = clamp(gp_6b94, -bound, +bound)    # (Ghidra's decompiler drops the 3rd arg on this call --
                                             #  confirmed AGAIN this session, same defect as before)
target  = (auth_scale2 * clamped) >> 15     # 0x45402/0a -- a SECOND Q15 scale, NOT in the prior memory
step    = (auth_step * cal_512_or_205) >> 15  # 0x4541a/1e; cal 0xC6206=512 (<16.6km/h) / 0xC6208=205
```

`auth_bound`/`auth_scale2`/`auth_step` are three related Q15 lanes from the same multi-lane min-chain
family as the documented 993ms/33-ct-per-tick authority ramp (`0xC6492`/`0xC6316`~10km/h gate). **At
full authority (post ~1s engagement ramp, no active derate) all three = 0x8000 unity**, collapsing to
the single formula already on record: `bound=gp-0x4f64`, `step=512or205`. What individually gates
`auth_scale2` vs `auth_step` (vs the documented `auth_bound` ramp) is NOT resolved -- likely
speed/fault-derate siblings of the same family; open, not blocking (steady-state numbers unaffected).

## 2. [EVIDENCE] The precise asymmetric-slew rule, instruction-exact

```
prev = gp_138a  (persistent state)
# reset-to-zero ONLY on a genuine sign crossing between target and prev (0x45426-0x45436):
if sign(target) != sign(prev) and not (target==0 and prev>=0): prev = 0
if target <= prev:                      # DECREASE (or equal) case
    new = target if target >= 0 else (clamp toward target by step, i.e. min magnitude move)
else:                                    # INCREASE case, target > prev
    new = target if target <= 0 else (ramp toward target by step, capped at target)
```
Net: **the step limiter binds ONLY when output magnitude is increasing in target's own sign direction.**
Any move that decreases magnitude, crosses zero, or reduces toward a non-positive/non-negative target
SNAPS INSTANTLY, no step limit. This is the exact form of the previously-recorded "toward zero
unlimited, away limited," now nailed to the instruction, plus the not-previously-documented instant
zero-snap on a sign flip.

## 3. [EVIDENCE] The final summation site — resolves "sum @ 0x43af4" precisely

`FUN_00042af8` (the SHAPER — confirmed by cross-reference: it's also `gp-0x4f64` reader #1 in the
fresh access census below), disasm 0x43ac0-0x43b34:

```python
term = validity_gate(gp_6afe, +-0x2800)      # 0x43ae0-af0; gp-0x6afe itself set by the TRIVIAL wrapper
                                              # FUN_00042ac6: gp-0x6afe = clamp_or_0x7fff_sentinel(param_1, +-0x2800)
sum_ = term + uVar34                          # 0x43af4  <-- THE EXACT INSTRUCTION THE ORCHESTRATOR NAMED
sum_ = clamp(sum_, +-((gp_4f64_or_0 * ...)))  # 0x43ae4-0x43b0a -- RE-CLAMPS AGAINST gp-0x4f64, A SECOND
                                              #   TIME (first clamp was inside the governor, section 1)
sum_ = clamp(sum_, -0x2000, +0x2000)          # 0x43b0e-0x43b20 -- hard, non-adaptive clamp
# -> unit-scale (movhi 0x4480,r0,r17 = 1024.0f; mulf.s; trncf.sw) -> gp-0x6b98
```
`uVar34` is the shaper's SM2/SM3-integrator-blended aggregator/governor output (already documented in
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]]). **`gp-0x4f64`'s rate-adaptive ceiling is applied
TWICE in series on the same signal** (once inside the governor on `gp-0x6b94`, again here on
`gp-0x6afe + uVar34`) — raising it moves both clamp sites at once, by construction (same cal cell).

## 4. 🛑🛑 [EVIDENCE, NEW] `gp-0x4f64` has two dispatch-table SELF-TEST writers of `gp-0x6b98`

Full-image `search_instructions -0x4f64`: **11 accesses** (3R+3W internal to `FUN_0007b022`, the sole
writer, matches prior census) **+ 5 EXTERNAL reads**: `FUN_00042af8`(shaper, above), `FUN_00043e44`("M2"),
`FUN_0004503c`(governor, section 1), and **two not previously documented**: `FUN_0006e09a`@0x6e0f2 and
`FUN_0006e140`@0x6e1ca.

Both are entries in a function-pointer table at **`0xbcb14`/`0xbcb18`** (`get_xrefs_to` on each function
address returns exactly `From 0000bcb14/18 [DATA]` — a jump/dispatch table, not a static call; consistent
with `get_function_callers` returning null for both, a register-indirect-dispatch blind spot, not a
static-analysis gap I could close this session). Both decompile as small state machines
(`param_1`=state index, persistent state `gp-0x2902`/`gp-0x2904`, elapsed-tick compare against
**`cal(0xC7C22)=14`**) that, on the "still within timeout" branch, **write `gp-0x6b98` DIRECTLY**:

```c
*(short *)(gp - 0x6b98) = *(short *)(gp - 0x4f64) * *(short *)(tp + 0x7c3c);   // cal 0xC7C3C = 168
*(short *)(gp - 0x4ce2) = *(short *)(gp - 0x4f64) * sVar1;                     // a companion/mirror
```
**This bypasses the ENTIRE aggregator/governor/shaper/final-clamp chain in sections 1-3.** On the
"timeout" branch each calls fault-style handlers (`FUN_0006d18a(7,0)`, a flag write to `gp-0x4f42`,
and `FUN_0005b612(2,1)`) — the standard OK/NG shape of a BIT (built-in test) or POST routine.

**[BELIEF, structural inference only]** Read as an EPS actuator self-test — dispatch-table invocation,
timer+state pattern, fault path on timeout are the standard shape for this. **NOT confirmed: what
schedules this table (ignition-on only? periodic while driving?), or the units/scale of `cal(0xC7C3C)
=168`** applied to `gp-0x4f64`(up to 4762) with NO visible shift in the decompile — dimensionally this
warrants a fresh raw-disasm check before trusting either the magnitude or the gating.

⇒ **Any lever that raises `0xC520C`/`0xC5224`/`0xC6202` (i.e. raises `gp-0x4f64`'s ceiling) proportionally
raises WHATEVER TEST TORQUE THIS ROUTINE COMMANDS.** This is the single highest-priority verification
gap before dosing that table — resolve the dispatch trigger first (candidate next step: find what writes
to the `0xbcb14`/`0xbcb18` table's INDEX, or what calls through it — likely a boot/diagnostic scheduler
in the 0x6dxxx-0x6fxxx range given the neighbouring address).

## Related
[[reference_accord_rate_limits_c6194_partition_and_c520c_ceiling_scale]] — the table/index formula this
extends. [[reference_accord_gp6ac0_rectify_after_iir_and_governor_bound_census]] — the governor bound
and sole-writer census this refines (adds the 2 external readers + the 2nd/3rd Q15 lanes + the exact
slew rule). [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] — the shaper/blend chain feeding
`uVar34`. [[reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling]] — a separate
diagnostic-cluster thread found the same session, do not conflate.
