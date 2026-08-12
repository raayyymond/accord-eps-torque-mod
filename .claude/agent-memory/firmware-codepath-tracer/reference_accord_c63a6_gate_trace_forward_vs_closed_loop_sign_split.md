---
name: reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split
description: Full GO/NO-GO trace of 0xC63A6 (gp-0x6b26's Path-2 weight in FUN_00038148) -- NO-GO verdict. Q1 (sole reader) and Q5 (flat scalar, no mode indirection) CLOSED clean. The load-bearing new result is a forward-path/closed-loop SIGN SPLIT that generalizes to all six FUN_00038148 lane weights, not just this one: the open-loop small-signal sign through the sign(x)*f(|x|) LERP stage is analytically determinate (the two sign(iVar6) factors in the chain rule square to +1 and cancel), but Path 2 is a genuine 1kHz closed loop through gp-0x6b98 with an unmeasured loop gain L, and the one sizing precedent for the sibling weight 0xC63A0 shows the plausible L range crosses an inversion boundary.
metadata:
  type: reference
---

# `0xC63A6` GATE trace -- NO-GO, and a reusable forward-path/closed-loop sign split

2026-08-12, `c63a6-gate-trace` task for team-lead, urgent build-blocking trace. Full Q1-Q5 in
`docs/HANDOFF`-equivalent detail sent via SendMessage (not filed as a doc this session -- see the
session transcript / team-lead's copy for the complete writeup). This file carries the durable
technical result.

## Q1/Q5 CLOSED, EVIDENCE, cheap to reuse
`0xC63A6` (`tp+0x73a6`) has **exactly one reader anywhere in the 1MB image**: `ld.hu 0x73a6,tp,r15
@0x381ca` inside `FUN_00038148` (Path 2). Confirmed 3 independent ways: fresh decompile, `search_instructions`
(1 real hit, 1 branch-target false positive excluded), raw Python LE byte scan (disp16 both bit0 parities,
LE32 absolute, movea-lower-half -- the one `0x63A6`-lower-half hit at `0x652aa` is a `jarl` displacement
coincidence in an unrelated diagnostic routine, disassembled and confirmed not a reference).
`get_xrefs_to(0xC63A6)` returned "No references found" -- **another confirmed instance of the tp-relative
xref blind spot**, caught by the required second method. It is a **flat, non-mode-indexed scalar** -- no
per-mode record exists for it at all (contrast the damper FactorC/E families, which ARE mode-indexed) --
so RULE 7's mode-10-vs-TVCA4 trap does not apply to this specific cal.

## Q2: Path 2 is not negligible vs Path 1 (magnitude alone does not decide this)
Path 1 (`FUN_0003aa2c`): `gp-0x6b26` added **unweighted, unity, zero-phase**, gate `|gp-0x6b26|<=1024`
always passes (upstream `0xC407E` clamps it to ±511). Live unconditionally -- `gp-0x67ac` (the branch's
suppression gate) independently reconfirmed CLOSED at 0 this session (cites
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]], not re-derived).

Path 2 (`FUN_00038148`, exact arithmetic, all cal values fresh-read this session):
```
w6b26 = (gp-0x6b26 * gate(raw, ±1024)) * 1024 >> 10      # 0xC63A6=1024 (Q10 unity) -- gate is on the RAW
                                                          #   value, so raising the weight cannot interact
                                                          #   with this gate at all (Q4 finding)
sum6  = w6b4e + w6b4c + w6b26 + w6b46 + w6bd0 + w6bbe
target = ((sum6 * polarity(gp-0x6752) * 2639) >> 10) * 16   # 0xC6468=2639, confirmed read_memory
gp-0x374c += ((target - gp-0x374c) * 102) >> 10              # 0xC63AC=102, confirmed; IIR fc~16Hz@1kHz
iVar6 = gp-0x6bfe + gated(gp-0x6bfa,±20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 1024 >> 10)    # 0xC63AE=1024 (unity x-scale), confirmed
            clamped ±8192                                   # 0xC6200=8192, confirmed
```
`gp-0x6bfe` <- `FUN_0003bc20` <- `gp-0x6bfc` <- `FUN_0003b8f6`, whose first input is `gp-0x6b98[n-1]`
(the aggregator's OWN previous-cycle output) -- **Path 2 is a real 1kHz closed digital feedback loop**,
not a feedforward chain (re-confirms [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]
cross-session). `gp-0x6bfa` <- `FUN_00026c80` mixer (LKAS-command domain), confirmed by fresh
`search_instructions`.

## Q3: THE REUSABLE RESULT -- forward-path sign is determinate, closed-loop sign is not

**Forward-path (open-loop) small-signal sign, NEW derivation, EVIDENCE from decompiled arithmetic +
2 stated assumptions:**
`gp-0x6b70 = sign(x)*f(|x|)` where `x = iVar6`. This construction is the natural odd continuation of
`f`, so for `x != 0`, `d[sign(x)*f(|x|)]/dx = f'(|x|)` **regardless of sign(x)** -- the two `sign(iVar6)`
factors that appear in the chain rule (one from `d|x|/dx`, one from re-applying the sign on the output)
square to +1 and cancel exactly. This means the sign-of-the-residual ambiguity that looked like it should
block the analysis actually drops out algebraically, IF `f` is monotone non-decreasing (`f'>=0`, plausible
for a calibration LERP, not independently confirmed -- the RAM table's actual shape is still
unreverse-engineered, see below).

Combined with `FUN_00037fe6` (fresh decompile this session -- **corrects the prior session's "unity
weight" shorthand to its exact form**): `gp-0x6b70`'s weight into the composite feeding `gp-0x6ad6` is
`(byte)*(tp+0x74b0)`, confirmed by `read_memory` = **1** (so "unity" was right, just not because there's
no cal -- there IS one, it happens to read 1), added **without negation** (unlike the sibling term-0,
`gp-0x6b4a`, which IS negated -- `FUN_00037fe6`, fresh decompile, `iVar4 = -gp-0x6b4a` for term 0 vs
plain `+= gp-0x6b70*1` for term 7). Also newly re-confirmed this session: `gp-0x67ab` (`FUN_00037fe6`'s
gate on the whole 7-lane composite including `gp-0x6b70`) is the CLOSED-at-0 twin of `gp-0x67ac`, per
[[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]] -- so Path 2's whole contribution
to `gp-0x6ad6` is unconditionally live, never gated off.

Chaining through the established PID sign convention (`err = gp-0x4f60 - gp-0x6ad6`, `gp-0x6752` polarity
boot-static +1, aggregator ADD -- **all three inherited from prior memory, not re-verified this session**):
`d(aggregator via Path2)/d(0xC63A6)` works out to **`+sign(gp-0x6b26)`** -- i.e. raising `0xC63A6`
REINFORCES Path 1's already-measured-dissipative delivery of `gp-0x6b26` at the open-loop level, under the
stated assumptions.

**But this is the OPEN-LOOP answer, and Path 2 closes on itself.** The true closed-loop transfer function
depends on a loop gain `L` (`FUN_0003b8f6`'s float EMA cascade -- 8 coefficients at `tp+0x50d4`,
`0x50d8`, `0x504c`, `0x5050`, `0x50bc`, `0x50d0`, `0x50d2`, `0x50d6` -- **never byte-read by any session,
including this one**, given the RAM LERP populator below already consumed the available time budget)
crossed with the LERP's actual local slope `f'`. **The one sizing precedent for the structurally
identical sibling weight `0xC63A0`** ([[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]])
found its own swept estimate crossing an inversion boundary between W=1024 (0.59/0.56, damper weakened,
not inverted) and W=2048 (1.18/1.12, damper INVERTED) at both 7.79Hz and 21Hz -- but that memory itself
flags this as **"the prior session's central sweep estimate, NOT independently pinned"**, i.e. BELIEF,
not a measurement, because `f'` and `L` were never measured, only swept as a bound. Nothing distinguishes
`0xC63A6` from that precedent -- same `sum6`, same `2639` gain, same IIR, same LERP, same clamp, same PID.

**Attempted to close `f`'s shape this session**: fresh decompile of `FUN_000389ec` (the RAM LERP
populator, task 5). It is a genuinely dense per-vehicle normalization/median-of-3/shadow-lockstep state
machine (200+ lines, dozens of locals) that did **not** yield the table's actual knot values in one pass
-- matches the IDENTICAL assessment from the prior session
([[reference_accord_fun38148_six_weight_v95_candidate_census]]'s Q5, and
[[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]]'s "next step"). Two independent sessions
now agree this function resists a single-pass decompile; treat as a genuinely hard item, not a
not-yet-gotten-to one.

Phase of the IIR alone (fresh computation, `a=102/1024`, `fs=1000Hz`, exact discrete one-pole formula):
**|H|=0.94/0.91/0.88, phase=-18.7/-23.6/-26.8 deg at 6/7.79/9 Hz; |H|=0.68/0.62/0.54/0.48,
phase=-44.0/-47.8/-52.7/-56.2 deg at 18/21/26/31 Hz.** This describes the LINEAR sub-path only and does
not resolve the loop-gain-crossing question above.

## Q4: UNRESOLVED, needs telemetry
`gp-0x6b70` clamps ±8192 (`0xC6200`, confirmed). No build has ever telemetered `gp-0x374c`/`gp-0x6b70`
directly -- the probe exists only as a spec ([[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]]),
never flown. Cannot do a RULE-8 observed-envelope clip check without it. One clean structural note: the
±1024 gate on `gp-0x6b26` inside `FUN_00038148` tests the RAW (pre-weight) value, so raising `0xC63A6`
cannot push that specific gate into clipping -- headroom risk, if any, is entirely downstream and
unmeasured.

## VERDICT: NO-GO
Not because any single question proves danger, but because Q3 -- the one question that actually decides
safety -- cannot be certified, and the kit already has a recent, expensive lesson
([[feedback-reducing-a-gain-is-not-a-safety-class]] / V94) about shipping a direction on `gp-0x6b26`
specifically without a measured closed-loop sign. `0xC63A6` is a second, independent lever on the exact
same underlying signal, sitting in a loop whose gain has never been measured, with a documented precedent
that the plausible range crosses an inversion.

## What would close this for a future build
1. Fly `gp-0x6b70` telemetry per the existing probe spec (piggyback on the V95 instrument build already
   speced in `docs/STATE.md` §A6, which already puts 4 of 6 `FUN_00038148` lanes on the wire).
2. OR decompile `FUN_0003b8f6`'s float cascade + a dedicated `FUN_000389ec`/LERP-table session to get `L`
   and `f'` analytically without a new flight.

## Related
[[reference_accord_fun38148_six_weight_v95_candidate_census]] -- the six-weight census this extends with a
full single-weight GATE-2 trace; its Q5 (sign) is the same open item, now further diagnosed (forward-path
resolved, closed-loop still open) rather than closed.
[[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]] -- the probe spec this verdict recommends
flying.
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]] -- the sibling-weight
precedent and closed-loop topology this trace leans on and reconfirms cross-session.
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] / [[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]]
-- the two gate closures (`gp-0x67ac`, `gp-0x67ab`) this session's Q2/Q3 depend on.
[[feedback-reducing-a-gain-is-not-a-safety-class]] -- the V94 process failure this verdict is explicitly
avoiding a repeat of.

## Reusable beyond this one cal
The forward-path/closed-loop sign split is a property of `FUN_00038148`'s Stage-2 architecture itself, not
specific to `0xC63A6`. It applies identically to `0xC63A0`, `0xC63A2`, `0xC63A4`, `0xC63A8`, `0xC63AA` --
**any** of the six lane weights. The open-loop sign is analytically tractable per-lane (same derivation,
different upstream sign source); the closed-loop verdict for ALL SIX is blocked on the same two unmeasured
quantities (`FUN_0003b8f6`'s cascade, `FUN_000389ec`'s LERP table). Closing those once closes GATE 2 for
the whole family, not just one weight -- worth prioritizing over re-deriving the open-loop half per-lane.
