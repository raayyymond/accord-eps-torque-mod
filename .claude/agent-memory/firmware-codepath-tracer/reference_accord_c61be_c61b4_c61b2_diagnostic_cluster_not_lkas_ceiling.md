---
name: reference_accord_c61be_c61b4_c61b2_diagnostic_cluster_not_lkas_ceiling
description: "CORRECTED same session: 0xC61BE (=15360, VIRGIN on stock/V106/V107) IS a real, live ceiling on the entire LKAS request via (0xC61BE*gain)>>15 -- confirmed instruction-level (gp-0x3d3c IIR state read back as r9 feeds the gain-multiply at 0x2a1fc) AND cross-validated against reference_accord_c4124_channel_router_two_lanes_lkas_is_slot1 (formula predicts stock max=417, matching an independently-recorded fact) and against fresh values: 0xC61B2/0xC61B4 are 512 on stock but RAISED to 3072 on V106/V107 (6.0x, tracking the gain 1:1) and never bind (~1.23x headroom throughout). gp-0x6b2e/30/32/34/36 remain a genuine diagnostic-only side output of the SAME computation, still 0 external readers -- do not conflate 'diagnostic side-output exists' with 'the whole computation is dead.'"
metadata:
  type: reference
---

# `0xC61BE` IS the live LKAS request ceiling — correction to my own same-session first pass

Traced 2026-08-26 (`ratecap` task). **This file's FIRST version (same session) wrongly called `0xC61BE`
a dead end** — caught and corrected before the operator could act on it, per
[[feedback_audit_your_own_claims_before_others_act_on_them]]. Kept as the durable record; the error and
its fix are both below because the failure mode (checked stock only, missed a build-script-scaled cal)
is worth remembering.

## 1. [EVIDENCE] `0xC61BE`=15360 is VIRGIN, and combines with the gain into a real ceiling

`(cal(0xC61BE) * cal(0xC6CD0 or 0xC646C)) >> 15` — **417 counts on stock** (891 gain), **2505 counts at
the current 6x** (5346 gain). Byte-confirmed this session: `0xC61BE` = 15360 IDENTICAL on stock, V106,
AND V107 — never touched in 102+ builds.

**417 independently matches an ALREADY-RECORDED fact elsewhere in this kit** ("Stock V9's max LKAS
command was 417," from [[reference-accord-c520c-cap-table-axis-provenance]]'s consequences section) —
two unrelated derivations agreeing is strong cross-validation this formula is real, not approximate.

## 2. [EVIDENCE] The instruction-level link, confirmed by connecting two disasm passes from the SAME session

`FUN_00028ea6`, disasm 0x2a13a-0x2a1aa: the `0xC61BE`-clamped quantity feeds a persistent one-pole
blend into `gp-0x3d3c` (`st.w r7,-0x3d3c,gp`@`0x2a1b0`). **Next cycle**, `0x2a178: ld.w -0x3d3c,gp,r9`
reads that state back as `r9` — and **`r9` reappears at `0x2a1fc: add r9,r11`**, exactly where the
gain-multiply-and-clamp block (section 3 of the superseded diagnostic-only draft) computes its input.
So the block's diagnostic writes (`gp-0x6b2e`@0x2a17c / `gp-0x6b32`@0x2a188 / `gp-0x6b34`@0x2a1a2 /
`gp-0x6b36`@0x2a19c, all still confirmed **0 external readers**, `gp-0x6b30` still self-referential-only)
are a genuine SIDE EFFECT of a computation whose PERSISTENT STATE (`gp-0x3d3c`) is live and feeds
forward. **Lesson: "these specific output cells are unread" does not mean "this computation is dead" —
check the function's PERSISTENT STATE for a feed-forward path before concluding a whole block is inert.**

## 3. [EVIDENCE] Full chain from the ceiling to the delivered request

```
FUN_00028ea6 @0x2a1ee: gain_cal(stock 0xC646C=891 / V57+ repointed to 0xC6CD0=5346) * polarity(gp-0x6752)
                        * (gp-0x3d3c-derived sum) >> 15, clamp +/-cal(0xC61B4)   -> gp-0x6b3c @0x2a2ea
                        (sibling gp-0x6b38 is a UDS telemetry mirror only, sole reader FUN_0004e82e)
FUN_0002b422 @0x2b422: reads gp-0x6b3c, clamps +/-cal(0xC61B2), struct[0]=1 (LKAS channel ID),
                        struct[4]=the clamped value, calls FUN_00025c32
FUN_00025c32 @0x25c32: slot=min(struct[0],10); gp-0x62f8[slot] = clamp(struct[4], +/-0x2800)
```
`gp-0x62f8[1]` = "the request," copied by the `0xC4124` router into `gp-0x62b0[1]` (governed lane,
modes 0/3/6, LKAS's actual mode) or `gp-0x62c8[1]` (direct lane) — **either way, `0xC61BE`'s ceiling
bounds the ENTIRE LKAS request before the router even sees it.**

## 4. [EVIDENCE] `0xC61B4`/`0xC61B2` NEVER BIND — confirmed on the actual built images, not just stock

🛑 **My own first-pass error: I read `0xC61B4`=512 from `code.bin` (STOCK) only and reported it as if
that were the built-image value.** Fresh Python LE read this session: **`0xC61B2`/`0xC61B4` are 512 on
stock but `3072` on BOTH V106 and V107** — this kit's build scripts raise them **exactly 6.0x**,
tracking `0xC6CD0`'s gain 1:1 (a calibration CONVENTION, not a runtime computation — confirms the
"tracks the gain 1:1" phrasing in the router memory literally). Ratio to the real ceiling stays ~1.23x
on both stock (512/417) and 6x (3072/2505) — **these two clamps are deliberately sized never to bind;
`0xC61BE` is the actual, load-bearing ceiling.**

## 5. Consequence for the "what caps max steering rate" question

`0xC61BE`'s ceiling (2505 counts at 6x) is **SMALLER than `0xC520C`/`gp-0x4f64`'s own best case (4762,
at rest)** and, unlike that table, **is NOT rate-adaptive** — it does not shrink as commanded/motor rate
climbs. It sits UPSTREAM of the entire chain in
[[reference_accord_governor_final_clamp_and_gp4f64_selftest_writers]] (arb-curve stage, before
`gp-0x6b4c` exists). **Candidate lever, likely a BETTER one than `0xC520C` for a flat rate-ceiling raise**
— virgin, cal-only, zero prior blast radius. **NOT YET DONE:** its own GATE-1 pass (full reader/writer
census beyond what's named above, shadow-lockstep check on `gp-0x3d3c`/`gp-0x6b3c`/`gp-0x62f8`, any
ASIL/fault monitor reading this chain) and an `0xC407E` interaction check. Do not dose without them.

## 6. 🛑🛑 [EVIDENCE + ONE UNRESOLVED LINK] `0xC674E` is NOT a soft convention — it is one arm of a
HISTORICALLY-PROVEN hard-fault INT/FLOAT LOCKSTEP MONITOR. Relationship to `0xC61B2`/`0xC61B4` unresolved.

`BUILD-LINEAGE.md`'s V101/V102 rows cite `0xC674E`=5120 as an "EME audit" ceiling `0xC61B2`/`0xC61B4`
must stay under (3072/4096 at those builds). **Zero hits for "0xC674E" in any `build_v*.py`** — it is
NOT a live Python assertion, only narrative. Chased the firmware: `FUN_00042af8`@`0x43066`
(`ld.h 0x774e,tp,r15`) reads it as one knot of a small LERP feeding **`gp-0x6af6` =
`max(driver-column-torque IIR gp-0x3574, corridor_LERP[cal 0xC674E]) x polarity`** — per
`memory/project/project_accord_torque_mod_v0.md`'s 2026-06-03 V25-V29 saga (already on record in this
kit, not rediscovered here). This is one arm of an **INT-vs-FLOAT LOCKSTEP FAULT MONITOR**
(`FUN_00042af8` Monitor1 + `FUN_00043e44` Monitor2, comparing `gp-0x6af6`/`gp-0x6b00` against a FLOAT
twin `gp-0x6db0`/`gp-0x6db8` at +/-5 LSB tolerance).

**This already bricked a build: V27 was flashed and HARD-FAULTED THE INSTANT THE WHEEL WAS TURNED**,
because it doubled the int wall (`0xC674E`) without doubling its FLOAT MIRROR
(`0xC6598`/`0xC659C`/`0xC65AC`/`0xC65B0`) in lockstep. V29 fixed it by doubling both sides together.

🛑 **UNRESOLVED: is `gp-0x6b3c`/`gp-0x62f8` (the LKAS chain this file traces) code-connected to this
corridor's query variable, or just numerically adjacent by convention?** I did not walk the corridor
LERP's query register (`r8`/`r14` at `FUN_00042af8`:`0x43040-0x43066`) back to its producer — the memory
above suggests it's driver-column-torque/speed-derived, not obviously LKAS-derived, but this is BELIEF,
not confirmed. **Given V27's precedent is an ACTUAL fault from touching one side of this exact family,
do not raise `0xC61B2`/`0xC61B4` (or `0xC61BE` far enough that they'd need to follow) past their current
tracked value without tracing this properly first.** A raise of `0xC61BE` that keeps
`(0xC61BE*gain)>>15` under the CURRENT `0xC61B2`/`0xC61B4`=3072 (i.e. `0xC61BE` up to ~18,832, +22.6%)
needs no change to those clamps and is clean on everything checked.

## Related
[[reference_accord_c4124_channel_router_two_lanes_lkas_is_slot1]] — the 2026-08-22 memory that found
this FIRST and that this session should have grepped before writing a contradicting first draft; its
"417"/"2505"/"never bind" numbers are the ones that turned out right.
[[reference_accord_governor_final_clamp_and_gp4f64_selftest_writers]] — the downstream chain this
ceiling feeds into (governor, final summation, the two self-test writers of `gp-0x4f64`).
[[reference_accord_c520c_empirically_slack_on_route_a6_and_scale_anchor]] — companion finding: unlike
`0xC61BE`, `0xC520C`'s ceiling is measured NOT to bind in practice; this one is flat/not rate-adaptive
so the same argument doesn't apply to it, but its own headroom (417/2505) is real and never-touched.
[[feedback_audit_your_own_claims_before_others_act_on_them]] — why this file exists in corrected form
rather than silently replaced.
