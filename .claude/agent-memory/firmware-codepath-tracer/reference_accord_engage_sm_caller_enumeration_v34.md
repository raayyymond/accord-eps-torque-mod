---
name: reference-accord-engage-sm-caller-enumeration-v34
description: Whole-image enumeration of all 7 callers of FUN_00040d58 (Accord TVA-A160 engage-SM decider) with their r6 param values, confirming the V34 NOP patch (0x40de2 be-nop, 0x40e12 bh-nop) affects ONLY the 2 ENGAGED-context and 1 HOLDING-context callers, all inside one contiguous engage-SM cluster (0x40fda-0x41386). Also corrects a JARL22 bit-encoding formula error in reference_accord_gp6cc4_tracking_pipeline.md's Method box, and clarifies that state=4 is never persisted to the outer dispatcher state gp-0x67DC.
metadata:
  type: reference
---

# FUN_00040d58 full caller enumeration + V34 patch scope verification (2020 Accord TVA-A160)

Session 2026-07-03 (V34 mission: verify NOP at `0x40de2`/`0x40e12` only affects ENGAGED/HOLDING). All
findings below independently re-derived via radare2 `v850.gnu` on stock `code.bin`
(`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, gp=0xFEDF8000, tp=0xBF000).

## CORRECTION to the JARL22 byte-encoding formula in `reference_accord_gp6cc4_tracking_pipeline.md` [V]

That memory's Method box claims `disp = ((byte1 & 0x3F) << 16) | (byte2 | byte3<<8)`. **This is WRONG** — it
only coincidentally matched the one negative-displacement example tested. Re-derived and validated on 3
fresh (src,target,bytes) triples this session (0x40ddc→0x406ae, 0x40e08→0x49a5a, 0x3c666→0x3bcb2), including
one POSITIVE-displacement case that exposed the error:

**Correct formula:** `hi6 = byte0 & 0x3F` (NOT byte1), `lo16 = byte2 | (byte3<<8)`, `disp22 = (hi6<<16)|lo16`,
sign-extend from bit21 (subtract 0x400000 if bit21 set). Opcode signature: `byte0 & 0xC0 == 0x80`; for a
`jarl ...,lp` call, `byte1 == 0xFF` (reg2=31=lp folds to all-1s in that byte, empirically). A whole-image scan
requiring only `byte0` (top2 + hi6, 8 bits) and `byte2,byte3` (16 bits) to match — leaving byte1 free — gives
~0.03 expected coincidental hits over the 1MB image, i.e. safe for exhaustive target-address search.
**Flagging, not silently editing** the sibling memory per project convention — ask before overwriting.

## FUN_00040d58 — ALL 7 callers, whole-image exhaustive scan [V]

| call site | param (r6) | meaning |
|---|---|---|
| 0x41000 | 1 | ENGAGING |
| 0x410a2 | 2 | ENGAGED |
| 0x41156 | 4 | RE-ARM |
| 0x4119a | 1 | ENGAGING (2nd instance, different handler function) |
| 0x411f6 | 1 | ENGAGING (3rd instance) |
| 0x41280 | 2 | ENGAGED (2nd instance) |
| 0x41364 | 3 | HOLDING |

**All 7 sites are inside ONE contiguous engage-SM dispatcher block, 0x40fda–0x41386** (a sequence of small
`prepare{lp},0 ... dispose 0,{lp},lp` handler functions run seemingly every cycle, each internally gated by a
state/flag read, e.g. `ld.bu -5007[gp]` (gp-0x138F) and `ld.bu -26622[gp]` (gp-0x67FE) checks — this is a
DIFFERENT variable from the outer dispatcher state gp-0x67DC; not fully characterized this session). **No
caller outside this cluster passes param 2 or 3** — confirmed by exhaustive whole-image byte scan (not a
regional search), so mission item 1 is answered with full confidence: the V34 patch (inside the callee) is
scoped correctly.

**Two param=2 sites, not one** — prior memory (`reference_accord_lkas_engage_sm_disengage_trigger.md`, still
correct on its OWN narrower claim about the FIRST gate) only documented "the engaged handler `FUN_00041222`
calls it with param=2" — true for one of the two sites, but there is a SECOND param=2 call at 0x41280 inside
a different handler (starting ~0x41222, itself preceded by an unconditional `jarl FUN_000406ae,lp` consensus
check and a `FUN_00046ea6(13)` fault-report call). Since the ENGAGED/HOLDING branch selection inside
`FUN_00040d58` is purely by the literal r6 value (not by which caller invoked it), **both param=2 sites
execute the exact same code path (0x40dc6 onward) and are both neutralized identically by the V34 patch** —
this doesn't weaken V34's scoping claim, but the caller count is 2-not-1.

## FUN_00040d58 full body — re-derived fresh, confirms 0x40e1a is EXCLUSIVELY reached by the 2 target branches [V]

Full linear disasm 0x40d58–0x40efc. Dispatch: `zxb r6; cmp1,r6; mov0,r12(default);
bl→0x40d70(r6==0,clear+return); be→0x40d78(r6==1 ENGAGING); cmp3,r6; bl→0x40dc6(r6==2 ENGAGED);
be→0x40dea(r6==3 HOLDING); cmp4,r6; be→0x40e1e(r6==4 RE-ARM)`.

Grepped the ENTIRE function disasm for the string `0x00040e1a` (the state-4 target): **exactly 3 hits** — the
two source branches (`0x40de2 be 0x40e1a` in ENGAGED, `0x40e12 bh 0x40e1a` in HOLDING) and the target label
itself (`0x40e1a: mov 4,r12 / br 0x40e64`). **No other branch in the function reaches 0x40e1a.** This
independently and fully confirms the V34 patch's claimed scope: NOPing exactly these two conditional branches
makes `mov 4,r12` (state-4) permanently unreachable from `FUN_00040d58`, for any param, while leaving the
"stay" fallthrough (`ld.bu -13750[gp],r12` — reads the just-cleared substate marker gp-0x35B6, effectively 0)
intact.

**ENGAGING(1) and RE-ARM(4) confirmed to NOT touch gp-0x6CC4/FUN_000406ae/FUN_00049a5a** (re-verified via full
fresh disasm of 0x40d78–0x40dc4 and 0x40e1e–0x40e62) — matches prior memory. RE-ARM's own tail (0x40e1e
onward) reuses the SAME 3-gate chain as ENGAGING (gp-0x6a60/cal-0xC6310, gp-0x4f68(-20328)/cal-0xC61CE,
gp-0x6ba4(-27556)/cal-0xC61CC) and can additionally return codes 5/6/7 (not previously documented) — these
are ENGAGING/RE-ARM-specific sub-codes, unrelated to the gp-0x6CC4 gate, out of scope for V34.

## State=4 is NEVER persisted to the outer dispatcher state gp-0x67DC [V — important nuance]

Scanned all `FUN_00040d38(n)` commit calls in the 0x40fda–0x41386 cluster: explicit params used are
**0, 1, 2, 3, 5, 6, 7 — never 4.** Every caller's post-decider handling is IDENTICAL for return value 2
(hard sensor-invalid/magnitude disengage) and 4 (consensus-fail leave): `cmp r0,r10; be <stay-path>; else
jarl FUN_00040e74,lp; br <exit>` — the caller code does not distinguish 2 from 4 at this layer. So:
- **State=4 is an ephemeral RETURN CODE, not a persisted FSM state.** It only triggers the one-line substate
  commit `FUN_00040e74` (`gp-0x35B5 = gp-0x35B6`) and immediate function exit; the outer gp-0x67DC dispatcher
  state is left unchanged (still 2 or 3), so the SAME handler re-runs next cycle under the same outer state.
- This is consistent with "gentle EME" being a transient/recoverable per-cycle LKAS torque dropout rather
  than a hard FSM reset — matches the existing HANDOFF characterization (no DTC, LKAS-only cut).
- **Caveat:** whatever consumes `gp-0x35B5` downstream (STEER_STATUS / deliver-flag machinery, per
  `FUN_0003d04c` — still not decompiled) could in principle treat substate values differently based on
  WHICH of {2,4} was committed via gp-0x35B6 before the commit — this was NOT traced. The claim "2 and 4
  look behaviorally identical" is proven only up to the FUN_00040e74 call; downstream differentiation is an
  open question.

## FUN_00040e74 / FUN_00040d38 / FUN_0006b9fa roles — re-verified [V]

- **`FUN_00040e74`** (0x40e74): `ld.bu -13750[gp],r14 / st.b r14,-13749[gp] / jmp[lp]` — literally
  `gp-0x35B5 = gp-0x35B6`, a one-instruction-pair substate commit. **No DTC/fault-latch call of any kind.**
  Re-confirms and supersedes-by-confirming the same claim in `reference_accord_lkas_engage_sm_disengage_trigger.md`.
- **`FUN_00040d38`** (0x40d38): writes param to `gp-0x67DC` (disp -26524) with lockstep shadow `gp-0x4CCB`
  (disp -19509); if the OLD primary/shadow values mismatch BEFORE the write, tail-jumps to `FUN_0006b9fa`
  (`jr`, not `jarl` — genuine tail call). **Only reached when gp-0x67DC is actually written with 0,1,2,3,5,6,
  or 7 — never on a bare state=4 return**, since (per above) state=4 never flows into `FUN_00040d38` at all.
- **`FUN_0006b9fa`** (0x6b9fa): NOT itself a DTC setter. Records the mismatching address's error code into a
  separate lockstep-shadowed byte pair (`gp-0x445F`/`gp-0x4E53`, tail-jumps to `FUN_0006ce7c(4)`), which is a
  GENERIC RAM-corruption/consistency-mismatch recorder shared by dozens of unrelated shadow-pairs throughout
  the firmware (not specific to the engage-SM). Whether this ultimately raises a UDS DTC via the
  `FUN_00016de6`/`0xF00049` chain (documented in `reference_accord_consistency_monitor_hardshutdown.md` for a
  DIFFERENT, torque-corridor-domain monitor) was **not fully traced this session** — open question. Important
  point either way: **this shadow-consistency path is completely UNCHANGED by V34** (V34 only NOPs 2
  instructions inside `FUN_00040d58` itself; none of the lockstep-shadow writer/checker code for gp-0x6CC4,
  gp-0x67DC, etc. is touched), so a genuine RAM bit-flip on the angle-tracking state would still be caught by
  this orthogonal mechanism after V34, independent of whether the plausibility-gate NOP is applied.

## gp-0x67FE (disp -26622) — investigated for mission item 2, RESULT: STRUCTURE CONFIRMED, TRIGGER CONDITION UNCERTAIN [self-corrected mid-session, flagging explicitly]

`gp-0x67FE` is the byte that, when ==2, causes BOTH the ENGAGED handler (0x410c0-0x410ce) and the RE-ARM
handler (0x41164-0x41172) to commit dispatcher STATE=3 (HOLDING) via `FUN_00040d38(3)`. It has 4 writer
sites (0x3bdb8, 0x3be4e, 0x3be5a, 0x3be7a — all clustered inside a FOC-controller mode-dispatch region
0x3bd90–0x3bee0, gated by a mode byte `gp-0x6772`(-26482) and a per-channel counter `gp-0x671D`(-26397) vs
cal `0xC6500`(tp+0x7500, **read as `ld.bu` — single BYTE, value = 3, NOT the 2-byte 771** — caught a misread
of this cal's width mid-session, worth flagging as a live example of the exact kind of error this domain
punishes). **I traced the branch polarity around this counter-vs-cal(3) comparison TWICE with conflicting
conclusions in the same session** (first pass: "counter>=3 sets gp-0x67FE=2, i.e. HOLDING is entered after
~3 cycles of maturity"; second closer pass: "counter>=3 instead SKIPS to a block that CLEARS gp-0x67FE=0, and
gp-0x67FE=2 is set on the fall-through when counter<3, i.e. HOLDING is an early/transient condition") — I did
NOT have budget to fully re-resolve this within the session. **Do not treat either polarity claim as settled.**
**What IS solid:** the mechanism (mode `gp-0x6772` + channel counter `gp-0x671D` + cal 3 gate the ENGAGED→
HOLDING transition trigger byte gp-0x67FE) and the consumption sites (0x410c0/0x41164). What is NOT solid:
which direction the counter-threshold comparison gates, and therefore whether a sustained hands-off turn
finds the SM in ENGAGED or HOLDING at the moment of a gentle-EME event. **Next step to resolve:** re-walk
0x3bd90–0x3bee0 with a byte-level V850 cmp/branch-flag reference table pinned down first (don't rely on
memory of "cmp(A,B) computes B-A" applied under time pressure — verify the flag semantics for `bnh` fresh
against a known-good example before trusting the polarity), or better, a live-RAM capture of gp-0x67FE
alongside gp-0x6CC4 during a real hands-off turn.

## DTC angle-fault category exists but not traced this session [pointer only]

`reference_accord_dtc_construction_mechanism.md`'s fault-descriptor structure notes byte[1] category codes
include **`0x2D` = "angle"** (alongside 0x0C=motor, 0x1C=sensor, 0x3D=init). This suggests a DEDICATED
hard-DTC path for genuine angle-sensor faults may exist, structurally separate from the soft gp-0x6CC4
consensus gate this session focused on — relevant to mission item 4 (is disabling the soft gate redundant
with a hard detector elsewhere). **Not traced this session which fault_id(s) carry category 0x2D or whether
they'd catch the same failure mode as gp-0x6CC4's plausibility check** — flagged as the concrete next hop.

## Related
[[reference-accord-engage-sm-second-gate-gp6cc4]] — original discovery of the gp-0x6CC4/cal-0xC6354 gate.
[[reference-accord-gp6cc4-tracking-pipeline]] — corrected writer count/identity for gp-0x6CC4; its Method
box's JARL formula is corrected above.
[[reference-accord-lkas-engage-sm-disengage-trigger]] — the FIRST gate (gp-0x6a62/cal-0xC6312), V33's target;
this session's fresh full-body disasm of FUN_00040d58 re-confirms all its cal-read addresses exactly.
[[reference-accord-consistency-monitor-hardshutdown]] — the SEPARATE torque-corridor hard-DTC monitor chain
(FUN_00016de6/0xF00049); distinct domain from the angle-tracking shadow-consistency checks noted here.
