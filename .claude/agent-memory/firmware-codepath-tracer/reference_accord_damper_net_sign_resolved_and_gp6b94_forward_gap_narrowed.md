---
name: reference_accord_damper_net_sign_resolved_and_gp6b94_forward_gap_narrowed
description: Damper (gp-0x6bd0) net sign to gp-0x6b94 is DISSIPATIVE-by-construction (verified both paths, decompile+disasm); the gp-0x6b94->motor forward hop is narrowed but still open -- the governor's real external input (gp-0x6afe) is proven to come from an unrelated Sensor-B lane, NOT from gp-0x6b94/gp-0x6ace.
metadata:
  type: reference
---

Session 2026-08-07 (post-V80 grinding investigation). Answers the operator's "what is the net sign of
the damper at the motor" question as far as evidence allows. GhidraMCP only, code.bin (stock).

## gp-0x6abe identity -- CLOSED (was open)
[EVIDENCE, decompile FUN_00041464 @0x41464] gp-0x6abe is the SIGNED, filtered form of the SAME
underlying quantity gp-0x6ac0 rectifies. Both derive from `uVar16`, an IIR-filtered (tp+0x743c),
Q10-scaled version of raw cell gp-0x4f50 (root already flagged in
[[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]] as shared with gp-0x6c2c).
At 0x41b56 (bVar2==false branch, i.e. |gp-0x4f50|<=~13000): `gp-0x6abe = (short)(uVar16>>10)` (SIGNED)
vs `gp-0x6ac0 = (short)(|uVar16|>>10)` (RECTIFIED). This is the EXACT pair the existing model called
"gp-0x6ac0 is a RECTIFIED filtered motor rate" -- gp-0x6abe is its signed twin. gp-0x4f50 is therefore
signed motor rate (or a quantity extremely close to it) at the model's own naming convention.

## gp-0x6bd0's sign is dissipative-by-construction -- CONFIRMED at instruction level
FUN_00034350, disassembly:
```
00034604: ld.h -0x6abe[gp],r11      ; r11 = gp-0x6abe (signed filtered motor rate)
...
00034698: mulu r16,r8,r0            ; r8 = product of FactorB*FactorC*FactorE*FactorD*seed (magnitude)
0003469c: shr 0xa,r8                ; >>10
0003469e: cmp r0,r11                ; compare gp-0x6abe to 0
000346a0: ble 0x000346a4            ; skip negate if gp-0x6abe <= 0
000346a2: subr r0,r8                ; r8 = -r8   (ONLY when gp-0x6abe > 0)
```
So sign(gp-0x6bd0 pre-clamp) = -sign(gp-0x6abe) whenever gp-0x6abe != 0 -- textbook `force = -sign(velocity)`.
Then symmetric clamp to ceiling LERP(gp-0x6ac2) at 0x34720-0x34766 (verified: st.h -0x6bd0[gp] at
0x34730/0x34744 for the two clamp rails, 0x34752 for pass-through).

## Path-2 net sign gp-0x6bd0 -> gp-0x6ad4: NON-INVERTING (surprising -- two negations cancel)
Walked FUN_00038148 (Stage1+Stage2), FUN_00037fe6 ("unity adder"), FUN_0003a382 (PID) by decompile.
- FUN_00038148 term5: `gp-0x6bd0 * gate * cal(tp+0x73a0=0xC63A0, =1024 stock, byte-read [0,4]) >> 10`,
  POSITIVE weight, summed with 5 siblings into S. S is then `* polarity(gp-0x6752) * innerWeight(>=0,
  ushort) >> 10 * 0x10`, IIR-lowpassed (tp+0x73ac) into state gp-0x374c (=iVar4). Then **Stage 2**:
  `iVar6 = gp-0x6bfe - (iVar4>>4) + gated(gp-0x6bfa)`, and `gp-0x6b70 = sign(iVar6)*LERP(|iVar6|-derived)`
  clamped. Net local sign gp-0x6bd0->gp-0x6b70 (holding gp-0x6bfe fixed) = **-polarity(gp-0x6752)**
  (one subtraction inverts the polarity-scaled forward term).
- FUN_00037fe6: gp-0x6b70 term has weight byte-read **1** at tp+0x74b0 (confirmed
  `read_memory(0xC64AD,7) = 01 01 01 01 01 01 01` for ALL 7 term weights tp+0x74ad..0x74b3 -- genuinely
  unity, no polarity multiplier anywhere in this function). Net sign gp-0x6b70->gp-0x6ad6 = **+1**.
- FUN_0003a382 (PID): `feedback=clamp(gp-0x6ad6,+-tp+0x7200)`, `err=clamp(gp-0x4f60-feedback,+-0x2800)`
  (confirmed: `iVar30 = gp-0x4f60 - uVar24`). Net sign gp-0x6ad6->err = **-1** (in the linear region).
  P/I/D lane gains (uVar20,uVar16,uVar12) are all non-negative ushort LERP outputs; anti-windup clamps
  the I lane to a non-negative-derived envelope but never flips sign. Final:
  `gp-0x6ad4 = ((D+I+P)>>5) * LERP(gp-0x671a,>=0) >>10 * polarity(gp-0x6752)`, clamped to authority.
  Net sign err->gp-0x6ad4 = **+polarity(gp-0x6752)**.
- **Compose**: (-P) * (+1) * (-1) * (+P) = **P^2 = +1, independent of P.** The Stage-2 subtraction and
  the PID's error subtraction cancel each other; the two polarity(gp-0x6752) multiplications ALSO cancel
  (regardless of steering side). ⇒ **Path 2's net sign gp-0x6bd0 -> gp-0x6ad4 is POSITIVE (non-inverting)**,
  holding gp-0x6bfe fixed for the instantaneous/forward-hop analysis (does not require solving the
  re-entry loop's gain, since gp-0x6bfe is exogenous within this same tick -- see below).

## Path 1 (bare) and Path 2 (via PID) REINFORCE, not cancel, at the aggregator
FUN_0003aa2c decompile, live (else) branch: `iVar19 = ... + gp-0x6ad4*(gate) + ... + gp-0x6bd0*(gate) + ...`
-- BOTH gp-0x6bd0 (Path 1, bare) and gp-0x6ad4 (Path 2 output) enter the SAME summation with literal
UNITY weight (no scale, no sign flip beyond the range gate). Combined with Path 2's net-positive
transfer above: **gp-0x6bd0's sign survives UNCHANGED into gp-0x6b94 via BOTH routes, and they add
rather than partially cancel.**

## VERDICT on the sign question, at gp-0x6b94
[EVIDENCE] The damper's contribution to gp-0x6b94 (the aggregator's raw sum) has
**sign = -sign(gp-0x6abe) = -sign(signed filtered motor rate)** -- i.e. it is **DISSIPATIVE BY
CONSTRUCTION at gp-0x6b94**: it opposes the direction the motor/resolver is turning. This holds through
BOTH the direct (Path 1) and PID-mediated (Path 2, via 0xC63A0) routes, and the two do not cancel.

## The gp-0x6b94 -> motor forward hop: STILL NOT FOUND, but narrowed and re-confirmed as a real gap
All 4 candidate readers of gp-0x6b94 resolved:
- **FUN_00036bec** -- sign-preserving 1st-order lag: `gp-0x6b48 = IIR(gp-0x6b94*0x40)>>6`. gp-0x6b48's
  only real readers are FUN_00036682 (ld.hu) and FUN_00036828 (ld.h). FUN_00036682 is called BY
  FUN_0003aa2c itself (`iVar14 = FUN_00036682(); iVar14 = iVar14 + iVar19;` before the gp-0x6b94 store)
  -- **this is an INTERNAL feedback loop inside the aggregator's own next-tick computation, not an exit
  to the motor.**
- **FUN_0004503c** -- clamps gp-0x6b94 via math-helper `FUN_00049a90` (median/double-bound clamp, decompiled,
  sign-preserving except at the rails) against a bound built from `gp-0x4f64` (the already-documented
  governor ceiling, [[reference_accord_gp4f64_three_consumers]]) -> writes **gp-0x6ace** (lockstep
  int/shadow pair). A state==4 branch can override gp-0x6ace with a separate cell gp-0x138a via a
  magnitude comparison (detail not fully chased -- not sign-relevant to this question).
- **FUN_0004595a** -- a CONSISTENCY MONITOR: computes `|gp-0x6b94| - |gp-0x6ace|` and the PRODUCT
  `gp-0x6b94*gp-0x6ace` (both Q10-descaled via float), writes gp-0x6aca/gp-0x6d9c/gp-0x68cc. Matches
  the existing [[reference_accord_consistency_monitor_hardshutdown]] entry -- not a forward path.
- **FUN_0007ff08** -- UNRELATED. A large DTC/diagnostic state machine (FUN_0005b2be/FUN_0006ff00 calls);
  touches gp-0x6b94 only as `== 0` in one branch condition. Not a torque-path consumer.

gp-0x6ace's readers (35 raw hits from operand-substring search; 27 are FALSE POSITIVES -- `clr1`/`tst1`/
`set1` bit-test immediates against base register **r18** (unrelated struct), and one `jr 0x26ace` branch
target -- none of these are gp-relative accesses at all, confirmed by inspecting the mnemonic+base-reg
triplet, not just the substring). The real gp-relative hits are: internal reads/writes inside
FUN_0004503c itself, plus **FUN_000456a4** and **FUN_00045a20** -- both ALREADY DOCUMENTED as
hard-shutdown "comp-term" monitors feeding DTC 0x1d
([[reference_accord_fun45a20_monitor_and_shadow_lockstep_pairs]],
[[reference_accord_fun456a4_signed_term_and_fun45a20_mismatch_refuted]]). **No other reader of gp-0x6ace
was found.**

**The obvious bridge candidate was chased and RULED OUT**: [[reference_accord_gp6b94_agg_governor_gap]]
(prior open item) named FUN_00042af8 as the function that writes gp-0x6b98 (the final motor command,
per the model), running on `gp-0x6afe / gp-0x6b08 / gp-0x4f64` rather than gp-0x6b94. This session traced
both:
- **gp-0x6b08** has exactly ONE writer (`st.h r11,-0x6b08,gp` @0x43206), and it is INSIDE FUN_00042af8
  itself -- self-referential/ramp state, not an external forward-path input.
- **gp-0x6afe** has exactly ONE writer, `FUN_00042ac6` @0x42ac6 (a one-sided clamp: pass-through unless
  `param_1+0x2800 > 0x5000` i.e. `param_1>0x2800`, in which case sentinel 0x7fff). Its SOLE caller is
  **FUN_00026c80** (confirmed via `get_function_callers`). Decompiled in full: FUN_00026c80 is an
  **independent 11-slot Sensor-B torque-coil vote/consistency state machine** (keyed on gp-0x67fa state
  codes 1-7, gated `*(char*)(unaff_tp+0x5118+i)`), and the value it passes to `FUN_00042ac6` at its tail
  (`FUN_00042ac6((int)sVar38)`) is **the SAME clamped sum** it ALSO stores to **gp-0x6b4e**
  (`sVar38 = clamp(iVar11, +-0x2800)`, where iVar11 is a slot-sum). gp-0x6b4e is itself one of
  FUN_00038148's OWN six summed terms (term1, sibling to the damper's term5) -- i.e. it is a genuinely
  PARALLEL Sensor-B lane, not gp-0x6b94-derived. **FUN_00026c80 runs BEFORE the aggregator in the same
  tick** (per the master dispatcher FUN_0002214a's call order: FUN_00026c80 -> ... -> FUN_00038148 ->
  FUN_00037fe6 -> FUN_0003a382 -> FUN_0003aa2c(aggregator, produces THIS tick's gp-0x6b94) ->
  FUN_0004503c/FUN_0004595a/FUN_000456a4/FUN_00045a20/**FUN_00042af8**/FUN_00043e44, all under the SAME
  `if ((uVar2 & 0xd30) != 0)` gate), so it is temporally impossible for gp-0x6afe to be derived from
  THIS tick's gp-0x6b94 even if an undiscovered link existed.

⇒ **[EVIDENCE, with the caveats below] Neither of FUN_00042af8's two documented external inputs
(gp-0x6afe, gp-0x6b08) derives from gp-0x6b94 or gp-0x6ace.** The damper's contribution, having reached
gp-0x6b94 with a confirmed dissipative sign, has NO CONFIRMED FORWARD PATH to gp-0x6b98 (the final motor
command) through anything found in this session or the prior one. All 4 gp-0x6b94 readers and gp-0x6ace's
real readers terminate in an internal feedback loop, a governor clamp with no further forward reader
found, or hard-shutdown/consistency MONITORS -- none is confirmed to influence the delivered torque.

**This is in tension with the observed physical effect** (V72->V80 dose response on grinding severity is
real and reproducible on-car), which argues SOME forward path must exist. Two explanations, neither
confirmed:
(a) the forward path is real but uses an encoding/addressing form this pass didn't sweep -- extended-disp
    gp/tp-relative (6-byte form), ep-relative, or a register-indirect/pointer-table access, none of which
    a `search_instructions` operand-substring scan over ALREADY-ANALYSED instructions is guaranteed to
    catch if the target region is unanalyzed (skill's documented blind spot); or
(b) the damper's on-car effect is NOT via a torque-command forward path at all, but via its influence on
    one of the hard-shutdown/consistency monitors it feeds (FUN_0004595a / FUN_000456a4 / FUN_00045a20,
    all downstream of gp-0x6b94/gp-0x6ace) -- e.g. destabilizing a monitor into a fault/DTC state that
    itself produces an audible symptom through fault-handling behavior, not through delivered current.
    [BELIEF -- not evidenced this session, and "grinding" reads more like a real torque oscillation than
    a fault-handling artifact, so (a) is the better-supported guess, but neither is confirmed.]

## What would settle it
1. A raw Python LE byte scan of code.bin for the 6-byte extended-disp encoding of gp-0x6ace / gp-0x6b94
   / gp-0x6afe / gp-0x6b08 (the skill's mandated second method for a load-bearing null), to rule out
   tool undercounting definitively.
2. `analyze_dataflow` or `get_bulk_xrefs` from gp-0x6ace/gp-0x6b94 (not yet tried this session) as an
   independent corroborating method to the operand-substring scan.
3. Decompile FUN_00042af8 in full (not done this session -- the model's characterization "runs on
   gp-0x6afe/gp-0x6b08/gp-0x4f64, never references gp-0x6b94" was taken from an EARLIER session's
   finding, not re-verified here) to confirm it truly has no third input.
4. Confirm gp-0x6b98 is still the correct "final FOC motor command" identity for THIS build/session
   (last independently verified per [[reference_accord_below_gp6b98_foc_delivery_path_swept]]).

## Cross-refs
[[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] (existing gp-0x6abe/6ac0 work -- this
session adds the exact producer instruction and confirms the shared-root claim at decompile level).
[[reference_accord_consistency_monitor_hardshutdown]], [[reference_accord_fun45a20_monitor_and_shadow_lockstep_pairs]],
[[reference_accord_gp4f64_three_consumers]], [[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]].
